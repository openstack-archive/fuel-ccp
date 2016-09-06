from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
CONF.import_group('builder', 'fuel_ccp.config.builder')
CONF.import_opt("action", "fuel_ccp.config.cli")
CONF.import_opt("deploy_config", "fuel_ccp.config.cli")
CONF.import_group('images', 'fuel_ccp.config.images')
CONF.import_group('kubernetes', 'fuel_ccp.config.kubernetes')
CONF.import_group('registry', 'fuel_ccp.config.registry')
CONF.import_group('repositories', 'fuel_ccp.config.repositories')


def setup_config():
    log.register_options(CONF)
    CONF(project='ccp')
    log.setup(CONF, 'fuel-ccp')
