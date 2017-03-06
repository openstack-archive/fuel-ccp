import filecmp
import os

import fixtures
import mock
import yaml

from fuel_ccp.config import _yaml
from fuel_ccp import deploy
from fuel_ccp.tests import base
from fuel_ccp.validation import deploy as deploy_validation


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

    def test_expand_items(self):
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
        deploy._expand_items(service, "files", files)
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
        self.conf.configs._merge({'ingress': {'enabled': False}})
        conf_dict = {"security": {"tls": {"openstack": {"enabled": False}}},
                     "etcd": {"tls": {"enabled": True}}}
        prepared_conf = self.nested_dict_to_attrdict(conf_dict)
        self.conf.configs._merge(prepared_conf)

        openrc_etalon_file = 'openrc-%s-etalon' % namespace
        openrc_test_file = 'openrc-%s' % namespace
        cert_path = os.path.join(os.getcwd(), 'ca-cert.pem')
        config = {
            "openstack": {
                "project_name": "admin",
                "user_name": "admin",
                "user_password": "password",
            },
            "keystone": {"public_port": {"cont": 5000}},
            "namespace": self.namespace,
            "security": {
                "tls": {
                    "create_certificates": "enabled",
                    "ca_cert": "test_certificate"
                }

            }
        }
        rc = [
            "export OS_PROJECT_DOMAIN_NAME=default",
            "export OS_USER_DOMAIN_NAME=default",
            "export OS_PROJECT_NAME=%s" % config['openstack']['project_name'],
            "export OS_USERNAME=%s" % config['openstack']['user_name'],
            "export OS_PASSWORD=%s" % config['openstack']['user_password'],
            "export OS_IDENTITY_API_VERSION=3",
            "export OS_AUTH_URL=http://keystone.ccp.svc.cluster.local:%s/v3" %
            config['keystone']['public_port']['cont'],
            "export OS_CACERT=%s" % cert_path,
        ]

        with open(openrc_etalon_file, 'w') as openrc_file:
            openrc_file.write("\n".join(rc))
        self.addCleanup(os.remove, openrc_etalon_file)
        deploy._create_openrc(config)
        self.addCleanup(os.remove, openrc_test_file)
        self.addCleanup(os.remove, "ca-cert.pem")
        result = filecmp.cmp(openrc_etalon_file,
                             openrc_test_file,
                             shallow=False)
        self.assertTrue(result)

    def test_get_configmaps_version(self):
        self.useFixture(fixtures.MockPatch(
            "fuel_ccp.deploy._get_service_files_hash", return_value='222'))

        cm_list = [mock.Mock(obj={'metadata': {'resourceVersion': '1'}})
                   for _ in range(3)]
        self.assertEqual('111222', deploy._get_configmaps_version(
            cm_list, mock.ANY, mock.ANY))

        cm_list = []
        self.assertEqual('222', deploy._get_configmaps_version(
            cm_list, mock.ANY, mock.ANY))

    def test_get_service_files_hash(self):
        files = {
            'file': {'content': '/tmp/file'}
        }
        self.useFixture(fixtures.MockPatch(
            "fuel_ccp.common.jinja_utils.jinja_render",
            return_value='rendered'))
        expected_hash = '86e85bd63aef5a740d4b7b887ade37ec9017c961'
        self.assertEqual(
            expected_hash, deploy._get_service_files_hash(files, {}))


class TestDeployProcessPorts(base.TestCase):
    def setUp(self):
        super(TestDeployProcessPorts, self).setUp()
        fixture = self.useFixture(fixtures.MockPatch(
            "fuel_ccp.kubernetes.process_object"))
        self.create_obj = fixture.mock

    def test_create_service_without_ports(self):
        deploy._process_ports({"name": "spam"})
        self.assertFalse(self.create_obj.called)

    def test_create_service(self):
        self.conf.configs._merge({'ingress': {'enabled': False}})
        service = {
            "name": "foo",
            "ports": [
                {"cont": 1111},
                {"cont": "2222"},
                {"cont": 3333,
                 "node": 30000},
                {"cont": "4444",
                 "node": "33333"}
            ]
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
  - name: "1111"
    port: 1111
    protocol: TCP
    targetPort: 1111
  - name: "2222"
    port: 2222
    protocol: TCP
    targetPort: 2222
  - name: "3333"
    nodePort: 30000
    port: 3333
    protocol: TCP
    targetPort: 3333
  - name: "4444"
    nodePort: 33333
    port: 4444
    protocol: TCP
    targetPort: 4444
  selector:
    app: foo
  type: NodePort"""
        objects = list(deploy._process_ports(service))
        self.assertEqual([yaml.load(service_k8s_obj)], objects)

    def test_create_service_with_annotations(self):
        self.conf.configs._merge({'ingress': {'enabled': False}})
        service = {
            "name": "foo",
            "annotations": {'service': {"bla": "ble", "foo": "boo"}},
            "ports": [
                {"cont": 1111},
                {"cont": "2222"},
                {"cont": 3333,
                 "node": 30000},
                {"cont": "4444",
                 "node": "33333"}
            ]
        }
        objects = list(deploy._process_ports(service))
        self.assertEqual(
            {'bla': 'ble', 'foo': 'boo'},
            objects[0]['metadata']['annotations'])

    def test_create_ingress(self):
        self.conf.configs._merge({'ingress': {'enabled': True,
                                              'domain': 'test'}})

        service = {
            "name": "foo",
            "ports": [
                {"cont": 1111,
                 "ingress": "bar"},
                {"cont": 3333,
                 "node": 30000,
                 "ingress": "eggs"}
            ]
        }

        ingress_k8s_obj = {
            'kind': 'Ingress',
            'spec': {
                'rules': [{
                    'host': 'bar.test',
                    'http': {
                        'paths': [{
                            'backend': {
                                'serviceName': 'foo',
                                'servicePort': 1111}
                        }]
                    }
                }, {
                    'host': 'eggs.test',
                    'http': {
                        'paths': [{
                            'backend': {
                                'serviceName': 'foo',
                                'servicePort': 3333}
                        }]
                    }
                }]
            },
            'apiVersion': 'extensions/v1beta1',
            'metadata': {
                'name': 'foo'
            }
        }

        objects = list(deploy._process_ports(service))
        self.assertEqual(2, len(objects))
        self.assertEqual(ingress_k8s_obj, objects[1])


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
        expected_workflows = {
            "kenny": {
                "workflow": {
                    "name": "south-park/kenny",
                    "dependencies": ["south-park/cartman-mom", "stan", "kyle"],
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
                    "name": "south-park/cartman-mom",
                    "dependencies": ["cartman-dad"],
                    "job": {
                        "command": "oops"
                    }
                }
            },
            "eric-mom": {
                "workflow": {
                    "name": "south-park/eric-mom",
                    "dependencies": ["eric-dad", "south-park/kenny"],
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

        node_list = ["node1", "node2", "node3"]
        self.useFixture(fixtures.MockPatch(
            "fuel_ccp.kubernetes.get_object_names", return_value=node_list))

        self._roles = _yaml.AttrDict({
            "controller": [
                "mysql",
                "keystone"
            ],
            "compute": [
                "nova-compute",
                "libvirtd"
            ]
        })

    def test_make_topology_failed(self):
        self.assertRaises(RuntimeError,
                          deploy._make_topology, _yaml.AttrDict(),
                          _yaml.AttrDict(), _yaml.AttrDict())
        self.assertRaises(RuntimeError,
                          deploy._make_topology, _yaml.AttrDict(),
                          _yaml.AttrDict({"spam": "eggs"}), _yaml.AttrDict())
        self.assertRaises(RuntimeError,
                          deploy._make_topology,
                          _yaml.AttrDict({"spam": "eggs"}),
                          _yaml.AttrDict(), _yaml.AttrDict())
        self.assertRaises(RuntimeError,
                          deploy._make_topology,
                          self.nested_dict_to_attrdict(
                              {"node1": {"configs": "because-cows"}}),
                          _yaml.AttrDict({"spam": "eggs"}), None)

    def test_nodes_configs_has_new_var(self):
        nodes = {
            'node1': {
                'configs': {
                    'heat': {
                        'stack_params': {
                            'converge_resources': 'True',
                        }
                    }
                }
            }
        }
        configs = {
            'heat': {
                'stack_params': {
                    'debug': True
                }
            }
        }
        nodes = self.nested_dict_to_attrdict(nodes)
        configs = self.nested_dict_to_attrdict(configs)
        self.assertFalse(deploy_validation.validate_nodes_section(nodes,
                                                                  configs))

    def test_make_topology_without_replicas(self):
        nodes = _yaml.AttrDict({
            "node1": {
                "roles": ["controller"]
            },
            "node[2-3]": {
                "roles": ["compute"]
            }
        })

        expected_topology = {
            "_ccp_jobs": ["node1", "node2", "node3"],
            "mysql": ["node1"],
            "keystone": ["node1"],
            "nova-compute": ["node2", "node3"],
            "libvirtd": ["node2", "node3"]
        }

        topology = deploy._make_topology(nodes, self._roles, _yaml.AttrDict())
        self.assertDictEqual(expected_topology, topology)

    def test_make_topology_without_replicas_unused_role(self):
        nodes = _yaml.AttrDict({
            "node1": {
                "roles": ["controller"]
            },
        })

        expected_topology = {
            "_ccp_jobs": ["node1"],
            "mysql": ["node1"],
            "keystone": ["node1"]
        }

        topology = deploy._make_topology(nodes, self._roles, _yaml.AttrDict())
        self.assertDictEqual(expected_topology, topology)

    def test_make_topology_without_replicas_twice_used_role(self):
        nodes = _yaml.AttrDict({
            "node1": {
                "roles": ["controller", "compute"]
            },
            "node[2-3]": {
                "roles": ["compute"]
            }
        })

        expected_topology = {
            "_ccp_jobs": ["node1", "node2", "node3"],
            "mysql": ["node1"],
            "keystone": ["node1"],
            "nova-compute": ["node1", "node2", "node3"],
            "libvirtd": ["node1", "node2", "node3"]
        }
        topology = deploy._make_topology(nodes, self._roles, _yaml.AttrDict())
        self.assertDictEqual(expected_topology, topology)

    def test_make_topology_without_replicas_twice_used_node(self):
        nodes = _yaml.AttrDict({
            "node1": {
                "roles": ["controller"]
            },
            "node[1-3]": {
                "roles": ["compute"]
            }
        })

        expected_topology = {
            "_ccp_jobs": ["node1", "node2", "node3"],
            "mysql": ["node1"],
            "keystone": ["node1"],
            "nova-compute": ["node1", "node2", "node3"],
            "libvirtd": ["node1", "node2", "node3"]
        }

        topology = deploy._make_topology(nodes, self._roles, _yaml.AttrDict())
        self.assertDictEqual(expected_topology, topology)

    def test_make_topology_replicas_bigger_than_nodes(self):
        replicas = _yaml.AttrDict({
            "keystone": 2
        })

        nodes = _yaml.AttrDict({
            "node1": {
                "roles": ["controller"]
            }
        })

        self.assertRaises(RuntimeError,
                          deploy._make_topology, nodes, self._roles, replicas)

    def test_make_topology_unspecified_service_replicas(self):
        replicas = _yaml.AttrDict({
            "foobar": 42
        })

        nodes = _yaml.AttrDict()

        self.assertRaises(RuntimeError,
                          deploy._make_topology, nodes, self._roles, replicas)
