from fuel_ccp.common import utils
from fuel_ccp import dependencies
import logging
import re

LOG = logging.getLogger(__name__)


def validate_requested_components(components, components_map):
    """Validate requested components.

    Validate that all components required for successful deployment of
    requested components are provided or already deployed.
    """
    deployed_components = utils.get_deployed_components()
    required_components = dependencies.get_deps(components, components_map)

    not_provided_components = (required_components - components -
                               deployed_components)
    if not_provided_components:
        raise RuntimeError('Following components are also required for '
                           'successful deployment: '
                           '%s' % ' '.join(not_provided_components))


def validate_topology(nodes, roles, k8s_node):
    failed = False
    if not nodes:
        LOG.error("Nodes section is not specified in configs")
        failed = True
    if not roles:
        LOG.error("Roles section is not specified in configs")
        failed = True
    if failed:
        raise RuntimeError("Failed to create topology for services")

    def find_match(glob):
        matcher = re.compile(glob)
        nodes = []
        for node in k8s_node:
            match = matcher.match(node)
            if match:
                nodes.append(node)
        return nodes

    for node in sorted(nodes):
        matched_nodes = find_match(node)
        if not matched_nodes:
            LOG.error("There is no node with name {}".format(node))
            raise RuntimeError("Failed to create topology for services")
