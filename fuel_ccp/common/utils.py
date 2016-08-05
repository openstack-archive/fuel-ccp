import os
import pkg_resources

from oslo_config import cfg
from oslo_log import log as logging
import yaml

import fuel_ccp


CONF = cfg.CONF
CONF.import_group('repositories', 'fuel_ccp.config.repositories')
CONF.import_opt("deploy_config", "fuel_ccp.config.cli")

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

    return cfg
