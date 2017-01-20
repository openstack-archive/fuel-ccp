import git
import mock
import os

import fixtures
from fuel_ccp import fetch
from fuel_ccp.tests import base
import testscenarios


STATUSES = {
    'fetch_alredy_existed': 'AlreadyExist',
    'fetch_failed': 'Failure',
    'fetch_succeeded': 'Success'
}


class TestFetch(testscenarios.WithScenarios, base.TestCase):
    component_def = {'name': 'compname', 'git_url': 'theurl'}
    update_def = {}
    dir_exists = False
    clone_side_effect = None
    checkout_side_effect = None

    scenarios = [
        ('exists', {'dir_exists': True}),
        ('clone_exception', {
            'clone_side_effect': git.exc.InvalidGitRepositoryError()}),
        ('clone', {}),
        ('checkout', {'update_def': {'git_ref': 'theref'}}),
        ('checkout_exception', {'update_def': {'git_ref': 'theref'},
                                'checkout_side_effect':
                                    git.exc.CheckoutError('msg', [], [], [])})
    ]

    def setUp(self):
        super(TestFetch, self).setUp()
        # Creating temporaty directory for repos
        self.tmp_path = self.useFixture(fixtures.TempDir()).path
        self.conf['repositories']['path'] = self.tmp_path
        if self.clone_side_effect:
            fixture_clone = fixtures.MockPatch('git.Repo.clone_from')
            self.mock_clone = self.useFixture(fixture_clone).mock
            self.mock_clone.side_effect = self.clone_side_effect
        else:
            repo = mock.Mock()
            repo.git.checkout.side_effect = self.checkout_side_effect
            fixture_clone = fixtures.MockPatch('git.Repo.clone_from',
                                               return_value=repo)
            self.mock_clone = self.useFixture(fixture_clone).mock

    def test_fetch_repository(self):
        component_def = self.component_def.copy()
        component_def.update(self.update_def)

        fixture = fixtures.MockPatch('os.path.isdir')
        isdir_mock = self.useFixture(fixture).mock
        isdir_mock.return_value = self.dir_exists

        status = fetch.fetch_repository(component_def)
        git_path = os.path.join(self.tmp_path, component_def['name'])
        isdir_mock.assert_called_once_with(git_path)
        if self.dir_exists:
            self.assertEqual(status['status'],
                             STATUSES['fetch_alredy_existed'])
            self.mock_clone.assert_not_called()

        elif self.clone_side_effect:
            self.mock_clone.assert_called_once_with('theurl', git_path)
            self.assertEqual(status['status'],
                             STATUSES['fetch_failed'])
        elif not self.clone_side_effect:
            git_ref = component_def.get('git_ref')
            if git_ref and self.checkout_side_effect:
                self.assertEqual(status['status'],
                                 STATUSES['fetch_failed'])
            elif git_ref:
                self.mock_clone.assert_called_once_with(
                    'theurl', git_path)
                self.assertEqual(status['status'],
                                 STATUSES['fetch_succeeded'])
            else:
                self.mock_clone.assert_called_once_with('theurl', git_path)
                self.assertEqual(status['status'],
                                 STATUSES['fetch_succeeded'])
