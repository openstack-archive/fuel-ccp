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
    def find_match(glob):
        matcher = re.compile(glob)
        nodes = []
        for node in k8s_node:
            match = matcher.match(node)
            if match:
                nodes.append(node)
        return nodes
    if not nodes._dict:
        LOG.error("Nodes section is not specified in configs")
        raise RuntimeError("Failed to create topology for services")
    for node in sorted(nodes):
        matched_nodes = find_match(node)
        if not matched_nodes:
            LOG.error("There is no node with name {}".format(node))
            raise RuntimeError("Failed to create topology for services")
        if 'roles' not in nodes[node]:
            LOG.error("Roles section is not specified for node {}".
                      format(matched_nodes))
            raise RuntimeError("Failed to create topology for services")
        for role in nodes[node]['roles']:
            if role not in roles:
                LOG.error("Role {} does not exists".format(role))
                raise RuntimeError("Failed to create topology for services")
