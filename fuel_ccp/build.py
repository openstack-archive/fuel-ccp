from concurrent import futures
import contextlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile

import docker
import git

from fuel_ccp.common import jinja_utils
from fuel_ccp import config
from fuel_ccp.config import images

BUILD_TIMEOUT = 2 ** 16  # in seconds

CONF = config.CONF

LOG = logging.getLogger(__name__)

_SHUTDOWN = False


def render_dockerfile(path, name, config):
    LOG.debug('%s: Rendering dockerfile', name)
    sources = set()
    parent = []  # Could've been None if we could use nonlocal

    def copy_sources(source_name, cont_dir):
        if source_name not in config['sources']:
            raise ValueError('No such source: %s' % source_name)
        sources.add(source_name)
        return 'COPY %s %s' % (source_name, cont_dir)

    def image_spec(image_name):
        if parent:
            raise RuntimeError('You can use image_spec only once in FROM line')
        parent.append(image_name)
        return images.image_spec(image_name, add_address=CONF.builder.push)

    def render(fname):
        dirname = os.path.dirname(path)
        fpath = os.path.join(dirname, fname)
        if fname.endswith('.j2'):
            oname = fname[:-3]
        else:
            oname = fname + '.rendered'
        opath = os.path.join(dirname, oname)
        content = jinja_utils.jinja_render(fpath, config['render'],
                                           [copy_sources, image_spec, render])
        with open(opath, 'wb') as f:
            f.write(content.encode('utf-8'))

        return oname

    content = jinja_utils.jinja_render(path, config['render'],
                                       [copy_sources, image_spec, render])

    return content, sources, parent[0] if parent else None


def prepare_source(source_name, name, dest_dir, config):
    tmp_dir = os.path.join(dest_dir, source_name)

    git_url = config['sources'].get(source_name, {}).get('git_url')
    source_dir = config['sources'].get(source_name, {}).get('source_dir')

    if git_url:
        ref = config['sources'][source_name]['git_ref']
        LOG.info('%s: Cloning repository "%s, reference %s"', name, git_url,
                 ref)
        git.Repo.clone_from(git_url, tmp_dir, branch=ref, depth=1)
        LOG.info('%s: Repository %s has been cloned', name, git_url)

    if source_dir:
        LOG.info('%s: Using local directory %s', name, source_dir)
        shutil.copytree(source_dir, tmp_dir)


def create_rendered_dockerfile(dockerfile, tmp_path, config):
    src_dir = os.path.dirname(dockerfile['path'])
    dest_dir = os.path.join(tmp_path, dockerfile['name'])
    os.makedirs(dest_dir)
    dockerfilename = os.path.join(dest_dir, 'Dockerfile')
    with open(dockerfilename, 'w') as f:
        f.write(dockerfile['content'])

    for source_name in dockerfile['sources']:
        prepare_source(source_name, dockerfile['name'], dest_dir, config)

    for filename in os.listdir(src_dir):
        if 'Dockerfile' in filename:
            continue
        full_filename = os.path.join(src_dir, filename)
        if os.path.isfile(full_filename):
            shutil.copy(full_filename, dest_dir)
        elif os.path.isdir(full_filename):
            shutil.copytree(full_filename, os.path.join(dest_dir, filename))

    return dockerfilename


def find_dockerfiles(repository_name, match=True):
    dockerfiles = {}
    repository_dir = os.path.join(CONF.repositories.path, repository_name)

    for root, __, files in os.walk(repository_dir):
        if 'Dockerfile.j2' in files:
            path = os.path.join(root, 'Dockerfile.j2')
        else:
            continue
        name = os.path.basename(os.path.dirname(path))
        spec = images.image_spec(name, add_address=CONF.builder.push)
        dockerfiles[name] = {
            'name': name,
            'full_name': spec,
            'path': path,
            'parent': None,
            'children': [],
            'match': match,
            'build_result': None,
            'push_result': None,
            'content': None,
            'sources': None,
        }

    if len(dockerfiles) == 0:
        msg = 'No dockerfile for %s found'
        if CONF.repositories.skip_empty:
            LOG.debug(msg, repository_name)
        else:
            LOG.error(msg, repository_name)
            sys.exit(1)

    return dockerfiles


def render_dockerfiles(dockerfiles, config):
    for dockerfile in dockerfiles.values():
        content, sources, parent = \
            render_dockerfile(dockerfile['path'], dockerfile['name'], config)
        dockerfile['content'] = content
        dockerfile['sources'] = sources
        dockerfile['parent'] = parent


IMAGE_FULL_NAME_RE = r"((?P<namespace>[\w:\.-]+)/){0,2}" \
                     "(?P<name>[\w_-]+)" \
                     "(:(?P<tag>[\w_\.-]+))?"
IMAGE_FULL_NAME_PATTERN = re.compile(IMAGE_FULL_NAME_RE)


def connect_children(dockerfiles):
    for dockerfile in dockerfiles.values():
        parent = dockerfile['parent']
        if parent:
            dockerfiles[parent]['children'].append(dockerfile)
            dockerfile['parent'] = dockerfiles[parent]


def get_dockerfiles(match=False):
    dockerfiles = {}
    for repository_def in CONF.repositories.repos:
        dockerfiles.update(
            find_dockerfiles(repository_def['name'], match=match))
    return dockerfiles


def get_dockerfiles_tree(match=False, config=None):
    if config is None:
        config = _get_config()

    dockerfiles = get_dockerfiles(match)
    render_dockerfiles(dockerfiles, config)
    connect_children(dockerfiles)

    return dockerfiles


def build_dockerfile(dc, dockerfile):
    LOG.info("%s: Starting image build", dockerfile['name'])
    for line in dc.build(rm=True,
                         forcerm=True,
                         nocache=CONF.builder.no_cache,
                         tag=dockerfile['full_name'],
                         path=os.path.dirname(dockerfile['path'])):
        if _SHUTDOWN:
            raise RuntimeError("Building '{}' was interrupted".format(
                dockerfile['name']
            ))
        build_data = json.loads(line.decode("UTF-8"))
        if 'stream' in build_data:
            LOG.debug('%s: %s' % (dockerfile['name'],
                                  build_data['stream'].rstrip()))
        if 'errorDetail' in build_data:
            LOG.error('%s: %s' % (dockerfile['name'],
                                  build_data['errorDetail']['message']))
            dockerfile['build_result'] = 'Failure'
            return
    dockerfile['build_result'] = 'Success'
    LOG.info("%s: Build succeeded", dockerfile['name'])


def push_dockerfile(dc, dockerfile):
    if dockerfile['build_result'] == 'Failure':
        dockerfile['push_result'] = 'Failure'
        LOG.error("%s: Push will be skipped due to build failure",
                  dockerfile['name'])
        return
    if CONF.registry.username and CONF.registry.password:
        dc.login(username=CONF.registry.username,
                 password=CONF.registry.password,
                 registry=CONF.registry.address)
    for line in dc.push(dockerfile['full_name'],
                        stream=True,
                        insecure_registry=CONF.registry.insecure):
        build_data = json.loads(line.decode("UTF-8"))

        status = build_data.get('status', '')

        if status:
            LOG.debug('%s: %s' % (dockerfile['name'], status))
        if build_data.get('progress'):
            LOG.debug('%s: %s' % (
                dockerfile['name'], build_data['progress'].rstrip()))

        if ('Layer already exists' in status and
                not dockerfile['push_result']):
            dockerfile['push_result'] = 'Exists'
        elif 'errorDetail' in build_data:
            LOG.error('%s: %s', dockerfile['name'],
                      build_data['errorDetail']['message'])
            dockerfile['push_result'] = 'Failure'
        elif status == 'Pushed' or 'Mounted from' in status:
            dockerfile['push_result'] = 'Success'
    if dockerfile['push_result'] == 'Success':
        LOG.info("%s: Push into %s registry finished", dockerfile['name'],
                 CONF.registry.address)
    elif dockerfile['push_result'] == 'Exists':
        LOG.info("%s: Already in %s registry", dockerfile['name'],
                 CONF.registry.address)


def process_dockerfile(dockerfile, tmp_dir, config, executor, future_list,
                       ready_images):
    path = create_rendered_dockerfile(dockerfile, tmp_dir, config)
    dockerfile['path'] = path
    with contextlib.closing(docker.Client(
            timeout=CONF.registry.timeout)) as dc:
        build_dockerfile(dc, dockerfile)
        if CONF.builder.push and CONF.registry.address:
            push_dockerfile(dc, dockerfile)

    for child in dockerfile['children']:
        if child['match'] or (CONF.builder.keep_image_tree_consistency and
                              child['name'] in ready_images):
            if dockerfile['build_result'] == 'Failure':
                LOG.error("%s: Build will be skipped due to parent image (%s) "
                          "build failure", child['name'], dockerfile['name'])
                child['build_result'] = 'Failure'
                if CONF.builder.push:
                    child['push_result'] = 'Failure'
            else:
                submit_dockerfile_processing(child, tmp_dir, config, executor,
                                             future_list, ready_images)


def submit_dockerfile_processing(dockerfile, tmp_dir, config, executor,
                                 future_list, ready_images):
    future_list.append(executor.submit(
        process_dockerfile, dockerfile, tmp_dir, config,
        executor, future_list, ready_images
    ))


def match_not_ready_base_dockerfiles(dockerfile, ready_images):
    while True:
        parent = dockerfile['parent']
        if parent is None or parent['match'] or parent['name'] in ready_images:
            break
        parent['match'] = True
        dockerfile = parent


def get_ready_image_names():
    with contextlib.closing(docker.Client(
            timeout=CONF.registry.timeout)) as dc:
        ready_images = []
        for image in dc.images():
            if image["RepoTags"]:
                for repo_tag in image["RepoTags"]:
                    matcher = IMAGE_FULL_NAME_PATTERN.match(repo_tag)
                    if not matcher:
                        continue
                    ns = matcher.group("namespace")
                    name = matcher.group("name")
                    tag = matcher.group("tag")
                    if CONF.images.namespace == ns and CONF.images.tag == tag:
                        ready_images.append(name)
    return ready_images


def match_dockerfiles_by_component(dockerfiles, component, ready_images=()):
    pattern = re.compile(re.escape(component))
    matched_dockerfiles = list(filter(pattern.match, dockerfiles.keys()))
    if matched_dockerfiles:
        LOG.info("Component \"%s\" matches: %s", component,
                 ", ".join(matched_dockerfiles))
    else:
        raise RuntimeError("Component \"%s\" doesn't match any "
                           "dockerfile" % component)
    for dockerfile in matched_dockerfiles:
        dockerfiles[dockerfile]['match'] = True
        if CONF.builder.build_base_images_if_not_exist:
            match_not_ready_base_dockerfiles(
                dockerfiles[dockerfile], ready_images)


def wait_futures(future_list, skip_errors=False):
    while future_list:
        future = future_list[0]
        if future.done():
            future_list.pop(0)
            continue
        try:
            # we need to use timeout because in this case python
            # thread wakes up time to time to check timeout and don't
            # block signal processing
            future.result(timeout=BUILD_TIMEOUT)
        except Exception as ex:
            if skip_errors:
                LOG.error(str(ex))
            else:
                raise


def _get_config():
    cfg = {'render': dict(CONF.images._items())}
    if CONF.registry.address:
        cfg['render']['namespace'] = '%s/%s' % (
            CONF.registry.address, cfg['render']['namespace'])

    cfg['render'].update(CONF.versions._items())
    cfg['render']['url'] = CONF.url
    cfg['sources'] = CONF.sources

    return cfg


def _get_summary(dockerfiles):
    LOG.info('#' * 50)
    LOG.info('Summary:')

    build_succeeded = [d['name'] for d in dockerfiles.values()
                       if d['build_result'] == 'Success']
    if build_succeeded:
        LOG.info('%d image(s) build succeeded: %s' % (
            len(build_succeeded), ', '.join(build_succeeded)))

    build_failed = [d['name'] for d in dockerfiles.values()
                    if d['build_result'] == 'Failure']
    if build_failed:
        LOG.error('%d image(s) build failed: %s' % (
            len(build_failed), ', '.join(build_failed)))

    push_succeeded = [d['name'] for d in dockerfiles.values()
                      if d['push_result'] == 'Success']
    if push_succeeded:
        LOG.info('%d image(s) push succeeded: %s' % (
            len(push_succeeded), ', '.join(push_succeeded)))

    already_pushed = [d['name'] for d in dockerfiles.values()
                      if d['push_result'] == 'Exists']
    if already_pushed:
        LOG.info('%d image(s) already in registry: %s' % (
            len(already_pushed), ', '.join(already_pushed)))

    push_failed = [d['name'] for d in dockerfiles.values()
                   if d['push_result'] == 'Failure']
    if push_failed:
        LOG.error('%d image(s) push failed: %s' % (
            len(push_failed), ', '.join(push_failed)))
    LOG.info('#' * 50)

    if build_failed or push_failed:
        return False
    return True

try:
    TemporaryDirectory = tempfile.TemporaryDirectory
except AttributeError:
    # This is based on TemporaryDirectory class that appeared in Python 3.2
    class TemporaryDirectory(object):
        def __init__(self, **kwargs):
            self.name = tempfile.mkdtemp(**kwargs)

        def __enter__(self):
            return self.name

        def __exit__(self, exc_type, exc_value, tb):
            shutil.rmtree(self.name)


def build_components(components=None):
    with TemporaryDirectory() as tmp_dir:
        config = _get_config()
        match = not bool(components)
        dockerfiles = get_dockerfiles_tree(match, config)

        ready_images = get_ready_image_names()

        if components is not None:
            for component in components:
                match_dockerfiles_by_component(dockerfiles, component,
                                               ready_images)

        with futures.ThreadPoolExecutor(max_workers=CONF.builder.workers) as (
                executor):
            future_list = []
            try:
                for dockerfile in dockerfiles.values():
                    if dockerfile['match'] and (
                            dockerfile['parent'] is None or
                            not dockerfile['parent']['match']):
                        submit_dockerfile_processing(
                            dockerfile, tmp_dir, config, executor,
                            future_list, ready_images)

                wait_futures(future_list)
            except SystemExit:
                global _SHUTDOWN
                _SHUTDOWN = True
                for future in future_list:
                    future.cancel()
                wait_futures(future_list, skip_errors=True)
                raise
            finally:
                build_succeeded = _get_summary(dockerfiles)
                if not build_succeeded:
                    sys.exit(1)
