from fuel_ccp.common import utils
from fuel_ccp.config import _yaml
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


def validate_nodes_config(node_config, global_config):
    for k in node_config:
        if k not in global_config:
            LOG.error('Nodes configs cannot contain new variables, just '
                      'override existent')
            raise RuntimeError("Failed to create topology for services")
        elif (isinstance(node_config[k], (dict, _yaml.AttrDict)) and
              isinstance(global_config[k], (dict, _yaml.AttrDict))):
            return validate_nodes_config(node_config[k], global_config[k])


def validate_topology(nodes, roles, k8s_node, configs):
    def find_match(glob):
        matcher = re.compile(glob)
        nodes = []
        for node in k8s_node:
            match = matcher.match(node)
            if match:
                nodes.append(node)
        return nodes
    if not nodes:
        LOG.error("Nodes section is not specified in configs")
        raise RuntimeError("Failed to create topology for services")
    if not roles:
        LOG.error("Roles section is not specified in configs")
        raise RuntimeError("Failed to create topology for services")
    for node in sorted(nodes):
        matched_nodes = find_match(node)
        if not matched_nodes:
            LOG.error("There is no node matched this expression {}"
                      .format(node))
            raise RuntimeError("Failed to create topology for services")
        if 'roles' not in nodes[node]:
            LOG.error("Roles section is not specified for node {}".
                      format(matched_nodes))
            raise RuntimeError("Failed to create topology for services")
        if 'configs' in nodes[node]:
            if not isinstance(nodes[node]['configs'], _yaml.AttrDict):
                LOG.error("Nodes configs should be a dict, found "
                          "%s" % type(nodes[node]['configs']))
                raise RuntimeError("Failed to create topology for services")
            else:
                validate_nodes_config(nodes[node]['configs'], configs)
        for role in nodes[node]['roles']:
            if role not in roles:
                LOG.error("Role {} does not exist".format(role))
                raise RuntimeError("Failed to create topology for services")
