DEFAULTS = {
    'kubernetes': {
        'server': '127.0.0.1:8080',
        'namespace': 'ccp',
        'ca_certs': None,
        'key_file': None,
        'cert_file': None,
    },
}

SCHEMA = {
    'kubernetes': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'server': {'type': 'string'},
            'namespace': {'type': 'string'},
            'ca_certs': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'key_file': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'cert_file': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
        },
    },
}
