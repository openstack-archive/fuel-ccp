import itertools
import logging
import os
import pkg_resources

import yaml

import fuel_ccp
from fuel_ccp.common import jinja_utils
from fuel_ccp import config
from fuel_ccp import kubernetes


CONF = config.CONF

LOG = logging.getLogger(__name__)


def get_ingress_host(ingress_name):
    return '.'.join((
        ingress_name, CONF.kubernetes.namespace, CONF.configs.ingress.domain))


def get_resource_path(path):
    return pkg_resources.resource_filename(fuel_ccp.version_info.package, path)


def get_config_paths():
    components = [d['name'] for d in CONF.repositories.repos]
    paths = []
    # Order does matter. At first we add global defaults.
    for conf_path in ("resources/defaults.yaml", "resources/globals.yaml"):
        paths.append(get_resource_path(conf_path))

    # After we add component defaults.
    for component in components:
        paths.append(os.path.join(CONF.repositories.path, component,
                                  "service/files/defaults.yaml"))

    return paths


def address(service, port=None, external=False, multiple=False, delimiter=','):
    addr = None
    if external:
        if not port:
            raise RuntimeError('Port config is required for external address')
        if CONF.configs.ingress.enabled and port.get('ingress'):
            addr = get_ingress_host(port['ingress'])
        elif port.get('node'):
            addr = '%s:%s' % (CONF.configs.k8s_external_ip, port['node'])

    if addr is None:
        addr = '%s.%s' % (service, CONF.kubernetes.namespace)
        if port:
            addr = '%s:%s' % (addr, port['cont'])
        if multiple:
            replicas = CONF.replicas.get(service, 1)
            urls = ['%s-%i.%s' % (service, pod_number, addr)
                    for pod_number in range(replicas)]
            addr = delimiter.join(urls)

    return addr


def get_deploy_components_info(rendering_context=None):
    if rendering_context is None:
        rendering_context = CONF.configs._dict
    components_map = {}

    for component_ref in CONF.repositories.repos:
        component_name = component_ref['name']
        service_dir = os.path.join(CONF.repositories.path,
                                   component_name,
                                   'service')
        if not os.path.isdir(service_dir):
            continue
        REPO_NAME_PREFIX = "fuel-ccp-"
        if component_name.startswith(REPO_NAME_PREFIX):
            component_name = component_name[len(REPO_NAME_PREFIX):]
        for service_file in os.listdir(service_dir):
            if service_file.endswith('.yaml'):
                LOG.debug("Rendering service definition: %s", service_file)
                content = jinja_utils.jinja_render(
                    os.path.join(service_dir, service_file), rendering_context,
                    functions=[address]
                )
                LOG.debug("Parse service definition: %s", service_file)
                service_definition = yaml.load(content)
                service_name = service_definition['service']['name']
                components_map[service_name] = {
                    'component_name': component_name,
                    'service_dir': service_dir,
                    'service_content': service_definition
                }
    return components_map


def get_deployed_components():
    """Returns set of deployed components."""
    deployed_daemonsets = kubernetes.list_cluster_daemonsets()
    deployed_deployments = kubernetes.list_cluster_deployments()
    deployed_petsets = kubernetes.list_cluster_petsets()
    deployed_components = set(kubernetes.get_object_names(
        itertools.chain(deployed_daemonsets, deployed_deployments,
                        deployed_petsets))
    )
    return deployed_components
