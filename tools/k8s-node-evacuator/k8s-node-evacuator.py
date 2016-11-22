import json
import logging
import os
import requests
import time

from six.moves import _thread as thread

from keystoneauth1 import loading
from keystoneauth1 import session
from novaclient import client


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__file__)


def nova_live_migrate(node):
    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(
        auth_url=os.environ["OS_AUTH_URL"],
        username=os.environ["OS_USERNAME"],
        password=os.environ["OS_PASSWORD"],
        user_domain_name=os.environ["OS_USER_DOMAIN_NAME"],
        project_domain_name=os.environ["OS_PROJECT_DOMAIN_NAME"],
        project_name=os.environ["OS_PROJECT_NAME"])
    OS_COMPUTE_API_VERSION = "2"
    sess = session.Session(auth=auth)
    nova = client.Client(OS_COMPUTE_API_VERSION, session=sess)

    LOG.info("Disabling nova-compute service on: %s", node)
    nova.services.disable(node, "nova-compute")

    for server in nova.servers.list(search_opts={'host': node}):
        LOG.info("Live-migrating instance: %s from node: %s", server.name,
                 node)
        server.live_migrate(block_migration=True)
        thread.start_new_thread(live_migration_watcher_thread, (nova, node))


def k8s_watcher():
    API_URL = os.environ["K8S_API_SERVER_URL"] + "/api/v1/events"
    LOG.debug("Listening for events from: %s", API_URL)
    response = requests.get(API_URL, params={'watch': 'true'}, stream=True)
    for line in response.iter_lines():
        event = json.loads(line)
        reason = event["object"]["reason"]
        if (reason == "NodeNotSchedulable"):
            node = event["object"]["involvedObject"]["name"]
            LOG.info("Detected event: %s for node: %s", reason, node)
            nova_live_migrate(node)


def live_migration_watcher_thread(nova, node):
    while len(nova.servers.list(search_opts={'host': node})):
        LOG.info("Waiting for instances from %s to live-migrate...", node)
        time.sleep(5)
    LOG.info("All instances from node %s has been live-migrated away.", node)


def main():
    k8s_watcher()


if __name__ == '__main__':
    main()
