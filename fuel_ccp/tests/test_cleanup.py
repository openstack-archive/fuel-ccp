import mock

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
        namespace = mock.Mock()
        namespace.exists.side_effect = [
            True, True, False]
        cleanup._wait_for_namespace_delete(namespace)
        self.assertEqual(2, m_sleep.call_count)

        # namespace is still exists
        k8s_api = mock.Mock()
        k8s_api.read_namespaced_namespace.return_value = 'ns'
        self.assertRaisesRegexp(
            RuntimeError, "Wasn't able to delete namespace ccp",
            cleanup._wait_for_namespace_delete, k8s_api)

    @mock.patch('time.sleep')
    @mock.patch('neutronclient.neutron.client.Client')
    def test_cleanup_network_resources(self, m_client, m_sleep):
        neutron = mock.Mock()
        # subnets and networks were removed
        neutron.list_floatingips.return_value = {"floatingips": []}
        neutron.list_routers.return_value = {"routers": []}
        neutron.list_ports.return_value = {"ports": []}
        neutron.list_networks.return_value = {"networks": []}
        m_client.return_value = neutron
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
