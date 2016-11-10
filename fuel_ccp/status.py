from __future__ import print_function

import copy
import logging

from fuel_ccp import config
from fuel_ccp import kubernetes

CONF = config.CONF

LOG = logging.getLogger(__name__)

EXT_LINK_TEMPLATE = "http://{ext_ip}:{port}"
STATE_TEMPLATE = {
    "pod_total": 0,
    "pod_running": 0,
    "job_total": 0,
    "job_completed": 0,
    "links": []
}


def is_app_ready(state):
    return (state["pod_total"] == state["pod_running"]
            and state["job_total"] == state["job_completed"])


def repr_state(state):
    return "ok" if is_app_ready(state) else "nok"


def get_pod_states(components=None):
    ext_ip = CONF.configs.get("k8s_external_ip", "")

    states = {}
    for pod in kubernetes.list_cluster_pods():
        app_name = pod.obj["metadata"]["labels"].get("app")
        if not app_name:
            continue
        states.setdefault(app_name, copy.deepcopy(STATE_TEMPLATE))
        states[app_name]["pod_total"] += 1
        if pod.ready:
            states[app_name]["pod_running"] += 1

    job_states = {}
    for job in kubernetes.list_cluster_jobs():
        app_name = job.obj["metadata"]["labels"].get("app")
        if not app_name:
            continue
        states.setdefault(app_name, copy.deepcopy(STATE_TEMPLATE))
        states[app_name]["job_total"] += job.obj["spec"]["completions"]
        states[app_name]["job_completed"] += (
                job.obj["status"].get("succeeded", 0))

    for svc in kubernetes.list_cluster_services():
        svc_name = svc.obj["metadata"]["name"]
        states.setdefault(svc_name, copy.deepcopy(STATE_TEMPLATE))
        for port in svc.obj["spec"]["ports"]:
            states[svc_name]["links"].append(EXT_LINK_TEMPLATE.format(
                ext_ip=ext_ip,
                port=port["nodePort"]))

    return states


def show_long_status(components=None):
    states = get_pod_states(components)
    columns = ("service", "pod", "job", "ready", "links")

    formatted_states = []

    for state in sorted(states):
        if not components or state in components:
            formatted_states.append((
                state,
                "{pod_running}/{pod_total}".format(**states[state]),
                "{job_completed}/{job_total}".format(**states[state]),
                repr_state(states[state]),
                "\n".join(states[state]["links"])))

    return columns, formatted_states


def show_short_status():
    states = get_pod_states()
    if not states:
        status = "no cluster"
    else:
        status = "ok" if all(map(is_app_ready, states.values())) else "nok"
    return ("status",), ((status,),)
