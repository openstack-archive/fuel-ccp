from oslo_config import cfg


CONF = cfg.CONF


auth_opts = [
    cfg.StrOpt('gerrit-username',
               help='Gerrit username'),
]
auth_opt_group = cfg.OptGroup(name='auth',
                              title='Authentication data')
CONF.register_group(auth_opt_group)
CONF.register_cli_opts(auth_opts, auth_opt_group)
CONF.register_opts(auth_opts, auth_opt_group)
