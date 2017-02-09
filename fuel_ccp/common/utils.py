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


def get_repositories_paths():
    """Get repositories paths.

    :returns: list -- list of full repositories paths
    """
    paths = []
    for repo in CONF.repositories.repos:
        paths.append(os.path.join(CONF.repositories.path, repo["name"]))
    return paths


def get_config_paths():
    paths = []
    # Order does matter. At first we add global defaults.
    for conf_path in ("resources/defaults.yaml", "resources/globals.yaml"):
        paths.append(get_resource_path(conf_path))

    # After we add component defaults.
    for repo in get_repositories_paths():
        paths.append(os.path.join(repo, "service", "files", "defaults.yaml"))

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
        addr = '.'.join((service, CONF.kubernetes.namespace, 'svc',
                         CONF.kubernetes.cluster_domain))
        if port:
            addr = '%s:%s' % (addr, port['cont'])

    if with_scheme:
        addr = "%s://%s" % (scheme, addr)

    return addr


def get_repositories_exports():
    """Load shared templates from ./exports dirs of the repositories. """
    exports = dict()
    for repo in get_repositories_paths():
        exports_dir = os.path.join(repo, 'exports')
        if os.path.exists(exports_dir) and os.path.isdir(exports_dir):
            for export_file in os.listdir(exports_dir):
                # Due to k8s keys constraints we need to remove non-alpha
                cm_key = ''.join([c for c in export_file if c.isalpha()])
                path = os.path.join(exports_dir, export_file)
                LOG.debug('Found shared jinja template file %s', path)
                if cm_key not in exports:
                    exports[cm_key] = {'name': export_file, 'body': ''}
                # Merge the files with same name
                with open(path) as f:
                    exports[cm_key]['body'] += f.read() + '\n'
    return exports


def get_component_name_from_repo_path(path):
    REPO_NAME_PREFIX = "fuel-ccp-"
    name = os.path.basename(path)
    if name.startswith(REPO_NAME_PREFIX):
        name = name[len(REPO_NAME_PREFIX):]
    return name


def get_deploy_components_info(rendering_context=None):
    if rendering_context is None:
        rendering_context = CONF.configs
    components_map = {}

    for repo in get_repositories_paths():
        service_dir = os.path.join(repo, "service")
        if not os.path.isdir(service_dir):
            continue
        component_name = get_component_name_from_repo_path(repo)

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
    deployed_statefulsets = kubernetes.list_cluster_statefulsets()
    deployed_components = set(kubernetes.get_object_names(
        itertools.chain(deployed_deployments, deployed_statefulsets))
    )
    return deployed_components
