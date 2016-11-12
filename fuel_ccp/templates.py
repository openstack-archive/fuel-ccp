import json

from fuel_ccp import config
from fuel_ccp.config import images

CONF = config.CONF

GLOBAL_CONFIG = "globals"
SCRIPT_CONFIG = "start-script"
FILES_CONFIG = "files"
META_CONFIG = "meta"
ROLE_CONFIG = "role"

ENTRYPOINT_PATH = "/opt/ccp_start_script/bin/start_script.py"
PYTHON_PATH = "/usr/bin/python"


def _get_start_cmd(role_name):
    return ["dumb-init", PYTHON_PATH, ENTRYPOINT_PATH, "provision", role_name]


def _get_readiness_cmd(role_name):
    return [PYTHON_PATH, ENTRYPOINT_PATH, "status", role_name]


def serialize_namespace(name):
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": name
        }
    }


def serialize_configmap(name, data):
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
            "labels": {
                "ccp": "true"
            }
        },
        "data": data
    }


def serialize_volume_mounts(container):
    spec = [
        {
            "name": GLOBAL_CONFIG,
            "mountPath": "/etc/ccp/%s" % GLOBAL_CONFIG
        },
        {
            "name": ROLE_CONFIG,
            "mountPath": "/etc/ccp/%s" % ROLE_CONFIG
        },
        {
            "name": META_CONFIG,
            "mountPath": "/etc/ccp/%s" % META_CONFIG
        },
        {
            "name": SCRIPT_CONFIG,
            "mountPath": "/opt/ccp_start_script/bin"
        },
        {
            "name": FILES_CONFIG,
            "mountPath": "/etc/ccp/%s" % FILES_CONFIG
        }
    ]
    for v in container.get("volumes", ()):
        spec.append({
            "name": v["name"],
            "mountPath": v.get("mount-path", v["path"]),
            "readOnly": v.get("readOnly", False)
        })
    return spec


def serialize_env_variables(container):
    env = [{
        "name": "CCP_NODE_NAME",
        "valueFrom": {
            "fieldRef": {
                "fieldPath": "spec.nodeName"
            }
        }
    }]
    if container.get('env'):
        env.extend(container['env'])
    return env


def serialize_liveness_probe(liveness):
    cont_spec = {}
    if liveness.get("type") == "httpGet":
        cont_spec["livenessProbe"] = {
            "httpGet": {
                "path": liveness["path"],
                "port": liveness["port"]
            },
            "timeoutSeconds": liveness.get("timeout", 1),
            "initialDelaySeconds": liveness.get("initialDelay", 10)
        }
    elif liveness.get("type") == "exec":
        cont_spec["livenessProbe"] = {
            "exec": {
                "command": [liveness["command"]]
            },
            "timeoutSeconds": liveness.get("timeout", 1),
            "initialDelaySeconds": liveness.get("initialDelay", 10)
        }
    return cont_spec


def serialize_daemon_container_spec(container):
    cont_spec = {
        "name": container["name"],
        "image": images.image_spec(container["image"]),
        "command": _get_start_cmd(container["name"]),
        "volumeMounts": serialize_volume_mounts(container),
        "readinessProbe": {
            "exec": {
                "command": _get_readiness_cmd(container["name"])
            },
            "timeoutSeconds": 1
        },
        "env": serialize_env_variables(container)
    }
    cont_spec['env'].append({
        "name": "CM_VERSION",
        "value": container['cm_version']
    })
    liveness = container.get("probes", {}).get("liveness", {})
    if liveness:
        liveness_spec = serialize_liveness_probe(liveness)
        cont_spec.update(liveness_spec)
    cont_spec["securityContext"] = {"privileged":
                                    container.get("privileged", False)}

    return cont_spec


def serialize_job_container_spec(container, job):
    return {
        "name": job["name"],
        "image": images.image_spec(container["image"]),
        "command": _get_start_cmd(job["name"]),
        "volumeMounts": serialize_volume_mounts(container),
        "env": serialize_env_variables(container)
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
        "restartPolicy": "Always",
        "hostNetwork": service.get("hostNetwork", False),
        "hostPID": service.get("hostPID", False)
    }

    return cont_spec


def serialize_volumes(service):
    workflow_items = []
    for cont in service["containers"]:
        workflow_items.append(
            {"key": cont["name"], "path": "%s.json" % cont["name"]})
        for job_type in ("pre", "post"):
            for job in cont.get(job_type, ()):
                if job.get("type", "local") == "single":
                    workflow_items.append(
                        {"key": job["name"], "path": "%s.json" % job["name"]})

    file_items = []
    for c in service["containers"]:
        for f_name, f_item in sorted(c["daemon"].get("files", {}).items()):
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
                           "path": "globals.json"}]
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
                           "path": "meta.json"}]
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


def serialize_job(name, spec, component_name, app_name):
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "labels": {
                "app": app_name,
                "ccp": "true",
                "ccp-component": component_name
            }
        },
        "spec": {
            "template": spec
        }
    }


def serialize_deployment(name, spec, affinity, replicas, component_name,
                         strategy):
    if strategy['type'] == 'RollingUpdate':
        strategy.setdefault("rollingUpdate", {
            "maxSurge": 1,
            "maxUnavailable": 0
        })

    deployment = {
        "apiVersion": "extensions/v1beta1",
        "kind": "Deployment",
        "metadata": {
            "name": name
        },
        "spec": {
            "replicas": replicas,
            "strategy": strategy,
            "template": {
                "metadata": {
                    "annotations": affinity,
                    "labels": {
                        "app": name,
                        "ccp": "true",
                        "ccp-component": component_name
                    }
                },
                "spec": spec
            }
        }
    }

    return deployment


def serialize_affinity(service, topology):
    policy = {
        "nodeAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": {
                "nodeSelectorTerms": [{
                    "matchExpressions": [{
                        "key": "kubernetes.io/hostname",
                        "operator": "In",
                        "values": topology[service["name"]]
                    }]
                }]
            }
        }
    }
    if service.get("hostNetwork"):
        policy["podAntiAffinity"] = {
            "requiredDuringSchedulingIgnoredDuringExecution": [{
                "labelSelector": {
                    "matchLabels": {
                        "app": service["name"]
                    }
                },
                "topologyKey": "kubernetes.io/hostname",
                "namespaces": []
            }]
        }
    elif service.get("kind") == "DaemonSet":
        policy["podAntiAffinity"] = {
            "requiredDuringSchedulingIgnoredDuringExecution": [{
                "labelSelector": {
                    "matchLabels": {
                        "app": service["name"]
                    }
                },
                "topologyKey": "kubernetes.io/hostname",
                "namespaces": [CONF.kubernetes.namespace]
            }]
        }
    return {"scheduler.alpha.kubernetes.io/affinity": json.dumps(
        policy, sort_keys=True)}


def serialize_service(name, ports, headless=False):
    ports_spec = []
    for port in ports:
        spec_entry = {"port": port["port"],
                      "name": port["name"]}
        if not headless:
            spec_entry.update({"protocol": "TCP",
                               "targetPort": port["port"]})
            if port.get("node-port"):
                spec_entry.update({"nodePort": port["node-port"]})
        ports_spec.append(spec_entry)

    obj = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "labels": {
                "ccp": "true"
            }
        },
        "spec": {
            "selector": {
                "app": name
            },
            "ports": ports_spec
        }
    }

    if not headless:
        obj["spec"]["type"] = "NodePort"
    else:
        obj["spec"]["clusterIP"] = "None"

    return obj


def serialize_ingress_rule(service, host, port):
    return {
        "host": host,
        "http": {
            "paths": [{
                "backend": {
                    "serviceName": service,
                    "servicePort": port
                }
            }]
        }
    }


def serialize_ingress(name, rules):
    return {
        "apiVersion": "extensions/v1beta1",
        "kind": "Ingress",
        "metadata": {
            "name": name,
            "ccp": "true"
        },
        "spec": {
            "rules": rules
        }
    }
