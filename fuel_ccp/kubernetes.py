import os
import yaml

from k8sclient.client import api_client
from k8sclient.client.apis import apisbatchv_api
from k8sclient.client.apis import apisextensionsvbeta_api
from k8sclient.client.apis import apiv_api
import k8sclient.client.rest
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_opt("action", "fuel_ccp.config.cli")
CONF.import_group('kubernetes', 'fuel_ccp.config.kubernetes')

LOG = logging.getLogger(__name__)


def get_client(kube_apiserver=None, key_file=None, cert_file=None,
               ca_certs=None):
    kube_apiserver = kube_apiserver or CONF.kubernetes.server
    key_file = key_file or CONF.kubernetes.key_file
    cert_file = cert_file or CONF.kubernetes.cert_file
    ca_certs = ca_certs or CONF.kubernetes.ca_certs

    return api_client.ApiClient(host=kube_apiserver, key_file=key_file,
                                cert_file=cert_file, ca_certs=ca_certs)


def create_object_from_definition(object_dict, namespace=None, client=None,
                                  update=False):
    LOG.debug("Deploying %s: \"%s\"",
              object_dict["kind"], object_dict["metadata"]["name"])
    if getattr(CONF.action, 'export_dir', False):
        file_name = '%s-%s.yaml' % (
            object_dict['metadata']['name'], object_dict['kind'].lower())
        if object_dict['kind'] == 'ConfigMap':
            file_path = os.path.join(
                CONF.action.export_dir, 'configmaps', file_name)
        else:
            file_path = os.path.join(CONF.action.export_dir, file_name)
        with open(file_path, 'w') as object_file:
            object_file.write(yaml.dump(
                object_dict, default_flow_style=False))

    if getattr(CONF.action, 'dry_run', False):
        LOG.info(yaml.dump(object_dict, default_flow_style=False))
        return

    namespace = namespace or CONF.kubernetes.namespace
    client = client or get_client()
    if object_dict['kind'] == 'Deployment':
        api = apisextensionsvbeta_api.ApisextensionsvbetaApi(client)
        if update:
            resp = api.patch_namespaced_deployment(
                body=object_dict, namespace=namespace,
                name=object_dict['metadata']['name'])
        else:
            resp = api.create_namespaced_deployment(
                body=object_dict, namespace=namespace)
    elif object_dict['kind'] == 'DaemonSet':
        if update:
            return
        api = apisextensionsvbeta_api.ApisextensionsvbetaApi(client)
        resp = api.create_namespaced_daemon_set(
            body=object_dict, namespace=namespace)
    elif object_dict['kind'] == 'Service':
        api = apiv_api.ApivApi(client)
        if update:
            resp = api.patch_namespaced_service(
                body=object_dict, namespace=namespace,
                name=object_dict['metadata']['name'])
        else:
            resp = api.create_namespaced_service(
                body=object_dict, namespace=namespace)
    elif object_dict['kind'] == 'Pod':
        api = apiv_api.ApivApi(client)
        resp = api.create_namespaced_pod(
            body=object_dict, namespace=namespace)
    elif object_dict["kind"] == "Job":
        if update:
            return
        api = apisbatchv_api.ApisbatchvApi(client)
        resp = api.create_namespaced_job(
            body=object_dict, namespace=namespace)
    elif object_dict["kind"] == "ConfigMap":
        api = apiv_api.ApivApi(client)
        if update:
            resp = api.patch_namespaced_config_map(
                body=object_dict, namespace=namespace,
                name=object_dict['metadata']['name'])
        else:
            resp = api.create_namespaced_config_map(
                body=object_dict, namespace=namespace)
    else:
        LOG.warning('"%s" object is not supported, skipping.'
                    % object_dict['kind'])
        return

    if update:
        LOG.debug('%s "%s" has been updated' % (
        object_dict['kind'], object_dict['metadata']['name']))
    else:
        LOG.debug('%s "%s" has been created' % (
            object_dict['kind'], object_dict['metadata']['name']))
    return resp


def get_v1_api(client):
    return apiv_api.ApivApi(client)


def list_k8s_nodes():
    api = get_v1_api(get_client())
    return api.list_namespaced_node().items


def list_cluster_daemonsets():
    client = get_client()
    api = apisextensionsvbeta_api.ApisextensionsvbetaApi(client)
    return api.list_namespaced_daemon_set(
        namespace=CONF.kubernetes.namespace,
        label_selector="ccp=true").items


def list_cluster_deployments():
    client = get_client()
    api = apisextensionsvbeta_api.ApisextensionsvbetaApi(client)
    return api.list_namespaced_deployment(
        namespace=CONF.kubernetes.namespace,
        label_selector="ccp=true").items


def get_object_names(items):
    names = []
    for item in items:
        names.append(item.metadata.name)
    return names


def handle_exists(fct, *args, **kwargs):
    try:
        fct(*args, **kwargs)
    except k8sclient.client.rest.ApiException as e:
        if e.status == 409:
            kwargs['update'] = True
            LOG.debug('Updating configmap')
            fct(*args, **kwargs)
        else:
            raise e
