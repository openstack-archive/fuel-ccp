DEFAULTS = {
}

SCHEMA = {
    'replicas': {
        'type': 'object',
        "additionalProperties": {
            "type": "integer",
            "minimum": 1,
        },
    },
}
