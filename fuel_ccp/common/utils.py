import os
import pkg_resources

from oslo_log import log as logging
import yaml

import fuel_ccp
from fuel_ccp.common import jinja_utils
from fuel_ccp import config
from fuel_ccp import kubernetes


CONF = config.CONF

LOG = logging.getLogger(__name__)


def k8s_name(*args):
    return "-".join(tuple(args)).replace("_", "-")


def get_resource_path(path):
    return pkg_resources.resource_filename(fuel_ccp.version_info.package, path)


def get_global_parameters(*config_groups):
    cfg = {}
    components = list(CONF.repositories.names)
    paths = []
    # Order does matter. At first we add global defaults.
    for conf_path in ("resources/defaults.yaml", "resources/globals.yaml"):
        paths.append(get_resource_path(conf_path))

    # After we add component defaults.
    for component in components:
        paths.append(os.path.join(CONF.repositories.path, component,
                                  "service/files/defaults.yaml"))

    # And finaly we add cluster-wide globals conf, if provided.
    if CONF.deploy_config:
        paths.append(CONF.deploy_config)

    for path in paths:
        if os.path.isfile(path):
            LOG.debug("Adding parameters from \"%s\"", path)
            with open(path, "r") as f:
                data = yaml.load(f)
                for group in config_groups:
                    cfg.setdefault(group, {})
                    cfg[group].update(data.get(group, {}))
        else:
            LOG.debug("\"%s\" not found, skipping", path)

    for group in config_groups:
        cfg.setdefault(group, {})
        try:
            config_group = CONF[group]
        except KeyError:
            continue
        else:
            cfg[group].update(config_group._items())

    return cfg


def get_deploy_components_info(rendering_context=None):
    if rendering_context is None:
        rendering_context = get_global_parameters("configs")["configs"]
    components_map = {}

    for component in CONF.repositories.names:
        service_dir = os.path.join(CONF.repositories.path,
                                   component,
                                   'service')
        if not os.path.isdir(service_dir):
            continue
        for service_file in os.listdir(service_dir):
            if service_file.endswith('.yaml'):
                LOG.debug("Rendering service definition: %s", service_file)
                content = jinja_utils.jinja_render(
                    os.path.join(service_dir, service_file), rendering_context
                )
                LOG.debug("Parse service definition: %s", service_file)
                service_definition = yaml.load(content)
                service_name = service_definition['service']['name']
                components_map[service_name] = {
                    'service_dir': service_dir,
                    'service_content': service_definition
                }
    return components_map


def get_deployed_components():
    """Returns set of deployed components."""
    deployed_daemonsets = kubernetes.list_cluster_daemonsets()
    deployed_deployments = kubernetes.list_cluster_deployments()
    deployed_components = set(kubernetes.get_object_names(
        deployed_daemonsets + deployed_deployments))

    return deployed_components
