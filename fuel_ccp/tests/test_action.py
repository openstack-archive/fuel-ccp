from collections import namedtuple
import copy
import io
import json
import os

import fixtures
import testscenarios

from fuel_ccp import action
from fuel_ccp.config import images as config_images
from fuel_ccp import exceptions
from fuel_ccp import templates
from fuel_ccp.tests import base

ACTION_DATA = {
    'name': 'test_name',
    'image': 'test_image',
    'command': 'test_command'
}


class TestActionFunctions(testscenarios.WithScenarios, base.TestCase):
    expected_clone_call = None
    dir_exists = True
    list_dir = ['test_1.yaml']

    data = {
        'actions': [
            copy.copy(ACTION_DATA)
        ]
    }
    true_scenario = False

    scenarios = [
        ('true_scenario', {'true_scenario': True}),
        ('no_dir', {'dir_exists': False}),
        ('no_yaml', {'list_dir': []}),
        ('no_actions', {'data': {'no_actions': True}}),
    ]

    def setUp(self):
        super(TestActionFunctions, self).setUp()
        # Creating temporaty directory for repos
        self.tmp_path = self.useFixture(fixtures.TempDir()).path
        self.conf['repositories']['path'] = self.tmp_path

        fixture = fixtures.MockPatch('os.path.isdir')
        self.isdir_mock = self.useFixture(fixture).mock
        self.isdir_mock.return_value = self.dir_exists

        fixture = fixtures.MockPatch('os.listdir')
        self.list_dir_mock = self.useFixture(fixture).mock
        self.list_dir_mock.return_value = self.list_dir

        fixture = fixtures.MockPatch('six.moves.builtins.open')
        self.mock_open = self.useFixture(fixture).mock

        fixture = fixtures.MockPatch('yaml.load')
        self.list_dir_mock = self.useFixture(fixture).mock
        self.list_dir_mock.return_value = self.data

    def test_action_list(self):
        actions = action.list_actions()
        if self.true_scenario:
            expected_result = {
                'restart_policy': 'never',
                'dependencies': (),
                'files': (),
            }
            if self.data.get('actions'):
                expected_result.update(self.data['actions'][0])
            components = [repo['name'][9:]
                          for repo in self.conf['repositories']['repos']]

            self.assertEqual(len(actions), len(components))

            for act in actions:
                act_dict = act.__dict__
                component_dir = act_dict.pop('component_dir')
                component = act_dict.pop('component')
                self.assertEqual(expected_result, act_dict)
                self.assertTrue(component in components)
                components.remove(component)
                self.assertEqual(component_dir,
                                 os.path.join(self.tmp_path,
                                              'fuel-ccp-' + component))
            self.assertFalse(components)
        else:
            self.assertFalse(actions)

    def test_get_action(self):
        if self.true_scenario:
            act = action.get_action('test_name')
            self.assertEqual(type(act), action.Action)
        else:
            self.assertRaises(exceptions.NotFoundException, action.get_action,
                              'test_name')

    def test_run_action(self):
        fixture = fixtures.MockPatchObject(action.Action, 'run')
        self.run_mock = self.useFixture(fixture).mock
        self.run_mock.return_value = 'test_name_1234567'
        if self.true_scenario:
            act = action.run_action('test_name')
            self.assertEqual(act, self.run_mock.return_value)
        else:
            self.assertRaises(exceptions.NotFoundException, action.get_action,
                              'test_name')


class TestAction(testscenarios.WithScenarios, base.TestCase):
    restart_policy = action.RESTART_POLICY_NEVER
    files = []
    scenarios = [
        ('pod', {}),
        ('job', {'restart_policy': action.RESTART_POLICY_ALWAYS}),
        ('not_valid', {'restart_policy': 'failed'}),
        ('with_files', {'files': [{'content': 'file_1', 'path': '',
                                   'perm': 'test_perm', 'user': 'test_user'}]})
    ]

    def setUp(self):
        super(TestAction, self).setUp()
        action_data = copy.copy(ACTION_DATA)
        # Creating temporaty directory for repos
        self.tmp_path = self.useFixture(fixtures.TempDir()).path
        self.conf['repositories']['path'] = self.tmp_path
        component = 'ceph'
        component_dir = os.path.join(self.tmp_path, 'fuel-ccp-' + component)
        if self.files:
            self.files[0]['path'] = self.tmp_path
        fixture = fixtures.MockPatch('six.moves.builtins.open')
        self.mock_open = self.useFixture(fixture).mock
        self.mock_open.side_effect = [io.StringIO(u'test')]
        action_data.update(component_dir=component_dir,
                           component=component,
                           restart_policy=self.restart_policy,
                           files=self.files)
        self.action = action.Action(**action_data)

        fixture = fixtures.MockPatch('fuel_ccp.kubernetes.process_object')
        self.kubernetes_mock = self.useFixture(fixture).mock

    def test_run(self):
        if self.restart_policy == 'failed':
            self.assertRaises(ValueError,
                              action.Action._create_action, self.action)
            return
        return_value = self.action.run()
        self.assertEqual(return_value, self.action.k8s_name)

    def _get_pod_spec(self):
        config_volume_items = [
            {
                'key': 'config',
                'path': 'globals/globals.json'
            },
            {
                'key': 'nodes-config',
                'path': 'nodes-config/nodes-config.json',
            },
            {
                'key': 'workflow',
                'path': 'role/%s.json' % self.action.name
            }
        ]
        if self.files:
            config_volume_items.append({
                'key':
                    self.files[0]['content'],
                'path':
                    'files/%s' % self.files[0]['content']
            })
        return {
            'metadata': {
                'name': self.action.k8s_name
            },
            'spec': {
                'containers': [
                    {
                        'name': self.action.k8s_name,
                        'image': config_images.image_spec(self.action.image),
                        'imagePullPolicy':
                            self.conf.kubernetes.image_pull_policy,
                        'command': templates.get_start_cmd(self.action.name),
                        'volumeMounts': [
                            {
                                'name': 'config-volume',
                                'mountPath': '/etc/ccp'
                            },
                            {
                                'name': 'start-script',
                                'mountPath': '/opt/ccp_start_script/bin'
                            }
                        ],
                        'env': templates.serialize_env_variables({}),
                        'restartPolicy': 'Never'
                    }
                ],
                'restartPolicy': 'Never',
                'volumes': [
                    {
                        'name': 'config-volume',
                        'configMap': {
                            'name': self.action.k8s_name,
                            'items': config_volume_items
                        }
                    },
                    {
                        'name': 'start-script',
                        'configMap': {
                            'name': templates.SCRIPT_CONFIG,
                            'items': [
                                {
                                    'key': templates.SCRIPT_CONFIG,
                                    'path': 'start_script.py'
                                }
                            ]
                        }
                    }
                ]
            }
        }

    def test_create_action(self):
        pod_spec = self._get_pod_spec()
        fixture = fixtures.MockPatchObject(action.Action, '_create_pod')
        create_pod_mock = self.useFixture(fixture).mock
        fixture = fixtures.MockPatchObject(action.Action, '_create_job')
        create_job_mock = self.useFixture(fixture).mock
        if self.restart_policy == 'failed':
            self.assertRaises(ValueError,
                              action.Action._create_action, self.action)
            return
        self.action._create_action()
        if self.restart_policy == action.RESTART_POLICY_NEVER:
            create_pod_mock.assert_called_once_with(pod_spec)
            create_job_mock.assert_not_called()
        elif self.restart_policy == action.RESTART_POLICY_ALWAYS:
            create_job_mock.assert_called_once_with(pod_spec)
            create_pod_mock.assert_not_called()

    def test_create_pod(self):
        pod_spec = self._get_pod_spec()
        pod_spec['metadata']['labels'] = {
            'app': self.action.name,
            'ccp': 'true',
            'ccp-action': 'true',
            'ccp-component': self.action.component
        }
        pod_spec.update({
            'kind': 'Pod',
            'apiVersion': 'v1'})

        self.action._create_pod(pod_spec)
        self.kubernetes_mock.assert_called_once_with(pod_spec)

    def test_create_job(self):
        job_spec = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': self.action.k8s_name,
                'labels': {
                    'app': self.action.name,
                    'ccp': 'true',
                    'ccp-component': self.action.component,
                    'ccp-action': 'true',
                }
            },
            'spec': {
                'template': self._get_pod_spec()
            }
        }
        self.action._create_job(self._get_pod_spec())
        self.kubernetes_mock.assert_called_once_with(job_spec)

    def _get_configmap(self):
        files = []
        if self.files:
            files = [
                {
                    'name': self.files[0]['content'],
                    'path': self.files[0]['path'],
                    'perm': self.files[0].get('perm'),
                    'user': self.files[0].get('user')
                }
            ]
        cm = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': self.action.k8s_name,
                'labels': {
                    'ccp': 'true'
                }
            },
            'data': {
                'config': self.conf.configs._json(sort_keys=True),
                'nodes-config': '{}',
                'workflow': json.dumps(
                    {
                        'workflow': {
                            'name': self.action.name,
                            'dependencies': self.action.dependencies,
                            'job': {
                                'command': self.action.command
                            },
                            'files': files
                        }
                    }
                )
            }
        }
        if self.files:
            cm['data'].update({'file_1': 'test'})
        return cm

    def test_create_configmap(self):
        self.action._create_configmap()
        self.kubernetes_mock.assert_called_once_with(self._get_configmap())


K8S_SPEC = {
    'name': 'test_action',
    'obj': {
        'metadata': {
            'creationTimestamp': 'time'
        },
        'status': {
            'failed': 0,
            'active': 0,
            'phase': 'Complete'
        }
    },
    'labels': {
        'ccp-component': 'test_component'
    },
    'kind': 'Job'
}

KUBERNETES = namedtuple('Kubernetes',
                        ['name', 'obj', 'labels', 'kind'])


class TestActionStatus(testscenarios.WithScenarios, base.TestCase):
    kind = 'Pod'
    phase = 'Pending'
    failed = 0
    active = True
    scenarios = [
        ('pod_failed', {'phase': 'Failed'}),
        ('pod_ok', {'phase': 'Completed'}),
        ('pod_wip', {}),
        ('job_restarts', {'kind': 'Job', 'failed': 2}),
        ('job_ok', {'kind': 'Job', 'active': False}),
        ('job_wip', {'kind': 'Job'}),
    ]

    def setUp(self):
        super(TestActionStatus, self).setUp()
        k8s_spec = copy.deepcopy(K8S_SPEC)
        k8s_spec['kind'] = self.kind
        k8s_spec['obj']['status'] = {
            'failed': self.failed,
            'active': self.active,
            'phase': self.phase
        }

        k8s_object = KUBERNETES(name=k8s_spec['name'],
                                obj=k8s_spec['obj'],
                                labels=k8s_spec['labels'],
                                kind=k8s_spec['kind'])

        self.status_obj = action.ActionStatus(k8s_object)

    def test_status(self):
        if self.kind == 'Job' and self.failed:
            self.assertEqual(self.status_obj.restarts, self.failed)

        if self.phase == 'Failed':
            self.assertEqual(self.status_obj.status, 'fail')
        elif self.active and not self.phase == 'Completed':
            self.assertEqual(self.status_obj.status, 'wip')
        else:
            self.assertEqual(self.status_obj.status, 'ok')


class TestListActionStatus(testscenarios.WithScenarios, base.TestCase):

    action_name = None
    scenarios = [
        ('no_name', {}),
        ('with_name', {'action_name': 'test_name'}),
    ]

    def setUp(self):
        super(TestListActionStatus, self).setUp()
        k8s_status = KUBERNETES(
            name=K8S_SPEC['name'],
            obj=K8S_SPEC['obj'],
            labels=K8S_SPEC['labels'],
            kind=K8S_SPEC['kind']
        )
        fixture = fixtures.MockPatch('fuel_ccp.kubernetes.list_cluster_jobs')
        self.kubernetes_job_mock = self.useFixture(fixture).mock
        self.kubernetes_job_mock.return_value = [k8s_status]

        fixture = fixtures.MockPatch('fuel_ccp.kubernetes.list_cluster_pods')
        self.kubernetes_pod_mock = self.useFixture(fixture).mock
        self.kubernetes_pod_mock.return_value = [k8s_status]

    def test_list_action_status(self):
        k8s_statuses = action.list_action_status(self.action_name)

        selector = 'ccp-action=true'
        if self.action_name:
            selector += ',' + 'app=%s' % self.action_name
        for k8s_status in k8s_statuses:
            self.assertEqual(type(k8s_status), action.ActionStatus)

        self.kubernetes_job_mock.assert_called_once_with(selector=selector)
        self.kubernetes_pod_mock.assert_called_once_with(selector=selector)
