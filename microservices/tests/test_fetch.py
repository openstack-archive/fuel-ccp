import getpass
import os

import fixtures
import mock
from oslo_config import cfg

from microservices import fetch
from microservices.tests import base


CONF = cfg.CONF


@mock.patch('git.Repo.clone_from')
class TestFetch(base.TestCase):

    def setUp(self):
        super(TestFetch, self).setUp()
        # Creating temporaty directory for repos
        tmp_dir = fixtures.TempDir()
        tmp_dir.setUp()
        self.tmp_path = tmp_dir.path
        CONF.set_override('path', self.tmp_path, group='repositories')
        # Create temporary directory for openstack-base to not clone it
        os.mkdir(os.path.join(self.tmp_path, 'ms-openstack-base'))

    def test_fetch_default_repositories(self, m_clone):
        fetch.fetch_repositories()
        # All repos except ms-openstack-base
        components = [
            'ms-debian-base',
            'ms-aodh',
            'ms-ceilometer',
            'ms-ceph',
            'ms-cinder',
            'ms-designate',
            'ms-elasticsearch',
            'ms-glance',
            'ms-heat',
            'ms-heka',
            'ms-horizon',
            'ms-ironic',
            'ms-keystone',
            'ms-kibana',
            'ms-magnum',
            'ms-manila',
            'ms-mariadb',
            'ms-memcached',
            'ms-mistral',
            'ms-mongodb',
            'ms-murano',
            'ms-neutron',
            'ms-nova',
            'ms-openvswitch',
            'ms-rabbitmq',
            'ms-sahara',
            'ms-swift',
            'ms-tempest',
            'ms-toolbox',
            'ms-trove',
            'ms-zaqar'
        ]
        username = getpass.getuser()
        expected_calls = [
            mock.call('ssh://%s@review.fuel-infra.org:29418/nextgen/%s' % (
                username, component), os.path.join(self.tmp_path, component))
            for component in components
        ]
        self.assertListEqual(expected_calls, m_clone.call_args_list)

    def test_fetch_custom_repositories(self, m_clone):
        fetch.fetch_repositories(components=['ms-openstack-base', 'ms-nova'])
        username = getpass.getuser()
        self.assertListEqual([
            mock.call('ssh://%s@review.fuel-infra.org:29418/nextgen/ms-nova' %
                      username, os.path.join(self.tmp_path, 'ms-nova'))
        ], m_clone.call_args_list)
