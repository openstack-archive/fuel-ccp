DEFAULTS = {
    'images': {
        'namespace': 'ccp',
        'tag': 'latest',
        'base_distro': 'debian',
        'base_tag': 'jessie',
        'maintainer': 'MOS Microservices <mos-microservices@mirantis.com>',
    },
}

SCHEMA = {
    'images': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'namespace': {'type': 'string'},
            'tag': {'type': 'string'},
            'base_distro': {'type': 'string'},
            'base_tag': {'type': 'string'},
            'maintainer': {'type': 'string'},
        },
    },
}
