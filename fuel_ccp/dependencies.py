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

import itertools
import logging

from fuel_ccp.common import utils
from fuel_ccp.validation import base as base_validation

LOG = logging.getLogger(__name__)


def get_service_deps(graph, service):
    visited, stack = set(), [service]
    while stack:
        vertex = stack.pop()
        if vertex not in visited:
            visited.add(vertex)
            stack.extend(graph[vertex] - visited)
    return visited


def get_deps_graph(components_map=None):
    """Returns dependencies map."""
    components_map = components_map or utils.get_deploy_components_info()
    deps_graph = {}
    for service_name, service in components_map.items():
        deps_graph[service_name] = set()
        containers = service['service_content']['service']['containers']
        for cont in containers:
            for cmd in itertools.chain(
                    cont.get('pre', []), [cont.get('daemon', [])],
                    cont.get('post', [])):
                for dep in cmd.get('dependencies', ()):
                    deps_graph[service_name].add(dep.partition("/")[0])
    return deps_graph


def get_deps(components, components_map):
    deps_graph = get_deps_graph(components_map)
    dependencies = set()
    for component in components:
        dependencies.update(get_service_deps(deps_graph, component))
    dependencies.add("etcd")
    return dependencies - set(components)


def show_dep(components):
    components_map = utils.get_deploy_components_info()
    base_validation.validate_components_names(set(components), components_map)

    deps = get_deps(components, components_map)
    print(" ".join(deps))
