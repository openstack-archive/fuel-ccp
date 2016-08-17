from __future__ import print_function

from oslo_log import log as logging
import prettytable

from fuel_ccp import kubernetes


LOG = logging.getLogger(__name__)


class State(object):
    def __init__(self, name, total, running, waiting, failed):
        self.name = name
        self.total = total or 0
        self.running = running or 0
        self.waiting = waiting or 0
        self.failed = failed or 0

    def __repr__(self):
        return "Service \"%s\": total %d, available %d" % (
            self.name, self.total, self.active)

    def __lt__(self, other):
        return self.name.__lt__(other.name)


def _red(s):
    return "\033[31m%s\033[39m" % s


def _yellow(s):
    return "\033[33m%s\033[39m" % s


def _colorized_if_not_zero(number, color):
    return number if number == 0 else color(number)


def _get_pods_status(service):
    pods = kubernetes.list_cluster_pods(service=service)
    total = running = waiting = failed = 0
    for pod in pods:
        total += 1
        phase = pod.status.phase
        if phase == "Running":
            running += 1
        elif phase in ("Pending", "Waiting", "ContainerCreating"):
            waiting += 1
        elif phase == "Failed":
            failed += 1
        else:
            LOG.warning("Unexpected phase \"%s\" for pod %s", phase,
                        pod.metadata.name)
    return State(
        name=service,
        total=total,
        running=running,
        waiting=waiting,
        failed=failed)


def show_status():
    states = []
    for dp in kubernetes.list_cluster_deployments():
        states.append(_get_pods_status(dp.metadata.name))
    for ds in kubernetes.list_cluster_daemonsets():
        states.append(_get_pods_status(ds.metadata.name))

    table = prettytable.PrettyTable()
    columns = ("Service", "Total", "Running", "Waiting", "Failed")
    aligns = ("l", "c", "c", "c", "c")
    for col, al in zip(columns, aligns):
        table.add_column(col, (), al)

    for state in sorted(states):
        table.add_row((
            state.name,
            state.total,
            state.running,
            _colorized_if_not_zero(state.waiting, _yellow),
            _colorized_if_not_zero(state.failed, _red)))

    print(table)
