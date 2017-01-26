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
        # Do it three times, because after first merge tls is just a dict, but
        # should be a AttrDict class.
        for i in range(3):
            confs = {"security": {"tls": {"openstack": {"enabled": False}}},
                     "etcd": {"tls": {"enabled": True}}}
            self.conf.configs._merge(confs)
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
            "keystone.ccp.svc.cluster.local",
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
            "keystone.ccp.svc.cluster.local",
            content)

        context = {
            "base_distro": "debian"
        }
        content = jinja_utils.jinja_render(
            self.filename, context, functions=[utils.address],
            ignore_undefined=True)
        self.assertEqual(
            "debian\n\n\n\n\nkeystone.ccp.svc.cluster.local\n"
            "keystone.ccp.svc.cluster.local",
            content)
