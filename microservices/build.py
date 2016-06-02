import contextlib
import json
import os
import re
import shutil
import sys
import tempfile
import threading

import docker
from oslo_config import cfg
from oslo_log import log as logging
import six

from microservices.common import jinja_utils


CONF = cfg.CONF
CONF.import_group('builder', 'microservices.config.builder')
CONF.import_group('images', 'microservices.config.images')
CONF.import_group('repositories', 'microservices.config.repositories')

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

    return dockerfilename


def find_dockerfiles(component, tmp_dir, match=True):
    dockerfiles = {}
    component_dir = os.path.join(CONF.repositories.path, component)

    namespace = CONF.images.namespace
    if CONF.builder.push:
        namespace = '%s/%s' % (CONF.builder.registry, namespace)

    for root, __, files in os.walk(component_dir):
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
            LOG.warn(msg, component)
        else:
            LOG.error(msg, component)
            sys.exit(1)

    return dockerfiles


def find_dependencies(dockerfiles):
    for name, dockerfile in dockerfiles.items():
        with open(dockerfile['path']) as f:
            content = f.read()

        parent = content.split(' ')[1].split('\n')[0]
        if CONF.images.namespace not in parent:
            continue
        if '/' in parent:
            parent = parent.split('/')[-1]
        if ':' in parent:
            parent = parent.split(':')[0]

        dockerfile['parent'] = dockerfiles[parent]
        dockerfiles[parent]['children'].append(dockerfile)


def create_initial_queue(dockerfiles):
    queue = six.moves.queue.Queue()
    for dockerfile in dockerfiles.values():
        if dockerfile['parent'] is None and dockerfile['match']:
            queue.put(dockerfile)
    return queue


def build_dockerfile(dc, dockerfile):
    for line in dc.build(rm=True,
                         forcerm=True,
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
    if CONF.auth.registry:
        dc.login(username=CONF.auth.registry_username,
                 password=CONF.auth.registry_password,
                 registry=CONF.builder.registry)
    for line in dc.push(dockerfile['full_name'],
                        stream=True,
                        insecure_registry=CONF.builder.insecure_registry):
        build_data = json.loads(line)
        if 'stream' in build_data:
            LOG.info('%s: %s', dockerfile['name'],
                     build_data['stream'].rstrip())
        if 'errorDetail' in build_data:
            LOG.error('%s: %s', dockerfile['name'],
                      build_data['errorDetail']['message'])


def process_dockerfile(queue):
    while True:
        dockerfile = queue.get()

        with contextlib.closing(docker.Client()) as dc:
            build_dockerfile(dc, dockerfile)
            if CONF.builder.push:
                push_dockerfile(dc, dockerfile)

        for child in dockerfile['children']:
            if child['match']:
                queue.put(child)

        queue.task_done()


def find_matched_dockerfiles_ancestors(dockerfile):
    while True:
        parent = dockerfile['parent']
        if parent is None:
            break
        parent['match'] = True
        dockerfile = parent


def match_dockerfiles_by_component(dockerfiles, component):
    pattern = re.compile(re.escape(component))

    for key, dockerfile in dockerfiles.items():
        if not pattern.search(key):
            continue
        dockerfile['match'] = True
        find_matched_dockerfiles_ancestors(dockerfile)


def build_repositories(components=None):
    tmp_dir = tempfile.mkdtemp()

    dockerfiles = {}
    match = not bool(components)
    for component in CONF.repositories.components:
        dockerfiles.update(find_dockerfiles(component, tmp_dir, match=match))

    find_dependencies(dockerfiles)

    if components is not None:
        for component in components:
            match_dockerfiles_by_component(dockerfiles, component)

    # TODO(mrostecki): Try to use multiprocessing there.
    # NOTE(mrostecki): Unfortunately, just using multiprocessing pool
    # with multiprocessing.Queue, while keeping the same logic, doesn't
    # work well with docker-py - each process exits before the image build
    # is done.
    queue = create_initial_queue(dockerfiles)
    threads = [threading.Thread(target=process_dockerfile, args=(queue,))
               for __ in range(CONF.builder.workers)]
    for thread in threads:
        thread.daemon = True
        thread.start()
    queue.join()

    shutil.rmtree(tmp_dir)
