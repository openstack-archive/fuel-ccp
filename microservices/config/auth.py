import getpass
from oslo_config import cfg


CONF = cfg.CONF


auth_opts = [
    cfg.StrOpt('gerrit-username',
               default=getpass.getuser()),
    cfg.BoolOpt('registry',
                default=False,
                help='Login to the Docker registry by user/pass'),
    cfg.StrOpt('registry-username',
               default='',
               help='Username for Docker registry'),
    cfg.StrOpt('registry-password',
               default='',
               help='Password for Docker registry')
]
auth_opt_group = cfg.OptGroup(name='auth',
                              title='Authentication data')
CONF.register_group(auth_opt_group)
CONF.register_cli_opts(auth_opts, auth_opt_group)
CONF.register_opts(auth_opts, auth_opt_group)
