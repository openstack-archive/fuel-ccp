import mock
from oslo_config import cfg
import yaml

from microservices import deploy
from microservices.tests import base

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
            "microservices.kubernetes.create_object_from_definition")
        self.create_obj = self._create_obj.start()

    def test_create_service_without_ports(self):
        deploy._create_service({"name": "spam"})
        self.assertFalse(self.create_obj.called)

    def test_create_service(self):
        service = {
            "name": "foo",
            "ports": [
                1234,
                "1122:3344",
                "5566",
                "port1",
                "port2:nodeport",
                "7788:nodeport",
                "port3:9900"
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
        with mock.patch("microservices.deploy._get_defaults",
                        return_value=defaults):
            deploy._create_service(service)
            self.create_obj.assert_called_once_with(yaml.load(service_k8s_obj))

    def teadDown(self):
        super(TestDeployCreateService, self).teadDown()
        self._create_obj.stop()
