import mock

from k8sclient.client import rest

from fuel_ccp import cleanup
from fuel_ccp.tests import base


class TestCleanup(base.TestCase):
    @mock.patch('time.sleep')
    def test_wait_until_empty(self, m_sleep):
        # resources were deleted
        test_command = mock.Mock(return_value=[])
        res = cleanup._wait_until_empty(3, None, test_command)
        m_sleep.assert_not_called()
        self.assertIsNone(res)

        # resources are still exist
        m_sleep.reset_mock()
        test_command = mock.Mock(return_value=['something'])
        res = cleanup._wait_until_empty(3, None, test_command)
        self.assertEqual(3, m_sleep.call_count)
        self.assertEqual(['something'], res)

    @mock.patch('time.sleep')
    def test_wait_for_namespace_delete(self, m_sleep):
        # namespace was deleted
        k8s_api = mock.Mock()
        k8s_api.read_namespaced_namespace.side_effect = [
            'ns', 'ns', rest.ApiException(404)]
        cleanup._wait_for_namespace_delete(k8s_api)
        self.assertEqual(2, m_sleep.call_count)

        # namespace is still exists
        k8s_api = mock.Mock()
        k8s_api.read_namespaced_namespace.return_value = 'ns'
        self.assertRaisesRegexp(
            RuntimeError, "Wasn't able to delete namespace mcp",
            cleanup._wait_for_namespace_delete, k8s_api)

    @mock.patch('time.sleep')
    @mock.patch('neutronclient.v2_0.client.Client')
    def test_cleanup_network_resources(self, m_client, m_sleep):
        # subnets were not removed
        neutron = mock.Mock()
        neutron.list_subnets.return_value = {
            'subnets': [{'id': 1, 'name': 'subnet1'}]}
        m_client.return_value = neutron
        self.assertRaisesRegexp(
            RuntimeError, "Some subnets were not removed: subnet1 \(1\)",
            cleanup._cleanup_network_resources, mock.Mock())

        # subnets were removed but networks were not
        neutron.list_subnets.return_value = {'subnets': []}
        neutron.list_networks.return_value = {
            'networks': [{'id': 1, 'name': 'net1'}]}
        self.assertRaisesRegexp(
            RuntimeError, "Some networks were not removed: net1 \(1\)",
            cleanup._cleanup_network_resources, mock.Mock())

        # subnets and networks were removed
        neutron.list_networks.return_value = {'networks': []}
        cleanup._cleanup_network_resources(mock.Mock())

    @mock.patch('time.sleep')
    @mock.patch('novaclient.client.Client')
    def test_cleanup_servers(self, m_client, m_sleep):
        # instances were not removed
        nova = mock.Mock()
        instance = mock.Mock(id=1)
        instance.name = 'inst1'

        nova.servers.list.return_value = [instance]
        m_client.return_value = nova
        self.assertRaisesRegexp(
            RuntimeError, "Some instances were not removed "
                          "after force delete: inst1 \(1\)",
            cleanup._cleanup_servers, mock.Mock())

        # instances were removed
        nova.servers.list.return_value = []
        cleanup._cleanup_servers(mock.Mock())
