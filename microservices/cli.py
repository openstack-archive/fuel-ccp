import sys

from oslo_config import cfg
from oslo_log import log as logging

from microservices import build
from microservices import deploy
from microservices import fetch


CONF = cfg.CONF
CONF.import_group('registry', 'microservices.config.registry')
CONF.import_group('repositories', 'microservices.config.repositories')
CONF.import_opt('action', 'microservices.config.cli')


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


def main():
    logging.register_options(CONF)
    CONF(sys.argv[1:])
    logging.setup(CONF, 'microservices')

    func = globals()['do_%s' % CONF.action.name]
    func()


if __name__ == '__main__':
    main()
