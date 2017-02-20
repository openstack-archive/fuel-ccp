import base64
import itertools
import json
import six

from fuel_ccp import config
from fuel_ccp.config import images

CONF = config.CONF

GLOBAL_CONFIG = "globals"
NODES_CONFIG = "nodes-config"
SERVICE_CONFIG = "service-config"
SCRIPT_CONFIG = "start-script"
FILES_CONFIG = "files"
META_CONFIG = "meta"
ROLE_CONFIG = "role"
EXPORTS_CONFIG = "exports"

ENTRYPOINT_PATH = "/opt/ccp_start_script/bin/start_script.py"
PYTHON_PATH = "/usr/bin/python"


def get_start_cmd(role_name):
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


def serialize_volume_mounts(container, for_job=None):
    if for_job is None:
        for_job = {}
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
            "name": EXPORTS_CONFIG,
            "mountPath": "/etc/ccp/%s" % EXPORTS_CONFIG
        },
        {
            "name": FILES_CONFIG,
            "mountPath": "/etc/ccp/%s" % FILES_CONFIG
        },
        {
            "name": NODES_CONFIG,
            "mountPath": "/etc/ccp/%s" % NODES_CONFIG
        },
        {
            "name": SERVICE_CONFIG,
            "mountPath": "/etc/ccp/%s" % SERVICE_CONFIG
        }
    ]
    for v in itertools.chain(container.get("volumes", ()),
                             for_job.get("volumes", ())):
        spec.append({
            "name": v["name"],
            "mountPath": v.get("mount-path", v["path"]),
            "readOnly": v.get("readOnly", False)
        })
    if "daemon" in container:
        for (name, secret) in six.iteritems(
                container["daemon"].get("secrets", {})):
            spec.append({
                "name": name,
                "mountPath": secret["path"]
            })

    return spec


def serialize_env_variables(container):
    env = [
        {
            "name": "CCP_NODE_NAME",
            "valueFrom": {
                "fieldRef": {
                    "fieldPath": "spec.nodeName"
                }
            }
        },
        {
            "name": "CCP_POD_NAME",
            "valueFrom": {
                "fieldRef": {
                    "fieldPath": "metadata.name"
                }
            }
        }
    ]
    if container.get('env'):
        env.extend(container['env'])
    return env


def serialize_liveness_probe(liveness):
    cont_spec = {}
    if liveness.get("type") == "httpGet":
        cont_spec["livenessProbe"] = {
            "httpGet": {
                "path": liveness["path"],
                "port": liveness["port"],
                "scheme": liveness.get("scheme", "http").upper()
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
        "imagePullPolicy": CONF.kubernetes.image_pull_policy,
        "command": get_start_cmd(container["name"]),
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
        "image": images.image_spec(job.get('image') or container["image"]),
        "imagePullPolicy": CONF.kubernetes.image_pull_policy,
        "command": get_start_cmd(job["name"]),
        "volumeMounts": serialize_volume_mounts(container, job),
        "env": serialize_env_variables(container)
    }


def serialize_job_pod_spec(service, job, cont_spec, affinity):
    return {
        "metadata": {
            "name": job["name"],
            "annotations": affinity,
        },
        "spec": {
            "containers": [cont_spec],
            "volumes": serialize_volumes(service, job),
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


def serialize_volumes(service, for_job=None):
    if for_job is None:
        for_job = {}
    workflow_items = []
    for cont in service["containers"]:
        workflow_items.append(
            {"key": cont["name"], "path": "%s.json" % cont["name"]})
        for job_type in ("pre", "post"):
            for job in cont.get(job_type, ()):
                if job.get("type", "local") == "single":
                    workflow_items.append(
                        {"key": job["name"], "path": "%s.json" % job["name"]})

    files = set()
    for c in service["containers"]:
        files.update(c["daemon"].get("files", {}))
        for job_type in ("pre", "post"):
            for job in c.get(job_type, ()):
                if job.get("type", "local") == "single" and job.get("files"):
                    files.update(job["files"])

    file_items = [{"key": f_name, "path": f_name} for f_name in sorted(files)]
    file_items.append({"key": "placeholder", "path": ".placeholder"})
    exports_map = service['exports_ctx']['map']
    exports_items = [{'key': cm_export_key,
                      'path': exports_map[cm_export_key]['name']}
                     for cm_export_key in sorted(exports_map)]
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
        },
        {
            "name": EXPORTS_CONFIG,
            "configMap": {
                "name": EXPORTS_CONFIG,
                "items": exports_items
            }
        },
        {
            "name": NODES_CONFIG,
            "configMap": {
                "name": NODES_CONFIG,
                "items": [{"key": NODES_CONFIG,
                           "path": "nodes-config.json"}]
            }
        },
        {
            "name": SERVICE_CONFIG,
            "configMap": {
                "name": "%s-%s" % (service["name"], SERVICE_CONFIG),
                "items": [{"key": SERVICE_CONFIG,
                           "path": "%s.json" % SERVICE_CONFIG}]
            }
        }
    ]
    volume_names = [GLOBAL_CONFIG, META_CONFIG, ROLE_CONFIG, SCRIPT_CONFIG,
                    FILES_CONFIG, EXPORTS_CONFIG, NODES_CONFIG, SERVICE_CONFIG]
    for cont in itertools.chain(service["containers"], [for_job]):
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

    for cont in service["containers"]:
        if "daemon" in cont:
            for (name, secret) in six.iteritems(
                    cont["daemon"].get("secrets", {})):
                if name in volume_names:
                    # TODO(dklenov): move to validation
                    continue
                vol_spec.append({
                    "name": name,
                    "secret": secret["secret"]
                })
                volume_names.append(name)

    return vol_spec


def serialize_job(name, spec, component_name, app_name):
    job = {
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
    if CONF.kubernetes.appcontroller["enabled"]:
        job = {
            "apiVersion": "appcontroller.k8s/v1alpha1",
            "kind": "Definition",
            "metadata": {
                "name": "job-%s" % name
            },
            "job": job
        }
    return job


def serialize_deployment(name, spec, annotations, replicas, component_name,
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
                    "annotations": annotations,
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


def serialize_statefulset(name, spec, annotations, replicas, component_name):
    return {
        "apiVersion": "apps/v1beta1",
        "kind": "StatefulSet",
        "metadata": {
            "name": name
        },
        "spec": {
            "serviceName": name,
            "replicas": replicas,
            "template": {
                "metadata": {
                    "annotations": annotations,
                    "labels": {
                        "ccp": "true",
                        "app": name,
                        "ccp-component": component_name
                    }
                },
                "spec": spec
            }
        }
    }


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
    if service.get("hostNetwork") or service.get("antiAffinity") == 'global':
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
    elif service.get("kind") == "DaemonSet" or service.get(
            "antiAffinity") == 'local':
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


def serialize_service(name, ports, headless=False, annotations=None):
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

    if annotations:
        obj['metadata']['annotations'] = annotations

    if not headless:
        obj["spec"]["type"] = "NodePort"
    else:
        obj["spec"]["clusterIP"] = "None"

    if CONF.kubernetes.appcontroller["enabled"]:
        obj = {
            "apiVersion": "appcontroller.k8s/v1alpha1",
            "kind": "Definition",
            "metadata": {
                "name": "service-%s" % name
            },
            "service": obj
        }

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
            "name": name
        },
        "spec": {
            "rules": rules
        }
    }


def serialize_secret(name, type="Opaque", data={}):
    data = dict(
        [(key, base64.b64encode(value.encode()).decode())
            for (key, value) in six.iteritems(data)]
    )
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": name
        },
        "type": type,
        "data": data
    }


def serialize_dependency(name, parent, child):
    return {
        "apiVersion": "appcontroller.k8s/v1alpha1",
        "kind": "Dependency",
        "metadata": {
            "name": name
        },
        "parent": parent,
        "child": child
    }
