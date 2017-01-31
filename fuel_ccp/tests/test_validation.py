import copy
import fixtures
import jsonschema
import mock
import testscenarios

from fuel_ccp.tests import base
from fuel_ccp.validation import action
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


class TestServiceValidation(testscenarios.WithScenarios, base.TestCase):
    scenarios = (
        ('incompatible', {'version': '0.3.0', 'raises': RuntimeError}),
        ('incompatible_major', {'version': '1.0.0', 'raises': RuntimeError}),
        ('compatible', {'version': '0.1.0'}),
        ('larget_but_compatible', {'version': '0.1.0'})
    )
    raises = None

    def setUp(self):
        super(TestServiceValidation, self).setUp()
        self.useFixture(fixtures.MockPatch("fuel_ccp.dsl_version",
                                           "0.2.0"))

    def test_validation(self):
        components_map = {
            "test": {
                "service_content": {
                    "dsl_version": self.version
                }
            }
        }
        if self.raises:
            self.assertRaises(
                self.raises, service_validation.validate_service_versions,
                components_map, ['test']
            )
        else:
            service_validation.validate_service_versions(
                components_map, ['test']
            )


class TestSchemaValidation(base.TestCase):
    def test_secret_permissions_validation(self):
        correct_permissions = ["0400", "0777", "0001"]
        for perm in correct_permissions:
            jsonschema.validate(perm, service_validation.PERMISSION_SCHEMA)

        incorrect_permissions = ["123", "0778", "1400"]
        for perm in incorrect_permissions:
            self.assertRaisesRegexp(
                jsonschema.exceptions.ValidationError,
                "'" + perm + "' does not match.*",
                jsonschema.validate,
                perm, service_validation.PERMISSION_SCHEMA)

    def test_secret_definition_validation(self):
        incorrect_secret = {
            "path": "/etc/keystone/fernet-keys",
            "secret": {
            }
        }
        self.assertRaisesRegexp(
            jsonschema.exceptions.ValidationError,
            "'secretName' is a required property.*",
            jsonschema.validate,
            incorrect_secret, service_validation.SECRET_SCHEMA)

        minimal_correct_secret = copy.deepcopy(incorrect_secret)
        minimal_correct_secret["secret"].update({"secretName": "fernet"})
        jsonschema.validate(minimal_correct_secret,
                            service_validation.SECRET_SCHEMA)

        correct_secret = copy.deepcopy(minimal_correct_secret)
        correct_secret["secret"] = {
            "secretName": "fernet",
            "defaultMode": "0777",
            "items": [
                {
                    "key": "username",
                    "path": "/specific/username/path",
                    "mode": "0777"
                },
                {
                    "key": "password",
                    "path": "/specific/password/path",
                    "mode": "0400"
                }
            ]
        }
        correct_secret["data"] = {
            "item1": "value 1",
            "2": "/path/file.ext"
        }
        jsonschema.validate(correct_secret, service_validation.SECRET_SCHEMA)


class TestValidateAction(base.TestCase):
    def setUp(self):
        super(TestValidateAction, self).setUp()
        self.action = {
            "name": "test_action",
            "image": "keystone",
            "command": "test_command",
            "files": [
                {
                    "path": "/etc/keystone/keystone.conf",
                    "content": "keystone.conf.j2"
                },
                {
                    "path": "/etc/path2",
                    "content": "file2.j2"
                }
            ]
        }

    def test_validate_successful(self):
        action.validate_action(self.action)

    def test_validate_error_field(self):
        self.action["test"] = "test"
        self.assertRaisesRegexp(
            RuntimeError,
            "Validation of action definition test_action is not passed",
            action.validate_action, self.action)

    def test_validate_error_type(self):
        self.action["command"] = ["echo", "Hello World"]
        self.assertRaisesRegexp(
            RuntimeError,
            "Validation of action definition test_action is not passed",
            action.validate_action, self.action)
