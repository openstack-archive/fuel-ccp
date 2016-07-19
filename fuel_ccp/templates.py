import copy

from oslo_config import cfg

from fuel_ccp.common import utils


CONF = cfg.CONF
CONF.import_group('images', 'fuel_ccp.config.images')
CONF.import_group('registry', 'fuel_ccp.config.registry')

GLOBAL_CONFIG = "globals"
SCRIPT_CONFIG = "start-script"
FILES_CONFIG = "files"
META_CONFIG = "meta"
ROLE_CONFIG = "role"


def _get_image_name(image_name):
    image_name = "%s/%s:%s" % (CONF.images.namespace, image_name,
                               CONF.images.tag)
    if CONF.registry.address:
        image_name = "%s/%s" % (CONF.registry.address, image_name)
    return image_name


def _get_start_cmd(cmd_name):
    return ["python", "/opt/mcp_start_script/bin/start_script.py", cmd_name]


def serialize_configmap(name, data):
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
            "mcp": "true"
        },
        "data": data
    }


def serialize_volume_mounts(container):
    spec = [
        {
            "name": GLOBAL_CONFIG,
            "mountPath": "/etc/mcp/%s" % GLOBAL_CONFIG
        },
        {
            "name": ROLE_CONFIG,
            "mountPath": "/etc/mcp/%s" % ROLE_CONFIG
        },
        {
            "name": META_CONFIG,
            "mountPath": "/etc/mcp/%s" % META_CONFIG
        },
        {
            "name": SCRIPT_CONFIG,
            "mountPath": "/opt/mcp_start_script/bin"
        },
        {
            "name": FILES_CONFIG,
            "mountPath": "/etc/mcp/%s" % FILES_CONFIG
        }
    ]
    for v in container.get("volumes", ()):
        spec.append({
            "name": v["name"],
            "mountPath": v.get("mount-path", v["path"])
        })
    return spec


def serialize_daemon_container_spec(container):
    cont_spec = {
        "name": container["name"],
        "image": _get_image_name(container["image"]),
        "command": _get_start_cmd(container["name"]),
        "volumeMounts": serialize_volume_mounts(container)
    }
    if container.get("probes", {}).get("readiness"):
        cont_spec["readinessProbe"] = {
            "exec": {
                "command": [container["probes"]["readiness"]]
            },
            "timeoutSeconds": 1
        }
    if container.get("probes", {}).get("liveness"):
        cont_spec["livenessProbe"] = {
            "exec": {
                "command": [container["probes"]["liveness"]]
            },
            "timeoutSeconds": 1
        }
    cont_spec["securityContext"] = {"privileged":
                                    container.get("privileged", False)}
    return cont_spec


def serialize_job_container_spec(container, job):
    return {
        "name": job["name"],
        "image": _get_image_name(container["image"]),
        "command": _get_start_cmd(job["name"]),
        "volumeMounts": serialize_volume_mounts(container)
    }


def serialize_job_pod_spec(service, job, cont_spec):
    return {
        "metadata": {
            "name": job["name"]
        },
        "spec": {
            "containers": [cont_spec],
            "volumes": serialize_volumes(service),
            "restartPolicy": "OnFailure"
        }
    }


def serialize_daemon_containers(service):
    return [serialize_daemon_container_spec(c) for c in service["containers"]]


def serialize_daemon_pod_spec(service):
    cont_spec = {
        "containers": serialize_daemon_containers(service),
        "volumes": serialize_volumes(service),
        "restartPolicy": "Always"
    }

    if service.get("host-net"):
        cont_spec["hostNetwork"] = True
    if service.get("node-selector"):
        cont_spec["nodeSelector"] = copy.deepcopy(service["node-selector"])
    return cont_spec


def serialize_volumes(service):
    workflow_items = []
    for cont in service["containers"]:
        workflow_items.append(
            {"key": cont["name"], "path": "%s.yaml" % cont["name"]})
        for job_type in ("pre", "post"):
            for job in cont.get(job_type, ()):
                if job.get("type", "local") == "single":
                    workflow_items.append(
                        {"key": job["name"], "path": "%s.yaml" % job["name"]})

    file_items = []
    for c in service["containers"]:
        for f_name, f_item in c["daemon"].get("files", {}).items():
            file_items.append({"key": f_name, "path": f_name})
        for job_type in ("pre", "post"):
            for job in c.get(job_type, ()):
                if job.get("type", "local") == "single" and job.get("files"):
                    for f_name in job["files"].keys():
                        file_items.append({"key": f_name, "path": f_name})
    file_items.append({"key": "placeholder", "path": ".placeholder"})
    vol_spec = [
        {
            "name": GLOBAL_CONFIG,
            "configMap": {
                "name": GLOBAL_CONFIG,
                "items": [{"key": GLOBAL_CONFIG,
                           "path": "globals.yaml"}]
            }
        },
        {
            "name": SCRIPT_CONFIG,
            "configMap": {
                "name": SCRIPT_CONFIG,
                "items": [{"key": SCRIPT_CONFIG,
                           "path": "start_script.py"}]
            }
        },
        {
            "name": ROLE_CONFIG,
            "configMap": {
                "name": "%s-%s" % (service["name"], ROLE_CONFIG),
                "items": workflow_items
            }
        },
        {
            "name": META_CONFIG,
            "configMap": {
                "name": "%s-%s" % (service["name"], META_CONFIG),
                "items": [{"key": META_CONFIG,
                           "path": "meta.yaml"}]
            }
        },
        {
            "name": FILES_CONFIG,
            "configMap": {
                "name": "%s-%s" % (service["name"], FILES_CONFIG),
                "items": file_items
            }
        }
    ]
    volume_names = [GLOBAL_CONFIG, META_CONFIG, ROLE_CONFIG, SCRIPT_CONFIG,
                    FILES_CONFIG]
    for cont in service["containers"]:
        for v in cont.get("volumes", ()):
            if v["name"] in volume_names:
                # TODO(apavlov): move to validation
                continue
            if v["type"] == "host":
                vol_spec.append({
                    "name": v["name"],
                    "hostPath": {
                        "path": v["path"]
                    }
                })
            elif v["type"] == "empty-dir":
                vol_spec.append({
                    "name": v["name"],
                    "emptyDir": {}
                })
            else:
                # TODO(sreshetniak): move it to validation
                raise ValueError("Volume type \"%s\" not supported" %
                                 v["type"])
            volume_names.append(v["name"])
    return vol_spec


def serialize_job(name, spec):
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "mcp": "true"
        },
        "spec": {
            "template": spec
        }
    }


def serialize_deployment(name, spec):
    return {
        "apiVersion": "extensions/v1beta1",
        "kind": "Deployment",
        "metadata": {
            "name": name
        },
        "spec": {
            "replicas": 1,
            "template": {
                "metadata": {
                    "labels": {
                        "mcp": "true",
                        "app": name
                    }
                },
                "spec": spec
            }
        }
    }


def serialize_daemonset(name, spec):
    return {
        "apiVersion": "extensions/v1beta1",
        "kind": "DaemonSet",
        "metadata": {
            "name": name
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {
                        "mcp": "true",
                        "app": name
                    }
                },
                "spec": spec
            }
        }
    }


def serialize_service(name, ports):
    ports_spec = []
    for port in ports:
        spec_entry = {"protocol": "TCP",
                      "port": port["port"],
                      "targetPort": port["port"],
                      "name": utils.k8s_name(port["name"])}
        if port.get("node-port"):
            spec_entry.update({"nodePort": port["node-port"]})
        ports_spec.append(spec_entry)
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "mcp": "true"
        },
        "spec": {
            "type": "NodePort",
            "selector": {
                "app": name
            },
            "ports": ports_spec
        }
    }
