import fixtures
import mock
import testscenarios

from fuel_ccp import kubernetes
from fuel_ccp.tests import base


class TestKubernetesClient(base.TestCase):
    config = {
        'contexts': [{
            'name': 'ccp',
            'context': {
                'cluster': 'ccp',
                'user': 'ccp'
            }
        }],
        'clusters': [{
            'cluster': {
                'certificate-authority': 'ca.crt',
                'server': 'http://localhost:8080'
            },
            'name': 'ccp'
        }],
        'users': [{
            'name': 'ccp',
            'user': {
                'client-certificate': 'test.cert',
                'client-key': 'test.key'
            }
        }],
        'current-context': 'ccp'
    }

    @mock.patch('pykube.KubeConfig')
    @mock.patch('pykube.HTTPClient')
    def test_get_client_with_conf(self, m_client, m_config):
        self.conf['kubernetes']._update(
            key_file='test.key',
            ca_cert='ca.crt',
            cert_file='test.cert',
        )

        kubernetes.get_client()
        m_config.assert_called_once_with(self.config)
        m_client.assrt_called_once_with(m_config)

    @mock.patch('pykube.KubeConfig')
    @mock.patch('pykube.HTTPClient')
    def test_get_client(self, m_client, m_config):
        kubernetes.get_client(
            kube_apiserver='http://localhost:8080', key_file='test.key',
            cert_file='test.cert', ca_cert='ca.crt')
        m_config.assert_called_once_with(self.config)
        m_client.assrt_called_once_with(m_config)


class TestKubernetesObjects(testscenarios.WithScenarios, base.TestCase):
    scenarios = (
        ('ConfigMap', {'kind': 'ConfigMap', 'update': True}),
        ('Deployment', {'kind': 'Deployment', 'update': True}),
        ('DaemonSet', {'kind': 'DaemonSet', 'update': False}),
        ('Job', {'kind': 'Job', 'update': False}),
        ('Namespace', {'kind': 'Namespace', 'update': False}),
        ('Service', {'kind': 'Service', 'update': True})
    )

    def setUp(self):
        super(TestKubernetesObjects, self).setUp()
        self.conf.action.dry_run = False
        self.conf.action.export_dir = False

    def test_object_create(self):
        obj_dict = {'kind': self.kind, 'metadata': {'name': 'test'}}
        m_obj = mock.Mock(exists=mock.Mock(return_value=False))
        m_class = self.useFixture(fixtures.MockPatch(
            'pykube.{}'.format(self.kind), return_value=m_obj))

        kubernetes.process_object(obj_dict, client=mock.Mock())
        m_class.mock.assert_called_once_with(mock.ANY, obj_dict)
        m_obj.create.assert_called_once_with()

    def test_object_update(self):
        obj_dict = {'kind': self.kind, 'metadata': {'name': 'test'}}
        m_obj = mock.Mock(exists=mock.Mock(return_value=True))
        m_class = self.useFixture(fixtures.MockPatch(
            'pykube.{}'.format(self.kind), return_value=m_obj))

        kubernetes.process_object(obj_dict, client=mock.Mock())
        m_class.mock.assert_called_once_with(mock.ANY, obj_dict)
        m_obj.exists.assert_called_once_with()
        m_obj.create.assert_not_called()
        if self.update:
            m_obj.update.assert_called_once_with()
