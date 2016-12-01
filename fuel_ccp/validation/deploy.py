from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp import dependencies

CONF = config.CONF


def validate_requested_components(components, components_map):
    """Validate requested components.

    Validate that all components required for successful deployment of
    requested components are provided or already deployed.
    """
    deployed_components = utils.get_deployed_components()
    external_components = set(CONF.external_services.keys())
    required_components = dependencies.get_deps(
        components, components_map) - external_components

    not_provided_components = (required_components - components -
                               deployed_components)
    if not_provided_components:
        raise RuntimeError('Following components are also required for '
                           'successful deployment: '
                           '%s' % ' '.join(not_provided_components))

    both_requested = components & external_components
    if both_requested:
        raise RuntimeError('Following components deployment requested, '
                           'however they are defined as external: %s'
                           % ' '.join(both_requested))
