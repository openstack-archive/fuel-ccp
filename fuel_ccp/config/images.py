from oslo_config import cfg


CONF = cfg.CONF
images_opts = [
    cfg.StrOpt('namespace',
               default='ccp',
               help='Namespace for Docker images'),
    cfg.StrOpt('tag',
               default='latest',
               help='Tag for Docker images'),
    cfg.StrOpt('base-distro',
               default='debian',
               help='Base distribution and image'),
    cfg.StrOpt('base-tag',
               default='jessie',
               help='Tag of the base image'),
    cfg.StrOpt('maintainer',
               default='MOS Microservices <mos-microservices@mirantis.com>')
]
images_opt_group = cfg.OptGroup(name='images',
                                title='Docker images')
CONF.register_group(images_opt_group)
CONF.register_cli_opts(images_opts, images_opt_group)
CONF.register_opts(images_opts, images_opt_group)

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
