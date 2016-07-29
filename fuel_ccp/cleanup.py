import time

from keystoneauth1 import exceptions as keystoneauth_exceptions
from keystoneauth1.identity import v3
from keystoneauth1 import session as keystone_session
from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client
from oslo_config import cfg
from oslo_log import log as logging

from fuel_ccp.common import utils
from fuel_ccp import kubernetes


CONF = cfg.CONF
CONF.import_group('kubernetes', 'fuel_ccp.config.kubernetes')


LOG = logging.getLogger(__name__)


def _wait_until_empty(command, *args, **kwargs):
    attempts = 60
    while attempts > 0:
        if not command(*args, **kwargs):
            return
        time.sleep(3)


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
    _wait_until_empty(nova.servers.list, search_opts={"all_tenants": True})
    server_list = nova.servers.list(search_opts={"all_tenants": True})
    if server_list:
        LOG.warning("Some instances were not removed, trying to force delete")
        for server in server_list:
            LOG.info('Force deleting instance %s(%s)',
                     (server.name, server.id))
            nova.servers.force_delete(server.id)
    _wait_until_empty(nova.servers.list, search_opts={"all_tenants": True})
    server_list = nova.servers.list(search_opts={"all_tenants": True})
    if server_list:
        raise Exception(
            'Some instances were not removed after force delete: %s'
            % ', '.join(['%s(%s)' % (server.name, server.id)
                         for server in server_list]))


def _cleanup_network_resources(session):
    neutron = neutron_client.Client(session=session)

    LOG.info('Cleaning up subnets')
    for subnet in neutron.list_subnets()['subnets']:
        LOG.info('Removing subnet %s (%s)', subnet['name'], subnet['id'])
        neutron.delete_subnet(subnet['id'])

    LOG.info('Cleaning up networks')
    for network in neutron.list_networks()['networks']:
        LOG.info('Removing network %s (%s)', network['name'], network['id'])
        neutron.delete_network(network['id'])


def _cleanup_openstack_environment(configs):
    if 'openstack_project_name' not in configs:
        # Ensure that keystone configs are provided. Assume that it is not an
        # OpenStack deployment otherwise
        LOG.info('There are no Keystone configs provided. '
                 'OpenStack environment cleanup will be skipped')
        return

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
            'was not deployed', configs['auth_url'])
        raise
    _cleanup_servers(session)
    _cleanup_network_resources(session)
    LOG.info('OpenStack cleanup has been finished successfully.')


def _cleanup_kubernetes_objects():
    k8s_api = kubernetes.get_v1_api(kubernetes.get_client())
    k8s_api.delete_namespaced_namespace({}, CONF.kubernetes.namespace)
    LOG.info('Kubernetes objects cleanup has been finished successfully.')


def cleanup(auth_url=None, skip_os_cleanup=False):
    configs = utils.get_global_parameters('configs')
    configs['auth_url'] = auth_url or 'http://keystone:%s/v3' % configs[
        'keystone_public_port']
    if not skip_os_cleanup:
        _cleanup_openstack_environment(configs)
    _cleanup_kubernetes_objects()
