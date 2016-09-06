from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF


def setup_config():
    log.register_options(CONF)
    CONF(project='ccp')
    log.setup(CONF, 'fuel-ccp')
