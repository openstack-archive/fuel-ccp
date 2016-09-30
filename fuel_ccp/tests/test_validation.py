import mock

from fuel_ccp.tests import base
from fuel_ccp.validation import base as base_validation
from fuel_ccp.validation import deploy as deploy_validation
from fuel_ccp.validation import service as service_validation


COMPONENTS_MAP = {
    'service1': {
        'some_field': True
    },
    'service2': {
        'another_field': False
    },
    'service3': {
        'new_field': None
    }
}


class TestBaseValidation(base.TestCase):
    def test_validate_components_names(self):
        # validations succeeded
        base_validation.validate_components_names(
            {'service1'}, COMPONENTS_MAP)

        base_validation.validate_components_names(
            {'service1', 'service2'}, COMPONENTS_MAP)

        # validations failed
        self.assertRaisesRegexp(
            RuntimeError,
            "Following components do not match any definitions: srv3",
            base_validation.validate_components_names,
            {'srv3'}, COMPONENTS_MAP)

        self.assertRaisesRegexp(
            RuntimeError,
            "Following components do not match any definitions: service4",
            base_validation.validate_components_names,
            {'service1', 'service4'}, COMPONENTS_MAP)


class TestDeployValidation(base.TestCase):
    @mock.patch('fuel_ccp.common.utils.get_deployed_components')
    @mock.patch('fuel_ccp.dependencies.get_deps')
    def test_validate_requested_components(self, m_get_deps, m_get_deployed):
        # validations succeeded
        # no dependencies and nothing is deployed
        m_get_deps.return_value = set()
        m_get_deployed.return_value = set()
        deploy_validation.validate_requested_components(
            {'service1', 'service2'}, COMPONENTS_MAP)

        # all dependencies requested
        m_get_deps.return_value = {'service1'}
        m_get_deployed.return_value = set()
        deploy_validation.validate_requested_components(
            {'service1', 'service2'}, COMPONENTS_MAP)

        # all dependencies deployed
        m_get_deps.return_value = {'service1', 'service2'}
        m_get_deployed.return_value = {'service2'}
        deploy_validation.validate_requested_components(
            {'service1'}, COMPONENTS_MAP)

        # some dependencies requested and some deployed
        m_get_deps.return_value = {'service1', 'service2', 'service3'}
        m_get_deployed.return_value = {'service3'}
        deploy_validation.validate_requested_components(
            {'service1', 'service2'}, COMPONENTS_MAP)

        # validations failed
        # requirements are not requested and are not deployed
        m_get_deps.return_value = {'service1', 'service2'}
        m_get_deployed.return_value = set()
        self.assertRaisesRegexp(
            RuntimeError,
            'Following components are also required for successful '
            'deployment: service2',
            deploy_validation.validate_requested_components,
            {'service1'}, COMPONENTS_MAP)


class TestValidationRegex(base.TestCase):
    def test_ports_re(self):
        regex = r"^{}(:{})?$".format(
            service_validation.ALL_PORT_RE, service_validation.HOST_PORT_RE)
        self.assertRegexpMatches('0', regex)
        self.assertRegexpMatches('12', regex)
        self.assertRegexpMatches('123', regex)
        self.assertRegexpMatches('1234', regex)
        self.assertRegexpMatches('12345', regex)
        self.assertRegexpMatches('65535', regex)

        self.assertNotRegexpMatches('65536', regex)
        self.assertNotRegexpMatches('123456', regex)

        self.assertRegexpMatches('1234:30000', regex)
        self.assertRegexpMatches('1234:32767', regex)

        self.assertNotRegexpMatches('1234:1000', regex)
        self.assertNotRegexpMatches('1234:29999', regex)
        self.assertNotRegexpMatches('1234:32768', regex)
        self.assertNotRegexpMatches('1234:40000', regex)