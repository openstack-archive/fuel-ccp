import os

import fixtures
from fuel_ccp import fetch
from fuel_ccp.tests import base
import mock
import testscenarios


@mock.patch('git.Repo.clone_from')
class TestFetch(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ("default", {
            "option": None,
            "value": None,
            "url": "https://review.openstack.org:443/openstack/%s"}),
        ("hostname", {
            "option": "hostname",
            "value": "host.name",
            "url": "https://host.name:443/openstack/%s"}),
        ('username', {
            "option": "username",
            "value": "someuser",
            "url": "https://someuser@review.openstack.org:443/openstack/%s",
        }),
        ('port', {
            "option": "port",
            "value": "9999",
            'url': "https://review.openstack.org:9999/openstack/%s",
        }),
        ('protocol', {
            "option": "protocol",
            "value": "ssh",
            'url': "ssh://review.openstack.org:443/openstack/%s",
        }),
        ('protocol', {
            "option": "protocol",
            "value": "http",
            'url': "http://review.openstack.org:443/openstack/%s",
        }),
        ('protocol', {
            "option": "protocol",
            "value": "git",
            'url': "git://review.openstack.org:443/openstack/%s",
        }),
        ('protocol', {
            "option": "protocol",
            "value": "https",
            'url': "https://review.openstack.org:443/openstack/%s",
        }),
        ('project', {
            "option": "project",
            "value": "someproject",
            'url': "https://review.openstack.org:443/someproject/%s",
        })
    ]
    url = None
    option = None
    delta = None

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
        if self.option is not None:
            self.conf['repositories'][self.option] = self.value
        self.conf['repositories']['path'] = self.tmp_path
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
            mock.call(
                self.url % (component),
                os.path.join(self.tmp_path, component))
            for component in components]
        for component, expected_call in zip(components, expected_calls):
            fetch.fetch_repository(component)
            self.assertIn(expected_call, m_clone.call_args_list)
