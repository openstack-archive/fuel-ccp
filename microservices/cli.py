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
        repository_names = CONF.repositories.names
        if CONF.repositories.clone:
            fetch.fetch_repositories(repository_names=repository_names)
        return f(*args, **kwargs)
    return wrapper


@command_prerequisites
def do_build():
    build.build_components(components=CONF.action.components)


@command_prerequisites
def do_deploy():
    deploy.deploy_components(components=CONF.action.components)


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
