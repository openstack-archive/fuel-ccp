import argparse

import os
from oslo_config import cfg
from oslo_log import log
import six
import yaml

CONF = cfg.CONF
CONF.import_group('builder', 'fuel_ccp.config.builder')
CONF.import_opt("action", "fuel_ccp.config.cli")
CONF.import_opt("deploy_config", "fuel_ccp.config.cli")
CONF.import_group('images', 'fuel_ccp.config.images')
CONF.import_group('kubernetes', 'fuel_ccp.config.kubernetes')
CONF.import_group('registry', 'fuel_ccp.config.registry')
CONF.import_group('repositories', 'fuel_ccp.config.repositories')


def setup_config():
    # TODO(yorik-sar): add file lookup in usual places
    config_file, args = get_cli_config()
    log.register_options(CONF)
    if config_file:
        yconf = parse_config(config_file)
        set_oslo_defaults(cfg.CONF, yconf)
    # Don't let oslo.config parse any config files
    CONF(args, project='ccp', default_config_files=[])
    log.setup(CONF, 'fuel-ccp')


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
