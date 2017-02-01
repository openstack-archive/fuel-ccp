import copy
import json
import logging
import os
import uuid

import yaml

from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp.config import images as config_images
from fuel_ccp import exceptions
from fuel_ccp import kubernetes
from fuel_ccp import templates


CONF = config.CONF

LOG = logging.getLogger(__name__)

RESTART_POLICY_ALWAYS = "always"
RESTART_POLICY_NEVER = "never"


class Action(object):
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.component = kwargs.pop("component")
        self.component_dir = kwargs.pop("component_dir")
        self.image = kwargs.pop("image")
        self.command = kwargs.pop("command")
        self.dependencies = kwargs.pop("dependencies", ())
        self.files = kwargs.pop("files", ())
        self.restart_policy = kwargs.pop("restart_policy",
                                         RESTART_POLICY_NEVER)

        if kwargs:
            key_names = ", ".join(kwargs.keys())
            raise ValueError("Invalid keys '%s' for '%s' action" % (
                             key_names, self.name))

    @property
    def k8s_name(self):
        if not hasattr(self, "_k8s_name"):
            self._k8s_name = "%s-%s" % (self.name, str(uuid.uuid4())[:8])
        return self._k8s_name

    def validate(self):
        pass

    def run(self):
        self._create_configmap()
        self._create_action()
        return self.k8s_name

    # configmap methods

    def _create_configmap(self):
        data = {
            "config": CONF.configs._json(sort_keys=True),
            "workflow": self._get_workflow()
        }
        data.update(self._get_file_templates())

        cm = templates.serialize_configmap(self.k8s_name, data)
        kubernetes.process_object(cm)

    def _get_workflow(self):
        wf = {
            "name": self.name,
            "dependencies": self.dependencies,
            "job": {
                "command": self.command
            },
            "files": []
        }
        for f in self.files:
            wf["files"].append({
                "name": f["content"],
                "path": f["path"],
                "perm": f.get("perm"),
                "user": f.get("user")
            })
        return json.dumps({"workflow": wf})

    def _get_file_templates(self):
        # TODO(sreshetniak): use imports and add macros CM
        data = {}
        for f in self.files:
            template_path = os.path.join(self.component_dir,
                                         "service", "files",
                                         f["content"])
            with open(template_path) as filedata:
                data[f["content"]] = filedata.read()
        return data

    # job methods

    def _create_action(self):
        cont_spec = {
            "name": self.k8s_name,
            "image": config_images.image_spec(self.image),
            "imagePullPolicy": CONF.kubernetes.image_pull_policy,
            "command": templates.get_start_cmd(self.name),
            "volumeMounts": [
                {
                    "name": "config-volume",
                    "mountPath": "/etc/ccp"
                },
                {
                    "name": "start-script",
                    "mountPath": "/opt/ccp_start_script/bin"
                }
            ],
            "env": templates.serialize_env_variables({}),
            "restartPolicy": "Never"
        }
        config_volume_items = [
            {
                "key": "config",
                "path": "globals/globals.json"
            },
            {
                "key": "workflow",
                "path": "role/%s.json" % self.name
            }
        ]
        for f in self.files:
            config_volume_items.append({
                "key": f["content"],
                "path": "files/%s" % f["content"]
            })
        pod_spec = {
            "metadata": {
                "name": self.k8s_name
            },
            "spec": {
                "containers": [cont_spec],
                "restartPolicy": "Never",
                "volumes": [
                    {
                        "name": "config-volume",
                        "configMap": {
                            "name": self.k8s_name,
                            "items": config_volume_items
                        }
                    },
                    {
                        "name": "start-script",
                        "configMap": {
                            "name": templates.SCRIPT_CONFIG,
                            "items": [
                                {
                                    "key": templates.SCRIPT_CONFIG,
                                    "path": "start_script.py"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        if self.restart_policy == RESTART_POLICY_NEVER:
            self._create_pod(pod_spec)
        elif self.restart_policy == RESTART_POLICY_ALWAYS:
            self._create_job(pod_spec)
        else:
            raise ValueError("Restart policy %s is not supported" % (
                self.restart_policy))

    def _create_pod(self, pod_spec):
        spec = copy.deepcopy(pod_spec)
        spec["metadata"].setdefault("labels", {})
        spec["metadata"]["labels"].update({
            "app": self.name,
            "ccp": "true",
            "ccp-action": "true",
            "ccp-component": self.component})
        spec.update({
            "kind": "Pod",
            "apiVersion": "v1"})
        kubernetes.process_object(spec)

    def _create_job(self, pod_spec):
        job_spec = templates.serialize_job(
            name=self.k8s_name,
            spec=pod_spec,
            component_name=self.component,
            app_name=self.name)
        job_spec["metadata"]["labels"].update({"ccp-action": "true"})
        if kubernetes.process_object(job_spec):
            LOG.info('%s: action "%s" has been successfully run',
                     self.component, self.k8s_name)


class ActionStatus(object):

    @classmethod
    def get_actions(cls, action_name=None):
        selector = "ccp-action=true"
        if action_name:
            selector += "," + "app=%s" % action_name
        actions = []
        for job in kubernetes.list_cluster_jobs(selector=selector):
            actions.append(cls(job))
        for pod in kubernetes.list_cluster_pods(selector=selector):
            actions.append(cls(pod))
        return actions

    def __init__(self, k8s_spec):
        self._spec = k8s_spec
        self.name = k8s_spec.name
        self.component = k8s_spec.labels["ccp-component"]
        self.date = k8s_spec.obj["metadata"]["creationTimestamp"]
        if k8s_spec.kind == "Job":
            self.restarts = k8s_spec.obj["status"].get("failed", 0)
            self.active = k8s_spec.obj["status"].get("active", 0)
            self.failed = False
        else:
            phase = k8s_spec.obj["status"]["phase"]
            self.restarts = 0
            self.active = 1 if phase not in {"Failed", "Completed"} else 0
            self.failed = phase == "Failed"

    @property
    def status(self):
        if self.failed:
            return "fail"
        if self.active:
            return "wip"
        return "ok"

    def log(self):
        if self._spec.kind == "Pod":
            return self._spec.logs()
        else:
            pod_selector = "job-name=%s" % self._spec.name
            pods = kubernetes.list_cluster_pods(raw_selector=pod_selector)
            for pod in pods:
                if pod.obj['status']['phase'] == "Failed":
                    continue
                return pod.logs()


def list_actions():
    """List of available actions.

    :returns: list -- list of all available actions
    """
    actions = []
    for repo in utils.get_repositories_paths():
        component_name = utils.get_component_name_from_repo_path(repo)
        action_path = os.path.join(repo, "service", "actions")
        if not os.path.isdir(action_path):
            continue
        for filename in os.listdir(action_path):
            if filename.endswith(".yaml"):
                with open(os.path.join(action_path, filename)) as f:
                    data = yaml.load(f)
                    for action_dict in data.get("actions", ()):
                        actions.append(Action(component=component_name,
                                              component_dir=repo,
                                              **action_dict))
    return actions


def get_action(action_name):
    """Get action by name.

    :returns: Action -- action object
    :raises: fuel_ccp.exceptions.NotFoundException
    """
    for action in list_actions():
        if action_name == action.name:
            return action
    raise exceptions.NotFoundException("Action with name '%s' not found" % (
                                       action_name))


def run_action(action_name):
    """Run action.

    :returns: str -- action name
    :raises: fuel_ccp.exceptions.NotFoundException
    """
    action = get_action(action_name)
    action.validate()
    return action.run()


def list_action_status(action_type=None):
    return ActionStatus.get_actions(action_type)


def get_action_status_by_name(action_name):
    for action in list_action_status():
        if action.name == action_name:
            return action
    raise exceptions.NotFoundException("Action with name \"%s\" not found" % (
                                       action_name))


def get_action_statuses_by_names(action_names):
    action_names = set(action_names)
    actions = []
    for action in list_action_status():
        if action.name in action_names:
            action_names.remove(action.name)
            actions.append(action)
    if action_names:
        raise exceptions.NotFoundException(
            "Action(s) with name(s) %s not found" % (
                ", ".join(action_names)))
    return actions
