DEFAULTS = {
    'images': {
        'namespace': 'ccp',
        'tag': 'latest',
        'base_distro': 'debian',
        'base_tag': 'jessie',
        'maintainer': 'MOS Microservices <mos-microservices@mirantis.com>',
        'image_tags': {},
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
            'image_tags': {
                'type': 'object',
                'additionalProperties': {
                    'type': 'string',
                },
            },
        },
    },
}


def get_tag_for_image(image_name):
    from fuel_ccp import config
    CONF = config._REAL_CONF
    tag = CONF.images.image_tags.get(image_name, CONF.images.tag)
    return tag
