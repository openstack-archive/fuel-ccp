from oslo_config import cfg

CONF = cfg.CONF

registry_opts = [
    cfg.StrOpt('address',
               default='',
               help='Docker registry address (host:port)'),
    cfg.BoolOpt('insecure',
                default=False,
                help='Permit registry access without SSL'),
    cfg.StrOpt('username',
               default='',
               help='Username for Docker registry'),
    cfg.StrOpt('password',
               default='',
               help='Password for Docker registry'),
    cfg.IntOpt('timeout',
               default=300,
               help='Registry request timeout, in seconds')
]
registry_opt_group = cfg.OptGroup(name='registry',
                                  title='Docker registry data')
CONF.register_group(registry_opt_group)
CONF.register_cli_opts(registry_opts, registry_opt_group)
CONF.register_opts(registry_opts, registry_opt_group)

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
