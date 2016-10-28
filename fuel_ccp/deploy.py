import hashlib
import json
import logging
import os
import re
import six

from fuel_ccp.common import jinja_utils
from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp import kubernetes
from fuel_ccp import templates
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


def _get_configmaps_version(configmaps, service_dir, files, configs):
    """Get overall ConfigMaps version

    If any of the ConfigMaps changed, the overall version will be
    changed and deployment will be updated no matter if the deployment spec
    was updated or not.
    """
    versions = ''.join(cm.obj['metadata']['resourceVersion']
                       for cm in configmaps)
    files_hash = _get_service_files_hash(service_dir, files, configs)

    return versions + files_hash


def _get_service_files_hash(service_dir, files, configs):
    data = {}
    if files:
        for filename, f in files.items():
            path = os.path.join(service_dir, "files", f["content"])
            data[filename] = jinja_utils.jinja_render(
                path, configs, ignore_undefined=True)
    dump = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha1(dump).hexdigest()


def parse_role(component, topology, configmaps):
    service_dir = component["service_dir"]
    role = component["service_content"]
    component_name = component["component_name"]
    service = role["service"]
    service_name = service["name"]

    if service_name not in topology:
        LOG.info("Service %s not in topology config, skipping deploy",
                 service_name)
        return
    LOG.info("Scheduling service %s deployment", service_name)
    _expand_files(service, role.get("files"))

    files_cm = _create_files_configmap(
        service_dir, service_name, role.get("files"))
    meta_cm = _create_meta_configmap(service)

    workflows = _parse_workflows(service)
    workflow_cm = _create_workflow(workflows, service_name)
    configmaps = configmaps + (files_cm, meta_cm, workflow_cm)

    if CONF.action.dry_run:
        cm_version = 'dry-run'
    else:
        cm_version = _get_configmaps_version(
            configmaps, service_dir, role.get("files"), CONF.configs._dict)

    for cont in service["containers"]:
        daemon_cmd = cont["daemon"]
        daemon_cmd["name"] = cont["name"]

        _create_pre_jobs(service, cont, component_name)
        _create_post_jobs(service, cont, component_name)
        cont['cm_version'] = cm_version

    cont_spec = templates.serialize_daemon_pod_spec(service)
    affinity = templates.serialize_affinity(service, topology)

    replicas = CONF.replicas.get(service_name)
    if service.get("kind") == 'DaemonSet':
        if replicas is not None:
            LOG.error("Replicas was specified for %s, but it's implemented "
                      "using Kubernetes DaemonSet that will deploy service on "
                      "all matching nodes (section 'nodes' in config file)",
                      service_name)
            raise RuntimeError("Replicas couldn't be specified for services "
                               "implemented using Kubernetes DaemonSet")

        obj = templates.serialize_daemonset(service_name, cont_spec,
                                            affinity, component_name)
    elif service.get("kind") == "PetSet":
        replicas = replicas or 1
        obj = templates.serialize_petset(service_name, cont_spec,
                                         affinity, replicas, component_name)
    else:
        replicas = replicas or 1
        obj = templates.serialize_deployment(service_name, cont_spec,
                                             affinity, replicas,
                                             component_name)
    kubernetes.process_object(obj)

    _process_ports(service)
    LOG.info("Service %s successfuly scheduled", service_name)


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
    return kubernetes.process_object(template)


def _process_ports(service):
    template_ports = service.get("ports")
    if not template_ports:
        return
    ports = []
    ingress_rules = []
    for port in service["ports"]:
        source_port = int(port.get('cont'))
        node_port = port.get('node')
        port_name = str(source_port)
        if node_port:
            ports.append({"port": source_port, "name": port_name,
                          "node-port": int(node_port)})
        else:
            ports.append({"port": source_port, "name": port_name})

        if CONF.configs.ingress.enabled and port.get("ingress"):
            ingress_host = utils.get_ingress_host(port.get("ingress"))
            if ingress_host:
                ingress_rules.append(templates.serialize_ingress_rule(
                    service["name"], ingress_host, source_port))
    service_template = templates.serialize_service(service["name"], ports)
    kubernetes.process_object(service_template)

    if ingress_rules:
        ingress_template = templates.serialize_ingress(
            service["name"], ingress_rules)
        kubernetes.process_object(ingress_template)


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


def _create_pre_jobs(service, container, component_name):
    for job in container.get("pre", ()):
        if _is_single_job(job):
            _create_job(service, container, job, component_name)


def _create_post_jobs(service, container, component_name):
    for job in container.get("post", ()):
        if _is_single_job(job):
            _create_job(service, container, job, component_name)


def _create_job(service, container, job, component_name):
    cont_spec = templates.serialize_job_container_spec(container, job)
    pod_spec = templates.serialize_job_pod_spec(service, job, cont_spec)
    job_spec = templates.serialize_job(job["name"], pod_spec, component_name)
    kubernetes.process_object(job_spec)


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
    data = {templates.GLOBAL_CONFIG: config._json(sort_keys=True)}
    cm = templates.serialize_configmap(templates.GLOBAL_CONFIG, data)
    return kubernetes.process_object(cm)


def _create_start_script_configmap():
    start_scr_path = os.path.join(CONF.repositories.path,
                                  "fuel-ccp-entrypoint",
                                  "fuel_ccp_entrypoint",
                                  "start_script.py")
    with open(start_scr_path) as f:
        start_scr_data = f.read()

    data = {
        templates.SCRIPT_CONFIG: start_scr_data
    }
    cm = templates.serialize_configmap(templates.SCRIPT_CONFIG, data)
    return kubernetes.process_object(cm)


def _create_files_configmap(service_dir, service_name, files):
    configmap_name = "%s-%s" % (service_name, templates.FILES_CONFIG)
    data = {}
    if files:
        for filename, f in files.items():
            with open(os.path.join(
                    service_dir, "files", f["content"]), "r") as f:
                data[filename] = f.read()
    data["placeholder"] = ""
    template = templates.serialize_configmap(configmap_name, data)
    return kubernetes.process_object(template)


def _create_meta_configmap(service):
    configmap_name = "%s-%s" % (service["name"], templates.META_CONFIG)
    data = {
        templates.META_CONFIG: json.dumps(
            {"service-name": service["name"],
             "host-net": service.get("hostNetwork", False),
             "replicas": CONF.replicas._dict}, sort_keys=True)
    }
    template = templates.serialize_configmap(configmap_name, data)
    return kubernetes.process_object(template)


def _make_topology(nodes, roles, replicas):
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

    # Replicas are optional, 1 replica will deployed by default
    replicas = replicas or dict()

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
    for node in sorted(nodes):
        matched_nodes = find_match(node)
        for role in nodes[node]["roles"]:
            roles_to_node.setdefault(role, [])
            roles_to_node[role].extend(matched_nodes)
    service_to_node = {}
    for role in sorted(roles):
        if role in roles_to_node:
            for svc in roles[role]:
                service_to_node.setdefault(svc, [])
                service_to_node[svc].extend(roles_to_node[role])
        else:
            LOG.warning("Role '%s' defined, but unused", role)

    replicas = replicas.copy()
    for svc, svc_hosts in six.iteritems(service_to_node):
        svc_replicas = replicas.pop(svc, None)

        if svc_replicas is None:
            continue

        svc_hosts_count = len(svc_hosts)
        if svc_replicas > svc_hosts_count:
            LOG.error("Requested %s replicas for %s while only %s hosts able "
                      "to run that service (%s)", svc_replicas, svc,
                      svc_hosts_count, ", ".join(svc_hosts))
            raise RuntimeError("Replicas doesn't match available hosts.")

    if replicas:
        LOG.error("Replicas defined for unspecified service(s): %s",
                  ", ".join(replicas.keys()))
        raise RuntimeError("Replicas defined for unspecified service(s)")

    return service_to_node


def _create_namespace(configs):
    if CONF.action.dry_run:
        return

    template = templates.serialize_namespace(configs['namespace'])
    kubernetes.process_object(template)


def _create_openrc(config):
    openrc = [
        "export OS_PROJECT_DOMAIN_NAME=default",
        "export OS_USER_DOMAIN_NAME=default",
        "export OS_PROJECT_NAME=%s" % config['openstack']['project_name'],
        "export OS_USERNAME=%s" % config['openstack']['user_name'],
        "export OS_PASSWORD=%s" % config['openstack']['user_password'],
        "export OS_IDENTITY_API_VERSION=3",
        "export OS_AUTH_URL=http://%s/v3" %
        utils.address('keystone', config['keystone']['public_port'], True)
    ]
    with open('openrc-%s' % config['namespace'], 'w') as openrc_file:
        openrc_file.write("\n".join(openrc))
    LOG.info("Openrc file for this deployment created at %s/openrc-%s",
             os.getcwd(), config['namespace'])


def deploy_components(components_map, components):
    if not components:
        components = set(components_map.keys())

    deploy_validation.validate_requested_components(components, components_map)

    if CONF.action.export_dir:
        os.makedirs(os.path.join(CONF.action.export_dir, 'configmaps'))

    topology = _make_topology(CONF.nodes, CONF.roles, CONF.replicas._dict)

    _create_namespace(CONF.configs)

    _create_globals_configmap(CONF.configs)
    start_script_cm = _create_start_script_configmap()
    configmaps = (start_script_cm,)

    for component in components:
        parse_role(components_map[component],
                   topology=topology,
                   configmaps=configmaps)

    if 'keystone' in components:
        _create_openrc(CONF.configs)
