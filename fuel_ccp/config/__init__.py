import argparse
import logging

import itertools
import jsonschema
import os
from oslo_config import cfg
from oslo_log import _options as log_options
from oslo_log import log
import six

from fuel_ccp.config import _yaml
from fuel_ccp.config import builder
from fuel_ccp.config import cli
from fuel_ccp.config import images
from fuel_ccp.config import kubernetes
from fuel_ccp.config import registry
from fuel_ccp.config import repositories

LOG = logging.getLogger(__name__)

_REAL_CONF = None


def setup_config():
    config_file, args = get_cli_config()
    if config_file is None:
        config_file = find_config()
    log.register_options(cfg.CONF)
    if config_file:
        yconf = _yaml.load_with_includes(config_file)
        set_oslo_defaults(cfg.CONF, yconf)
    # Don't let oslo.config parse any config files
    cfg.CONF(args, project='ccp', default_config_files=[])
    log.setup(cfg.CONF, 'fuel-ccp')
    if config_file:
        LOG.debug('Loaded config from file %s', config_file)
    else:
        LOG.debug('No config file loaded')
        yconf = _yaml.AttrDict()
    copy_values_from_oslo(cfg.CONF, yconf)
    validate_config(yconf)
    global _REAL_CONF
    _REAL_CONF = yconf


def get_cli_config():
    parser = argparse.ArgumentParser(add_help=False)
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


def set_oslo_defaults(oconf, yconf):
    for key, value in six.iteritems(oconf):
        if key == 'action':
            continue
        try:
            yconf_value = yconf[key]
        except KeyError:
            continue
        if isinstance(value, cfg.ConfigOpts.GroupAttr):
            for subkey, subvalue in yconf_value._items():
                oconf.set_default(group=key, name=subkey, default=subvalue)
        else:
            oconf.set_default(group=None, name=key, default=yconf_value)


def copy_values_from_oslo(oconf, yconf):
    for key, value in six.iteritems(oconf):
        if isinstance(value, (cfg.ConfigOpts.GroupAttr,
                              cfg.ConfigOpts.SubCommandAttr)):
            try:
                yconf_value = yconf[key]
            except KeyError:
                yconf_value = yconf[key] = _yaml.AttrDict()
            if isinstance(value, cfg.ConfigOpts.SubCommandAttr):
                yconf_items = set(yconf_value)
                for skey in ['name', 'components', 'dry_run', 'export_dir',
                             'auth_url', 'skip_os_cleanup']:
                    try:
                        svalue = getattr(value, skey)
                    except cfg.NoSuchOptError:
                        continue
                    if skey not in yconf_items or svalue is not None:
                        yconf_value[skey] = svalue
            else:
                yconf_value._update(value)
        else:
            yconf[key] = value


class _Wrapper(object):
    def __getattr__(self, name):
        return getattr(_REAL_CONF, name)

    def __getitem__(self, name):
        return _REAL_CONF[name]

CONF = _Wrapper()


def get_config_schema():
    schema = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'additionalProperties': False,
        'properties': {
            'debug': {'type': 'boolean'},
            'verbose': {'type': 'boolean'},
        },
    }
    for module in [cli, builder, images, kubernetes, registry, repositories]:
        schema['properties'].update(module.SCHEMA)
    # Don't validate all options added from oslo.log and oslo.config
    ignore_opts = ['config_file', 'config_dir']
    for opt in itertools.chain(log_options.logging_cli_opts,
                               log_options.generic_log_opts,
                               log_options.log_opts):
        ignore_opts.append(opt.name.replace('-', '_'))
    for name in ignore_opts:
        schema['properties'][name] = {}
    # Also for now don't validate sections that used to be in deploy config
    for name in ['configs', 'nodes', 'roles', 'sources', 'versions']:
        schema['properties'][name] = {'type': 'object'}
    return schema


def validate_config(yconf=None):
    if yconf is None:
        yconf = _REAL_CONF
    schema = get_config_schema()
    jsonschema.validate(_yaml.UnwrapAttrDict(yconf), schema)
