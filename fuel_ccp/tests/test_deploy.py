import filecmp
import os

import fixtures
import yaml

from fuel_ccp import deploy
from fuel_ccp.tests import base


class TestDeploy(base.TestCase):
    def setUp(self):
        super(TestDeploy, self).setUp()
        self.namespace = "py27_test_delme"

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

    def test_create_openrc(self):
        namespace = self.namespace
        openrc_etalon_file = 'openrc-%s-etalon' % namespace
        openrc_test_file = 'openrc-%s' % namespace
        config = {"openstack_project_name": "admin",
                  "openstack_user_name": "admin",
                  "openstack_user_password": "password",
                  "keystone_public_port": 5000}
        rc = ["export OS_PROJECT_DOMAIN_NAME=default",
              "export OS_USER_DOMAIN_NAME=default",
              "export OS_PROJECT_NAME=%s" % config['openstack_project_name'],
              "export OS_USERNAME=%s" % config['openstack_user_name'],
              "export OS_PASSWORD=%s" % config['openstack_user_password'],
              "export OS_IDENTITY_API_VERSION=3",
              "export OS_AUTH_URL=http://keystone.%s.svc.cluster.local:%s/v3" %
              (namespace, config['keystone_public_port'])]

        with open(openrc_etalon_file, 'w') as openrc_file:
            openrc_file.write("\n".join(rc))
        self.addCleanup(os.remove, openrc_etalon_file)
        deploy._create_openrc(config, namespace)
        self.addCleanup(os.remove, openrc_test_file)
        result = filecmp.cmp(openrc_etalon_file,
                             openrc_test_file,
                             shallow=False)
        self.assertTrue(result)


class TestDeployCreateService(base.TestCase):
    def setUp(self):
        super(TestDeployCreateService, self).setUp()
        fixture = self.useFixture(fixtures.MockPatch(
            "fuel_ccp.kubernetes.create_object_from_definition"))
        self.create_obj = fixture.mock

    def test_create_service_without_ports(self):
        deploy._create_service({"name": "spam"}, {})
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
  labels:
    ccp: "true"
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
        deploy._create_service(service, defaults)
        self.create_obj.assert_called_once_with(yaml.load(service_k8s_obj))


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


class TestDeployMakeTopology(base.TestCase):
    def setUp(self):
        super(TestDeployMakeTopology, self).setUp()
        self.useFixture(
            fixtures.MockPatch("fuel_ccp.kubernetes.list_k8s_nodes"))

    def test_make_empty_topology(self):
        self.assertRaises(RuntimeError,
                          deploy._make_topology, None, None)
        self.assertRaises(RuntimeError,
                          deploy._make_topology, None, {"spam": "eggs"})
        self.assertRaises(RuntimeError,
                          deploy._make_topology, {"spam": "eggs"}, None)

    def test_make_topology(self):
        node_list = ["node1", "node2", "node3"]
        self.useFixture(fixtures.MockPatch(
            "fuel_ccp.kubernetes.get_object_names", return_value=node_list))

        roles = {
            "controller": [
                "mysql",
                "keystone"
            ],
            "compute": [
                "nova-compute",
                "libvirtd"
            ]
        }

        nodes = {
            "node1": {
                "roles": ["controller"]
            },
            "node[2-3]": {
                "roles": ["compute"]
            }
        }

        expected_topology = {
            "mysql": ["node1"],
            "keystone": ["node1"],
            "nova-compute": ["node2", "node3"],
            "libvirtd": ["node2", "node3"]
        }

        topology = deploy._make_topology(nodes, roles)
        self.assertDictEqual(expected_topology, topology)

        # check if role is defined but not used
        nodes = {
            "node1": {
                "roles": ["controller"]
            },
        }

        expected_topology = {
            "mysql": ["node1"],
            "keystone": ["node1"]
        }
        topology = deploy._make_topology(nodes, roles)
        self.assertDictEqual(expected_topology, topology)

        # two ways to define topology that should give the same result
        # first
        nodes = {
            "node1": {
                "roles": ["controller", "compute"]
            },
            "node[2-3]": {
                "roles": ["compute"]
            }
        }

        expected_topology = {
            "mysql": ["node1"],
            "keystone": ["node1"],
            "nova-compute": ["node1", "node2", "node3"],
            "libvirtd": ["node1", "node2", "node3"]
        }
        topology = deploy._make_topology(nodes, roles)
        self.assertDictEqual(expected_topology, topology)

        # second
        nodes = {
            "node1": {
                "roles": ["controller"]
            },
            "node[1-3]": {
                "roles": ["compute"]
            }
        }

        expected_topology = {
            "mysql": ["node1"],
            "keystone": ["node1"],
            "nova-compute": ["node1", "node2", "node3"],
            "libvirtd": ["node1", "node2", "node3"]
        }
        topology = deploy._make_topology(nodes, roles)
        self.assertDictEqual(expected_topology, topology)
