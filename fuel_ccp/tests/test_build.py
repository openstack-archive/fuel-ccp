import collections
import io

import mock
from oslo_config import fixture as conf_fixture

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

    def setUp(self):
        super(TestBuild, self).setUp()
        self.cfg = self.useFixture(conf_fixture.Config())

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

    def test_find_dependencies_no_registry(self):
        m_open = mock.mock_open()
        m_open.side_effect = [
            io.StringIO(BASE_DOCKERFILE),
            io.StringIO(COMPONENT_DOCKERFILE.format(''))
        ]
        dockerfiles = self.__create_dockerfile_objects()
        with mock.patch('fuel_ccp.build.open', m_open, create=True):
            build.find_dependencies(dockerfiles)

        self.assertListEqual([dockerfiles['ms-mysql']],
                             dockerfiles['ms-debian-base']['children'])
        self.assertDictEqual(dockerfiles['ms-debian-base'],
                             dockerfiles['ms-mysql']['parent'])

    def test_find_dependencies_registry(self):
        m_open = mock.mock_open()
        m_open.side_effect = [
            io.StringIO(BASE_DOCKERFILE),
            io.StringIO(COMPONENT_DOCKERFILE.format('example.com:8909/'))
        ]
        dockerfiles = self.__create_dockerfile_objects()
        with mock.patch('fuel_ccp.build.open', m_open, create=True):
            build.find_dependencies(dockerfiles)

        self.assertListEqual([dockerfiles['ms-mysql']],
                             dockerfiles['ms-debian-base']['children'])
        self.assertDictEqual(dockerfiles['ms-debian-base'],
                             dockerfiles['ms-mysql']['parent'])

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

        self.cfg.config(group="builder", keep_image_tree_consistency=False)

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
            'name': 'mariadb',
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
