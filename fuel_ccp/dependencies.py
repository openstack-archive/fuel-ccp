"""Show dependencies CCP command.

This module provides logic for execution 'show-dep' command.
This command returns a set of dependencies for specified CCP components.

Usage:
    ccp --config-file=<path_to_config> show-dep <component1> <component2> ...

Example:
    The following example command will return set of dependencies for
    nova-api and nova-compute CCP components:
        ccp --config-file=~/ccp.conf show-dep nova-api nova-compute
"""

import logging
import re
import sys

from fuel_ccp.common import utils
from fuel_ccp.validation import base as base_validation

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


class Node(object):
    """Reperesents dependency. Service or job."""

    TYPES = ['service', 'container', 'job']

    def __init__(self, name, sort, dependencies=None, parent_service=None):
        self.name = name
        self.sort = sort
        self.dependencies = dependencies or []
        self.parent_service = parent_service
        if sort not in Node.TYPES:
            raise ValueError('Node type must be one of: %s'
                             % ','.join(Node.TYPES))
        if sort != 'service' and not parent_service:
            raise ValueError('You need to specify a parent service '
                             'for %s node' % self.sort)

    def is_service(self):
        return self.sort == 'service'


def get_deps_map(components_map=None):
    """Returns dependencies map."""
    components_map = components_map or utils.get_deploy_components_info()

    deps_map = {}
    for service_name, service_map in components_map.items():
        deps_map.update(_parse_service_deps(
            service_name, service_map['service_content']))
        deps_map.update(_parse_pre_and_post_deps(
            service_map['service_content']))

    return deps_map


def _prepare_deps(deps):
    return [dep.partition(":")[0] for dep in deps]


def _parse_service_deps(service_name, service_map):
    """Collect per service and per containers depependencies into dep map"""

    deps_map = {}
    service_dependencies = set()

    for container in service_map['service']['containers']:

        cont_name = container['name']
        cont_deps = _prepare_deps(container['daemon'].get('dependencies', []))
        cont_deps = set(cont_deps)

        for pre in container.get('pre', []):
            if pre.get('type') == 'single':
                cont_deps.update([pre['name']])
            else:
                deps = _prepare_deps(pre.get('dependencies', []))
                cont_deps.update(deps)
        for post in container.get('post', []):
            if post.get('type') != 'single':
                deps = _prepare_deps(post.get('dependencies', []))
                cont_deps.update(deps)

        service_dependencies.update(cont_deps)
        deps_map[cont_name] = Node(cont_name,
                                   sort='container',
                                   parent_service=service_name,
                                   dependencies=list(cont_deps))
    # can overwrite previously defined container dependency with same name
    deps_map[service_name] = Node(service_name,
                                  sort='service',
                                  dependencies=list(service_dependencies))
    return deps_map


def _parse_pre_and_post_deps(service_map):
    """Parses service map and finds pres and their dependencies."""
    deps = {}
    for container in service_map['service']['containers']:
        for pre in container.get('pre', []):
            pre_deps = _prepare_deps(pre.get('dependencies', []))
            deps[pre['name']] = Node(pre['name'],
                                     'job',
                                     pre_deps,
                                     service_map['service']['name'])

        for post in container.get('post', []):
            if post.get('type') == 'single':
                post_deps = _prepare_deps(post.get('dependencies', []))
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
    parent_services = set()
    current_iteration_set = {deps_map[service_name]}

    while current_iteration_set:
        next_iteration_set = set()
        for dep in current_iteration_set:
            if deps_map[dep.name].is_service():
                deps.update([deps_map[dep.name]])
            else:
                parent_services.update([dep.parent_service])

        for dep in current_iteration_set:
            for dependency in deps_map[dep.name].dependencies:
                next_iteration_set.update([deps_map[dependency]])
        current_iteration_set = next_iteration_set

    deps = {dep.name for dep in deps}
    return deps, parent_services


def get_deps(components, components_map=None):
    deps_map = get_deps_map(components_map)
    result_deps = set()
    for service_name in components:
        deps, parent_services = _calculate_service_deps(service_name, deps_map)
        checked = {service_name}

        while True:
            deps.update(parent_services)
            if not parent_services - checked:
                break
            for parent in parent_services - checked:
                parent_deps, parent_parents = _calculate_service_deps(
                    parent, deps_map)
                deps.update(parent_deps)
                checked.update(parent_services - checked)
                parent_services.update(parent_parents)
        result_deps.update(deps)
    result_deps.add('etcd')

    return result_deps - set(components)


def show_dep(components):
    components_map = utils.get_deploy_components_info()
    base_validation.validate_components_names(set(components), components_map)

    deps = get_deps(components, components_map)
    print(" ".join(deps))
