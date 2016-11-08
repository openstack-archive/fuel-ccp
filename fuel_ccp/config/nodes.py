DEFAULTS = {
    'nodes': {}
}

SCHEMA = {
    'nodes': {
        'type': 'object',
        'additionalProperties': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'roles': {
                    'type': 'array', 'items': {'type': 'string'}, 'minItems': 1
                },
            }, 'required': ['roles'],
        }
    },
}
