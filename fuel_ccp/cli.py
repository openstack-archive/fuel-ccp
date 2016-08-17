import signal
import sys

from oslo_config import cfg
from oslo_log import log as logging

from fuel_ccp import build
from fuel_ccp import cleanup
from fuel_ccp import dependencies
from fuel_ccp import deploy
from fuel_ccp import fetch
from fuel_ccp import status


CONF = cfg.CONF
CONF.import_group('registry', 'fuel_ccp.config.registry')
CONF.import_group('repositories', 'fuel_ccp.config.repositories')
CONF.import_opt('action', 'fuel_ccp.config.cli')


def do_build():
    if CONF.builder.push and not CONF.registry.address:
        raise RuntimeError('No registry specified, cannot push')
    if CONF.repositories.clone:
        do_fetch()
    build.build_components(components=CONF.action.components)


def do_deploy():
    if CONF.repositories.clone:
        do_fetch()
    deploy.deploy_components(components=CONF.action.components)


def do_fetch():
    fetch.fetch_repositories(CONF.repositories.names)


def do_cleanup():
    cleanup.cleanup(auth_url=CONF.action.auth_url,
                    skip_os_cleanup=CONF.action.skip_os_cleanup)


def do_show_dep():
    if CONF.repositories.clone:
        do_fetch()
    dependencies.show_dep(CONF.action.components)


def do_status():
    status.show_status()


def signal_handler(signo, frame):
    sys.exit(-signo)


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logging.register_options(CONF)
    CONF(sys.argv[1:])
    logging.setup(CONF, 'fuel-ccp')

    func = globals()['do_%s' % CONF.action.name.replace('-', '_')]
    func()


if __name__ == '__main__':
    main()
