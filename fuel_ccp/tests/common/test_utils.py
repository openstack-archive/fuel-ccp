import os

from jinja2 import exceptions as jinja_exceptions
import yaml

from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp.tests import base


class TestUtils(base.TestCase):

    def test_get_deploy_components_info_with_default_context(self):

        default_params = {
            "configs": {
                "service_name": "keystone",
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

        conf = config._yaml.AttrDict()
        conf._merge(default_params)
        conf._merge(config._REAL_CONF)
        config._REAL_CONF = conf

        base_dir = os.path.dirname(__file__)

        self.conf.repositories.path = os.path.join(base_dir, "test_repo_dir")
        self.conf.repositories.names = ["component"]

        res = (
            utils.get_deploy_components_info()["keystone"]["service_content"]
        )

        with open(os.path.join(base_dir,
                               "service-rendered-example-default.yaml")) as f:
            expected = yaml.load(f)

        self.assertDictEqual(expected, res)

    def test_get_deploy_components_info_with_custom_context(self):

        custom_params = {
            "configs": {
                "service_name": "keystone",
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

        conf = config._yaml.AttrDict()
        conf._merge(custom_params)
        conf._merge(config._REAL_CONF)
        config._REAL_CONF = conf
        base_dir = os.path.dirname(__file__)

        self.conf.repositories.path = os.path.join(base_dir, "test_repo_dir")
        self.conf.repositories.names = ["component"]

        config.load_component_defaults()

        res = utils.get_deploy_components_info(
            rendering_context=custom_params["configs"]
        )["keystone"]["service_content"]

        with open(os.path.join(base_dir,
                               "service-rendered-example-custom.yaml")) as f:
            expected = yaml.load(f)

        self.assertDictEqual(expected, res)

    def test_get_deploy_components_info_with_not_enough_context(self):

        default_params = {
            "configs": {
                "service_name": "keystone",
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

        conf = config._yaml.AttrDict()
        conf._merge(default_params)
        conf._merge(config._REAL_CONF)
        config._REAL_CONF = conf

        base_dir = os.path.dirname(__file__)

        self.conf.repositories.path = os.path.join(base_dir, "test_repo_dir")
        self.conf.repositories.names = ["component"]

        config.load_component_defaults()

        self.assertRaises(jinja_exceptions.UndefinedError,
                          utils.get_deploy_components_info)
