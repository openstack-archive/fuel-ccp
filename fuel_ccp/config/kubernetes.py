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
        'namespace_limits': None,
    },
}

STRING_OR_NULL = {'anyOf': [{'type': 'string'}, {'type': 'null'}]}

LIMIT_OBJECT_SCHEMA = {
    'type': 'object',
    'required': ['cpu', 'memory'],
    'properties': {
        'cpu': {'type': 'string'},
        'memory': {'type': 'string'}
    }
}

LIMIT_ITEM_POD_SCHEMA = {
    'type': 'object',
    'required': ['min', 'max'],
    'additionalProperties': False,
    'properties': {
        'min': LIMIT_OBJECT_SCHEMA,
        'max': LIMIT_OBJECT_SCHEMA
    }
}

LIMIT_ITEM_CONTAINER_SCHEMA = {
    'type': 'object',
    'required': ['min', 'max', 'default', 'defaultRequest'],
    'additionalProperties': False,
    'properties': {
        'min': LIMIT_OBJECT_SCHEMA,
        'max': LIMIT_OBJECT_SCHEMA,
        'default': LIMIT_OBJECT_SCHEMA,
        'defaultRequest': LIMIT_OBJECT_SCHEMA
    }
}

LIMIT_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'Pod': {'anyOf': [LIMIT_ITEM_POD_SCHEMA, {'type': 'null'}]},
        'Container': {'anyOf': [LIMIT_ITEM_CONTAINER_SCHEMA, {'type': 'null'}]}
    }
}

LIMIT_OR_NULL = {'anyOf': [LIMIT_SCHEMA, {'type': 'null'}]}

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
            'namespace_limits': LIMIT_OR_NULL
        },
    },
}
