from fuel_ccp.common import utils

from validation import service as service_validation


def validate(components, types):
    if not types:
        types = ["services"]

    for validation_type in set(types):
        if validation_type == "services":
            component_map = utils.get_deploy_components_info()
            service_validation.validate_services(component_map, components)
        else:
            raise RuntimeError(
                "Unexpected validation type: '{}'".format(validation_type)
            )
