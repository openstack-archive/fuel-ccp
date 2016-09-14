import collections
import functools

import fixtures
import jsonschema
from oslo_config import cfg
import six
import testscenarios

from fuel_ccp import config
from fuel_ccp.config import _yaml
from fuel_ccp.tests import base


class ArgumentParserError(Exception):
    pass


class TestGetCLIConfig(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ('base', {
            'argv': ['--config-file', '/etc/ccp.yaml'],
            'expected_result': ('/etc/ccp.yaml', []),
        }),
        ('missing', {
            'argv': ['--other-arg', 'smth'],
            'expected_result': (None, ['--other-arg', 'smth']),
        }),
        ('with_extra', {
            'argv': ['--config-file', '/etc/ccp.yaml', '--other-arg', 'smth'],
            'expected_result': ('/etc/ccp.yaml', ['--other-arg', 'smth']),
        }),
    ]

    argv = None
    expected_result = None

    def test_get_cli_config(self):
        self.useFixture(fixtures.MockPatch(
            'argparse.ArgumentParser.error', side_effect=ArgumentParserError))
        new_argv = ['ccp'] + self.argv
        self.useFixture(fixtures.MockPatch('sys.argv', new=new_argv))
        result = config.get_cli_config()
        self.assertEqual(result, self.expected_result)


def nested_dict_to_attrdict(d):
    if isinstance(d, dict):
        return _yaml.AttrDict({k: nested_dict_to_attrdict(v)
                               for k, v in six.iteritems(d)})
    elif isinstance(d, list):
        return list(map(nested_dict_to_attrdict, d))
    else:
        return d


class TestSetOsloDefaults(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ('empty', {'yconf': {}, 'expected_defaults': {}}),
        ('bogus', {'yconf': {'bogus': 1}, 'expected_defaults': {}}),
        ('simple', {
            'yconf': {'debug': False},
            'expected_defaults': {None: {'debug': False}},
        }),
        ('deep', {
            'yconf': {'thegroup': {'count': 42}},
            'expected_defaults': {'thegroup': {'count': 42}},
        }),
    ]

    yconf = None
    expected_defaults = None

    def setUp(self):
        super(TestSetOsloDefaults, self).setUp()
        self.conf = cfg.ConfigOpts()
        self.conf.register_opt(cfg.BoolOpt('debug', default=False))
        self.conf.register_opt(cfg.IntOpt('count'), group='thegroup')

    def get_defaults(self):
        res = collections.defaultdict(
            functools.partial(collections.defaultdict, dict))
        for opt_info, group in self.conf._all_opt_infos():
            try:
                default = opt_info['default']
            except KeyError:
                continue
            if group is not None:
                group = group.name
            res[group][opt_info['opt'].name] = default
        return res

    def test_set_oslo_defaults(self):
        yconf = nested_dict_to_attrdict(self.yconf)
        config.set_oslo_defaults(self.conf, yconf)
        self.assertEqual(self.get_defaults(), self.expected_defaults)


class TestCopyValuesFromOslo(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ('simple', {
            'yconf': {},
            'oconf': {None: {'debug': True}},
            'expected_result': {'debug': True, 'thegroup': {'count': None}},
        }),
        ('overwrite', {
            'yconf': {'debug': False},
            'oconf': {None: {'debug': True}},
            'expected_result': {'debug': True, 'thegroup': {'count': None}},
        }),
        ('deep', {
            'yconf': {'debug': False},
            'oconf': {'thegroup': {'count': 3}},
            'expected_result': {'debug': False, 'thegroup': {'count': 3}},
        }),
        ('deep_overwrite_with_bogus', {
            'yconf': {'thegroup': {'bogus': 'value'}, 'other': 1},
            'oconf': {'thegroup': {'count': 3}},
            'expected_result': {
                'debug': False,
                'thegroup': {'count': 3, 'bogus': 'value'},
                'other': 1,
            },
        }),
    ]

    yconf = None
    oconf = None
    expected_result = None

    def test_copy_values_from_oslo(self):
        conf = cfg.ConfigOpts()
        conf.register_opt(cfg.BoolOpt('debug', default=False))
        conf.register_opt(cfg.IntOpt('count'), group='thegroup')
        for group, values in six.iteritems(self.oconf):
            for key, value in six.iteritems(values):
                conf.set_default(group=group, name=key, default=value)
        yconf = nested_dict_to_attrdict(self.yconf)
        config.copy_values_from_oslo(conf, yconf)
        self.assertEqual(yconf, self.expected_result)


class TestConfigSchema(base.TestCase):
    def test_validate_config_schema(self):
        schema = config.get_config_schema()
        jsonschema.Draft4Validator.check_schema(schema)

    def test_validate_default_oslo_conf(self):
        config.validate_config(self.conf)

    def test_validate_default_conf(self):
        config.validate_config(config.get_config_defaults())
