PATH_RE = r'^(/|((/[\w.-]+)+/?))$'
FILE_PATH_RE = r'^(/|((/[\w.-]+)+))$'
SECRET_PERMISSIONS_RE = r'^(0[0-7]{3})$'
NOT_EMPTY_STRING_RE = r"^\s*\S.*$"

NOT_EMPTY_STRING_SCHEMA = {
    "type": "string",
    "pattern": NOT_EMPTY_STRING_RE
}

NOT_EMPTY_STRING_ARRAY_SCHEMA = {
    "type": "array",
    "minItems": 1,

    "items": NOT_EMPTY_STRING_SCHEMA
}
FILE_ENTRY_SCHEMA = {
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

FILES_SCHEMA = {
    "type": "object",
    "patternProperties": {
        r"^[\w][\w.-]*$": FILE_ENTRY_SCHEMA
    }
}


def validate_components_names(components, components_map):
    """Validate that requested components match existing ones."""
    valid_components = set(components_map.keys())
    invalid_components = components - valid_components
    if invalid_components:
        raise RuntimeError('Following components do not match any '
                           'definitions: %s' % ' '.join(invalid_components))
