from __future__ import print_function

import logging

from fuel_ccp import config
from fuel_ccp import kubernetes

CONF = config.CONF

LOG = logging.getLogger(__name__)


class State(object):
    def __init__(self, name, total, running, urls):
        self.name = name
        self.total = total or 0
        self.running = running or 0
        self.urls = urls or []

    def __repr__(self):
        return "Service \"%s\": total %d, available %d" % (
            self.name, self.total, self.running)

    def __lt__(self, other):
        return self.name.__lt__(other.name)

    def __bool__(self):
        return self.ready

    @property
    def ready(self):
        return self.total == self.running


def _get_pods_status(service, svc_map):
    pods = kubernetes.list_cluster_pods(service=service)
    total = running = waiting = failed = 0
    for pod in pods:
        total += 1
        if pod.ready:
            running += 1
    return State(
        name=service,
        total=total,
        running=running,
        urls=svc_map.get(service, []))


def get_pod_states(components=None):
    ext_ip = CONF.configs.get("k8s_external_ip", "")
    ext_link_template = "http://{ext_ip}:{port}"
    states = []
    svc_map = {}
    for svc in kubernetes.list_cluster_services():
        svc_name = svc.obj["metadata"]["name"]
        svc_map.setdefault(svc_name, [])
        for port in svc.obj["spec"]["ports"]:
            svc_map[svc_name].append(ext_link_template.format(ext_ip=ext_ip,
                port=port["nodePort"]))
    for dp in kubernetes.list_cluster_deployments():
        if not components or dp.name in components:
            states.append(_get_pods_status(dp.name, svc_map))
    for ds in kubernetes.list_cluster_daemonsets():
        if not components or ds.name in components:
            states.append(_get_pods_status(ds.name, svc_map))

    return states


def show_long_status(components=None):
    states = get_pod_states(components)
    columns = ("service", "pod", "ready", "links")

    formatted_states = []

    for state in sorted(states):
        formatted_states.append((
            state.name,
            "/".join((str(state.running), str(state.total))),
            "ok" if state else "fail",
            "\n".join(state.urls)))

    return columns, formatted_states


def show_short_status():
    status = "ok" if all(get_pod_states()) else "fail"
    return ("status",), ((status,),)
