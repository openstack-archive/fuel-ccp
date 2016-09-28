import logging

import jsonschema
import os

from fuel_ccp.config import _yaml
from fuel_ccp.config import builder
from fuel_ccp.config import cli
from fuel_ccp.config import images
from fuel_ccp.config import kubernetes
from fuel_ccp.config import registry
from fuel_ccp.config import replicas
from fuel_ccp.config import repositories

LOG = logging.getLogger(__name__)

_REAL_CONF = None


def setup_config(config_file):
    yconf = get_config_defaults()
    if config_file:
        loaded_conf = _yaml.load_with_includes(config_file)
        yconf._merge(loaded_conf)
    validate_config(yconf)
    global _REAL_CONF
    _REAL_CONF = yconf


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


class _Wrapper(object):
    def __getattr__(self, name):
        return getattr(_REAL_CONF, name)

    def __getitem__(self, name):
        return _REAL_CONF[name]

CONF = _Wrapper()


def get_config_defaults():
    defaults = _yaml.AttrDict({
        'debug': False,
        'verbose_level': 1,
        'log_file': None,
    })
    for name in ['configs', 'nodes', 'roles', 'sources', 'versions']:
        defaults[name] = _yaml.AttrDict()
    for module in [cli, builder, images, kubernetes, registry, replicas,
                   repositories]:
        defaults._merge(module.DEFAULTS)
    return defaults


def get_config_schema():
    schema = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'additionalProperties': False,
        'properties': {
            'debug': {'type': 'boolean'},
            'verbose_level': {'type': 'integer'},
            'log_file': {'anyOf': [{'type': 'null'}, {'type': 'string'}]},
        },
    }
    for module in [cli, builder, images, kubernetes, registry, replicas,
                   repositories]:
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


def load_component_defaults():
    from fuel_ccp.common import utils

    sections = ['versions', 'sources', 'configs', 'nodes', 'roles', 'replicas']
    gp = utils.get_global_parameters(*sections)
    new_config = _yaml.AttrDict()
    new_config._merge(gp)
    global _REAL_CONF
    new_config._merge(_REAL_CONF)
    _REAL_CONF = new_config


def dump_yaml(stream):
    _yaml.dump(_REAL_CONF, stream)
