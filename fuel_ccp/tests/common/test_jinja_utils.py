from jinja2 import exceptions

from fuel_ccp.common import jinja_utils
from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp.tests import base


class TestJinjaUtils(base.TestCase):
    filename = utils.get_resource_path('tests/common/example.j2')

    def setUp(self):
        super(TestJinjaUtils, self).setUp()
        conf = config._yaml.AttrDict()
        conf_dict = {"security": {"tls": {"openstack": {"enabled": False}}},
                     "etcd": {"tls": {"enabled": True}},
                     "ingress": {"enabled": True, "port": 8443,
                                 "domain": "ccp.svc.cluster.local"}}
        prepared_conf = self.nested_dict_to_attrdict(conf_dict)
        self.conf.configs._merge(prepared_conf)
        conf._merge(config._REAL_CONF)
        config._REAL_CONF = conf

    def test_jinja_render_strict(self):
        context = {
            "base_distro": "debian",
            "base_tag": "jessie",
            "maintainer": "some maintainer",
            "duck": {"egg": "needle"}
        }

        content = jinja_utils.jinja_render(self.filename, context,
                                           functions=[utils.address])
        self.assertEqual(
            "debian\njessie\nsome maintainer\nneedle\nneedle\n"
            "keystone.ccp.svc.cluster.local\n"
            "keystone.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local:8443",
            content)

        context = {
            "base_distro": "debian"
        }
        self.assertRaises(exceptions.UndefinedError, jinja_utils.jinja_render,
                          self.filename, context)

    def test_jinja_render_silent(self):
        context = {
            "base_distro": "debian",
            "base_tag": "jessie",
            "maintainer": "some maintainer",
            "duck": {"egg": "needle"}
        }
        content = jinja_utils.jinja_render(
            self.filename, context, functions=[utils.address],
            ignore_undefined=True)
        self.assertEqual(
            "debian\njessie\nsome maintainer\nneedle\nneedle\n"
            "keystone.ccp.svc.cluster.local\n"
            "keystone.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local:8443",
            content)

        context = {
            "base_distro": "debian"
        }
        content = jinja_utils.jinja_render(
            self.filename, context, functions=[utils.address],
            ignore_undefined=True)
        self.assertEqual(
            "debian\n\n\n\n\nkeystone.ccp.svc.cluster.local\n"
            "keystone.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local\n"
            "gerrit.ccp.svc.cluster.local:8443",
            content)
