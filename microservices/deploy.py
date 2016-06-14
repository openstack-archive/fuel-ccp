import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging

from microservices.common import jinja_utils
from microservices import kubernetes


CONF = cfg.CONF
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')
YAML_J2_FILE_RE = re.compile(r'\.yaml\.j2$')
J2_FILE_EXTENSION = re.compile(r'\.j2')


def render_k8s_yaml(k8s_yaml):
    content = jinja_utils.jinja_render(k8s_yaml)
    return yaml.load_all(content)


def create_k8s_objects(k8s_objects):
    for k8s_object in k8s_objects:
        kubernetes.create_object_from_definition(k8s_object)


def deploy_component(component):
    service_dir = os.path.join(CONF.repositories.path, component, 'service')

    if not os.path.isdir(service_dir):
        return

    for service_file in os.listdir(service_dir):
        k8s_objects = []
        if YAML_FILE_RE.search(service_file):
            k8s_objects = yaml.load_all(os.path.join(
                service_dir, service_file))
        elif YAML_J2_FILE_RE.search(service_file):
            k8s_objects = render_k8s_yaml(
                os.path.join(service_dir, service_file))

        create_k8s_objects(k8s_objects)


def _create_namespace():
    namespace = CONF.kubernetes.environment
    client = kubernetes.get_client()
    api = kubernetes.get_v1_api(client)
    # TODO(sreshetniak): add selector??
    namespaces = api.list_namespaced_namespace().items
    for ns in namespaces:
        if ns.metadata.name == namespace:
            LOG.info("Namespace \"%s\" exists", namespace)
            break
    else:
        LOG.info("Create namespace \"%s\"", namespace)
        api.create_namespaced_namespace(
            body={"metadata": {"name": namespace}})


def deploy_components(components=None):
    if components is None:
        components = CONF.repositories.names

    _create_namespace()

    for component in components:
        deploy_component(component)
