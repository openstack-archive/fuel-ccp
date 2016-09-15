import fixtures

from fuel_ccp import config


class Config(fixtures.Fixture):
    def _setUp(self):
        self.useFixture(fixtures.MockPatchObject(config, '_REAL_CONF'))
        config.setup_config(None)
        self.conf = config._REAL_CONF
