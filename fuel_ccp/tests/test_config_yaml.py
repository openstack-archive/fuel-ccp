import fixtures
import mock
import six
import testscenarios

from fuel_ccp.config import _yaml
from fuel_ccp.tests import base


class TestLoadWithIncludes(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ('empty', {
            'files': {'config': ''},
            'expected_result': {},
        }),
        ('onedoc', {
            'files': {'config': 'key: value'},
            'expected_result': {'key': 'value'},
        }),
        ('twodoc', {
            'files': {'config': '''
                ---
                a: 1
                b: 2
                ---
                a: 3
                c: 4
                '''},
            'expected_result': {'a': 3, 'b': 2, 'c': 4},
        }),
        ('oneinclude', {
            'files': {
                'config': '''
                    ---
                    a: 1
                    b: 2
                    ---
                    !include
                    - otherfile
                    ''',
                'otherfile': '''
                    ---
                    a: 3
                    c: 4
                    ''',
            },
            'expected_result': {'a': 3, 'b': 2, 'c': 4},
        }),
        ('preinclude', {
            'files': {
                'config': '''
                    ---
                    !include
                    - otherfile
                    ---
                    a: 3
                    c: 4
                    ''',
                'otherfile': '''
                    ---
                    a: 1
                    b: 2
                    ''',
            },
            'expected_result': {'a': 3, 'b': 2, 'c': 4},
        }),
        ('deep', {
            'files': {
                'config': '''
                    ---
                    !include
                    - inc1
                    ''',
                'inc1': '''
                    {"a": {"b": 1, "c": 2}}
                    ---
                    !include
                    - inc2
                    ''',
                'inc2': '{"a": {"c": 3}, "d": 4}',
            },
            'expected_result': {'a': {'b': 1, 'c': 3}, 'd': 4},
        }),
    ]

    files = None
    expected_result = None

    def test_load_with_includes(self):
        self.files_mocks = {}
        for name, content in six.iteritems(self.files):
            if content.startswith('\n'):
                lines = content.splitlines()[1:]
                indent = len(lines[0]) - len(lines[0].lstrip(' '))
                content = '\n'.join(l[indent:] for l in lines)
            m = mock.mock_open(read_data=content)
            self.files_mocks[name] = m.return_value
        fixture = fixtures.MockPatch('six.moves.builtins.open')
        self.mock_open = self.useFixture(fixture).mock
        self.mock_open.side_effect = self.files_mocks.__getitem__

        res = _yaml.load_with_includes('config')
        self.assertEqual(res, self.expected_result)
