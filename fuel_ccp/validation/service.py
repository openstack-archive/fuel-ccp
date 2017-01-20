import copy
from distutils import version
import logging

import fuel_ccp
from fuel_ccp.validation import base as validation_base
import jsonschema


LOG = logging.getLogger(__name__)

PATH_RE = r'^(/|((/[\w.-]+)+/?))$'
FILE_PATH_RE = r'^(/|((/[\w.-]+)+))$'
SECRET_PERMISSIONS_RE = r'^(0[0-7]{3})$'
NOT_EMPTY_STRING_RE = r"^\s*\S.*$"


class ServiceFormatChecker(jsonschema.FormatChecker):
    def __init__(self):
        super(ServiceFormatChecker, self).__init__()
        self.checkers['valid_version'] = (self.valid_version, ())

    def valid_version(self, entry):
        return version.StrictVersion(entry) is not None


NOT_EMPTY_STRING_SCHEMA = {
    "type": "string",
    "pattern": NOT_EMPTY_STRING_RE
}

NOT_EMPTY_STRING_ARRAY_SCHEMA = {
    "type": "array",
    "minItems": 1,

    "items": NOT_EMPTY_STRING_SCHEMA
}

PERMISSION_SCHEMA = {
    "type": "string",
    "pattern": SECRET_PERMISSIONS_RE
}

PATH_SCHEMA = {
    "type": "string",
    "pattern": PATH_RE
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
        "secrets": NOT_EMPTY_STRING_ARRAY_SCHEMA,
        "user": NOT_EMPTY_STRING_SCHEMA
    }
}

SINGLE_COMMAND_SCHEMA = copy.deepcopy(LOCAL_COMMAND_SCHEMA)
SINGLE_COMMAND_SCHEMA["required"] = ["name", "command", "type"]
SINGLE_COMMAND_SCHEMA["properties"]["type"]["enum"] = ["single"]
SINGLE_COMMAND_SCHEMA["properties"]["image"] = NOT_EMPTY_STRING_SCHEMA

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
        "path": PATH_SCHEMA,
        "mount-path": PATH_SCHEMA,
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
        "type": {
            "enum": ["exec"]
        },
        "command": NOT_EMPTY_STRING_SCHEMA,
        "initialDelay": TIMEOUT_SCHEMA,
        "timeout": TIMEOUT_SCHEMA
    }
}

PORT_SCHEMA = {
    "type": "integer",
    "minimum": 1,
    "maximum": 65535
}

PROBE_SCHEMA_HTTP = {
    "type": "object",
    "additionalProperties": False,
    "required": ["path", "type", "port"],

    "properties": {
        "type": {
            "enum": ["httpGet"]
        },
        "port": PORT_SCHEMA,
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

SECRET_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["secret", "path"],
    "properties": {
        "type": NOT_EMPTY_STRING_SCHEMA,
        "data": {
            "type": "object",
            "patternProperties": {
                NOT_EMPTY_STRING_RE: NOT_EMPTY_STRING_SCHEMA
            }
        },
        "secret": {
            "type": "object",
            "additionalProperties": False,
            "required": ["secretName"],
            "properties": {
                "secretName": NOT_EMPTY_STRING_SCHEMA,
                "defaultMode": PERMISSION_SCHEMA,
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["key", "path"],
                        "properties": {
                            "key": NOT_EMPTY_STRING_SCHEMA,
                            "path": PATH_SCHEMA,
                            "mode": PERMISSION_SCHEMA
                        }
                    }
                }
            }
        },
        "path": PATH_SCHEMA
    }
}

SERVICE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["dsl_version", "service"],

    "properties": {
        "dsl_version": {
            "type": "string",
            "format": "valid_version"
        },
        "service": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "containers"],

            "not": {  # strategy needs to be absent for StatefulSet's
                "properties": {
                    "kind": {"enum": ["StatefulSet"]},
                },
                "required": ["kind", "strategy"],
            },

            "properties": {
                "name": NOT_EMPTY_STRING_SCHEMA,
                "ports": {
                    "type": "array",
                    "minItems": 1,

                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["cont"],
                        "properties": {
                            "cont": PORT_SCHEMA,
                            'node': PORT_SCHEMA,
                            "ingress": {
                                "type": "string"
                            }
                        }
                    }
                },
                "annotations": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "pod": {"type": "object"},
                        "service": {"type": "object"},
                    }
                },
                "kind": {
                    "enum": ["Deployment", "DaemonSet", "StatefulSet"]
                },
                "hostNetwork": {
                    "type": "boolean"
                },
                "hostPID": {
                    "type": "boolean"
                },
                "strategy": {
                    "enum": ["RollingUpdate", "Recreate"]
                },
                "antiAffinity": {
                    "enum": [None, "local", "global"]
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
                                    "readiness": {"oneOf": [
                                        NOT_EMPTY_STRING_SCHEMA,
                                        PROBE_SCHEMA,
                                    ]},
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
                            },
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
                        "path": PATH_SCHEMA,
                        "content": NOT_EMPTY_STRING_SCHEMA,
                        "perm": {
                            "type": "string",
                            "pattern": "[0-7]{3,4}"
                        },
                        "user": NOT_EMPTY_STRING_SCHEMA
                    }
                }
            }
        },
        "secrets": {
            "type": "object",
            "patternProperties": {
                NOT_EMPTY_STRING_RE: SECRET_SCHEMA
            }
        }
    }
}


def validate_service_definitions(components_map, components=None):
    if not components:
        components = components_map.keys()
    else:
        validation_base.validate_components_names(components, components_map)

    not_passed_components = set()

    for component in components:
        try:
            jsonschema.validate(components_map[component]["service_content"],
                                SERVICE_SCHEMA,
                                format_checker=ServiceFormatChecker())
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
        LOG.info("Service definitions validation passed successfully")


def validate_service_versions(components_map, components=None):
    if not components:
        components = components_map.keys()
    incompatible_services = []
    parser_version = version.StrictVersion(fuel_ccp.dsl_version)
    for component in components:
        service_version = version.StrictVersion(
            components_map[component]['service_content']['dsl_version'])
        if service_version > parser_version:
            LOG.error('%s: Service version validation failed: service version '
                      '(%s) greater than parser version (%s)',
                      component, str(service_version), str(parser_version))
            incompatible_services.append(component)
            continue

        service_major_version = service_version.version[0]
        parser_major_version = parser_version.version[0]
        if service_major_version != parser_major_version:
            LOG.error("%s: Service version validation failed: major versions "
                      "of service (%s) and parser (%s) are not equal",
                      component, str(service_version), str(parser_version))
            incompatible_services.append(component)

    if incompatible_services:
        raise RuntimeError('The following services have incompatible versions:'
                           ' %s' % ', '.join(incompatible_services))
    else:
        LOG.info('Service versions validation passed successfully')
