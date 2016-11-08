DEFAULTS = {
    'roles': {}
}

SCHEMA = {
    'roles': {
        'type': 'object',
        'additionalProperties': {
            'type': 'array', 'items': {'type': 'string'}, 'minItems': 1
        }
    }
}
