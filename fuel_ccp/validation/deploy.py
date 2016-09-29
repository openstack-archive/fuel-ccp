import re

from fuel_ccp.common import utils
from fuel_ccp import dependencies
from fuel_ccp.validation import service as service_validation


ADL_VERSION_PATTEN = re.compile(service_validation.ADL_VERSION_RE)


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


def validation_service_versions(parser_version, components, components_map):
    matcher = ADL_VERSION_PATTEN.match(parser_version)
    if matcher is None:
        raise RuntimeError("Wrong ADL parser version: " + str(parser_version))

    major_parser_ver = int(matcher.group(1))
    minor_parser_ver = int(matcher.group(2))

    not_passed_components = set()

    for component in components:
        service_def = components_map[component]["service_content"]
        service_version = service_def.get("version")
        if service_version is None:
            continue

        matcher = ADL_VERSION_PATTEN.match(service_version)

        major_service_ver = int(matcher.group(1))
        minor_service_ver = int(matcher.group(2))

        if (major_service_ver != major_parser_ver or
                minor_service_ver > minor_parser_ver):
            not_passed_components.add((component, service_version))

    if not_passed_components:
        incompatible_versions_str = ", ".join(
            "'{}': '{}'".format(component, version)
            for component, version in not_passed_components
        )
        raise RuntimeError(
            "Validation of service versions for {} of {} components is "
            "not passed. Service definition parser version: '{}'. "
            "Incompatible versions: [{}]".format(
                len(not_passed_components), len(components), parser_version,
                incompatible_versions_str
            )
        )
