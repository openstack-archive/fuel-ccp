import os

import fixtures
import mock

from fuel_ccp import fetch
from fuel_ccp.tests import base


@mock.patch('git.Repo.clone_from')
class TestFetch(base.TestCase):

    def setUp(self):
        super(TestFetch, self).setUp()
        # Creating temporaty directory for repos
        tmp_dir = fixtures.TempDir()
        tmp_dir.setUp()
        self.tmp_path = tmp_dir.path
        self.conf['repositories']['path'] = self.tmp_path
        # Create temporary directory for openstack-base to not clone it
        os.mkdir(os.path.join(self.tmp_path, 'ms-openstack-base'))

    def test_fetch_default_repositories(self, m_clone):
        # All repos except ms-openstack-base
        components = ['fuel-ccp-debian-base',
                      'fuel-ccp-entrypoint',
                      'fuel-ccp-etcd',
                      'fuel-ccp-glance',
                      'fuel-ccp-horizon',
                      'fuel-ccp-keystone',
                      'fuel-ccp-mariadb',
                      'fuel-ccp-memcached',
                      'fuel-ccp-neutron',
                      'fuel-ccp-nova',
                      'fuel-ccp-rabbitmq',
                      'fuel-ccp-stacklight']
        expected_calls = [
            mock.call('https://%s@review.openstack.org:443/openstack/%s' % (
                '', component), os.path.join(self.tmp_path, component))
            for component in components
        ]
        for component, expected_call in zip(components, expected_calls):
            fetch.fetch_repository(component)
            self.assertIn(expected_call, m_clone.call_args_list)
