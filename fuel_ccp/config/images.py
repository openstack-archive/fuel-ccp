DEFAULTS = {
    'images': {
        'namespace': 'ccp',
        'tag': 'latest',
        'base_distro': 'debian',
        'base_tag': 'jessie',
        'maintainer': 'MOS Microservices <mos-microservices@mirantis.com>',
        'image_specs': {},
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
            'image_specs': {
                'type': 'object',
                'additionalProperties': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'tag': {'type': 'string'},
                        'namespace': {'type': 'string'},
                    },
                },
            },
        },
    },
}


def image_spec(image_name, add_address=True):
    from fuel_ccp import config
    CONF = config._REAL_CONF
    spec = {
        'name': image_name,
        'namespace': CONF.images.namespace,
        'tag': CONF.images.tag,
    }
    image_spec = CONF.images.image_specs.get(image_name)
    if image_spec:
        spec.update(image_spec._items())
    spec_str = '{namespace}/{name}:{tag}'.format(**spec)
    if add_address and CONF.registry.address:
        spec_str = '{}/{}'.format(CONF.registry.address, spec_str)
    return spec_str
