from fuel_ccp.action import Action
from fuel_ccp.tests import base


class TestValidateAction(base.TestCase):
    def setUp(self):
        super(TestValidateAction, self).setUp()
        self.action = {
            "name": "test_action",
            "image": "keystone",
            "command": "test_command",
        }

    def test_validate_successful(self):
        Action.validate(self.action)

    def test_validate_error_field(self):
        self.action["test"] = "test"
        self.assertRaisesWithMessageIn(ValueError, "'test' was unexpected",
                                       Action.validate, self.action)

    def test_validate_error_type(self):
        self.action["command"] = ["echo", "Hello World"]
        self.assertRaisesWithMessageIn(ValueError, "not of type 'string'",
                                       Action.validate, self.action)
