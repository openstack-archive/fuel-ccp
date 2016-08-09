"""Show dependencies CCP command.

This module provides logic for execution 'show-dep' command.
This command returns a set of dependencies for specified CCP component.

Usage:
    ccp --config-file=<path_to_config> show-dep <component>

Example:
    The following example command will return set of dependencies for
    heat-api CCP component:
        ccp --config-file=~/ccp.conf show-dep heat-api
"""

import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('repositories', 'fuel_ccp.config.repositories')

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


class Node(object):
    """Reperesents dependency. Service or job."""

    def __init__(self, name, sort, dependencies=[]):
        self.name = name
        self.sort = sort
        if sort not in ['service', 'job']:
            msg = "'sort' attribute must be 'servive' or 'job' not \
            '{sort}'".format(sort=sort)
            raise ValueError(msg)

        self.dependencies = dependencies

    def is_service(self):
        return self.sort == 'service'


def _get_deps_map():
    """Returns dependencies map"""
    components = CONF.repositories.names
    components_map = {}

    for component in components:
        service_dir = os.path.join(CONF.repositories.path,
                                   component,
                                   'service')
        if not os.path.isdir(service_dir):
            continue
        for service_file in os.listdir(service_dir):
            if YAML_FILE_RE.search(service_file):
                LOG.debug("Parse role file: %s", service_file)
                with open(os.path.join(service_dir, service_file), "r") as f:
                    role_obj = yaml.load(f)
                components_map[service_file.split('.')[0]] = role_obj

    deps_map = {}
    for service_name, service_map in components_map.items():
        deps_map[service_name] = Node(service_name,
                                      'service',
                                      _parse_service_deps(service_map))
        deps_map.update(_parse_pres_and_post_deps(service_map))

    return deps_map


def _parse_service_deps(service_map):
    """Parses service map and finds dependencies of daemons."""
    dependencies = set([])
    for container in service_map['service']['containers']:
        dependencies.update(container['daemon'].get('dependencies', []))
        for pre in container.get('pre', []):
            dependencies.update([pre['name']])
    return list(dependencies)


def _parse_pres_and_post_deps(service_map):
    """Parses service map and finds pres and their dependencies."""
    deps = {}
    for container in service_map['service']['containers']:
        for pre in container.get('pre', []):
            deps[pre['name']] = Node(pre['name'],
                                     'job',
                                     pre.get('dependencies', []))

        for post in container.get('post', []):
            deps[post['name']] = Node(post['name'],
                                      'job',
                                      post.get('dependencies', []))
    return deps


def _calculate_service_deps(service_name, deps_map):
    deps = set([])
    current_iteration_set = set([deps_map[service_name]])

    while current_iteration_set:

        for dep in current_iteration_set:
            if deps_map[dep.name].is_service():
                deps.update([deps_map[dep.name]])

        next_iteration_set = set([])

        for dep in current_iteration_set:
            for dependency in deps_map[dep.name].dependencies:
                next_iteration_set.update([deps_map[dependency]])
        current_iteration_set = next_iteration_set

    deps = [dep.name for dep in deps]
    return list(deps)


def show_dep(component_name):
    deps_map = _get_deps_map()
    deps = _calculate_service_deps(component_name, deps_map)
    print(", ".join(deps))
