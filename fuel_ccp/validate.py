from fuel_ccp.common import utils

from fuel_ccp.validation import dockerfiles
from fuel_ccp.validation import service as service_validation


def validate(components, types):
    if not types:
        types = ["service-def", "dockerfiles"]

    for validation_type in set(types):
        if validation_type == "service-def":
            component_map = utils.get_deploy_components_info()
            service_validation.validate_service_definitions(component_map,
                                                            components)
        elif validation_type == "dockerfiles":
            component_map = utils.get_deploy_components_info()
            dockerfiles.validate(component_map, components)
        else:
            raise RuntimeError(
                "Unexpected validation type: '{}'".format(validation_type)
            )
