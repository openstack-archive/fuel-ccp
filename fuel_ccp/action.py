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


class Action(object):
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.component = kwargs.pop("component")
        self.component_dir = kwargs.pop("component_dir")
        self.image = kwargs.pop("image")
        self.command = kwargs.pop("command")
        self.dependencies = kwargs.pop("dependencies", ())
        self.files = kwargs.pop("files", ())

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
        self._create_job()

    def delete(self, job_names=None):
        selector = "ccp-action=true"
        selector += "," + "app=%s" % self.name
        result = kubernetes.delete_action(selector, job_names)
        deleted_jobs = ', '.join(result['deleted'])
        LOG.info('Jobs have been deleted: %s', deleted_jobs)
        if result['not_founded']:
            raise exceptions.NotFoundException(
                "Job(s) with name(s) '%s' not found" % result['not_founded'])

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

    def _create_job(self):
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
    def get_actions(cls, action_name):
        selector = "ccp-action=true"
        if action_name:
            selector += "," + "app=%s" % action_name
        actions = []
        for job in kubernetes.list_cluster_jobs(selector):
            actions.append(cls(job))
        return actions

    def __init__(self, k8s_job):
        self.name = k8s_job.name
        self.component = k8s_job.labels["ccp-component"]
        self.date = k8s_job.obj["metadata"]["creationTimestamp"]
        self.restarts = k8s_job.obj["status"].get("failed", 0)
        self.active = k8s_job.obj["status"].get("active", 0)

    @property
    def status(self):
        if self.restarts:
            return "fail"
        if self.active:
            return "wip"
        return "ok"


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

    :raises: fuel_ccp.exceptions.NotFoundException
    """
    action = get_action(action_name)
    action.validate()
    action.run()


def list_action_status(action_name=None):
    return ActionStatus.get_actions(action_name)


def delete_action(action_name, job_names):
    """Delete action.

    :raises: fuel_ccp.exceptions.NotFoundException
    """
    action = get_action(action_name)
    action.delete(job_names)
