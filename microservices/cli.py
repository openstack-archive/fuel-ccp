import sys

from oslo_config import cfg
from oslo_log import log as logging

from microservices import fetch


CONF = cfg.CONF
CONF.import_group('repositories', 'microservices.config.repositories')
CONF.import_opt('action', 'microservices.config.cli')


def do_build():
    if CONF.repositories.clone:
        fetch.fetch_repositories(components=CONF.action.components)
    # TODO(mrostecki): implement build


def do_fetch():
    fetch.fetch_repositories(components=CONF.action.components)


def main():
    logging.register_options(CONF)
    logging.setup(CONF, 'microservices')
    CONF(sys.argv[1:])

    func = globals()['do_%s' % CONF.action.name]
    func()


if __name__ == '__main__':
    main()
