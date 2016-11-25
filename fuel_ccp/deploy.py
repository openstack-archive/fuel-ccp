import collections
import hashlib
import itertools
import json
import logging
import os
import re

import pykube.exceptions
import six
from six.moves import zip_longest

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
    files_hash = _get_service_files_hash(files, configs)

    return versions + files_hash


def _get_service_files_hash(files, configs):
    data = {}
    if files:
        for filename, f in files.items():
            data[filename] = jinja_utils.jinja_render(
                f["content"], configs, ignore_undefined=True)
    dump = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha1(dump).hexdigest()


def process_files(files, service_dir):
    if not files:
        return
    for filename, f in files.items():
        if CONF.files.get(filename):
            content = CONF.files.get(filename)
        else:
            content = os.path.join(service_dir, "files", f["content"])
        f["content"] = content


def parse_role(component, topology, configmaps, label=None):
    service_dir = component["service_dir"]
    role = component["service_content"]
    component_name = component["component_name"]
    service = role["service"]
    service_name = service["name"]

    LOG.info("Scheduling service %s deployment", service_name)
    _expand_files(service, role.get("files"))

    process_files(role.get("files"), service_dir)
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

        yield _create_pre_jobs(service, cont, component_name, topology)
        yield _create_post_jobs(service, cont, component_name, topology)
        cont['cm_version'] = cm_version

    cont_spec = templates.serialize_daemon_pod_spec(service, label)
    affinity = templates.serialize_affinity(service, topology,
                                            node_affinity=label is None)

    replicas = CONF.replicas.get(service_name)
    strategy = {'type': service.get('strategy', 'RollingUpdate')}
    if service.get("kind") == 'DaemonSet':
        LOG.warning("Deployment is being used instead of DaemonSet to support "
                    "updates")
        if replicas is not None:
            LOG.error("Replicas was specified for %s, but it's implemented "
                      "in DaemonSet-like way and will be deployed on "
                      "all matching nodes (section 'nodes' in config file)",
                      service_name)
            raise RuntimeError("Replicas couldn't be specified for services "
                               "implemented using Kubernetes DaemonSet")
        replicas = len(set(topology[service_name]))
        if strategy['type'] == 'RollingUpdate':
            strategy['rollingUpdate'] = {'maxSurge': 0,
                                         'maxUnavailable': '50%'}
    else:
        replicas = replicas or 1

    obj = templates.serialize_deployment(service_name, cont_spec, affinity,
                                         replicas, component_name, strategy)
    yield [obj]

    yield _process_ports(service)
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
    yield service_template

    if ingress_rules:
        ingress_template = templates.serialize_ingress(
            service["name"], ingress_rules)
        yield ingress_template


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


def _create_pre_jobs(service, container, component_name, topology):
    for job in container.get("pre", ()):
        if _is_single_job(job):
            yield _get_job(service, container, job, component_name, topology)


def _create_post_jobs(service, container, component_name, topology):
    for job in container.get("post", ()):
        if _is_single_job(job):
            yield _get_job(service, container, job, component_name, topology)


def _get_job(service, container, job, component_name, topology):
    if 'topology_key' in job:
        affinity = templates.serialize_affinity(
            {"name": job['topology_key']}, topology)
    else:
        affinity = {}
    cont_spec = templates.serialize_job_container_spec(container, job)
    pod_spec = templates.serialize_job_pod_spec(service, job, cont_spec,
                                                affinity)
    job_spec = templates.serialize_job(job["name"], pod_spec, component_name,
                                       service["name"])
    return job_spec


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
            with open(f["content"], "r") as f:
                data[filename] = f.read()
    data["placeholder"] = ""
    template = templates.serialize_configmap(configmap_name, data)
    return kubernetes.process_object(template)


def _create_meta_configmap(service):
    configmap_name = "%s-%s" % (service["name"], templates.META_CONFIG)
    data = {
        templates.META_CONFIG: json.dumps(
            {"service-name": service["name"],
             "host-net": service.get("hostNetwork", False)}, sort_keys=True)
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
    nodes_to_roles = collections.defaultdict(set)
    for node_re in sorted(nodes):
        matched_nodes = find_match(node_re)
        for role in nodes[node_re]["roles"]:
            roles_to_node.setdefault(role, [])
            roles_to_node[role].extend(matched_nodes)
        for node in matched_nodes:
            nodes_to_roles[node].update(nodes[node_re]["roles"])

    service_to_node = {}
    service_to_roles = collections.defaultdict(list)
    for role in sorted(roles):
        if role in roles_to_node:
            for svc in roles[role]:
                service_to_node.setdefault(svc, [])
                service_to_node[svc].extend(roles_to_node[role])
                service_to_roles[svc].append(role)
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

    return service_to_node, nodes_to_roles, service_to_roles


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
        "export OS_AUTH_URL=%s/v3" %
        utils.address('keystone', config['keystone']['public_port'], True,
                      True)
    ]
    with open('openrc-%s' % config['namespace'], 'w') as openrc_file:
        openrc_file.write("\n".join(openrc))
    LOG.info("Openrc file for this deployment created at %s/openrc-%s",
             os.getcwd(), config['namespace'])


def check_images_change(objects):
    for obj in objects:
        if obj['kind'] not in ('Deployment', 'DaemonSet', 'PetSet'):
            continue
        kube_obj = kubernetes.get_pykube_object_if_exists(obj)
        if kube_obj is None:
            continue
        old_obj = kube_obj.obj
        old_containers = old_obj['spec']['template']['spec']['containers']
        old_images = [c['image'] for c in old_containers]
        new_containers = obj['spec']['template']['spec']['containers']
        new_images = [c['image'] for c in new_containers]
        for old_image, new_image in zip_longest(old_images, new_images):
            if old_image != new_image:
                return old_image, new_image
    return False


def create_upgrade_jobs(component_name, upgrade_data, configmaps, topology):
    from_version = upgrade_data['_meta']['from']
    to_version = upgrade_data['_meta']['to']
    component = upgrade_data['_meta']['component']
    upgrade_def = component['upgrades']['default']['upgrade']
    files = component['upgrades']['default'].get('files')
    prefix = '{}-{}-{}'.format(upgrade_def['name'], from_version, to_version)

    LOG.info("Scheduling component %s upgrade", component_name)
    for step in upgrade_def['steps']:
        if step.get('files'):
            step['files'] = {f: files[f] for f in step['files']}

    _create_files_configmap(
        component['service_dir'], prefix, files)
    container = {
        "name": prefix,
        "pre": [],
        "daemon": {},
        "image": upgrade_def['image'],
    }
    service = {
        "name": prefix,
        "containers": [container],
    }
    _create_meta_configmap(service)

    workflows = {prefix: ""}
    jobs = container["pre"]
    last_deps = []

    for step in upgrade_def['steps']:
        step_type = step.get('type', 'single')
        job_name = "{}-{}".format(prefix, step['name'])
        job = {"name": job_name, "type": "single"}
        for key in ['files', 'volumes', 'topology_key']:
            if step.get(key):
                job[key] = step[key]
        jobs.append(job)
        workflow = {
            'name': job_name,
            'dependencies': last_deps,
        }
        last_deps = [job_name]
        if step_type == 'single':
            workflow['job'] = job = {}
            _fill_cmd(job, step)
            _push_files_to_workflow(workflow, step.get('files'))
        elif step_type == 'rolling-upgrade':
            services = step.get('services')
            if services is None:
                services = [s for s in upgrade_data if s != '_meta']
            workflow['roll'] = roll = []
            for service_name in services:
                roll.extend(upgrade_data[service_name])
        elif step_type == 'kill-services':
            services = step.get('services')
            if services is None:
                services = [s for s in upgrade_data if s != '_meta']
            workflow['kill'] = kill = []
            for service_name in services:
                for object_dict in upgrade_data[service_name]:
                    if object_dict['kind'] == 'Deployment':
                        kill.append(object_dict)
        else:
            raise RuntimeError("Unsupported upgrade step type: %s" % step_type)
        workflows[job_name] = \
            json.dumps({'workflow': workflow}, sort_keys=True)

    _create_workflow(workflows, prefix)

    job_specs = _create_pre_jobs(service, container, component_name, topology)
    for job_spec in job_specs:
        kubernetes.process_object(job_spec)

    LOG.info("Upgrade of component %s successfuly scheduled", component_name)


def version_diff(from_image, to_image):
    from_tag = from_image.rpartition(':')[-1]
    to_tag = to_image.rpartition(':')[-1]
    return from_tag, to_tag


def _label_from_roles(roles):
    return '{}-role-{}'.format(
        CONF.kubernetes.namespace,
        '-'.join(sorted(roles)),
    )


def generate_labels(nodes_to_roles, service_to_roles):
    roles_to_labels = collections.defaultdict(list)
    labels_for_services = {}
    for service, roles in service_to_roles.items():
        label = _label_from_roles(roles)
        labels_for_services[service] = label
        if len(roles) > 1:
            for role in roles:
                roles_to_labels[role].append(label)
    labels_for_nodes = {}
    for node, roles in nodes_to_roles.items():
        labels_for_nodes[node] = labels = []
        for role in roles:
            labels.append(_label_from_roles([role]))
            labels.extend(roles_to_labels.get(role, ()))
    return labels_for_nodes, labels_for_services


def set_node_labels(labels_for_nodes):
    nodes = kubernetes.list_k8s_nodes()
    prefix = '{}-role-'.format(CONF.kubernetes.namespace)
    for node in nodes:
        for attempt in range(10):
            labels = {}
            meta = node.obj['metadata']
            if 'labels' in meta:
                for label, value in meta['labels'].items():
                    if not label.startswith(prefix):
                        labels[label] = value
            for label in labels_for_nodes.get(node.name, []):
                labels[label] = 'true'
            if labels != meta['labels']:
                meta['labels'] = labels
                try:
                    node.update()
                except pykube.exceptions.HTTPError:
                    if attempt == 9:
                        raise
                    LOG.debug("Failed to update node '%s', attempt #%d",
                              node.name, attempt)
                    node.reload()
                    continue
            break


def deploy_components(components_map, components):

    topology, nodes_to_roles, service_to_roles = \
        _make_topology(CONF.nodes, CONF.roles, CONF.replicas._dict)
    if not components:
        components = set(topology.keys()) & set(components_map.keys())

    deploy_validation.validate_requested_components(components, components_map)

    if CONF.action.export_dir:
        os.makedirs(os.path.join(CONF.action.export_dir, 'configmaps'))

    _create_namespace(CONF.configs)
    _create_globals_configmap(CONF.configs)
    start_script_cm = _create_start_script_configmap()
    configmaps = (start_script_cm,)

    if CONF.kubernetes.use_labels:
        labels_for_nodes, labels_for_services = \
            generate_labels(nodes_to_roles, service_to_roles)
        set_node_labels(labels_for_nodes)

    upgrading_components = {}
    for service_name in components:
        service = components_map[service_name]

        if CONF.kubernetes.use_labels:
            label = labels_for_services[service_name]
        else:
            label = None

        objects_gen = parse_role(service,
                                 topology=topology,
                                 configmaps=configmaps,
                                 label=label)
        objects = list(itertools.chain.from_iterable(objects_gen))
        component_name = service['component_name']
        do_upgrade = component_name in upgrading_components
        if not do_upgrade and service['component']['upgrades']:
            res = check_images_change(objects)
            do_upgrade = bool(res)
            if do_upgrade:
                from_image, to_image = res
                from_version, to_version = version_diff(from_image, to_image)
                upgrading_components[component_name] = {
                    '_meta': {
                        'from': from_version,
                        'to': to_version,
                        'component': service['component']
                    },
                }
                LOG.info('Upgrade will be triggered for %s'
                         ' from version %s to version %s because image for %s'
                         ' changed from %s to %s',
                         component_name, from_version, to_version,
                         service_name, from_image, to_image)

        if not do_upgrade:
            for obj in objects:
                kubernetes.process_object(obj)
        else:
            upgrading_components[component_name][service_name] = objects

    for component_name, component_upg in upgrading_components.items():
        create_upgrade_jobs(component_name, component_upg, configmaps,
                            topology)

    if 'keystone' in components:
        _create_openrc(CONF.configs)
