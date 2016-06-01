from k8sclient.client import api_client
from k8sclient.client.apis import apisbatchv_api
from k8sclient.client.apis import apisextensionsvbeta_api
from k8sclient.client.apis import apiv_api

from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('kubernetes', 'microservices.config.kubernetes')

LOG = logging.getLogger(__name__)


def get_client(kube_apiserver=None, key_file=None, cert_file=None,
               ca_certs=None):
    kube_apiserver = kube_apiserver or CONF.kubernetes.server
    key_file = key_file or CONF.kubernetes.key_file
    cert_file = cert_file or CONF.kubernetes.cert_file
    ca_certs = ca_certs or CONF.kubernetes.ca_certs

    return api_client.ApiClient(host=kube_apiserver, key_file=key_file,
                                cert_file=cert_file, ca_certs=ca_certs)


def create_object_from_definition(object_dict, namespace=None, client=None):
    namespace = namespace or CONF.kubernetes.environment
    client = client or get_client()
    if object_dict['kind'] == 'Deployment':
        api = apisextensionsvbeta_api.ApisextensionsvbetaApi(client)
        resp = api.create_namespaced_deployment(
            body=object_dict, namespace=namespace)
    elif object_dict['kind'] == 'DaemonSet':
        api = apisextensionsvbeta_api.ApisextensionsvbetaApi(client)
        resp = api.create_namespaced_daemon_set(
            body=object_dict, namespace=namespace)
    elif object_dict['kind'] == 'Service':
        api = apiv_api.ApivApi(client)
        resp = api.create_namespaced_service(
            body=object_dict, namespace=namespace)
    elif object_dict['kind'] == 'Pod':
        api = apiv_api.ApivApi(client)
        resp = api.create_namespaced_pod(
            body=object_dict, namespace=namespace)
    elif object_dict["kind"] == "Job":
        api = apisbatchv_api.ApisbatchvApi(client)
        resp = api.create_namespaced_job(
            body=object_dict, namespace=namespace)
    elif object_dict["kind"] == "ConfigMap":
        api = apiv_api.ApivApi(client)
        resp = api.create_namespaced_config_map(
            body=object_dict, namespace=namespace)
    else:
        LOG.warning('"%s" object is not supported, skipping.'
                    % object_dict['kind'])
        return

    LOG.info('%s "%s" has been created' % (
        object_dict['kind'], object_dict['metadata']['name']))
    return resp
