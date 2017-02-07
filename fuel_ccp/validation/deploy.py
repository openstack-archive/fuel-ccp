import logging

from fuel_ccp.common import utils
from fuel_ccp import dependencies

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


def validate_nodes_section(nodes, configs):
    valid = True
    if not nodes:
        LOG.error("Nodes section is not specified in configs")
        valid = False
    elif 'configs' in nodes:
        if not isinstance(nodes['configs'], dict):
            LOG.error("Nodes configs should be a dict, found %s" % type(
                nodes['configs']))
            valid = False
        else:
            valid = validate_nodes_config(nodes['configs'], configs)
    return valid


def validate_nodes_config(node_config, global_config):
    for k, v in node_config.items():
        if k not in global_config:
            LOG.error('Nodes configs cannot contain new variables, just '
                      'override existent')
            return False
        elif isinstance(v, dict) and isinstance(global_config[k], dict):
            return validate_nodes_config(v, global_config)
    return True
