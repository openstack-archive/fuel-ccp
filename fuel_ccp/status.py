from __future__ import print_function

import copy
import logging
import sys

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
COLORS = {
    "green": "\033[92m%s\033[39m",
    "yellow": "\033[93m%s\033[39m"
}


def colorized(color, s):
    if sys.stdout.isatty():
        return COLORS[color] % s
    else:
        return s


ST_OK = colorized("green", "ok")
ST_WIP = colorized("yellow", "wip")


def is_app_ready(state):
    return (state["pod_total"] == state["pod_running"]
            and state["job_total"] == state["job_completed"])


def repr_state(state):
    return ST_OK if is_app_ready(state) else ST_WIP


def get_pod_states(components=None):
    ext_ip = CONF.configs.get("k8s_external_ip", "")

    states = {}
    selector = "app in (%s)" % ','.join(components) if components else None
    for dp in kubernetes.list_cluster_deployments(selector):
        states.setdefault(dp.name, copy.deepcopy(STATE_TEMPLATE))
        dp_st = dp.obj["status"]
        states[dp.name]["pod_total"] = dp.obj["spec"]["replicas"]
        states[dp.name]["pod_running"] = min(
            dp_st.get("availableReplicas", 0), dp_st.get("updatedReplicas", 0))

    for job in kubernetes.list_cluster_jobs(selector):
        app_name = job.obj["metadata"]["labels"].get("app")
        states.setdefault(app_name, copy.deepcopy(STATE_TEMPLATE))
        states[app_name]["job_total"] += job.obj["spec"]["completions"]
        states[app_name]["job_completed"] += (
            job.obj["status"].get("succeeded", 0))

    if CONF.configs.ingress.enabled:
        url_template = "https://%s"
        if CONF.configs.ingress.get("port"):
            url_template += ":%d" % CONF.configs.ingress.port
        for ing in kubernetes.list_cluster_ingress():
            if components and ing.name not in components:
                continue
            states.setdefault(ing.name, copy.deepcopy(STATE_TEMPLATE))
            for rule in ing.obj['spec']['rules']:
                states[ing.name]['links'].append(url_template % rule['host'])
    else:
        for svc in kubernetes.list_cluster_services():
            svc_name = svc.obj["metadata"]["name"]
            if components and svc_name not in components:
                continue
            states.setdefault(svc_name, copy.deepcopy(STATE_TEMPLATE))
            for port in svc.obj["spec"]["ports"]:
                if port.get('nodePort'):
                    states[svc_name]["links"].append(EXT_LINK_TEMPLATE.format(
                        ext_ip=ext_ip,
                        port=port["nodePort"]))
    return states


def show_long_status(components=None):
    states = get_pod_states(components)
    columns = ("service", "pod", "job", "ready", "links")

    formatted_states = []

    for state in sorted(states):
        formatted_states.append((
            state,
            "{pod_running}/{pod_total}".format(**states[state]),
            "{job_completed}/{job_total}".format(**states[state]),
            repr_state(states[state]),
            "\n".join(states[state]["links"])))

    return columns, formatted_states


def show_short_status(components=None):
    states = get_pod_states(components)
    if not states:
        status = "not deployed"
    else:
        status = ST_OK if all(map(is_app_ready, states.values())) else ST_WIP
    return ("status",), ((status,),)
