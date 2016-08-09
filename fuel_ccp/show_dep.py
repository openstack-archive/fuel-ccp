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
import sys

import yaml

from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('repositories', 'fuel_ccp.config.repositories')

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


class Node(object):
    """Reperesents dependency. Service or job."""

    def __init__(self, name, sort, dependencies=[], parent_service=None):
        self.name = name
        self.sort = sort
        if sort not in ['service', 'job']:
            msg = "'sort' attribute must be 'service' or 'job' not \
            '{sort}'".format(sort=sort)
            raise ValueError(msg)

        self.dependencies = dependencies
        self.parent_service = parent_service

        if self.sort == 'job' and self.parent_service is None:
            msg = "'parent_service' attribute for 'job' mustn't be None"
            raise ValueError(msg)

    def is_service(self):
        return self.sort == 'service'


def _get_deps_map():
    """Returns dependencies map."""
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
                    components_map[role_obj['service']['name']] = role_obj

    deps_map = {}
    for service_name, service_map in components_map.items():
        deps_map[service_name] = Node(service_name,
                                      'service',
                                      _parse_service_deps(service_map))
        deps_map.update(_parse_pre_and_post_deps(service_map))

    return deps_map


def _parse_service_deps(service_map):
    """Parses service map and finds dependencies of daemons."""
    dependencies = set()
    for container in service_map['service']['containers']:
        dependencies.update(container['daemon'].get('dependencies', []))
        for pre in container.get('pre', []):
            dependencies.update([pre['name']])
    return list(dependencies)


def _parse_pre_and_post_deps(service_map):
    """Parses service map and finds pres and their dependencies."""
    deps = {}
    for container in service_map['service']['containers']:
        for pre in container.get('pre', []):
            deps[pre['name']] = Node(pre['name'],
                                     'job',
                                     pre.get('dependencies', []),
                                     service_map['service']['name'])

        for post in container.get('post', []):
            post_deps = post.get('dependencies', [])
            post_deps.append(service_map['service']['name'])
            deps[post['name']] = Node(post['name'],
                                      'job',
                                      post_deps,
                                      service_map['service']['name'])
    return deps


def _calculate_service_deps(service_name, deps_map):
    if service_name not in deps_map:
        msg = "Wrong component name '{}'".format(service_name)
        LOG.error(msg)
        sys.exit(1)
    deps = set()
    current_iteration_set = set([deps_map[service_name]])

    while current_iteration_set:
        for dep in current_iteration_set:
            if deps_map[dep.name].is_service() and \
                    dep.name != service_name:
                deps.update([deps_map[dep.name]])
            elif not deps_map[dep.name].is_service() and \
                    dep.parent_service != service_name:
                deps.update([deps_map[dep.parent_service]])

        next_iteration_set = set()
        for dep in current_iteration_set:
            for dependency in deps_map[dep.name].dependencies:
                next_iteration_set.update([deps_map[dependency]])
        current_iteration_set = next_iteration_set

    deps = [dep.name for dep in deps]
    return deps


def show_dep(components):
    deps_map = _get_deps_map()
    deps = set()
    for component in components:
        deps.update(_calculate_service_deps(component, deps_map))
    print(" ".join(deps))
