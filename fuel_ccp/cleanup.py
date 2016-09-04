import time

from keystoneauth1 import exceptions as keystoneauth_exceptions
from keystoneauth1.identity import v3
from keystoneauth1 import session as keystone_session
from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client
from oslo_log import log as logging
import pykube

from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp import kubernetes

CONF = config.CONF

LOG = logging.getLogger(__name__)


def _wait_until_empty(attempts, resource_path,
                      command, *args, **kwargs):
    while attempts > 0:
        resources_list = command(*args, **kwargs)
        if resource_path:
            resources_list = resources_list[resource_path]
        if not resources_list:
            return
        time.sleep(3)
        attempts -= 1
    return command(*args, **kwargs)


def _get_session(auth_url, username, password, project_name,
                 project_domain_name='default', user_domain_name='default'):
    auth = v3.Password(auth_url=auth_url,
                       username=username,
                       password=password,
                       project_name=project_name,
                       project_domain_name=project_domain_name,
                       user_domain_name=user_domain_name)

    return keystone_session.Session(auth=auth)


def _cleanup_servers(session):
    LOG.info('Cleaning up instances')
    nova = nova_client.Client("2", session=session)
    server_list = nova.servers.list(search_opts={"all_tenants": True})
    if not server_list:
        return
    for server in server_list:
        LOG.info('Removing instance %s (%s)', server.name, server.id)
        nova.servers.delete(server.id)
    server_list = _wait_until_empty(
        60, None, nova.servers.list, search_opts={"all_tenants": True})
    if server_list:
        LOG.warning("Some instances were not removed, trying to force delete")
        for server in server_list:
            LOG.info('Force deleting instance %s (%s)', server.name, server.id)
            nova.servers.force_delete(server.id)
    server_list = _wait_until_empty(
        60, None, nova.servers.list, search_opts={"all_tenants": True})
    if server_list:
        raise RuntimeError(
            'Some instances were not removed after force delete: %s'
            % ', '.join(['%s (%s)' % (server.name, server.id)
                         for server in server_list]))


def _cleanup_network_resources(session):
    neutron = neutron_client.Client(session=session)
    LOG.info('Cleaning up subnets')
    for subnet in neutron.list_subnets()['subnets']:
        LOG.info('Removing subnet %s (%s)', subnet['name'], subnet['id'])
        neutron.delete_subnet(subnet['id'])
    subnet_list = _wait_until_empty(10, 'subnets', neutron.list_subnets)
    if subnet_list:
        raise RuntimeError(
            'Some subnets were not removed: %s'
            % ', '.join(['%s (%s)' % (subnet['name'], subnet['id'])
                         for subnet in subnet_list['subnets']]))

    LOG.info('Cleaning up networks')
    for network in neutron.list_networks()['networks']:
        LOG.info('Removing network %s (%s)', network['name'], network['id'])
        neutron.delete_network(network['id'])
    network_list = _wait_until_empty(10, 'networks', neutron.list_networks)
    if network_list:
        raise RuntimeError(
            'Some networks were not removed: %s'
            % ', '.join(['%s (%s)' % (network['name'], network['id'])
                         for network in network_list['networks']]))


def _cleanup_openstack_environment(configs, auth_url=None):
    if 'openstack_project_name' not in configs:
        # Ensure that keystone configs are provided. Assume that it is not an
        # OpenStack deployment otherwise
        raise RuntimeError('There are no Keystone configs provided. '
                           'Run with --skip-os-cleanup flag if OpenStack '
                           'is not deployed')

    configs['auth_url'] = auth_url or 'http://keystone:%s/v3' % configs[
        'keystone_public_port']

    session = _get_session(
        configs['auth_url'], configs['openstack_user_name'],
        configs['openstack_user_password'], configs['openstack_project_name'])

    try:
        session.get_project_id()
    except (keystoneauth_exceptions.ConnectFailure,
            keystoneauth_exceptions.EndpointNotFound):
        LOG.error(
            'Keystone is not deployed or %s is not accessible. '
            'Cleanup is aborted. '
            'Run with --skip-os-cleanup flag if OpenStack '
            'is not deployed', configs['auth_url'])
        raise
    try:
        _cleanup_servers(session)
    except keystoneauth_exceptions.EndpointNotFound:
        LOG.info('Nova is not present, skipping instances cleanup')
        pass
    try:
        _cleanup_network_resources(session)
    except keystoneauth_exceptions.EndpointNotFound:
        LOG.info('Neutron is not present, skipping network resources '
                 'cleanup')
        pass
    LOG.info('OpenStack cleanup has been finished successfully.')


def _wait_for_namespace_delete(namespace):
    attempts = 60
    while attempts > 0:
        if not namespace.exists():
            return
        time.sleep(3)
        attempts -= 1
    raise RuntimeError(
        "Wasn't able to delete namespace %s" % CONF.kubernetes.namespace)


def _cleanup_kubernetes_objects():
    k8s_api = kubernetes.get_client()
    ns = pykube.Namespace.objects(k8s_api).get_or_none(
        name=CONF.kubernetes.namespace)
    if ns:
        LOG.info('Starting Kubernetes objects cleanup')
        ns.delete()
    else:
        LOG.info('Kubernetes namespace not found')

    _wait_for_namespace_delete(ns)
    LOG.info('Kubernetes objects cleanup has been finished successfully.')


def cleanup(auth_url=None, skip_os_cleanup=False):
    configs = utils.get_global_parameters('configs')['configs']
    if not skip_os_cleanup:
        _cleanup_openstack_environment(configs, auth_url)
    _cleanup_kubernetes_objects()
