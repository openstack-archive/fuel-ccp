import os

from jinja2 import exceptions as jinja_exceptions
import testscenarios
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
        self.conf.repositories.repos = [{"name": "component"}]

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
        self.conf.repositories.repos = [{"name": "component"}]

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
        self.conf.repositories.repos = [{"name": "component"}]

        config.load_component_defaults()

        self.assertRaises(jinja_exceptions.UndefinedError,
                          utils.get_deploy_components_info)

    def test_get_ingress_host(self):
        self.conf.configs._merge({'ingress': {'domain': 'test'}})
        self.assertEqual('service.ccp.test', utils.get_ingress_host('service'))


class TestAddress(testscenarios.WithScenarios, base.TestCase):
    scenarios = (
        ('internal_without_port', {'address': 'service.ccp'}),
        ('internal_with_port', {'address': 'service.ccp:1234',
                                'port': {'cont': 1234}}),
        ('external_with_nodeport',
         {'address': '1.1.1.1:30000', 'external': True, 'ingress': False,
          'port': {'cont': 1234, 'ingress': 'test', 'node': 30000}}),
        ('external_without_ingress_and_nodeport',
         {'address': 'service.ccp:1234', 'external': True, 'ingress': False,
          'port': {'cont': 1234, 'ingress': 'test'}}),
        ('external_with_ingress_enabled',
         {'address': 'test.ccp.external', 'external': True, 'ingress': True,
          'port': {'cont': 1234, 'ingress': 'test'}}),
        ('external_with_ingress_not_provided',
         {'address': '1.1.1.1:30000', 'external': True, 'ingress': True,
          'port': {'cont': 1234, 'node': 30000}}),
        ('external_with_ingress_and_nodeport_not_provided',
         {'address': 'service.ccp:1234', 'external': True, 'ingress': True,
          'port': {'cont': 1234}}),
        ('multiple_without_port',
         {'address': ['service-0.service.ccp', 'service-1.service.ccp'],
          'multiple': True}),
        ('multiple_with_port',
         {'address': ['service-0.service.ccp:1234',
                      'service-1.service.ccp:1234'],
          'port': {'cont': 1234}, 'multiple': True}),
    )

    port = None
    external = None
    ingress = False
    multiple = False

    def test_address(self):
        self.conf.replicas = {'service': 2}
        self.conf.configs._merge({'ingress': {'enabled': self.ingress,
                                              'domain': 'external'},
                                  'k8s_external_ip': '1.1.1.1'})
        self.assertEqual(self.address,
                         utils.address('service', self.port, self.external,
                                       self.multiple))
