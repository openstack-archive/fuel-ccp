from fuel_ccp.common import utils
from fuel_ccp import dependencies


def validate_requested_components(components, components_map):
    requested_components = set(components)
    deployed_components = utils.get_deployed_components()
    required_components = dependencies.get_deps(components, components_map)

    already_deployed_components = requested_components & deployed_components
    if already_deployed_components:
        raise RuntimeError('Following components are already deployed: '
                           '%s' % ' '.join(already_deployed_components))

    not_provided_components = (required_components - requested_components -
                               deployed_components)
    if not_provided_components:
        raise RuntimeError('Following components are also required for '
                           'successful deployment: '
                           '%s' % ' '.join(not_provided_components))
