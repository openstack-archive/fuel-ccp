from jinja2 import exceptions

from fuel_ccp.common import jinja_utils
from fuel_ccp.common import utils
from fuel_ccp.tests import base


class TestJinjaUtils(base.TestCase):
    filename = utils.get_resource_path('tests/common/example.j2')

    def test_str_to_bool(self):
        self.assertTrue(jinja_utils.str_to_bool('true'))
        self.assertTrue(jinja_utils.str_to_bool('yes'))
        self.assertFalse(jinja_utils.str_to_bool('false'))
        self.assertFalse(jinja_utils.str_to_bool('no'))
        self.assertFalse(jinja_utils.str_to_bool('some_random_string'))

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
            "debian\njessie\nsome maintainer\nneedle\nneedle\nkeystone.ccp",
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
            "debian\njessie\nsome maintainer\nneedle\nneedle\nkeystone.ccp",
            content)

        context = {
            "base_distro": "debian"
        }
        content = jinja_utils.jinja_render(
            self.filename, context, functions=[utils.address],
            ignore_undefined=True)
        self.assertEqual(
            "debian\n\n\n\n\nkeystone.ccp", content)
