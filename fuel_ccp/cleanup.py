import logging
import time

from glanceclient import client as glance_client
from keystoneauth1 import exceptions as keystoneauth_exceptions
from keystoneauth1.identity import v3
from keystoneauth1 import session as keystone_session
from neutronclient.neutron import client as neutron_client
from novaclient import client as nova_client
import pykube
from swiftclient import client as swift_client

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
                 project_domain_name='default', user_domain_name='default',
                 verify=True):
    auth = v3.Password(auth_url=auth_url,
                       username=username,
                       password=password,
                       project_name=project_name,
                       project_domain_name=project_domain_name,
                       user_domain_name=user_domain_name)

    return keystone_session.Session(auth=auth, verify=verify)


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
    neutron = neutron_client.Client("2.0", session=session)

    LOG.debug("Cleaning up floatingips")
    for fip in neutron.list_floatingips()["floatingips"]:
        LOG.debug("Removing floatingip %s", fip["id"])
        neutron.delete_floatingip(fip["id"])

    LOG.debug("Cleaning up routers")
    for router in neutron.list_routers()["routers"]:
        LOG.debug("Removing router %s", router["id"])
        neutron.remove_gateway_router(router["id"])
        for port in neutron.list_ports(device_id=router["id"])["ports"]:
            neutron.remove_interface_router(router["id"],
                                            {"port_id": port["id"]})
        neutron.delete_router(router["id"])

    LOG.debug("Cleaning up ports")
    for port in neutron.list_ports()["ports"]:
        LOG.debug("Removing port %s", port["id"])
        neutron.delete_port(port["id"])

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


def _cleanup_images(session):
    LOG.debug("Cleaning up glance images")
    glance = glance_client.Client("2", session=session)
    for image in glance.images.list():
        LOG.debug("Removing glance image %s", image.id)
        glance.images.delete(image.id)


def _cleanup_object_storage(session):
    LOG.info("Cleaning up object storage")
    swift = swift_client.Connection(session=session)
    for cont in swift.get_account()[1]:
        LOG.debug("Delete bucket %s", cont["name"])
        for obj in swift.get_container(cont["name"])[1]:
            swift.delete_object(cont["name"], obj["name"])
        swift.delete_container(cont["name"])


def _cleanup_openstack_environment(configs, auth_url=None, verify=True):
    if 'project_name' not in configs.get('openstack', {}):
        # Ensure that keystone configs are provided. Assume that it is not an
        # OpenStack deployment otherwise
        raise RuntimeError('There are no Keystone configs provided. '
                           'Run with --skip-os-cleanup flag if OpenStack '
                           'is not deployed')

    configs['auth_url'] = auth_url or '%s/v3' % utils.address(
        {}, 'keystone', configs['keystone']['public_port'], True, True)

    session = _get_session(
        configs['auth_url'], configs['openstack']['user_name'],
        configs['openstack']['user_password'],
        configs['openstack']['project_name'],
        verify=verify)

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
        _cleanup_images(session)
    except keystoneauth_exceptions.EndpointNotFound:
        LOG.info('Glance is not present, skipping images cleanup')
        pass

    try:
        _cleanup_network_resources(session)
    except keystoneauth_exceptions.EndpointNotFound:
        LOG.info('Neutron is not present, skipping network resources '
                 'cleanup')
        pass

    try:
        _cleanup_object_storage(session)
    except keystoneauth_exceptions.EndpointNotFound:
        LOG.info("Object storage is not present, skipping buckets cleanup")
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
        return

    _wait_for_namespace_delete(ns)
    LOG.info('Kubernetes objects cleanup has been finished successfully.')


def cleanup(auth_url=None, skip_os_cleanup=False, verify=True):
    if not skip_os_cleanup:
        conf = utils.get_rendering_config()
        _cleanup_openstack_environment(conf, auth_url, verify)
    _cleanup_kubernetes_objects()
