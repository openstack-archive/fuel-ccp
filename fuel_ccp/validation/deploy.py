from fuel_ccp.common import utils
from fuel_ccp.validation import base as validation_base
from fuel_ccp import dependencies

validate_required_config_sections = validation_base.require_config_sections(
    ['nodes', 'roles']
)


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
