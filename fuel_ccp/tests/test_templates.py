from fuel_ccp import templates
from fuel_ccp.tests import base


class TestDeploy(base.TestCase):

    def test_serialize_daemon_container_spec(self):
        container = {
            "name": "name_foo",
            "image": "image_foo",
            "command": "command_foo",
            "cm_version": 1,
            "env": [{
                "name": "env_foo",
                "valueFrom": {
                    "valueField": {
                        "valuePath": "metadata.name"
                    }
                }
            }]
        }
        container_spec = templates.serialize_daemon_container_spec(container)
        expected = {
            "name": "name_foo",
            "image": "ccp/image_foo:latest",
            "command": [
                "dumb-init",
                "/usr/bin/python",
                "/opt/ccp_start_script/bin/start_script.py",
                "provision",
                "name_foo"
            ],
            "volumeMounts": [
                {'mountPath': '/etc/ccp/globals', 'name': 'globals'},
                {'mountPath': '/etc/ccp/role', 'name': 'role'},
                {'mountPath': '/etc/ccp/meta', 'name': 'meta'},
                {'mountPath': '/opt/ccp_start_script/bin',
                 'name': 'start-script'},
                {'mountPath': '/etc/ccp/files', 'name': 'files'}
            ],
            "readinessProbe": {
                "exec": {
                    "command": [
                        "/usr/bin/python",
                        "/opt/ccp_start_script/bin/start_script.py",
                        "status",
                        "name_foo"
                    ]
                },
                "timeoutSeconds": 1
            },
            "env": [{
                "name": "CCP_NODE_NAME",
                'valueFrom': {
                    'fieldRef': {
                        'fieldPath': 'spec.nodeName'
                    }
                }
            },
                {
                "name": "env_foo",
                "valueFrom": {
                    "valueField": {
                        "valuePath": "metadata.name"
                    }
                }
            },
                {
                "name": "CM_VERSION",
                "value": 1
            }],
            "securityContext": {
                "privileged": False
            }
        }
        self.assertDictEqual(expected, container_spec)
