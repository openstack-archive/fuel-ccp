from concurrent import futures
import contextlib
import json
import os
import re
import shutil
import sys
import tempfile

import docker
from oslo_config import cfg
from oslo_log import log as logging

from microservices.common import jinja_utils


CONF = cfg.CONF
CONF.import_group('builder', 'microservices.config.builder')
CONF.import_group('images', 'microservices.config.images')
CONF.import_group('repositories', 'microservices.config.repositories')
CONF.import_group('registry', 'microservices.config.registry')

LOG = logging.getLogger(__name__)


def create_rendered_dockerfile(path, name, tmp_path):
    content = jinja_utils.jinja_render(path)
    src_dir = os.path.dirname(path)
    dest_dir = os.path.join(tmp_path, name)
    os.makedirs(dest_dir)
    dockerfilename = os.path.join(dest_dir, 'Dockerfile')
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


def find_dockerfiles(repository_name, tmp_dir, match=True):
    dockerfiles = {}
    repository_dir = os.path.join(CONF.repositories.path, repository_name)

    namespace = CONF.images.namespace
    if CONF.builder.push and CONF.registry.address:
        namespace = '%s/%s' % (CONF.registry.address, namespace)

    for root, __, files in os.walk(repository_dir):
        if 'Dockerfile.j2' in files:
            path = os.path.join(root, 'Dockerfile.j2')
            is_jinja2 = True
        elif 'Dockerfile' in files:
            path = os.path.join(root, 'Dockerfile')
            is_jinja2 = False
        else:
            continue
        name = os.path.basename(os.path.dirname(path))
        if is_jinja2:
            path = create_rendered_dockerfile(path, name, tmp_dir)
        dockerfiles[name] = {
            'name': name,
            'full_name': '%s/%s' % (namespace, name),
            'path': path,
            'parent': None,
            'children': [],
            'match': match
        }

    if len(dockerfiles) == 0:
        msg = 'No dockerfile for %s found'
        if CONF.repositories.skip_empty:
            LOG.warn(msg, repository_name)
        else:
            LOG.error(msg, repository_name)
            sys.exit(1)

    return dockerfiles


IMAGE_FULL_NAME_RE = "(([\\w_-]+)\\/)?([\\w_-]+)(:([\\w_.-]+))?"
IMAGE_FULL_NAME_PATTERN = re.compile(IMAGE_FULL_NAME_RE)

DOCKER_FILE_FROM_PATTERN = re.compile(
    "^\\s?FROM\\s+{}\\s?$".format(IMAGE_FULL_NAME_RE), re.MULTILINE
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

        parent_ns, parent_name, parent_tag = matcher.group(2, 3, 5)

        if CONF.images.namespace != parent_ns:
            continue

        dockerfile['parent'] = dockerfiles[parent_name]
        dockerfiles[parent_name]['children'].append(dockerfile)


def build_dockerfile(dc, dockerfile):
    for line in dc.build(rm=True,
                         forcerm=True,
                         nocache=CONF.builder.no_cache,
                         tag=dockerfile['full_name'],
                         path=os.path.dirname(dockerfile['path'])):
        build_data = json.loads(line)
        if 'stream' in build_data:
            LOG.info('%s: %s' % (dockerfile['name'],
                                 build_data['stream'].rstrip()))
        if 'errorDetail' in build_data:
            LOG.error('%s: %s' % (dockerfile['name'],
                                  build_data['errorDetail']['message']))


def push_dockerfile(dc, dockerfile):
    if CONF.registry.username and CONF.registry.password:
        dc.login(username=CONF.registry.username,
                 password=CONF.registry.password,
                 registry=CONF.registry.address)
    for line in dc.push(dockerfile['full_name'],
                        stream=True,
                        insecure_registry=CONF.registry.insecure):
        build_data = json.loads(line)
        if 'stream' in build_data:
            LOG.info('%s: %s', dockerfile['name'],
                     build_data['stream'].rstrip())
        if 'errorDetail' in build_data:
            LOG.error('%s: %s', dockerfile['name'],
                      build_data['errorDetail']['message'])
    LOG.info("%s - Push into %s registry finished", dockerfile['name'],
             CONF.registry.address)


def process_dockerfile(dockerfile, executor, future_list, ready_images):
    with contextlib.closing(docker.Client()) as dc:
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
    with contextlib.closing(docker.Client()) as dc:
        ready_images = []
        for image in dc.images():
            matcher = IMAGE_FULL_NAME_PATTERN.match(image["RepoTags"][0])
            if not matcher:
                continue
            ns, name, tag = matcher.group(2, 3, 5)
            if CONF.images.namespace == ns:
                ready_images.append(name)
    return ready_images


def match_dockerfiles_by_component(dockerfiles, component, ready_images):
    pattern = re.compile(re.escape(component))

    for key, dockerfile in dockerfiles.items():
        if pattern.search(key):
            dockerfile['match'] = True
            if CONF.builder.build_base_images_if_not_exist:
                match_not_ready_base_dockerfiles(dockerfile, ready_images)


def build_components(components=None):
    tmp_dir = tempfile.mkdtemp()

    dockerfiles = {}
    match = not bool(components)
    for repository_name in CONF.repositories.names:
        dockerfiles.update(
            find_dockerfiles(repository_name, tmp_dir, match=match))

    find_dependencies(dockerfiles)

    ready_images = get_ready_image_names()

    if components is not None:
        for component in components:
            match_dockerfiles_by_component(dockerfiles, component,
                                           ready_images)

    with futures.ThreadPoolExecutor(max_workers=CONF.builder.workers) as (
            executor):
        future_list = []
        for dockerfile in dockerfiles.values():
            if dockerfile['match'] and (dockerfile['parent'] is None or
                                        not dockerfile['parent']['match']):
                submit_dockerfile_processing(dockerfile, executor, future_list,
                                             ready_images)

        while future_list:
            future = future_list.pop(0)
            future.result()

    shutil.rmtree(tmp_dir)
