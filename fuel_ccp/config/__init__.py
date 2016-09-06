import argparse

import os
from oslo_config import cfg
from oslo_log import log
import six
import yaml

LOG = log.getLogger(__name__)

CONF = cfg.CONF
CONF.import_group('builder', 'fuel_ccp.config.builder')
CONF.import_opt("action", "fuel_ccp.config.cli")
CONF.import_opt("deploy_config", "fuel_ccp.config.cli")
CONF.import_group('images', 'fuel_ccp.config.images')
CONF.import_group('kubernetes', 'fuel_ccp.config.kubernetes')
CONF.import_group('registry', 'fuel_ccp.config.registry')
CONF.import_group('repositories', 'fuel_ccp.config.repositories')


def setup_config():
    config_file, args = get_cli_config()
    if config_file is None:
        config_file = find_config()
    log.register_options(CONF)
    if config_file:
        yconf = parse_config(config_file)
        set_oslo_defaults(cfg.CONF, yconf)
    # Don't let oslo.config parse any config files
    CONF(args, project='ccp', default_config_files=[])
    log.setup(CONF, 'fuel-ccp')
    if config_file:
        LOG.debug('Loaded config from file %s', config_file)
    else:
        LOG.debug('No config file loaded')


def get_cli_config():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config-file',
        metavar='PATH',
        help=('Path to a config file to use.'))
    args, rest = parser.parse_known_args()
    if args.config_file:
        config_file = os.path.abspath(os.path.expanduser(args.config_file))
    else:
        config_file = None
    return config_file, rest


def find_config():
    home = os.path.expanduser('~')
    candidates = [
        os.path.join(home, '.ccp.yaml'),
        os.path.join(home, '.ccp/ccp.yaml'),
        '/etc/ccp.yaml',
        '/etc/ccp/ccp.yaml',
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    else:
        return None


def parse_config(config_file):
    with open(config_file) as f:
        return yaml.load(f)


def set_oslo_defaults(oconf, yconf):
    for key, value in six.iteritems(oconf):
        if key == 'action':
            continue
        try:
            yconf_value = yconf[key]
        except KeyError:
            continue
        if isinstance(value, cfg.ConfigOpts.GroupAttr):
            for subkey, subvalue in six.iteritems(yconf_value):
                oconf.set_default(group=key, name=subkey, default=subvalue)
        else:
            oconf.set_default(group=None, name=key, default=yconf_value)
