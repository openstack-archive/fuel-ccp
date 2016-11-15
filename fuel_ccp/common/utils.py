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


def get_ingress_domains(components=None):
    components_map = get_deploy_components_info()
    components = components or components_map.keys()
    domains = []
    for component in components:
        service = components_map[component]["service_content"]["service"]
        for port in service.get("ports", []):
            if port.get("ingress"):
                domains.append(get_ingress_host(port.get("ingress")))
    return domains


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


def address(service, port=None, external=False, with_scheme=False):
    addr = None
    scheme = 'http'
    if external:
        if not port:
            raise RuntimeError('Port config is required for external address')
        if CONF.configs.ingress.enabled and port.get('ingress'):
            scheme = 'https'
            addr = "%s:%s" % (get_ingress_host(port['ingress']),
                              CONF.configs.ingress.port)
        elif port.get('node'):
            addr = '%s:%s' % (CONF.configs.k8s_external_ip, port['node'])

    if addr is None:
        addr = '%s.%s' % (service, CONF.kubernetes.namespace)
        if port:
            addr = '%s:%s' % (addr, port['cont'])

    if with_scheme:
        addr = "%s://%s" % (scheme, addr)

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

        component = {
            "name": component_name,
            "upgrades": {},
            "service_dir": service_dir,
        }

        upgrade_dir = os.path.join(service_dir, "upgrade")
        if os.path.isdir(upgrade_dir):
            for upgrade_fname in os.listdir(upgrade_dir):
                if not upgrade_fname.endswith('.yaml'):
                    continue
                LOG.debug("Loading upgrade definition: %s", upgrade_fname)
                with open(os.path.join(upgrade_dir, upgrade_fname)) as f:
                    upgrade_def = yaml.load(f)
                key = upgrade_fname[:-len('.yaml')]
                component['upgrades'][key] = upgrade_def

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
                    'component': component,
                    'component_name': component_name,
                    'service_dir': service_dir,
                    'service_content': service_definition
                }
    return components_map


def get_deployed_components():
    """Returns set of deployed components."""
    deployed_deployments = kubernetes.list_cluster_deployments()
    deployed_components = set(
        kubernetes.get_object_names(deployed_deployments)
    )
    return deployed_components


def merge_configs(source, destination):
    """Creates a recursive dicts merge."""
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge_configs(value, node)
        else:
            destination[key] = value

    return destination
