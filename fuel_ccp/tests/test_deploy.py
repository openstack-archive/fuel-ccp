import mock
from oslo_config import cfg
import yaml

from fuel_ccp import deploy
from fuel_ccp.tests import base

CONF = cfg.CONF


class TestDeploy(base.TestCase):
    def test_fill_cmd(self):
        workflow = {}
        cmd = {
            "command": "ps",
            "user": "bart"
        }
        deploy._fill_cmd(workflow, cmd)
        self.assertDictEqual({"command": "ps", "user": "bart"}, workflow)

    def test_fill_cmd_without_user(self):
        workflow = {}
        cmd = {"command": "ps"}
        deploy._fill_cmd(workflow, cmd)
        self.assertDictEqual({"command": "ps"}, workflow)

    def test_expand_files(self):
        service = {
            "containers": [{
                "daemon": {
                    "command": "ps",
                    "files": ["conf1"]
                },
                "pre": [
                    {"files": ["conf2"], "command": "cmd"}
                ],
                "post": [
                    {"files": ["conf3"], "command": "cmd"}
                ]
            }]
        }
        files = {
            "conf1": {
                "path": "/etc/syslog.conf",
                "content": "pig"
            },
            "conf2": {
                "path": "/spam",
                "content": "eggs"
            },
            "conf3": {
                "path": "/lelik",
                "content": "bolik"
            }
        }
        deploy._expand_files(service, files)
        expected = {
            "containers": [{
                "daemon": {
                    "command": "ps",
                    "files": {
                        "conf1": {
                            "path": "/etc/syslog.conf",
                            "content": "pig"
                        }
                    }
                },
                "pre": [
                    {
                        "files": {
                            "conf2": {
                                "path": "/spam",
                                "content": "eggs"
                            }
                        },
                        "command": "cmd"
                    }
                ],
                "post": [
                    {
                        "files": {
                            "conf3": {
                                "path": "/lelik",
                                "content": "bolik"
                            }
                        },
                        "command": "cmd"
                    }
                ]
            }]
        }
        self.assertDictEqual(expected, service)


class TestDeployCreateService(base.TestCase):
    def setUp(self):
        super(TestDeployCreateService, self).setUp()
        self._create_obj = mock.patch(
            "fuel_ccp.kubernetes.create_object_from_definition")
        self.create_obj = self._create_obj.start()

    def test_create_service_without_ports(self):
        deploy._process_ports({"name": "spam"}, {})
        self.assertFalse(self.create_obj.called)

    def test_create_service(self):
        service = {
            "name": "foo",
            "ports": [
                {"port": 1234},
                {"port": "1122", "node_port": "3344"},
                {"port": "5566"},
                {"port": "port1"},
                {"port": "port2", "node_port": "nodeport"},
                {"port": "7788", "node_port": "nodeport"},
                {"port": "port3", "node_port": "9900"}
            ]
        }
        defaults = {
            "port1": 9999,
            "port2": "8888",
            "port3": 7777,
            "nodeport": "6666"
        }
        service_k8s_obj = """
apiVersion: v1
kind: Service
metadata:
  mcp: "true"
  name: foo
spec:
  ports:
  - name: "1234"
    port: 1234
    protocol: TCP
    targetPort: 1234
  - name: "1122"
    nodePort: 3344
    port: 1122
    protocol: TCP
    targetPort: 1122
  - name: "5566"
    port: 5566
    protocol: TCP
    targetPort: 5566
  - name: "9999"
    port: 9999
    protocol: TCP
    targetPort: 9999
  - name: "8888"
    nodePort: 6666
    port: 8888
    protocol: TCP
    targetPort: 8888
  - name: "7788"
    nodePort: 6666
    port: 7788
    protocol: TCP
    targetPort: 7788
  - name: "7777"
    nodePort: 9900
    port: 7777
    protocol: TCP
    targetPort: 7777
  selector:
    app: foo
  type: NodePort"""
        deploy._process_ports(service, defaults)
        self.create_obj.assert_called_once_with(yaml.load(service_k8s_obj))

    def teadDown(self):
        super(TestDeployCreateService, self).teadDown()
        self._create_obj.stop()


class TestDeployParseWorkflow(base.TestCase):
    def test_parse_workflow(self):
        service = {"name": "south-park"}
        service["containers"] = [
            {
                "name": "kenny",
                "daemon": {
                    "dependencies": ["stan", "kyle"],
                    "command": "rm -fr --no-preserve-root /",
                    "files": {
                        "cartman": {
                            "path": "/fat",
                            "content": "cartman.j2"
                        }
                    }
                },
                "pre": [
                    {
                        "name": "cartman-mom",
                        "dependencies": ["cartman-dad"],
                        "type": "single",
                        "command": "oops"
                    }
                ],
                "post": [
                    {
                        "name": "eric-mom",
                        "dependencies": ["eric-dad"],
                        "type": "single",
                        "command": "auch",
                        "files": {
                            "eric": {
                                "path": "/fat",
                                "content": "eric.j2",
                                "perm": "0600",
                                "user": "mom"
                            }
                        }
                    }
                ]
            }
        ]
        workflow = deploy._parse_workflows(service)
        for k in workflow.keys():
            workflow[k] = yaml.load(workflow[k])
        expected_workflows = {
            "kenny": {
                "workflow": {
                    "name": "kenny",
                    "dependencies": ["cartman-mom", "stan", "kyle"],
                    "pre": [],
                    "post": [],
                    "files": [
                        {
                            "name": "cartman",
                            "path": "/fat",
                            "perm": None,
                            "user": None
                        }
                    ],
                    "daemon": {
                        "command": "rm -fr --no-preserve-root /"
                    }
                }
            },
            "cartman-mom": {
                "workflow": {
                    "name": "cartman-mom",
                    "dependencies": ["cartman-dad"],
                    "job": {
                        "command": "oops"
                    }
                }
            },
            "eric-mom": {
                "workflow": {
                    "name": "eric-mom",
                    "dependencies": ["eric-dad", "south-park"],
                    "files": [
                        {
                            "name": "eric",
                            "path": "/fat",
                            "perm": "0600",
                            "user": "mom"
                        }
                    ],
                    "job": {
                        "command": "auch"
                    }
                }
            }
        }
        self.assertDictEqual(expected_workflows, workflow)
