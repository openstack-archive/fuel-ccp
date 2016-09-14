import fixtures
import jsonschema
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
        result = config.get_cli_config(self.argv)
        self.assertEqual(result, self.expected_result)


def nested_dict_to_attrdict(d):
    if isinstance(d, dict):
        return _yaml.AttrDict({k: nested_dict_to_attrdict(v)
                               for k, v in six.iteritems(d)})
    elif isinstance(d, list):
        return list(map(nested_dict_to_attrdict, d))
    else:
        return d


class TestConfigSchema(base.TestCase):
    def test_validate_config_schema(self):
        schema = config.get_config_schema()
        jsonschema.Draft4Validator.check_schema(schema)

    def test_validate_default_oslo_conf(self):
        config.validate_config(self.conf)

    def test_validate_default_conf(self):
        config.validate_config(config.get_config_defaults())
