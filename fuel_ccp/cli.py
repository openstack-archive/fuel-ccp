import signal
import sys

from oslo_config import cfg
from oslo_log import log as logging

from fuel_ccp import build
from fuel_ccp import deploy
from fuel_ccp import fetch
from fuel_ccp import validate


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


def do_validate():
    if CONF.repositories.clone:
        do_fetch()
    validate.validate(type=CONF.action.type)


def do_fetch():
    fetch.fetch_repositories(CONF.repositories.names)


def signal_handler(signo, frame):
    sys.exit(-signo)


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logging.register_options(CONF)
    CONF(sys.argv[1:])
    logging.setup(CONF, 'fuel-ccp')

    func = globals()['do_%s' % CONF.action.name]
    func()


if __name__ == '__main__':
    main()
