import collections
import io
import mock

from microservices import build
from microservices.tests import base


BASE_DOCKERFILE = u"""FROM debian:jessie
MAINTAINER Foo Bar <foo@bar.org>

RUN apt-get install \
      curl \
    && apt-get clean"""
COMPONENT_DOCKERFILE = u"""FROM mcp/ms-debian-base
MAINTAINER Foo Bar <foo@bar.org>

RUN apt-get -y install \
      mysql-server \
    && apt-get clean"""


class TestBuild(base.TestCase):

    def test_find_dependencies(self):
        m_open = mock.mock_open()
        m_open.side_effect = [
            io.StringIO(BASE_DOCKERFILE),
            io.StringIO(COMPONENT_DOCKERFILE)
        ]
        with mock.patch('microservices.build.open', m_open, create=True):
            dockerfiles = collections.OrderedDict([
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
            build.find_dependencies(dockerfiles)

        self.assertListEqual([dockerfiles['ms-mysql']],
                             dockerfiles['ms-debian-base']['children'])
        self.assertDictEqual(dockerfiles['ms-debian-base'],
                             dockerfiles['ms-mysql']['parent'])
