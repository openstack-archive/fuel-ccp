import os

import fixtures
from fuel_ccp import fetch
from fuel_ccp.tests import base
import testscenarios


class TestFetch(testscenarios.WithScenarios, base.TestCase):
    component_def = {'name': 'compname', 'git_url': 'theurl'}
    update_def = {}
    expected_clone_call = None
    dir_exists = False

    scenarios = [
        ('exists', {'dir_exists': True}),
    ]

    def setUp(self):
        super(TestFetch, self).setUp()
        # Creating temporaty directory for repos
        self.tmp_path = self.useFixture(fixtures.TempDir()).path
        self.conf['repositories']['path'] = self.tmp_path
        fixture = fixtures.MockPatch('git.Repo.clone_from')
        self.mock_clone = self.useFixture(fixture).mock

    def test_fetch_repository(self):
        component_def = self.component_def.copy()
        component_def.update(self.update_def)

        fixture = fixtures.MockPatch('os.path.isdir')
        isdir_mock = self.useFixture(fixture).mock
        isdir_mock.return_value = self.dir_exists

        fetch.fetch_repository(component_def)

        git_path = os.path.join(self.tmp_path, component_def['name'])
        isdir_mock.assert_called_once_with(git_path)
        if self.expected_clone_call:
            git_ref = component_def.get('git_ref')
            if git_ref:
                self.mock_clone.assert_called_once_with(
                    'theurl', git_path, branch=git_ref)
            else:
                self.mock_clone.assert_called_once_with('theurl', git_path)
        else:
            self.mock_clone.assert_not_called()
