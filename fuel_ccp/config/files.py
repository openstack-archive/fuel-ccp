DEFAULTS = {
    'files': {}
}

SCHEMA = {
    'files': {
        'type': 'object',
        "additionalProperties": {
            "type": "string",
            "minimum": 1,
        },
    },
}
