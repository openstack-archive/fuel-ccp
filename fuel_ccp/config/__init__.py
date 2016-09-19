import argparse
import logging
import sys

import jsonschema
import os

from fuel_ccp.config import _yaml
from fuel_ccp.config import builder
from fuel_ccp.config import cli
from fuel_ccp.config import images
from fuel_ccp.config import kubernetes
from fuel_ccp.config import registry
from fuel_ccp.config import repositories

LOG = logging.getLogger(__name__)

_REAL_CONF = None


def setup_config(args=None):
    if args is None:
        args = sys.argv[1:]
    config_file, args = get_cli_config(args)
    if config_file is None:
        config_file = find_config()
    yconf = get_config_defaults()
    if config_file:
        loaded_conf = _yaml.load_with_includes(config_file)
        yconf._merge(loaded_conf)
    action_dict = parse_args(args)
    yconf._merge({'action': action_dict})
    logging.basicConfig(level=logging.DEBUG)
    if config_file:
        LOG.debug('Loaded config from file %s', config_file)
    else:
        LOG.debug('No config file loaded')
    validate_config(yconf)
    global _REAL_CONF
    _REAL_CONF = yconf


def get_cli_config(args):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--config-file',
        metavar='PATH',
        help=('Path to a config file to use.'))
    args, rest = parser.parse_known_args(args)
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


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--log-file', default=None)
    subparsers = parser.add_subparsers(dest='action')
    cli.add_parsers(subparsers)
    action_dict = vars(parser.parse_args(args))
    action_dict['name'] = action_dict.pop('action')
    for name in ['debug', 'verbose', 'log_file']:
        del action_dict[name]
    return action_dict


class _Wrapper(object):
    def __getattr__(self, name):
        return getattr(_REAL_CONF, name)

    def __getitem__(self, name):
        return _REAL_CONF[name]

CONF = _Wrapper()


def get_config_defaults():
    defaults = _yaml.AttrDict()
    for module in [cli, builder, images, kubernetes, registry, repositories]:
        defaults._merge(module.DEFAULTS)
    return defaults


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
    # Don't validate all options used to be added from oslo.log and oslo.config
    ignore_opts = ['debug', 'verbose', 'log_file']
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
