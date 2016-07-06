import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging

from fuel_ccp.common import utils
from fuel_ccp import kubernetes
from fuel_ccp import templates


CONF = cfg.CONF
CONF.import_group('repositories', 'fuel_ccp.config.repositories')
CONF.import_opt("action", "fuel_ccp.config.cli")
CONF.import_opt("deploy_config", "fuel_ccp.config.cli")

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


def _expand_files(service, files):
    def _expand(cmd):
        if cmd.get("files"):
            cmd["files"] = {f: files[f] for f in cmd["files"]}

    for cont in service["containers"]:
        _expand(cont["daemon"])
        for cmd in cont.get("pre", ()):
            _expand(cmd)
        for cmd in cont.get("post", ()):
            _expand(cmd)


def parse_role(service_dir, role, config):
    service = role["service"]
    LOG.info("Using service %s", service["name"])
    _expand_files(service, role.get("files"))

    _create_files_configmap(service_dir, service["name"], role.get("files"))
    _create_meta_configmap(service)

    workflows = _parse_workflows(service)
    _create_workflow(workflows, service["name"])

    for cont in service["containers"]:
        daemon_cmd = cont["daemon"]
        daemon_cmd["name"] = cont["name"]

        _create_pre_jobs(service, cont)
        _create_post_jobs(service, cont)

    cont_spec = templates.serialize_daemon_pod_spec(service)
    affinity = templates.serialize_affinity(service, config.get("topology"))

    if service.get("daemonset", False):
        obj = templates.serialize_daemonset(service["name"], cont_spec,
                                            affinity)
    else:
        obj = templates.serialize_deployment(service["name"], cont_spec,
                                             affinity)
    kubernetes.create_object_from_definition(obj)

    _create_service(service, config["configs"])


def _parse_workflows(service):
    workflows = {}
    for cont in service["containers"]:
        job_wfs = _create_job_wfs(cont, service["name"])
        workflows.update(job_wfs)

        wf = {}
        _create_pre_commands(wf, cont)
        _create_daemon(wf, cont)
        _create_post_commands(wf, cont)
        workflows.update({cont["name"]: yaml.dump({"workflow": wf})})
    return workflows


def _create_job_wfs(container, service_name):
    wfs = {}
    for job in container.get("pre", ()):
        if _is_single_job(job):
            wfs.update(_create_job_wf(container, job))
    for job in container.get("post", ()):
        if _is_single_job(job):
            wfs.update(_create_job_wf(container, job, True, service_name))
    return wfs


def _fill_cmd(workflow, cmd):
    workflow.update({"command": cmd["command"]})
    if "user" in cmd:
        workflow.update({"user": cmd["user"]})


def _create_workflow(workflow, name):
    configmap_name = "%s-%s" % (name, templates.ROLE_CONFIG)
    template = templates.serialize_configmap(configmap_name, workflow)
    kubernetes.handle_exists(
        kubernetes.create_object_from_definition, template)


def _create_service(service, config):
    template_ports = service.get("ports")
    if not template_ports:
        return
    ports = []
    for port in service["ports"]:
        source_port, _, node_port = str(port).partition(":")
        source_port = int(config.get(source_port, source_port))
        if node_port:
            node_port = int(config.get(node_port, node_port))
        name_port = str(source_port)
        if node_port:
            ports.append({"port": source_port, "name": name_port,
                          "node-port": node_port})
        else:
            ports.append({"port": source_port, "name": name_port})
    template = templates.serialize_service(service["name"], ports)
    kubernetes.create_object_from_definition(template)


def _create_pre_commands(workflow, container):
    workflow["pre"] = []
    for cmd in container.get("pre", ()):
        _create_command(workflow["pre"], container, cmd)


def _create_daemon(workflow, container):
    workflow["name"] = container["name"]
    daemon = container["daemon"]
    workflow["dependencies"] = []
    # TODO(sreshetniak): add files from job
    for cmd in container.get("pre", ()):
        if cmd.get("type", "local") == "single":
            workflow["dependencies"].append(cmd["name"])
    workflow["dependencies"].extend(daemon.get("dependencies", ()))
    workflow["daemon"] = {}
    _fill_cmd(workflow["daemon"], daemon)
    _push_files_to_workflow(workflow, daemon.get("files"))


def _create_post_commands(workflow, container):
    LOG.debug("Create post jobs")
    workflow["post"] = []
    for cmd in container.get("post", ()):
        _create_command(workflow["post"], container, cmd)


def _is_single_job(job):
    return job.get("type", "local") == "single"


def _create_pre_jobs(service, container):
    for job in container.get("pre", ()):
        if _is_single_job(job):
            _create_job(service, container, job)


def _create_post_jobs(service, container):
    for job in container.get("post", ()):
        if _is_single_job(job):
            _create_job(service, container, job)


def _create_job(service, container, job):
    cont_spec = templates.serialize_job_container_spec(container, job)
    pod_spec = templates.serialize_job_pod_spec(service, job, cont_spec)
    job_spec = templates.serialize_job(job["name"], pod_spec)
    kubernetes.create_object_from_definition(job_spec)


def _create_command(workflow, container, cmd):
    if cmd.get("type", "local") == "local":
        cmd_flow = {}
        _fill_cmd(cmd_flow, cmd)
        workflow.append(cmd_flow)


def _create_job_wf(container, job, post=False, service_name=None):
    wrk = {}
    wrk["name"] = job["name"]
    wrk["dependencies"] = job.get("dependencies", [])
    if post:
        wrk["dependencies"].append(service_name)
    wrk["job"] = {}
    _fill_cmd(wrk["job"], job)
    _push_files_to_workflow(wrk, job.get("files"))
    return {job["name"]: yaml.dump({"workflow": wrk})}


def _push_files_to_workflow(workflow, files):
    if not files:
        return
    workflow["files"] = [{
        "name": filename,
        "path": f["path"],
        "perm": f.get("perm"),
        "user": f.get("user")
    } for filename, f in files.items()]


def _create_globals_configmap(config):
    data = {
        templates.GLOBAL_CONFIG: yaml.dump(config)
    }
    cm = templates.serialize_configmap(templates.GLOBAL_CONFIG, data)
    kubernetes.handle_exists(kubernetes.create_object_from_definition, cm)


def _create_start_script_configmap():
    start_scr_path = os.path.join(CONF.repositories.path,
                                  "fuel-ccp-entrypoint",
                                  "ms_ext_config",
                                  "start_script.py")
    with open(start_scr_path) as f:
        start_scr_data = f.read()

    data = {
        templates.SCRIPT_CONFIG: start_scr_data
    }
    cm = templates.serialize_configmap(templates.SCRIPT_CONFIG, data)
    kubernetes.handle_exists(kubernetes.create_object_from_definition, cm)


def _create_files_configmap(service_dir, service_name, configs):
    configmap_name = "%s-%s" % (service_name, templates.FILES_CONFIG)
    data = {}
    if configs:
        for filename, f in configs.items():
            with open(os.path.join(
                    service_dir, "files", f["content"]), "r") as f:
                data[filename] = f.read()
    data["placeholder"] = ""
    template = templates.serialize_configmap(configmap_name, data)
    kubernetes.handle_exists(
        kubernetes.create_object_from_definition, template)


def _create_meta_configmap(service):
    configmap_name = "%s-%s" % (service["name"], templates.META_CONFIG)
    data = {
        templates.META_CONFIG: yaml.dump(
            {"service-name": service["name"],
             "host-net": service.get("host-net", False)})
    }
    template = templates.serialize_configmap(configmap_name, data)
    kubernetes.handle_exists(
        kubernetes.create_object_from_definition, template)


def deploy_component(component, config):
    service_dir = os.path.join(CONF.repositories.path, component, 'service')

    if not os.path.isdir(service_dir):
        return

    for service_file in os.listdir(service_dir):
        if YAML_FILE_RE.search(service_file):
            LOG.debug("Parse role file: %s", service_file)
            with open(os.path.join(service_dir, service_file), "r") as f:
                role_obj = yaml.load(f)

            parse_role(service_dir, role_obj, config)


def _make_topology(nodes, roles):
    if not (nodes and roles):
        LOG.debug("Topology is not specified")
        return {}

    # TODO(sreshetniak): add validation
    k8s_nodes = kubernetes.list_k8s_nodes()

    def find_match(glob):
        matcher = re.compile(glob)
        nodes = []
        for node in k8s_nodes:
            match = matcher.match(node)
            if match:
                nodes.append(match.group(0))
        return nodes

    roles_to_node = {}
    for node in nodes.keys():
        matched_nodes = find_match(node)
        for role in nodes[node]["roles"]:
            roles_to_node.setdefault(role, [])
            roles_to_node[role].extend(matched_nodes)
    service_to_node = {}
    for role in roles.keys():
        for svc in roles[role]:
            service_to_node.setdefault(svc, [])
            service_to_node[svc].extend(roles_to_node[role])
    return service_to_node


def _create_namespace():
    if CONF.action.dry_run:
        return
    namespace = CONF.kubernetes.namespace
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

    config = utils.get_global_parameters("configs", "nodes", "roles")
    config["topology"] = _make_topology(config.get("nodes"),
                                        config.get("roles"))
    _create_globals_configmap(config["configs"])
    _create_start_script_configmap()

    for component in components:
        deploy_component(component, config)
