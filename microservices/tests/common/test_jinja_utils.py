import os
import sys

from microservices.common import jinja_utils
from microservices.tests import base


class TestJinjaUtils(base.TestCase):

    def test_str_to_bool(self):
        self.assertTrue(jinja_utils.str_to_bool('true'))
        self.assertTrue(jinja_utils.str_to_bool('yes'))
        self.assertFalse(jinja_utils.str_to_bool('false'))
        self.assertFalse(jinja_utils.str_to_bool('no'))
        self.assertFalse(jinja_utils.str_to_bool('some_random_string'))

    def test_jinja_render(self):
        filename = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            'example.j2')
        content = jinja_utils.jinja_render(filename)
        self.assertEqual("debian\njessie\n"
                         "MOS Microservices <mos-microservices@mirantis.com>",
                         content)
