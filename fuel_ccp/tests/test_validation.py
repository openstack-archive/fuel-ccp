import fixtures
import mock

import fuel_ccp
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


class TestServiceValidation(base.TestCase):
    def setUp(self):
        super(TestServiceValidation, self).setUp()
        self.useFixture(fixtures.MockPatch("fuel_ccp.service_parser_version",
                                           "0.2.0"))

    def test_validation_service_versions_incompatible(self):
        components_map = {
            "test": {
                "service_content": {
                    "dsl_version": "0.3.0"
                }
            }
        }
        self.assertRaises(
            RuntimeError, service_validation.validate_service_versions,
            components_map, ['test']
        )

    def test_validation_service_versions_incompatible_major(self):
        components_map = {
            "test": {
                "service_content": {
                    "dsl_version": "1.0.0"
                }
            }
        }
        self.assertRaises(
            RuntimeError, service_validation.validate_service_versions,
            components_map, ["test"]
        )

    def test_validation_service_versions_compatible(self):
        components_map = {
            "test": {
                "service_content": {
                    "dsl_version": "0.1.0"
                }
            }
        }
        service_validation.validate_service_versions(
            components_map, ['test']
        )
