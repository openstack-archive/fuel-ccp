import io

import fixtures
import testscenarios
from testtools import content

from fuel_ccp import cli
from fuel_ccp import config
from fuel_ccp.tests import base


class SafeCCPApp(cli.CCPApp):
    # Cliff always outputs str
    if str is bytes:
        _io_cls = io.BytesIO
    else:
        _io_cls = io.StringIO

    def __init__(self):
        super(SafeCCPApp, self).__init__(
            stdin=self._io_cls(),
            stdout=self._io_cls(),
            stderr=self._io_cls(),
        )

    def build_option_parser(self, description, version, argparse_kwargs=None):
        # Debug does magic in cliff, we need it always on
        parser = super(SafeCCPApp, self).build_option_parser(
            description, version, argparse_kwargs)
        parser.set_defaults(debug=True, verbosity_level=2)
        return parser

    def get_fuzzy_matches(self, cmd):
        # Turn off guessing, we need exact failures in tests
        return []

    def run(self, argv):
        try:
            exit_code = super(SafeCCPApp, self).run(argv)
        except SystemExit as e:
            exit_code = e.code
        return exit_code


class TestCase(base.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.app = SafeCCPApp()


class TestCLI(TestCase):
    def test_help(self):
        exit_code = self.app.run(["--help"])
        self.assertEqual(exit_code, 0)
        self.assertFalse(self.app.stderr.getvalue())
        self.assertNotIn('Could not', self.app.stdout.getvalue())


class TestParser(testscenarios.WithScenarios, TestCase):
    scenarios = []

    cmd = None
    argv = None

    def setUp(self):
        super(TestParser, self).setUp()
        fixture = fixtures.MockPatch('fuel_ccp.fetch.fetch_repositories')
        self.fetch_mock = self.useFixture(fixture).mock
        self.useFixture(
            fixtures.MockPatch('fuel_ccp.config.load_component_defaults'))

    def _run_app(self):
        exit_code = self.app.run([self.cmd] + self.argv)
        stdout = self.app.stdout.getvalue()
        stderr = self.app.stderr.getvalue()
        self.addDetail('stdout', content.text_content(stdout))
        self.addDetail('stderr', content.text_content(stderr))
        self.assertEqual(exit_code, 0)
        self.assertFalse(stdout)
        self.assertFalse(stderr)


class TestBuild(TestParser):
    cmd = 'build'
    scenarios = [
        ('empty', {'argv': [], 'components': None}),
        ('seq', {'argv': ['-c', '1', '2'], 'components': ['1', '2']}),
        ('sep', {'argv': ['-c', '1', '-c', '2'], 'components': ['2']}),
        ('long', {
            'argv': ['--components', '1', '2'],
            'components': ['1', '2'],
        }),
    ]

    components = None

    def test_parser(self):
        fixture = fixtures.MockPatch('fuel_ccp.build.build_components')
        bc_mock = self.useFixture(fixture).mock
        self._run_app()
        bc_mock.assert_called_once_with(components=self.components)


class TestDeploy(TestParser):
    cmd = 'deploy'
    scenarios = testscenarios.multiply_scenarios(TestBuild.scenarios, [
        ('no_add', {
            'add_argv': [],
            'action_vals': {'dry_run': False, 'export_dir': None}
        }),
        ('dry_run', {
            'add_argv': ['--dry-run'],
            'action_vals': {'dry_run': True, 'export_dir': None}
        }),
        ('dry_run_export_dir', {
            'add_argv': ['--dry-run', '--export-dir', 'test'],
            'action_vals': {'dry_run': True, 'export_dir': 'test'}
        }),
    ])

    add_argv = None
    components = None
    action_vals = None

    def test_parser(self):
        fixture = fixtures.MockPatch('fuel_ccp.deploy.deploy_components')
        dc_mock = self.useFixture(fixture).mock
        fixture = fixtures.MockPatch(
            'fuel_ccp.validation.service.validate_service_definitions')
        self.useFixture(fixture)
        self.useFixture(fixtures.MockPatch(
            'fuel_ccp.common.utils.get_deploy_components_info',
            return_value={}))
        self.useFixture(fixtures.MockPatch(
            'fuel_ccp.validation.service.validate_service_versions'))
        self.argv += self.add_argv
        self._run_app()
        if self.components is None:
            components = None
        else:
            components = set(self.components)
        dc_mock.assert_called_once_with({}, components)
        for k, v in self.action_vals.items():
            self.assertEqual(config.CONF.action[k], v)


class TestFetch(TestParser):
    cmd = 'fetch'
    scenarios = [('empty', {'argv': []})]

    def test_parser(self):
        self._run_app()
        self.fetch_mock.assert_called_once_with()


class TestCleanup(TestParser):
    cmd = 'cleanup'
    scenarios = [
        ('empty', {
            'argv': [],
            'margs': {'auth_url': None, 'skip_os_cleanup': False,
                      'insecure': False},
        }),
        ('auth_url', {
            'argv': ['--auth-url', 'testurl'],
            'margs': {'auth_url': 'testurl', 'skip_os_cleanup': False,
                      'insecure': False},
        }),
        ('auth_url_cleanup', {
            'argv': ['--auth-url', 'testurl', '--skip-os-cleanup'],
            'margs': {'auth_url': 'testurl', 'skip_os_cleanup': True,
                      'insecure': False},
        }),
        ('insecure', {
            'argv': ['--insecure'],
            'margs': {'auth_url': None, 'skip_os_cleanup': False,
                      'insecure': True},
        }),
        ('empty', {
            'argv': ['--ca-cert', '/tmp/ca.crt'],
            'margs': {'auth_url': None, 'skip_os_cleanup': False,
                      'insecure': False, 'ca_cert': '/tmp/ca.crt'},
        }),
    ]

    margs = None

    def test_parser(self):
        fixture = fixtures.MockPatch('fuel_ccp.cleanup.cleanup')
        c_mock = self.useFixture(fixture).mock
        self._run_app()
        insecure = self.margs.pop('insecure', None)
        ca_cert = self.margs.pop('ca_cert', None)
        self.margs['verify'] = ca_cert or not insecure
        c_mock.assert_called_once_with(**self.margs)


class TestShowDep(TestParser):
    cmd = 'show-dep'
    scenarios = [
        ('one', {'argv': ['1'], 'components': ['1']}),
        ('two', {'argv': ['1', '2'], 'components': ['1', '2']}),
    ]

    components = None

    def test_parser(self):
        fixture = fixtures.MockPatch('fuel_ccp.dependencies.show_dep')
        d_mock = self.useFixture(fixture).mock
        self._run_app()
        d_mock.assert_called_once_with(self.components)


class ArgumentParserError(Exception):
    pass


class TestGetConfigFile(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ('base', {
            'argv': ['--config-file', '/etc/ccp.yaml'],
            'expected_result': '/etc/ccp.yaml',
        }),
        ('missing', {
            'argv': ['--other-arg', 'smth'],
            'expected_result': None,
        }),
        ('with_extra', {
            'argv': ['--config-file', '/etc/ccp.yaml', '--other-arg', 'smth'],
            'expected_result': '/etc/ccp.yaml',
        }),
    ]

    argv = None
    expected_result = None

    def test_get_cli_config(self):
        self.useFixture(fixtures.MockPatch(
            'argparse.ArgumentParser.error', side_effect=ArgumentParserError))
        result = cli.CCPApp.get_config_file(self.argv)
        self.assertEqual(result, self.expected_result)
