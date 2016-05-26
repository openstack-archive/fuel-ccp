import mock
import os

from oslo_config import cfg

from microservices import deploy
from microservices.tests import base

CONF = cfg.CONF


class TestDeploy(base.TestCase):
    def test_render_k8s_yaml(self):
        deployment_dict = {
            'kind': 'Deployment',
            'spec': {
                'template': {
                    'spec': {
                        'containers': [{
                            'image': 'mcp/test:latest',
                            'name': 'test',
                            'ports': [{'containerPort': 12345}]}]},
                    'metadata': {
                        'labels': {
                            'app': 'test'}}},
                'replicas': 2},
            'apiVersion': 'extensions/v1beta1',
            'metadata': {
                'name': 'test-deployment'}}

        service_dict = {
            'kind': 'Service',
            'spec': {'ports': [{
                'targetPort': 12345,
                'name': 'keystona-api',
                'port': 12345}],
                'selector': {
                    'app': 'test'}},
            'apiVersion': 'v1',
            'metadata': {
                'labels': {
                    'app': 'test'},
                'name': 'test-service'}}

        objects = list(deploy.render_k8s_yaml(
            os.path.join(os.path.dirname(__file__),
                         'test_repository/service/test.yaml.j2')))
        self.assertDictEqual(deployment_dict, objects[0])
        self.assertDictEqual(service_dict, objects[1])

    @mock.patch('microservices.deploy.create_k8s_objects')
    @mock.patch('microservices.deploy.render_k8s_yaml')
    def test_deploy_component(self, render_yaml, create_objects):
        CONF.set_override('path', os.path.dirname(__file__),
                          group='repositories')
        render_yaml.return_value = [{'kind': 'Deployment'}]

        deploy.deploy_component('test_repository')
        create_objects.assert_called_once_with([{'kind': 'Deployment'}])
