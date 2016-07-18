import collections
import io

import mock
from oslo_config import fixture as conf_fixture

from microservices import build
from microservices import exceptions
from microservices.tests import base


BASE_DOCKERFILE = u"""FROM debian:jessie
MAINTAINER Foo Bar <foo@bar.org>

RUN apt-get install \
      curl \
    && apt-get clean"""

COMPONENT_DOCKERFILE = u"""FROM {}mcp/ms-debian-base
MAINTAINER Foo Bar <foo@bar.org>

RUN apt-get -y install \
      mysql-server \
    && apt-get clean"""


class TestBuild(base.TestCase):

    def setUp(self):
        super(TestBuild, self).setUp()
        self.cfg = conf_fixture.Config()
        self.cfg.setUp()

    def tearDown(self):
        super(TestBuild, self).tearDown()
        self.cfg.cleanUp()

    @staticmethod
    def __create_dockerfile_objects():
        return collections.OrderedDict([
            ('ms-debian-base', {
                'name': 'ms-debian-base',
                'path': '/home/test/microservices/ms-base/docker/'
                        'Dockerfile',
                'is_jinja2': False,
                'parent': None,
                'children': []
            },),
            ('ms-mysql', {
                'name': 'ms-mysql',
                'path': '/home/test/microservices/ms-mysql/docker/'
                        'Dockerfile',
                'is_jinja2': False,
                'parent': None,
                'children': []
            },)
        ])

    def test_find_dependencies_no_registry(self):
        m_open = mock.mock_open()
        m_open.side_effect = [
            io.StringIO(BASE_DOCKERFILE),
            io.StringIO(COMPONENT_DOCKERFILE.format(''))
        ]
        dockerfiles = self.__create_dockerfile_objects()
        with mock.patch('microservices.build.open', m_open, create=True):
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
        with mock.patch('microservices.build.open', m_open, create=True):
            build.find_dependencies(dockerfiles)

        self.assertListEqual([dockerfiles['ms-mysql']],
                             dockerfiles['ms-debian-base']['children'])
        self.assertDictEqual(dockerfiles['ms-debian-base'],
                             dockerfiles['ms-mysql']['parent'])

    @mock.patch("docker.Client")
    @mock.patch("microservices.build.build_dockerfile")
    @mock.patch("microservices.build.submit_dockerfile_processing")
    def test_process_dockerfile_middle(self, submit_dockerfile_processing_mock,
                                       build_dockerfile_mock, dc_mock):
        dockerfiles = {
            'root': {
                'name': 'root',
                'full_name': 'ms/root',
                'parent': None,
                'children': ['middle'],
                'match': False
            },
            'middle': {
                'name': 'middle',
                'full_name': 'ms/middle',
                'parent': 'root',
                'children': ['leaf'],
                'match': True
            },
            'leaf': {
                'name': 'leaf',
                'full_name': 'ms/leaf',
                'parent': 'middle',
                'children': [],
                'match': False
            }
        }

        for dockerfile in dockerfiles.values():
            if dockerfile['parent']:
                dockerfile['parent'] = dockerfiles[dockerfile['parent']]
            for i in range(len(dockerfile['children'])):
                dockerfile['children'][i] = (
                    dockerfiles[dockerfile['children'][i]]
                )

        build.process_dockerfile(dockerfiles["middle"], mock.ANY, mock.ANY,
                                 ["root", "middle", "leaf"])

        submit_dockerfile_processing_mock.assert_called_once_with(
            dockerfiles["leaf"], mock.ANY, mock.ANY, mock.ANY)

    @mock.patch("docker.Client")
    @mock.patch("microservices.build.build_dockerfile")
    @mock.patch("microservices.build.submit_dockerfile_processing")
    def test_process_dockerfile_middle_keep_consistency_off(
            self, submit_dockerfile_processing_mock,
            build_dockerfile_mock, dc_mock):
        dockerfiles = {
            'root': {
                'name': 'root',
                'full_name': 'ms/root',
                'parent': None,
                'children': ['middle'],
                'match': False
            },
            'middle': {
                'name': 'middle',
                'full_name': 'ms/middle',
                'parent': 'root',
                'children': ['leaf'],
                'match': True
            },
            'leaf': {
                'name': 'leaf',
                'full_name': 'ms/leaf',
                'parent': 'middle',
                'children': [],
                'match': False
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

        build.process_dockerfile(dockerfiles["middle"], mock.ANY, mock.ANY, [])

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

    @mock.patch("docker.Client")
    def test_build_failed(self, dc_mock):
        dc_mock.build.return_value = [
            '{"errorDetail": {"message": "Some error"}}']
        dockerfile = {
            'name': 'test',
            'full_name': 'namespace/test',
            'parent': None,
            'children': [],
            'match': True,
            'path': '/tmp'
        }
        with self.assertRaisesRegexp(
                exceptions.ImageBuildException,
                'The "test" image build failed: "Some error"'):
            build.build_dockerfile(dc_mock, dockerfile)

    @mock.patch("docker.Client")
    def test_push_failed(self, dc_mock):
        self.cfg.config(group="registry", address='1.2.3.4:5000')
        dc_mock.push.return_value = [
            '{"errorDetail": {"message": "Some error"}}']
        dockerfile = {
            'name': 'test',
            'full_name': 'namespace/test',
            'parent': None,
            'children': [],
            'match': True,
            'path': '/tmp'
        }
        with self.assertRaisesRegexp(
                exceptions.ImagePushException,
                'The "test" image push to the registry '
                '"1.2.3.4:5000" failed: "Some error"'):
            build.push_dockerfile(dc_mock, dockerfile)
