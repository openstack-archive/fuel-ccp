import mock

from oslo_config import cfg

from microservices import kubernetes
from microservices.tests import base

CONF = cfg.CONF


class TestKubernetes(base.TestCase):
    @mock.patch('k8sclient.client.api_client.ApiClient')
    def test_get_client_with_conf(self, api_client):
        CONF.set_override('key_file', 'test.key', group='kubernetes')
        CONF.set_override('ca_certs', 'ca.crt', group='kubernetes')
        CONF.set_override('cert_file', 'test.cert', group='kubernetes')

        kubernetes.get_client()
        api_client.assert_called_once_with(
            ca_certs='ca.crt', cert_file='test.cert', host='127.0.0.1:8080',
            key_file='test.key')

    @mock.patch('k8sclient.client.api_client.ApiClient')
    def test_get_client(self, api_client):
        CONF.set_override('key_file', 'test.key', group='kubernetes')
        CONF.set_override('ca_certs', 'ca.crt', group='kubernetes')
        CONF.set_override('cert_file', 'test.cert', group='kubernetes')

        kubernetes.get_client(
            kube_apiserver='1.2.3.4:8080', key_file='test.key',
            cert_file='test.cert', ca_certs='ca.crt')
        api_client.assert_called_once_with(
            ca_certs='ca.crt', cert_file='test.cert', host='1.2.3.4:8080',
            key_file='test.key')

    @mock.patch(
        'k8sclient.client.apis.apisextensionsvbeta_api.ApisextensionsvbetaApi')
    def test_create_deployment(self, api_beta):
        CONF.action.dry_run = False
        api = mock.Mock()
        api.create_namespaced_deployment = mock.Mock()
        api_beta.return_value = api

        deployment_dict = {'kind': 'Deployment', 'metadata': {'name': 'test'}}
        kubernetes.create_object_from_definition(
            deployment_dict, client=mock.Mock())
        api.create_namespaced_deployment.assert_called_once_with(
            body=deployment_dict, namespace='default')

    @mock.patch('k8sclient.client.apis.apiv_api.ApivApi')
    def test_create_service(self, api_v1):
        CONF.action.dry_run = False
        api = mock.Mock()
        api.create_namespaced_service = mock.Mock()
        api_v1.return_value = api

        service_dict = {'kind': 'Service', 'metadata': {'name': 'test'}}
        kubernetes.create_object_from_definition(
            service_dict, client=mock.Mock())

        api.create_namespaced_service.assert_called_once_with(
            body=service_dict, namespace='default')
