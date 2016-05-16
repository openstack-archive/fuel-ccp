from oslo_config import cfg


CONF = cfg.CONF
images_opts = [
    cfg.StrOpt('namespace',
               default='mcp',
               help='Namespace for Docker images'),
    cfg.StrOpt('tag',
               default='latest',
               help='Tag for Docker images'),
    cfg.StrOpt('base_distro',
               default='debian',
               help='Base distribution and image'),
    cfg.StrOpt('base_tag',
               default='jessie',
               help='Tag of the base image'),
    cfg.StrOpt('maintainer',
               default='MOS Microservices <mos-microservices@mirantis.com>'),
    cfg.StrOpt('branch',
               default='master',
               help='Branch to use in OpenStack sources')
]
images_opt_group = cfg.OptGroup(name='images',
                                title='Docker images')
CONF.register_group(images_opt_group)
CONF.register_cli_opts(images_opts, images_opt_group)
CONF.register_opts(images_opts, images_opt_group)
