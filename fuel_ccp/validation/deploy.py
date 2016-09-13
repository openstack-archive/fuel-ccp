from fuel_ccp.common import utils
from fuel_ccp import dependencies


def validate_requested_components(components, components_map):
    """Validate requested components.

    Validate that requested components are not already deployed and all
    required components provided.
    """
    deployed_components = utils.get_deployed_components()
    required_components = dependencies.get_deps(components, components_map)

    not_provided_components = (required_components - components -
                               deployed_components)
    if not_provided_components:
        raise RuntimeError('Following components are also required for '
                           'successful deployment: '
                           '%s' % ' '.join(not_provided_components))
