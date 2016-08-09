import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('repositories', 'fuel_ccp.config.repositories')

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


def _get_dep(service_map):
    pres_set = set([])
    deps_set = set([])
    dependencies = set([])

    for container in service_map['service']['containers']:
        dependencies.update(container['daemon'].get('dependencies', []))
        for pre in container.get('pre', []):
            if pre:
                pres_set.update([pre['name']])
                deps_set.update(pre.get('dependencies', []))

    dependencies.update(deps_set - pres_set)
    return list(dependencies)


def show_dep(component_name):
    components = CONF.repositories.names
    components_map = {}

    for component in components:
        service_dir = os.path.join(CONF.repositories.path,
                                   component,
                                   'service')
        if not os.path.isdir(service_dir):
            continue
        for service_file in os.listdir(service_dir):
            if YAML_FILE_RE.search(service_file):
                LOG.debug("Parse role file: %s", service_file)
                with open(os.path.join(service_dir, service_file), "r") as f:
                    role_obj = yaml.load(f)
                components_map[service_file.split('.')[0]] = role_obj

    try:
        dependencies = _get_dep(components_map[component_name])
    except KeyError:
        msg = "Wrong name of component or repositories are not cloned"
        raise RuntimeError(msg)

    print(", ".join(dependencies))
