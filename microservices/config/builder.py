import multiprocessing

from oslo_config import cfg


CONF = cfg.CONF
builder_opts = [
    cfg.IntOpt('workers',
               default=multiprocessing.cpu_count(),
               help='Number of workers which build docker images')
]
builder_opt_group = cfg.OptGroup(name='builder',
                                 title='Images builder')
CONF.register_group(builder_opt_group)
CONF.register_cli_opts(builder_opts, builder_opt_group)
CONF.register_opts(builder_opts, builder_opt_group)
