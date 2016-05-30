import functools
import sys

from oslo_config import cfg
from oslo_log import log as logging

from microservices import build
from microservices import deploy
from microservices import fetch


CONF = cfg.CONF
CONF.import_group('repositories', 'microservices.config.repositories')
CONF.import_opt('action', 'microservices.config.cli')


def command_prerequisites(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        components = CONF.action.components
        if CONF.repositories.clone:
            fetch.fetch_repositories(components=components)
        return f(components, *args, **kwargs)
    return wrapper


@command_prerequisites
def do_build(components):
    build.build_repositories(components=components)


@command_prerequisites
def do_deploy(components):
    deploy.deploy_repositories(components=CONF.action.components)


def do_fetch():
    fetch.fetch_repositories(components=CONF.action.components)


def main():
    logging.register_options(CONF)
    CONF(sys.argv[1:])
    logging.setup(CONF, 'microservices')

    func = globals()['do_%s' % CONF.action.name]
    func()


if __name__ == '__main__':
    main()
