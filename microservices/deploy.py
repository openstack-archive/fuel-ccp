import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging
import pkg_resources

import microservices
from microservices import kubernetes
from microservices import templates


CONF = cfg.CONF
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)

DEFAULT_CONFIGMAP = "openstack-default-files"

YAML_FILE_RE = re.compile(r'\.yaml$')


def _expand_files(service, files):
    def _expand(cmd):
        if cmd.get("files"):
            cmd["files"] = {f: files[f] for f in cmd["files"]}

    _expand(service["daemon"])
    for cmd in service.get("pre", ()):
        _expand(cmd)
    for cmd in service.get("post", ()):
        _expand(cmd)


def parse_role(service_dir, role):
    service = role["service"]
    _expand_files(service, role.get("files"))

    workflow = {}

    create_pre_commands(workflow, service_dir, service)
    create_daemon(workflow, service_dir, service)
    create_post_commands(workflow, service_dir, service)
    _create_workflow(workflow, service["name"])

    daemon_cmd = service["daemon"]
    daemon_cmd["name"] = service["name"]
    create_configmap(service_dir, service, daemon_cmd)

    cont_spec = templates.serialize_container_spec(
        service, service["name"], daemon_cmd, DEFAULT_CONFIGMAP, "Always")
    dp = templates.serialize_deployment(service["name"], cont_spec)
    kubernetes.create_object_from_definition(dp)

    _create_service(service)


def _fill_cmd(workflow, cmd):
    workflow.update({"command": cmd["command"]})
    if "user" in cmd:
        workflow.update({"user": cmd["user"]})


def _create_workflow(workflow, name):
    template = templates.serialize_configmap(
        "%s-workflow" % name, {"workflow": yaml.dump({"workflow": workflow})})
    kubernetes.handle_exists(
        kubernetes.create_object_from_definition, template)


def _create_service(service):
    ports = []
    defaults = _get_defaults()
    for port in service.get("ports", ()):
        p = defaults.get(port)
        if p:
            ports.append({"port": int(p), "name": port})
        else:
            ports.append({"port": int(port), "name": str(port)})
    template = templates.serialize_service(service["name"], ports)
    kubernetes.create_object_from_definition(template)


def create_pre_commands(workflow, service_dir, service):
    LOG.debug("Create pre jobs")
    workflow["pre"] = []
    for cmd in service.get("pre", ()):
        create_command(workflow["pre"], service_dir, service, cmd)


def create_daemon(workflow, service_dir, service):
    workflow["name"] = service["name"]
    daemon = service["daemon"]
    workflow["dependencies"] = []
    for cmd in service.get("pre", ()):
        if cmd.get("type", "local") == "single":
            workflow["dependencies"].append(cmd["name"])
    workflow["dependencies"].extend(daemon.get("dependencies", ()))
    workflow["daemon"] = {}
    _fill_cmd(workflow["daemon"], daemon)
    push_files_to_workflow(workflow, daemon.get("files"))


def create_post_commands(workflow, service_dir, service):
    LOG.debug("Create post jobs")
    workflow["post"] = []
    for cmd in service.get("post", ()):
        create_command(workflow["post"], service_dir, service, cmd, "post")


def create_command(workflow, service_dir, service, cmd, cmd_type=None):
    if cmd.get("type", "local") == "local":
        cmd_flow = {}
        _fill_cmd(cmd_flow, cmd)
        workflow.append(cmd_flow)
    else:
        create_job(service_dir, service, cmd, cmd_type)


def create_job(service_dir, service, cmd, cmd_type=None):
    LOG.debug("Create %s job", cmd["name"])
    wrk = {}
    wrk["name"] = cmd["name"]
    wrk["dependencies"] = cmd.get("dependencies", [])
    if cmd_type == "post":
        wrk["dependencies"].append(service["name"])
    wrk["job"] = {}
    _fill_cmd(wrk["job"], cmd)
    push_files_to_workflow(wrk, cmd.get("files"))

    _create_workflow(wrk, cmd["name"])
    create_configmap(service_dir, service, cmd)
    cont_spec = templates.serialize_container_spec(
        service, cmd["name"], cmd, DEFAULT_CONFIGMAP, "OnFailure")
    job_template = templates.serialize_job(cmd["name"], cont_spec)
    LOG.debug("Job: %s", cmd["name"])
    kubernetes.create_object_from_definition(job_template)


def push_files_to_workflow(workflow, files):
    if not files:
        return
    workflow["files"] = [{
        "name": filename,
        "path": f["path"],
        "perm": f.get("perm"),
        "user": f.get("user")
    } for filename, f in files.items()]


def create_configmap(service_dir, service, cmd):
    configmap_name = cmd["name"]
    LOG.debug("Create configmap %s", configmap_name)
    data = {}
    if "files" not in cmd:
        return
    for filename, f in cmd["files"].items():
        with open(os.path.join(service_dir, "files", f["content"]), "r") as f:
            data[filename] = f.read()
    template = templates.serialize_configmap(configmap_name, data)
    kubernetes.handle_exists(
        kubernetes.create_object_from_definition, template)


def deploy_component(component):
    service_dir = os.path.join(CONF.repositories.path, component, 'service')

    if not os.path.isdir(service_dir):
        return

    for service_file in os.listdir(service_dir):
        if YAML_FILE_RE.search(service_file):
            LOG.debug("Parse role file: %s", service_file)
            with open(os.path.join(service_dir, service_file), "r") as f:
                role_obj = yaml.load(f)

            parse_role(service_dir, role_obj)


def _get_defaults():
    cfg = {}
    components = list(CONF.repositories.names)
    paths = []
    for component in components:
        paths.append(os.path.join(CONF.repositories.path, component,
                                  "service/files/defaults.yaml"))
    for conf_path in ("resources/defaults.yaml", "resources/globals.yaml"):
        paths.append(_get_resource_path(conf_path))

    for path in paths:
        if os.path.isfile(path):
            LOG.debug("Adding parameters from \"%s\"", path)
            with open(path, "r") as f:
                cfg.update(yaml.load(f).get("configs", {}))
        else:
            LOG.warning("\"%s\" not found, skipping", path)

    return cfg


def _push_defaults():
    cfg = _get_defaults()
    start_scr_path = os.path.join(CONF.repositories.path, "ms-ext-config",
                                  "ms_ext_config", "start_script.py")
    with open(start_scr_path, "r") as f:
        start_scr_data = f.read()
    cm_data = {
        "configs": yaml.dump(cfg),
        "start-script": start_scr_data
    }
    cm = templates.serialize_configmap(DEFAULT_CONFIGMAP, cm_data)
    kubernetes.handle_exists(kubernetes.create_object_from_definition, cm)


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


def _get_resource_path(path):
    return pkg_resources.resource_filename(
        microservices.version_info.package, path)


def _deploy_etcd():
    LOG.info("Creating etcd cluster")

    dp_path = _get_resource_path("resources/etcd-deployment.yaml")
    with open(dp_path) as f:
        obj = yaml.load(f)
    kubernetes.handle_exists(kubernetes.create_object_from_definition, obj)

    svc_path = _get_resource_path("resources/etcd-service.yaml")
    with open(svc_path) as f:
        obj = yaml.load(f)
    kubernetes.handle_exists(kubernetes.create_object_from_definition, obj)


def deploy_components(components=None):
    if components is None:
        components = CONF.repositories.names

    _create_namespace()
    _deploy_etcd()

    _push_defaults()

    for component in components:
        deploy_component(component)
