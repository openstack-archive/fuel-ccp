import io
import jsonschema
import testscenarios

from fuel_ccp import config
from fuel_ccp.config import _yaml
from fuel_ccp.tests import base


class TestConfigSchema(base.TestCase):
    def test_validate_config_schema(self):
        schema = config.get_config_schema()
        jsonschema.Draft4Validator.check_schema(schema)

    def test_validate_default_oslo_conf(self):
        config.validate_config(self.conf)

    def test_validate_default_conf(self):
        config.validate_config(config.get_config_defaults())

    def test_dump_load_validate_default(self):
        conf = config.get_config_defaults()
        if str is bytes:
            stream = io.BytesIO()
        else:
            stream = io.StringIO()
        _yaml.dump(conf, stream)
        new_conf = _yaml.load(stream.getvalue())
        config.validate_config(new_conf)


class TestAttrDict(testscenarios.WithScenarios, base.TestCase):
    scenarios = (
        ('empty_dict',
            {'init_dict': {},
             'value': {},
             'repr': True,
             'res': "AttrDict({})"}),
        ('one_value_dict',
            {'init_dict': {},
             'value': {'foo': True},
             'repr': True,
             'res': "AttrDict({'foo': True})"}),
        ('nested_dict',
            {'init_dict': {},
             'value': {'bar': {'foo': True}},
             'repr': True,
             'res': "AttrDict({'bar': AttrDict({'foo': True})})"}),
        ('nested_nested_dict',
            {'init_dict': {},
             'value': {'baz': {'bar': {'foo': True}}},
             'repr': True,
             'res': "AttrDict({'baz': AttrDict({'bar': "
                    "AttrDict({'foo': True})})})"}),
        ('merge_class',
            {'init_dict': {},
             'value': _yaml.AttrDict({'foo': 'bar'}),
             'repr': True,
             'res': "AttrDict({'foo': 'bar'})"}),
        ('merge_class_same_val',
            {'init_dict': {'foo': True},
             'value': _yaml.AttrDict({'foo': 'bar'}),
             'repr': True,
             'res': "AttrDict({'foo': 'bar'})"}),
        ('merge_dict_same_val',
            {'init_dict': {'foo': True},
             'value': {'foo': 'bar'},
             'repr': True,
             'res': "AttrDict({'foo': 'bar'})"}),
        ('merge_nested_multi',
            {'init_dict': {},
             'value': {'baz': {'bar': {'foo': True}}, 'boom': {'cat': 'no'},
                       'end': 'yes'},
             'repr': False,
             'res': {'baz': {'bar': {'foo': True}},
                     'boom': {'cat': 'no'}, 'end': 'yes'}}),
        ('merge_dict_diff_val',
            {'init_dict': {'baz': True},
             'value': {'foo': 'bar'},
             'repr': False,
             'res': {'baz': True, 'foo': 'bar'}}),
        ('merge_dict_mixed_val',
            {'init_dict': {'baz': True, 'foo': False},
             'value': {'foo': 'bar', 'cat': 'dog'},
             'repr': False,
             'res': {'baz': True, 'cat': 'dog', 'foo': 'bar'}}),
    )

    def test_merge(self):
        cls = _yaml.AttrDict(self.init_dict)
        cls._merge(self.value)
        if self.repr:
            self.assertEqual(self.res, repr(cls))
        else:
            res = _yaml.JSONEncoder(sort_keys=True).encode(self.res)
            self.assertEqual(res, str(cls))
