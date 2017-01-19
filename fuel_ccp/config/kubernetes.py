DEFAULTS = {
    'kubernetes': {
        'server': 'http://localhost:8080',
        'namespace': 'ccp',
        'ca_cert': None,
        'key_file': None,
        'cert_file': None,
        'insecure': False,
        'username': None,
        'password': None,
        'cluster_domain': 'cluster.local',
        'image_pull_policy': None,
        'external_ips': {},
    },
}

STRING_OR_NULL = {'anyOf': [{'type': 'string'}, {'type': 'null'}]}
STRING_ARRAY = {'type': 'array', 'item': {'type': 'string'}}

SCHEMA = {
    'kubernetes': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'server': {'type': 'string'},
            'namespace': {'type': 'string'},
            'ca_cert': STRING_OR_NULL,
            'key_file': STRING_OR_NULL,
            'cert_file': STRING_OR_NULL,
            'insecure': {'type': 'boolean'},
            'username': STRING_OR_NULL,
            'password': STRING_OR_NULL,
            'cluster_domain': {'type': 'string'},
            'image_pull_policy': {'oneOf': [
                {'type': 'null'},
                {'enum': ['Always', 'IfNotPresent', 'Never']},
            ]},
            'external_ips': {
                'type': 'object',
                'additionalProperties': {
                    'type': 'array',
                    'item': {'type': 'string'},
                },
            },
        },
    },
}
