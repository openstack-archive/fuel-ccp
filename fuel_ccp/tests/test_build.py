import collections
import copy
import os

import fixtures
import mock
import testscenarios

from fuel_ccp import build
from fuel_ccp.tests import base


BASE_DOCKERFILE = u"""FROM debian:jessie
MAINTAINER Foo Bar <foo@bar.org>

RUN apt-get install \
      curl \
    && apt-get clean"""

COMPONENT_DOCKERFILE = u"""FROM {}ccp/ms-debian-base
MAINTAINER Foo Bar <foo@bar.org>

RUN apt-get -y install \
      mysql-server \
    && apt-get clean"""


class TestBuild(base.TestCase):

    @staticmethod
    def __create_dockerfile_objects():
        return collections.OrderedDict([
            ('ms-debian-base', {
                'name': 'ms-debian-base',
                'path': '/home/test/microservices/ms-base/docker/'
                        'Dockerfile',
                'is_jinja2': False,
                'parent': None,
                'children': [],
                'build_result': 'Success',
                'push_result': 'Success'
            },),
            ('ms-mysql', {
                'name': 'ms-mysql',
                'path': '/home/test/microservices/ms-mysql/docker/'
                        'Dockerfile',
                'is_jinja2': False,
                'parent': None,
                'children': [],
                'build_result': 'Success',
                'push_result': 'Success'
            },)
        ])

    @mock.patch("docker.Client")
    @mock.patch("fuel_ccp.build.build_dockerfile")
    @mock.patch("fuel_ccp.build.submit_dockerfile_processing")
    @mock.patch("fuel_ccp.build.create_rendered_dockerfile")
    def test_process_dockerfile_middle(
            self, render_mock, submit_dockerfile_processing_mock,
            build_dockerfile_mock, dc_mock):
        dockerfiles = {
            'root': {
                'name': 'root',
                'full_name': 'ms/root',
                'parent': None,
                'children': ['middle'],
                'match': False,
                'path': '/tmp'
            },
            'middle': {
                'name': 'middle',
                'full_name': 'ms/middle',
                'parent': 'root',
                'children': ['leaf'],
                'match': True,
                'path': '/tmp',
                'build_result': 'Success'
            },
            'leaf': {
                'name': 'leaf',
                'full_name': 'ms/leaf',
                'parent': 'middle',
                'children': [],
                'match': False,
                'path': '/tmp'
            }
        }

        for dockerfile in dockerfiles.values():
            if dockerfile['parent']:
                dockerfile['parent'] = dockerfiles[dockerfile['parent']]
            for i in range(len(dockerfile['children'])):
                dockerfile['children'][i] = (
                    dockerfiles[dockerfile['children'][i]]
                )

        build.process_dockerfile(
            dockerfiles["middle"], mock.ANY, mock.ANY, mock.ANY, mock.ANY,
            ["root", "middle", "leaf"])

        submit_dockerfile_processing_mock.assert_called_once_with(
            dockerfiles["leaf"], mock.ANY, mock.ANY, mock.ANY,
            mock.ANY, ["root", "middle", "leaf"])

    @mock.patch("docker.Client")
    @mock.patch("fuel_ccp.build.build_dockerfile")
    @mock.patch("fuel_ccp.build.submit_dockerfile_processing")
    @mock.patch("fuel_ccp.build.create_rendered_dockerfile")
    def test_process_dockerfile_parent_build_failed(
            self, render_mock, submit_dockerfile_processing_mock,
            build_dockerfile_mock, dc_mock):
        dockerfiles = {
            'parent': {
                'name': 'parent',
                'full_name': 'ms/parent',
                'parent': None,
                'children': ['child'],
                'match': True,
                'path': '/tmp',
                'build_result': 'Failure'
            },
            'child': {
                'name': 'child',
                'full_name': 'ms/child',
                'parent': 'parent',
                'children': [],
                'match': True,
                'path': '/tmp'
            }
        }

        for dockerfile in dockerfiles.values():
            if dockerfile['parent']:
                dockerfile['parent'] = dockerfiles[dockerfile['parent']]
            for i in range(len(dockerfile['children'])):
                dockerfile['children'][i] = (
                    dockerfiles[dockerfile['children'][i]]
                )

        build.process_dockerfile(
            dockerfiles["parent"], mock.ANY, mock.ANY, mock.ANY, mock.ANY,
            [])
        submit_dockerfile_processing_mock.assert_not_called()

    @mock.patch("docker.Client")
    @mock.patch("fuel_ccp.build.build_dockerfile")
    @mock.patch("fuel_ccp.build.submit_dockerfile_processing")
    @mock.patch("fuel_ccp.build.create_rendered_dockerfile")
    def test_process_dockerfile_middle_keep_consistency_off(
            self, render_mock, submit_dockerfile_processing_mock,
            build_dockerfile_mock, dc_mock):
        dockerfiles = {
            'root': {
                'name': 'root',
                'full_name': 'ms/root',
                'parent': None,
                'children': ['middle'],
                'match': False,
                'path': '/tmp'
            },
            'middle': {
                'name': 'middle',
                'full_name': 'ms/middle',
                'parent': 'root',
                'children': ['leaf'],
                'match': True,
                'path': '/tmp'
            },
            'leaf': {
                'name': 'leaf',
                'full_name': 'ms/leaf',
                'parent': 'middle',
                'children': [],
                'match': False,
                'path': '/tmp'
            }
        }

        self.conf["builder"]["keep_image_tree_consistency"] = False

        for dockerfile in dockerfiles.values():
            if dockerfile['parent']:
                dockerfile['parent'] = dockerfiles[dockerfile['parent']]
            for i in range(len(dockerfile['children'])):
                dockerfile['children'][i] = (
                    dockerfiles[dockerfile['children'][i]]
                )

        build.process_dockerfile(dockerfiles["middle"], mock.ANY, mock.ANY,
                                 mock.ANY, mock.ANY, [])

        self.assertTrue(not submit_dockerfile_processing_mock.called)

    def test_match_not_ready_base_dockerfiles(self):
        dockerfile = {
            'name': 'galera',
            'match': True,
            'parent': {
                'name': 'base-tools',
                'match': False,
                'parent': {
                    'name': 'base',
                    'match': False,
                    'parent': None
                }
            }
        }
        build.match_not_ready_base_dockerfiles(dockerfile, [])
        self.assertEqual(dockerfile['parent']['match'], True)
        self.assertEqual(dockerfile['parent']['parent']['match'], True)

    def test_get_summary_succeeded(self):
        dockerfiles = self.__create_dockerfile_objects()
        self.assertTrue(build._get_summary(dockerfiles))

    def test_get_summary_not_pushed(self):
        dockerfiles = self.__create_dockerfile_objects()
        dockerfiles['ms-debian-base']['push_result'] = 'Exists'
        dockerfiles['ms-mysql']['push_result'] = 'Exists'
        self.assertTrue(build._get_summary(dockerfiles))

    def test_get_summary_build_failed(self):
        dockerfiles = self.__create_dockerfile_objects()
        dockerfiles['ms-debian-base']['build_result'] = 'Failure'
        self.assertFalse(build._get_summary(dockerfiles))

    def test_get_summary_push_failed(self):
        dockerfiles = self.__create_dockerfile_objects()
        dockerfiles['ms-debian-base']['push_result'] = 'Failure'
        self.assertFalse(build._get_summary(dockerfiles))


class TestRenderDockerfile(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ('empty', {
            'config': {'render': {}},
            'source': '',
            'result': ('', set(), [], None),
        }),
        ('one_source', {
            'config': {'render': {}, 'sources': {'one': {}}},
            'source': '{{ copy_sources("one", "/tmp") }}',
            'result': ('COPY one /tmp', {'one'}, [], None),
        }),
        ('wrong_source', {
            'config': {'render': {}, 'sources': {'one': {}}},
            'source': '{{ copy_sources("wrong", "/tmp") }}',
            'exception': Exception('No such source: wrong'),
        }),
        ('one_from', {
            'config': {'render': {}},
            'source': 'FROM {{ image_spec("one") }}',
            'result': ('FROM ccp/one:latest', set(), [], 'one'),
        }),
    ]

    config = None
    source = None
    result = None
    exception = None

    def test_render_dockerfile(self):
        tmp_dir = self.useFixture(fixtures.TempDir()).path
        fname = os.path.join(tmp_dir, 'Dockerfile.j2')
        with open(fname, 'w') as f:
            f.write(self.source)
        if not self.exception:
            res = build.render_dockerfile(fname, 'name', self.config)
            self.assertEqual(res, self.result)
        else:
            exc = self.assertRaises(ValueError, build.render_dockerfile,
                                    fname, 'name', self.config)
            self.assertEqual(exc.args[0], self.exception.args[0])


class TestConnectChildren(testscenarios.WithScenarios, base.TestCase):
    scenarios = [
        ("normal", {
            "dockerfiles": {
                "base": {
                    "name": "base",
                    "parent": None,
                    "children": [],
                },
                "dock-a": {
                    "name": "dock-a",
                    "parent": "base",
                    "children": [],
                },
                "dock-b": {
                    "name": "dock-b",
                    "parent": "dock-a",
                    "children": [],
                },
            },
            "children": {
                "base": ["dock-a"],
                "dock-a": ["dock-b"],
                "dock-b": [],
            },

        }),
        ("orphan", {
            "dockerfiles": {
                "dock-a": {
                    "name": "dock-a",
                    "parent": "dock-c",
                    "children": [],
                },
                "dock-b": {
                    "name": "dock-b",
                    "parent": "dock-a",
                    "children": [],
                },
            },
            "exception": (
                RuntimeError,
                "Could not find parents for the following images: "
                "dock-a[dock-c]",
            ),
        }),
    ]

    dockerfiles = None
    orphan = None
    exception = None

    def test_connect_children(self):
        dockerfiles = copy.deepcopy(self.dockerfiles)
        if self.exception is None:
            build.connect_children(dockerfiles)
            result_children = {}
            for dockerfile in dockerfiles.values():
                result_children[dockerfile["name"]] = \
                    [d["name"] for d in dockerfile["children"]]
            self.assertEqual(self.children, result_children)
        else:
            exc = self.assertRaises(
                self.exception[0], build.connect_children, dockerfiles)
            self.assertEqual(exc.args[0], self.exception[1])
