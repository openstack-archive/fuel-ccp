import signal
import sys

from fuel_ccp import build
from fuel_ccp import cleanup
from fuel_ccp import config
from fuel_ccp.common import utils
from fuel_ccp import dependencies
from fuel_ccp import deploy
from fuel_ccp import fetch
from fuel_ccp import validate
from fuel_ccp.validation import service as validation_service

CONF = config.CONF


def do_build():
    if CONF.builder.push and not CONF.registry.address:
        raise RuntimeError('No registry specified, cannot push')
    if CONF.repositories.clone:
        do_fetch()
    build.build_components(components=CONF.action.components)


def do_deploy():
    if CONF.repositories.clone:
        do_fetch()
    components_map = utils.get_deploy_components_info()

    components = CONF.action.components
    if components:
        components = set(components)

    validation_service.validate_service_definitions(components_map, components)
    deploy.deploy_components(components_map, components)


def do_validate():
    if CONF.repositories.clone:
        do_fetch()

    components = CONF.action.components
    if components:
        components = set(components)
    validate.validate(components=components, types=CONF.action.types)


def do_fetch():
    fetch.fetch_repositories(CONF.repositories.names)


def do_cleanup():
    cleanup.cleanup(auth_url=CONF.action.auth_url,
                    skip_os_cleanup=CONF.action.skip_os_cleanup)


def do_show_dep():
    if CONF.repositories.clone:
        do_fetch()
    dependencies.show_dep(CONF.action.components)


def signal_handler(signo, frame):
    sys.exit(-signo)


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    config.setup_config()

    func = globals()['do_%s' % CONF.action.name.replace('-', '_')]
    func()


if __name__ == '__main__':
    main()
