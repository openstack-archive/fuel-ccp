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

import os
import re
import sys

from oslo_config import cfg
from oslo_log import log as logging
import yaml


CONF = cfg.CONF
CONF.import_group('repositories', 'fuel_ccp.config.repositories')

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


class Node(object):
    """Reperesents dependency. Service or job."""

    def __init__(self, name, sort, dependencies=None, job_parent=None):
        self.name = name
        self.sort = sort
        if sort not in ['service', 'job']:
            msg = "'sort' attribute must be 'service' or 'job' not \
            '{sort}'".format(sort=sort)
            raise ValueError(msg)

        self.dependencies = dependencies or []
        self.job_parent = job_parent

        if self.sort == 'job' and self.job_parent is None:
            msg = "'job_parent' attribute for 'job' mustn't be None"
            raise ValueError(msg)

    def is_service(self):
        return self.sort == 'service'


def _get_deps_map():
    """Returns dependencies map."""
    components = CONF.repositories.names
    component_map_list = []

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
                    component_map_list.append(yaml.load(f))

    deps_map = {}
    for service_map in component_map_list:
        service_name = service_map['service']['name']
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
    job_parents = set()
    current_iteration_set = {deps_map[service_name]}

    while current_iteration_set:
        next_iteration_set = set()
        for dep in current_iteration_set:
            if deps_map[dep.name].is_service():
                deps.update([deps_map[dep.name]])
            else:
                job_parents.update([dep.job_parent])

        for dep in current_iteration_set:
            for dependency in deps_map[dep.name].dependencies:
                next_iteration_set.update([deps_map[dependency]])
        current_iteration_set = next_iteration_set

    deps = {dep.name for dep in deps}
    return deps, job_parents


def _get_deps(components):
    deps_map = _get_deps_map()

    result_deps = set()
    for service_name in components:
        deps, job_parents = _calculate_service_deps(service_name, deps_map)
        checked = {service_name}

        while True:
            deps.update(job_parents)
            if not job_parents - checked:
                break
            for parent in job_parents - checked:
                parent_deps, parent_parents = _calculate_service_deps(
                    parent, deps_map)
                deps.update(parent_deps)
                checked.update(job_parents - checked)
                job_parents.update(parent_parents)
        result_deps.update(deps)

    result_deps.update(['etcd'])
    return list(result_deps - set(components))


def show_dep(components):
    deps = _get_deps(components)
    print(" ".join(deps))
