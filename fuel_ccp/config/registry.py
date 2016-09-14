DEFAULTS = {
    'registry': {
        'address': '',
        'insecure': False,
        'username': '',
        'password': '',
        'timeout': 300,
    },
}

SCHEMA = {
    'registry': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'address': {'type': 'string'},
            'insecure': {'type': 'boolean'},
            'username': {'type': 'string'},
            'password': {'type': 'string'},
            'timeout': {'type': 'integer'},
        },
    },
}
