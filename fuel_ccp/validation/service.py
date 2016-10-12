import copy
import logging

from fuel_ccp.validation import base as validation_base
import jsonschema


LOG = logging.getLogger(__name__)


# RegExp for range 0-65535
ALL_PORT_RE = (
    r'0*(?:6553[0-5]|655[0-2][0-9]|65[0-4][0-9]{2}|6[0-4][0-9]{3}|[1-5][0-9]'
    r'{4}|[1-9][0-9]{1,3}|[0-9])'
)
# RegExp for range 30000-32767
HOST_PORT_RE = (
    r'(3[0-1][0-9]{3}|32[0-6][0-9]{2}|327[0-5][0-9]|3276[0-7])'
)

PATH_RE = r'^(/|((/[\w.-]+)+/?))$'
FILE_PATH_RE = r'^(/|((/[\w.-]+)+))$'

NOT_EMPTY_STRING_SCHEMA = {
    "type": "string",
    "pattern": r"^\s*\S.*$"
}

NOT_EMPTY_STRING_ARRAY_SCHEMA = {
    "type": "array",
    "minItems": 1,

    "items": NOT_EMPTY_STRING_SCHEMA
}

LOCAL_COMMAND_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["command"],

    "properties": {
        "name": NOT_EMPTY_STRING_SCHEMA,
        "command": NOT_EMPTY_STRING_SCHEMA,
        "dependencies": NOT_EMPTY_STRING_ARRAY_SCHEMA,
        "type": {
            "enum": ["local"]
        },
        "files": NOT_EMPTY_STRING_ARRAY_SCHEMA,
        "user": NOT_EMPTY_STRING_SCHEMA
    }
}

SINGLE_COMMAND_SCHEMA = copy.deepcopy(LOCAL_COMMAND_SCHEMA)
SINGLE_COMMAND_SCHEMA["required"] = ["name", "command", "type"]
SINGLE_COMMAND_SCHEMA["properties"]["type"]["enum"] = ["single"]

COMMAND_SCHEMA = {
    "type": "object",
    "oneOf": [
        LOCAL_COMMAND_SCHEMA,
        SINGLE_COMMAND_SCHEMA
    ]
}

NOT_EMPTY_COMMAND_ARRAY_SCHEMA = {
    "type": "array",
    "minItems": 1,

    "items": COMMAND_SCHEMA
}

EMPTY_DIR_VOLUME_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "path"],

    "properties": {
        "name": NOT_EMPTY_STRING_SCHEMA,
        "type": {
            "enum": ["empty-dir"]
        },
        "path": {
            "type": "string",
            "pattern": PATH_RE
        },
        "mount-path": {
            "type": "string",
            "pattern": PATH_RE
        },
        "readOnly": {
            "type": "boolean"
        }
    }
}

HOST_VOLUME_SCHEMA = copy.deepcopy(EMPTY_DIR_VOLUME_SCHEMA)
HOST_VOLUME_SCHEMA["required"] = ["name", "path", "type"]
HOST_VOLUME_SCHEMA["properties"]["type"]["enum"] = ["host"]

VOLUME_SCHEMA = {
    "type": "object",
    "oneOf": [
        EMPTY_DIR_VOLUME_SCHEMA,
        HOST_VOLUME_SCHEMA
    ]
}

TIMEOUT_SCHEMA = {
    "type": "integer",
    "minimum": 1,
    "maximum": 360
}

PROBE_SCHEMA_EXEC = {
    "type": "object",
    "additionalProperties": False,
    "required": ["command", "type"],

    "properties": {
        "type": "exec",
        "command": NOT_EMPTY_STRING_SCHEMA,
        "initialDelay": TIMEOUT_SCHEMA,
        "timeout": TIMEOUT_SCHEMA
    }
}

PROBE_SCHEMA_HTTP = {
    "type": "object",
    "additionalProperties": False,
    "required": ["path", "type", "port"],

    "properties": {
        "type": "httpGet",
        "port": {
            "type": "integer"
        },
        "path": NOT_EMPTY_STRING_SCHEMA,
        "initialDelay": TIMEOUT_SCHEMA,
        "timeout": TIMEOUT_SCHEMA
    }
}

PROBE_SCHEMA = {
    "type": "object",
    "oneOf": [
        PROBE_SCHEMA_EXEC,
        PROBE_SCHEMA_HTTP
    ]
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
                        "oneOf": [
                            {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 65535
                            },
                            {
                                "type": "string",
                                "pattern": r"^{}(:{})?$".format(
                                    ALL_PORT_RE, HOST_PORT_RE
                                )
                            }
                        ]
                    }
                },
                "kind": {
                    "enum": ["Deployment", "DaemonSet"]
                },
                "host-net": {
                    "type": "boolean"
                },
                "hostPID": {
                    "type": "boolean"
                },
                "containers": {
                    "type": "array",
                    "minItems": 1,

                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "image", "daemon"],

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
                                    "liveness": PROBE_SCHEMA
                                }
                            },
                            "volumes": {
                                "type": "array",
                                "minItems": 1,

                                "items": VOLUME_SCHEMA
                            },
                            "pre": NOT_EMPTY_COMMAND_ARRAY_SCHEMA,
                            "daemon": LOCAL_COMMAND_SCHEMA,
                            "post": NOT_EMPTY_COMMAND_ARRAY_SCHEMA,
                            "env": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["name"],

                                    "properties": {
                                        "name": NOT_EMPTY_STRING_SCHEMA,
                                        "value": NOT_EMPTY_STRING_SCHEMA,
                                        "valueFrom": {"type": "object"}
                                    }
                                }
                            }
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
                        "path": {
                            "type": "string",
                            "pattern": FILE_PATH_RE
                        },
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


def validate_service_definitions(components_map, components):
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
            LOG.error("Validation of service definitions for component '%s' "
                      "is not passed: '%s'", component, e.message)
            not_passed_components.add(component)

    if not_passed_components:
        raise RuntimeError(
            "Validation of service definitions for {} of {} components is "
            "not passed.".format(len(not_passed_components), len(components))
        )
    else:
        LOG.info(
            "Validation of service definitions for %s components passed "
            "successfully!", len(components)
        )
