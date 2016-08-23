from concurrent import futures
import contextlib
import json
import os
import re
import shutil
import sys
import tempfile

import docker
import git
from oslo_config import cfg
from oslo_log import log as logging

from fuel_ccp.common import jinja_utils
from fuel_ccp.common import utils


BUILD_TIMEOUT = 2 ** 16  # in seconds

CONF = cfg.CONF
CONF.import_group('builder', 'fuel_ccp.config.builder')
CONF.import_group('images', 'fuel_ccp.config.images')
CONF.import_group('repositories', 'fuel_ccp.config.repositories')
CONF.import_group('registry', 'fuel_ccp.config.registry')

LOG = logging.getLogger(__name__)

_SHUTDOWN = False


def render_dockerfiles(dockerfiles, tmp_dir, config):
    for df_name, df in dockerfiles.items():
        if df['match']:
            path = create_rendered_dockerfile(
                df['path'], df['name'], tmp_dir, config)
            dockerfiles[df_name]['path'] = path


def create_rendered_dockerfile(path, name, tmp_path, config):
    def COPY_repository(project_name, cont_dir):
        tmp_dir = os.path.join(tmp_path, name, project_name)

        git_url = config['sources'].get(project_name, {}).get('git_url')
        if git_url:
            LOG.info('%s: Cloning repository %s', name, git_url)
            repo = git.Repo.clone_from(git_url, tmp_dir)
            ref = config['sources'][project_name]['git_ref']
            LOG.info('%s: Changing reference to %s', name, ref)
            repo.head.reference = repo.commit(ref)
            LOG.info('%s: Repository %s has been cloned', name, git_url)

        source_dir = config['sources'].get(project_name, {}).get('source_dir')
        if source_dir:
            LOG.info('%s: Using local directory %s', name, source_dir)
            shutil.copytree(source_dir, tmp_dir)

        return 'COPY %s %s' % (project_name, cont_dir)

    LOG.info('%s: Rendering dockerfile', name)
    src_dir = os.path.dirname(path)
    dest_dir = os.path.join(tmp_path, name)
    os.makedirs(dest_dir)
    dockerfilename = os.path.join(dest_dir, 'Dockerfile')
    content = jinja_utils.jinja_render(
        path, config['render'], [COPY_repository])
    with open(dockerfilename, 'w') as f:
        f.write(content)

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

    namespace = CONF.images.namespace
    if CONF.builder.push and CONF.registry.address:
        namespace = '%s/%s' % (CONF.registry.address, namespace)

    for root, __, files in os.walk(repository_dir):
        if 'Dockerfile.j2' in files:
            path = os.path.join(root, 'Dockerfile.j2')
        else:
            continue
        name = os.path.basename(os.path.dirname(path))
        dockerfiles[name] = {
            'name': name,
            'full_name': '%s/%s:%s' % (namespace, name, CONF.images.tag),
            'path': path,
            'parent': None,
            'children': [],
            'match': match,
            'build_result': None,
            'push_result': None
        }

    if len(dockerfiles) == 0:
        msg = 'No dockerfile for %s found'
        if CONF.repositories.skip_empty:
            LOG.warn(msg, repository_name)
        else:
            LOG.error(msg, repository_name)
            sys.exit(1)

    return dockerfiles


IMAGE_FULL_NAME_RE = r"((?P<namespace>[\w:\.-]+)/){0,2}" \
                     "(?P<name>[\w_-]+)" \
                     "(:(?P<tag>[\w_\.-]+))?"
IMAGE_FULL_NAME_PATTERN = re.compile(IMAGE_FULL_NAME_RE)
# This regex is needed for matching not yet rendered images
NOT_RENDERED_IMAGE_PATTERN = (r"((?P<namespace>[\w:\.\-}{ ]+)/){0,2}"
                              r"(?P<name>[\w_\-}{ ]+)"
                              r"(:(?P<tag>[\w_\.\-}{ ]+))?")

DOCKER_FILE_FROM_PATTERN = re.compile(
    r"^\s?FROM\s+{}\s?$".format(NOT_RENDERED_IMAGE_PATTERN), re.MULTILINE
)


def find_dependencies(dockerfiles):
    for name, dockerfile in dockerfiles.items():
        with open(dockerfile['path']) as f:
            content = f.read()

        matcher = DOCKER_FILE_FROM_PATTERN.search(content)
        if not matcher:
            raise RuntimeError(
                "FROM clause was not found in dockerfile for image: " + name
            )

        parent_ns = matcher.group("namespace")
        if not parent_ns:
            continue
        parent_name = matcher.group("name")

        dockerfile['parent'] = dockerfiles[parent_name]
        dockerfiles[parent_name]['children'].append(dockerfile)


def build_dockerfile(dc, dockerfile):
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


def process_dockerfile(dockerfile, executor, future_list, ready_images):
    with contextlib.closing(docker.Client(
            timeout=CONF.registry.timeout)) as dc:
        build_dockerfile(dc, dockerfile)
        if CONF.builder.push and CONF.registry.address:
            push_dockerfile(dc, dockerfile)

    for child in dockerfile['children']:
        if child['match'] or (CONF.builder.keep_image_tree_consistency and
                              child['name'] in ready_images):
            submit_dockerfile_processing(child, executor, future_list,
                                         ready_images)


def submit_dockerfile_processing(dockerfile, executor, future_list,
                                 ready_images):
    future_list.append(executor.submit(
        process_dockerfile, dockerfile, executor, future_list, ready_images
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
                matcher = IMAGE_FULL_NAME_PATTERN.match(image["RepoTags"][0])
                if not matcher:
                    continue
                ns = matcher.group("namespace")
                name = matcher.group("name")
                tag = matcher.group("tag")
                if CONF.images.namespace == ns and CONF.images.tag == tag:
                    ready_images.append(name)
    return ready_images


def match_dockerfiles_by_component(dockerfiles, component, ready_images):
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
    cfg = {'render': dict(CONF.images.items())}
    if CONF.registry.address:
        cfg['render']['namespace'] = '%s/%s' % (
            CONF.registry.address, cfg['render']['namespace'])

    global_params = utils.get_global_parameters('versions', 'sources')
    cfg['render'].update(global_params['versions'])
    cfg['sources'] = global_params['sources']

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


def build_components(components=None):
    tmp_dir = tempfile.mkdtemp()

    config = _get_config()
    dockerfiles = {}
    try:
        match = not bool(components)
        for repository_name in CONF.repositories.names:
            dockerfiles.update(
                find_dockerfiles(repository_name, match=match))

        find_dependencies(dockerfiles)

        ready_images = get_ready_image_names()

        if components is not None:
            for component in components:
                match_dockerfiles_by_component(dockerfiles, component,
                                               ready_images)

        render_dockerfiles(dockerfiles, tmp_dir, config)

        with futures.ThreadPoolExecutor(max_workers=CONF.builder.workers) as (
                executor):
            future_list = []
            try:
                for dockerfile in dockerfiles.values():
                    if dockerfile['match'] and (
                            dockerfile['parent'] is None or
                            not dockerfile['parent']['match']):
                        submit_dockerfile_processing(dockerfile, executor,
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
        shutil.rmtree(tmp_dir)
        if not build_succeeded:
            sys.exit(1)
