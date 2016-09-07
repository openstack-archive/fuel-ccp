import fixtures
from oslo_config import cfg

from fuel_ccp import config
from fuel_ccp.config import _yaml


class Config(fixtures.Fixture):
    def _setUp(self):
        self.conf = _yaml.AttrDict()
        config.copy_values_from_oslo(cfg.CONF, self.conf)
        self.useFixture(
            fixtures.MockPatchObject(config, '_REAL_CONF', new=self.conf))
