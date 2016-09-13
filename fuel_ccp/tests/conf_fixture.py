import fixtures
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_log import log

from fuel_ccp import config
from fuel_ccp.config import _yaml


class Config(fixtures.Fixture):
    def _setUp(self):
        self.useFixture(oslo_fixture.Config())
        log.register_options(cfg.CONF)
        cfg.CONF(['build'], default_config_files=[])
        self.conf = _yaml.AttrDict()
        config.copy_values_from_oslo(cfg.CONF, self.conf)
        self.useFixture(
            fixtures.MockPatchObject(config, '_REAL_CONF', new=self.conf))
