import io
import jsonschema
import six

from fuel_ccp import config
from fuel_ccp.config import _yaml
from fuel_ccp.tests import base


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

    def test_dump_load_validate_default(self):
        conf = config.get_config_defaults()
        if str is bytes:
            stream = io.BytesIO()
        else:
            stream = io.StringIO()
        _yaml.dump(conf, stream)
        new_conf = _yaml.load(stream.getvalue())
        config.validate_config(new_conf)
