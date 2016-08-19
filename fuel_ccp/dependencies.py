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

import re
import sys

from oslo_config import cfg
from oslo_log import log as logging

from fuel_ccp.common import utils


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


def get_deps_map(components_map=None):
    """Returns dependencies map."""
    components_map = components_map or utils.get_deploy_components_info()

    deps_map = {}
    for service_name, service_map in components_map.items():
        deps_map[service_name] = Node(
            service_name, 'service', _parse_service_deps(
                service_map['service_content']))
        deps_map.update(_parse_pre_and_post_deps(
            service_map['service_content']))

    return deps_map


def _parse_service_deps(service_map):
    """Parses service map and finds dependencies of daemons."""
    dependencies = set()
    for container in service_map['service']['containers']:
        dependencies.update(container['daemon'].get('dependencies', []))
        for pre in container.get('pre', []):
            if pre.get('type', 'local') == 'single':
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
            if post.get('type', 'local') == 'single':
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


def get_deps(components, components_map=None):
    deps_map = get_deps_map(components_map)

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
    result_deps.add('etcd')

    return result_deps - set(components)


def show_dep(components):
    deps = get_deps(components)
    print(" ".join(deps))
