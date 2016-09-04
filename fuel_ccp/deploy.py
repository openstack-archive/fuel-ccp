import json
import os
import re

from oslo_log import log as logging

from fuel_ccp.common import jinja_utils
from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp import kubernetes
from fuel_ccp import templates
from fuel_ccp.validation import base as base_validation
from fuel_ccp.validation import deploy as deploy_validation


CONF = config.CONF

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


def _update_container_volumes(cont, jvars):
    """Loop though all volumes and render jinja2 templates, if available"""

    for v in cont.get('volumes', {}):
        v['path'] = jinja_utils.jinja_render_str(v['path'], jvars)
        if v.get('mount-path'):
            v['mount-path'] = jinja_utils.jinja_render_str(v['mount-path'],
                                                           jvars)


def parse_role(service_dir, role, config):
    service = role["service"]
    if service["name"] not in config.get("topology", {}):
        LOG.info("Service %s not in topology config, skipping deploy",
                 service["name"])
        return
    LOG.info("Scheduling service %s deployment", service["name"])
    _expand_files(service, role.get("files"))

    _create_files_configmap(service_dir, service["name"], role.get("files"))
    _create_meta_configmap(service)

    workflows = _parse_workflows(service)
    _create_workflow(workflows, service["name"])

    for cont in service["containers"]:
        daemon_cmd = cont["daemon"]
        daemon_cmd["name"] = cont["name"]

        _update_container_volumes(cont, config['configs'])
        _create_pre_jobs(service, cont)
        _create_post_jobs(service, cont)

    cont_spec = templates.serialize_daemon_pod_spec(service)
    affinity = templates.serialize_affinity(service, config["topology"])

    if service.get("daemonset", False):
        obj = templates.serialize_daemonset(service["name"], cont_spec,
                                            affinity)
    else:
        obj = templates.serialize_deployment(service["name"], cont_spec,
                                             affinity)
    kubernetes.create_object_from_definition(obj)

    _create_service(service, config["configs"])
    LOG.info("Service %s successfuly scheduled", service["name"])


def _parse_workflows(service):
    workflows = {}
    for cont in service["containers"]:
        job_wfs = _create_job_wfs(cont, service["name"])
        workflows.update(job_wfs)

        wf = {}
        _create_pre_commands(wf, cont)
        _create_daemon(wf, cont)
        _create_post_commands(wf, cont)
        workflows.update({cont["name"]: json.dumps(
            {"workflow": wf}, sort_keys=True)})
    return workflows


def _create_job_wfs(container, service_name):
    wfs = {}
    for job in container.get("pre", ()):
        if _is_single_job(job):
            wfs.update(_create_job_wf(job))
    for job in container.get("post", ()):
        if _is_single_job(job):
            wfs.update(_create_job_wf(job, True, service_name))
    return wfs


def _fill_cmd(workflow, cmd):
    workflow.update({"command": cmd["command"]})
    if "user" in cmd:
        workflow.update({"user": cmd["user"]})


def _create_workflow(workflow, name):
    configmap_name = "%s-%s" % (name, templates.ROLE_CONFIG)
    template = templates.serialize_configmap(configmap_name, workflow)
    kubernetes.create_object_from_definition(template)


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
        _create_command(workflow["pre"], cmd)


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
    readiness_cmd = container.get("probes", {}).get("readiness")
    if readiness_cmd:
        workflow["readiness"] = readiness_cmd


def _create_post_commands(workflow, container):
    LOG.debug("Create post jobs")
    workflow["post"] = []
    for cmd in container.get("post", ()):
        _create_command(workflow["post"], cmd)


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


def _create_command(workflow, cmd):
    if cmd.get("type", "local") == "local":
        cmd_flow = {}
        _fill_cmd(cmd_flow, cmd)
        workflow.append(cmd_flow)


def _create_job_wf(job, post=False, service_name=None):
    wrk = {}
    wrk["name"] = job["name"]
    wrk["dependencies"] = job.get("dependencies", [])
    if post:
        wrk["dependencies"].append(service_name)
    wrk["job"] = {}
    _fill_cmd(wrk["job"], job)
    _push_files_to_workflow(wrk, job.get("files"))
    return {job["name"]: json.dumps({"workflow": wrk}, sort_keys=True)}


def _push_files_to_workflow(workflow, files):
    if not files:
        return
    workflow["files"] = [{
        "name": filename,
        "path": f["path"],
        "perm": f.get("perm"),
        "user": f.get("user")
    } for filename, f in sorted(files.items())]


def _create_globals_configmap(config):
    data = {
        templates.GLOBAL_CONFIG: json.dumps(config, sort_keys=True)
    }
    cm = templates.serialize_configmap(templates.GLOBAL_CONFIG, data)
    kubernetes.create_object_from_definition(cm)


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
    kubernetes.create_object_from_definition(cm)


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
    kubernetes.create_object_from_definition(template)


def _create_meta_configmap(service):
    configmap_name = "%s-%s" % (service["name"], templates.META_CONFIG)
    data = {
        templates.META_CONFIG: json.dumps(
            {"service-name": service["name"],
             "host-net": service.get("host-net", False)}, sort_keys=True)
    }
    template = templates.serialize_configmap(configmap_name, data)
    kubernetes.create_object_from_definition(template)


def _make_topology(nodes, roles):
    failed = False
    # TODO(sreshetniak): move it to validation
    if not nodes:
        LOG.error("Nodes section is not specified in configs")
        failed = True
    if not roles:
        LOG.error("Roles section is not specified in configs")
        failed = True
    if failed:
        raise RuntimeError("Failed to create topology for services")

    # TODO(sreshetniak): add validation
    k8s_nodes = kubernetes.list_k8s_nodes()
    k8s_node_names = kubernetes.get_object_names(k8s_nodes)

    def find_match(glob):
        matcher = re.compile(glob)
        nodes = []
        for node in k8s_node_names:
            match = matcher.match(node)
            if match:
                nodes.append(node)
        return nodes

    roles_to_node = {}
    for node in nodes.keys():
        matched_nodes = find_match(node)
        for role in nodes[node]["roles"]:
            roles_to_node.setdefault(role, [])
            roles_to_node[role].extend(matched_nodes)
    service_to_node = {}
    for role in roles.keys():
        if role in roles_to_node:
            for svc in roles[role]:
                service_to_node.setdefault(svc, [])
                service_to_node[svc].extend(roles_to_node[role])
        else:
            LOG.warning("Role '%s' defined, but unused", role)
    return service_to_node


def _create_namespace(namespace):
    if CONF.action.dry_run:
        return

    template = templates.serialize_namespace(namespace)
    kubernetes.create_object_from_definition(template)


def _create_openrc(config, namespace):
    openrc = ["export OS_PROJECT_DOMAIN_NAME=default",
              "export OS_USER_DOMAIN_NAME=default",
              "export OS_PROJECT_NAME=%s" % config['openstack_project_name'],
              "export OS_USERNAME=%s" % config['openstack_user_name'],
              "export OS_PASSWORD=%s" % config['openstack_user_password'],
              "export OS_IDENTITY_API_VERSION=3",
              "export OS_AUTH_URL=http://keystone.%s.svc.cluster.local:%s/v3" %
              (namespace, config['keystone_public_port'])]
    with open('openrc-%s' % namespace, 'w') as openrc_file:
        openrc_file.write("\n".join(openrc))
    LOG.info("Openrc file for this deployment created at %s/openrc-%s",
             os.getcwd(), namespace)


def deploy_components(components=None):
    components_map = utils.get_deploy_components_info()
    components = set(components) if components else set(components_map.keys())

    base_validation.validate_components_names(components, components_map)
    deploy_validation.validate_requested_components(components, components_map)

    if CONF.action.export_dir:
        os.makedirs(os.path.join(CONF.action.export_dir, 'configmaps'))

    config = utils.get_global_parameters("configs", "nodes", "roles")
    config["topology"] = _make_topology(config.get("nodes"),
                                        config.get("roles"))

    namespace = CONF.kubernetes.namespace
    _create_namespace(namespace)

    _create_globals_configmap(config["configs"])
    _create_start_script_configmap()

    for component in components:
        parse_role(components_map[component]['service_dir'],
                   components_map[component]['service_content'],
                   config)

    if 'keystone' in components:
        _create_openrc(config['configs'], namespace)
