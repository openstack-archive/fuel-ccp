import logging
import os

import pykube
import yaml

from fuel_ccp import config

CONF = config.CONF

LOG = logging.getLogger(__name__)

UPDATABLE_OBJECTS = ('ConfigMap', 'Deployment', 'Service')


def get_client(kube_apiserver=None, key_file=None, cert_file=None,
               ca_cert=None, insecure=None):
    kube_apiserver = kube_apiserver or CONF.kubernetes.server
    key_file = key_file or CONF.kubernetes.key_file
    cert_file = cert_file or CONF.kubernetes.cert_file
    ca_cert = ca_cert or CONF.kubernetes.ca_cert
    insecure = insecure or CONF.kubernetes.insecure

    cluster = {"server": kube_apiserver}
    if ca_cert:
        cluster["certificate-authority"] = ca_cert
    elif insecure:
        cluster['insecure-skip-tls-verify'] = insecure

    user = {}
    if cert_file and key_file:
        user["client-certificate"] = cert_file
        user["client-key"] = key_file

    config = {
        "clusters": [
            {
                "name": "ccp",
                "cluster": cluster
            }
        ],
        "users": [
            {
                "name": "ccp",
                "user": user
            }
        ],
        "contexts": [
            {
                "name": "ccp",
                "context": {
                    "cluster": "ccp",
                    "user": "ccp"
                },
            }
        ],
        "current-context": "ccp"
    }
    return pykube.HTTPClient(pykube.KubeConfig(config))


def export_object(object_dict):
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


def _reload_obj(obj, updated_dict):
    obj.reload()
    obj.obj = updated_dict


def process_object(object_dict, namespace=None, client=None):
    LOG.debug("Deploying %s: \"%s\"",
              object_dict["kind"], object_dict["metadata"]["name"])
    if not object_dict['kind'] == 'Namespace':
        if CONF.action.export_dir:
            export_object(object_dict)
        if CONF.action.dry_run:
            LOG.info(yaml.dump(object_dict, default_flow_style=False))
            return

        object_dict['metadata']['namespace'] = (
            namespace or CONF.kubernetes.namespace)

    obj_class = getattr(pykube, object_dict["kind"], None)
    if not obj_class:
        LOG.warning('"%s" object is not supported, skipping.'
                    % object_dict['kind'])
        return

    client = client or get_client()
    obj = obj_class(client, object_dict)
    if obj.exists():
        LOG.debug('%s "%s" already exists', object_dict['kind'],
                  object_dict['metadata']['name'])
        if object_dict['kind'] in UPDATABLE_OBJECTS:
            if object_dict['kind'] == 'Service':
                # Reload object and merge new and old fields
                _reload_obj(obj, object_dict)
            obj.update()
            LOG.debug('%s "%s" has been updated', object_dict['kind'],
                      object_dict['metadata']['name'])
        if object_dict['kind'] == 'DaemonSet':
            LOG.warning('%s will not be updated (DaemonSet objects cannot be '
                        'updated' % object_dict['metadata']['name'])
    else:
        obj.create()
        LOG.debug('%s "%s" has been created', object_dict['kind'],
                  object_dict['metadata']['name'])
    return obj


def list_k8s_nodes():
    client = get_client()
    return pykube.Node.objects(client).all()


def list_cluster_daemonsets():
    client = get_client()
    return pykube.DaemonSet.objects(client).filter(
        namespace=CONF.kubernetes.namespace,
        selector="ccp=true")


def list_cluster_deployments():
    client = get_client()
    return pykube.Deployment.objects(client).filter(
        namespace=CONF.kubernetes.namespace,
        selector="ccp=true")


def list_cluster_pods(service=None):
    selector = "ccp=true"
    if service:
        selector = ",".join((selector, "app=%s" % service))
    client = get_client()
    return pykube.Pod.objects(client).filter(
        namespace=CONF.kubernetes.namespace,
        selector=str(selector))


def list_cluster_jobs():
    client = get_client()
    return pykube.Job.objects(client).filter(
        namespace=CONF.kubernetes.namespace,
        selector="ccp=true")


def list_cluster_services():
    client = get_client()
    return pykube.Service.objects(client).filter(
        namespace=CONF.kubernetes.namespace,
        selector="ccp=true")


def get_object_names(items):
    names = []
    for item in items:
        names.append(item.name)
    return names
