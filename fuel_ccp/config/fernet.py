DEFAULTS = {
    'fernet': {
        'max_active_keys': 3,
        'secret_name': 'fernet-keys',
    },
}

SCHEMA = {
    'fernet': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'max_active_keys': {'type': 'integer'},
            'secret_name': {'type': 'string'},
        },
    },
}
