import contextlib
import json
import os
import sys
import threading

import docker
from oslo_config import cfg
from oslo_log import log as logging
import six


CONF = cfg.CONF
CONF.import_group('builder', 'microservices.config.builder')
CONF.import_group('images', 'microservices.config.images')
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)


def find_dockerfiles(component):
    dockerfiles = {}
    component_dir = os.path.join(CONF.repositories.path, component)
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
        dockerfiles[name] = {
            'name': name,
            'path': path,
            'is_jinja2': is_jinja2,
            'parent': None,
            'children': []
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
        if dockerfile['parent'] is None:
            queue.put(dockerfile)
    return queue


def build_dockerfile(queue):
    dockerfile = queue.get()
    with contextlib.closing(docker.Client()) as dc:
        if dockerfile['is_jinja2']:
            # TODO(mrostecki): Write jinja2 templating functionality.
            pass

        for line in dc.build(fileobj=open(dockerfile['path'], 'r'), rm=True,
                             tag='%s/%s:%s' % (CONF.images.namespace,
                                               dockerfile['name'],
                                               CONF.images.tag)):
            build_data = json.loads(line)
            if 'stream' in build_data:
                LOG.info(build_data['stream'].rstrip())
            if 'errorDetail' in build_data:
                LOG.error(build_data['errorDetail']['message'])
    for child in dockerfile['children']:
        queue.put(child)
    queue.task_done()


def build_repositories(components=None):
    if components is None:
        components = CONF.repositories.components

    dockerfiles = {}
    for component in components:
        dockerfiles.update(find_dockerfiles(component))

    find_dependencies(dockerfiles)
    # TODO(mrostecki): Try to use multiprocessing there.
    # NOTE(mrostecki): Unfortunately, just using multiprocessing pool
    # with multiprocessing.Queue, while keeping the same logic, doesn't
    # work well with docker-py - each process exits before the image build
    # is done.
    queue = create_initial_queue(dockerfiles)
    threads = [threading.Thread(target=build_dockerfile, args=(queue,))
               for __ in range(CONF.builder.workers)]
    for thread in threads:
        thread.daemon = True
        thread.start()
    queue.join()
