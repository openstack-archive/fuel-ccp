import os

from jinja2 import exceptions as jinja_exceptions
from mock import mock
from oslo_config import fixture as oslo_config_fixture
import yaml

from fuel_ccp.common import utils
from fuel_ccp.tests import base


class TestUtils(base.TestCase):

    def setUp(self):
        super(TestUtils, self).setUp()

        self.cfg = oslo_config_fixture.Config()
        self.cfg.setUp()

    @mock.patch("fuel_ccp.common.utils.get_global_parameters")
    def test_get_deploy_components_info_with_default_context(
            self, get_global_parameters_mock):

        default_params = {
            "configs": {
                "db_root_password": "db_root_password_default",
                "keystone_db_name": "keystone_db_name_default",
                "keystone_db_username": "keystone_db_username_default",
                "keystone_db_password": "keystone_db_password_default",
                "openstack_user_password": "os_user_password_default",
                "openstack_user_name": "os_user_name_default",
                "openstack_project_name": "os_project_name_default",
                "openstack_role_name": "os_role_name_default",
                "keystone_admin_port": "keystone_admin_port_default",
                "keystone_public_port": "keystone_public_port_default"
            }
        }

        get_global_parameters_mock.return_value = default_params

        base_dir = os.path.dirname(__file__)

        self.cfg.config(
            group="repositories",
            path=os.path.join(base_dir, "test_repo_dir")
        )
        self.cfg.config(
            group="repositories",
            names=["component"]
        )

        res = (
            utils.get_deploy_components_info()["component"]["service_content"]
        )

        get_global_parameters_mock.assert_called_once_with("configs")

        with open(os.path.join(base_dir,
                               "service-rendered-example-default.yaml")) as f:
            expected = yaml.load(f)

        self.assertDictEqual(expected, res)

    @mock.patch("fuel_ccp.common.utils.get_global_parameters")
    def test_get_deploy_components_info_with_custom_context(
            self, get_global_parameters_mock):

        custom_params = {
            "configs": {
                "db_root_password": "db_root_password_custom",
                "keystone_db_name": "keystone_db_name_custom",
                "keystone_db_username": "keystone_db_username_custom",
                "keystone_db_password": "keystone_db_password_custom",
                "openstack_user_password": "os_user_password_custom",
                "openstack_user_name": "os_user_name_custom",
                "openstack_project_name": "os_project_name_custom",
                "openstack_role_name": "os_role_name_custom",
                "keystone_admin_port": "keystone_admin_port_custom",
                "keystone_public_port": "keystone_public_port_custom"
            }
        }

        base_dir = os.path.dirname(__file__)

        self.cfg.config(
            group="repositories",
            path=os.path.join(base_dir, "test_repo_dir")
        )
        self.cfg.config(
            group="repositories",
            names=["component"]
        )

        res = utils.get_deploy_components_info(
            rendering_context=custom_params["configs"]
        )["component"]["service_content"]

        get_global_parameters_mock.assert_not_called()

        with open(os.path.join(base_dir,
                               "service-rendered-example-custom.yaml")) as f:
            expected = yaml.load(f)

        self.assertDictEqual(expected, res)

    @mock.patch("fuel_ccp.common.utils.get_global_parameters")
    def test_get_deploy_components_info_with_not_enough_context(
            self, get_global_parameters_mock):

        default_params = {
            "configs": {
                "db_root_password": "db_root_password_default",
                "keystone_db_name": "keystone_db_name_default",
                "keystone_db_username": "keystone_db_username_default",
                "keystone_db_password": "keystone_db_password_default",
                "openstack_user_password": "os_user_password_default",
                "openstack_user_name": "os_user_name_default",
                "openstack_project_name": "os_project_name_default",
                "openstack_role_name": "os_role_name_default",
            }
        }

        get_global_parameters_mock.return_value = default_params

        base_dir = os.path.dirname(__file__)

        self.cfg.config(
            group="repositories",
            path=os.path.join(base_dir, "test_repo_dir")
        )
        self.cfg.config(
            group="repositories",
            names=["component"]
        )

        self.assertRaises(jinja_exceptions.UndefinedError,
                          utils.get_deploy_components_info)

        get_global_parameters_mock.assert_called_once_with("configs")
