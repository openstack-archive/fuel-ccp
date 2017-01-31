import logging

import jsonschema

from fuel_ccp.validation import base


RESTART_POLICY_ALWAYS = "always"
RESTART_POLICY_NEVER = "never"

ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "image", "command"],
    "properties": {
        "name": base.NOT_EMPTY_STRING_SCHEMA,
        "image": base.NOT_EMPTY_STRING_SCHEMA,
        "command": base.NOT_EMPTY_STRING_SCHEMA,
        "dependencies": base.NOT_EMPTY_STRING_ARRAY_SCHEMA,
        "files": {"type": "array", "items": base.FILE_ENTRY_SCHEMA},
        "restart_policy": {"enum": [RESTART_POLICY_ALWAYS,
                                    RESTART_POLICY_NEVER]}
    }
}

LOG = logging.getLogger(__name__)


def validate_action(data):
    try:
        jsonschema.validate(data, ACTION_SCHEMA)
    except jsonschema.ValidationError as e:
        LOG.error("Validation of action definition {} is not passed: {}".
                  format(data['name'], e.message))
        raise RuntimeError("Validation of action definition {} is not passed".
                           format(data['name']))
