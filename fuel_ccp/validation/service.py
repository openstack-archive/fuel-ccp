from fuel_ccp.validation import base as validation_base
import jsonschema
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

NOT_EMPTY_STRING_SCHEMA = {
    "type": "string",
    "pattern": r"^\s*\S.*$"
}

NOT_EMPTY_STRING_ARRAY_SCHEMA = {
    "type": "array",
    "minItems": 1,

    "items": NOT_EMPTY_STRING_SCHEMA
}

COMMAND_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["command"],

    "properties": {
        "name": NOT_EMPTY_STRING_SCHEMA,
        "command": NOT_EMPTY_STRING_SCHEMA,
        "dependencies": NOT_EMPTY_STRING_ARRAY_SCHEMA,
        "type": {
            "enum": ["single", "local"]
        },
        "files": NOT_EMPTY_STRING_ARRAY_SCHEMA,
        "user": NOT_EMPTY_STRING_SCHEMA
    }
}

NAMED_COMMAND_SCHEMA = COMMAND_SCHEMA.copy()
NAMED_COMMAND_SCHEMA["required"] = ["name", "command"]

NOT_EMPTY_NAMED_COMMAND_ARRAY_SCHEMA = {
    "type": "array",
    "minItems": 1,

    "items": COMMAND_SCHEMA
}

SERVICE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["service"],

    "properties": {
        "service": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "containers"],

            "properties": {
                "name": NOT_EMPTY_STRING_SCHEMA,
                "ports": {
                    "type": "array",
                    "minItems": 1,

                    "items": {
                        "type": "string",
                        "pattern": r"^[\w]+(:[\w]+)?$"
                    }
                },
                "daemonset": {
                    "type": "boolean"
                },
                "host-net": {
                    "type": "boolean"
                },
                "containers": {
                    "type": "array",
                    "minItems": 1,

                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "image"],

                        "properties": {
                            "name": NOT_EMPTY_STRING_SCHEMA,
                            "image": NOT_EMPTY_STRING_SCHEMA,
                            "privileged": {
                                "type": "boolean"
                            },
                            "probes": {
                                "type": "object",
                                "additionalProperties": False,

                                "properties": {
                                    "readiness": NOT_EMPTY_STRING_SCHEMA,
                                    "liveness": NOT_EMPTY_STRING_SCHEMA
                                }
                            },
                            "volumes": {
                                "type": "array",
                                "minItems": 1,

                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["name"],

                                    "properties": {
                                        "name": NOT_EMPTY_STRING_SCHEMA,
                                        "type": {
                                            "enum": ["host", "empty-dir"]
                                        },
                                        "path": NOT_EMPTY_STRING_SCHEMA,
                                        "mount-path": NOT_EMPTY_STRING_SCHEMA,
                                        "readOnly": {
                                            "type": "boolean"
                                        }
                                    }
                                }
                            },
                            "pre": NOT_EMPTY_NAMED_COMMAND_ARRAY_SCHEMA,
                            "daemon": COMMAND_SCHEMA,
                            "post": NOT_EMPTY_NAMED_COMMAND_ARRAY_SCHEMA
                        }
                    }
                }
            }
        },
        "files": {
            "type": "object",
            "patternProperties": {
                r"^[\w][\w.-]*$": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "content"],

                    "properties": {
                        "path": NOT_EMPTY_STRING_SCHEMA,
                        "content": NOT_EMPTY_STRING_SCHEMA,
                        "perm": {
                            "type": "string",
                            "pattern": "[0-7]{3,4}"
                        },
                        "user": NOT_EMPTY_STRING_SCHEMA
                    }
                }
            }
        }
    }
}


def validate_services(components_map, components):
    if not components:
        components = components_map.keys()
    else:
        validation_base.validate_components_names(components, components_map)

    not_passed_components = set()

    for component in components:
        try:
            jsonschema.validate(components_map[component]["service_content"],
                                SERVICE_SCHEMA)
        except jsonschema.ValidationError as e:
            LOG.error("Validation for component '%s' is not passed: '%s'",
                      component, e.message)
            not_passed_components.add(component)

    if not_passed_components:
        raise RuntimeError(
            "Validation of services for {} of {} components is not passed."
            .format(len(not_passed_components), len(components))
        )
    else:
        LOG.info(
            "Validation of services for %s components passed successfully!",
            len(components)
        )
