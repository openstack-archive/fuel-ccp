import argparse
import logging
import os.path
import signal
import sys

from cliff import app
from cliff import command
from cliff import commandmanager

import fuel_ccp
from fuel_ccp import build
from fuel_ccp import cleanup
from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp import dependencies
from fuel_ccp import deploy
from fuel_ccp import fetch
from fuel_ccp import validate
from fuel_ccp.validation import service as validation_service

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BaseCommand(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super(BaseCommand, self).get_parser(*args, **kwargs)
        parser.set_defaults(**CONF.action._dict)
        return parser


class Build(BaseCommand):
    """Build CCP docker images"""

    def get_parser(self, *args, **kwargs):
        parser = super(Build, self).get_parser(*args, **kwargs)
        parser.add_argument('-c', '--components',
                            nargs='+',
                            help='CCP component to build')
        return parser

    def take_action(self, parsed_args):
        if CONF.builder.push and not CONF.registry.address:
            raise RuntimeError('No registry specified, cannot push')
        if CONF.repositories.clone:
            do_fetch()
        build.build_components(components=parsed_args.components)


class Deploy(BaseCommand):
    """Deploy CCP"""

    def get_parser(self, *args, **kwargs):
        parser = super(Deploy, self).get_parser(*args, **kwargs)
        parser.add_argument('-c', '--components',
                            nargs='+',
                            help='CCP component to build')
        parser.add_argument("--dry-run",
                            action='store_true',
                            help="Print k8s objects definitions without"
                                 "actual creation")
        parser.add_argument('--export-dir',
                            help='Directory to export created k8s objects')
        return parser

    def take_action(self, parsed_args):
        if CONF.repositories.clone:
            do_fetch()
        # only these two are being implicitly passed
        CONF.action._update(
            dry_run=parsed_args.dry_run,
            export_dir=parsed_args.export_dir,
        )
        components_map = utils.get_deploy_components_info()

        components = parsed_args.components
        if components:
            components = set(components)

        validation_service.validate_service_definitions(
            components_map, components)
        deploy.deploy_components(components_map, components)


def do_fetch():
    fetch.fetch_repositories(CONF.repositories.names)


class Fetch(BaseCommand):
    """Fetch all repos with components definitions"""

    def take_action(self, parsed_args):
        do_fetch()


class Validate(BaseCommand):
    """Validate CCP components"""

    def get_parser(self, *args, **kwargs):
        parser = super(Deploy, self).get_parser(*args, **kwargs)
        parser.add_argument('-c', '--components',
                            nargs='+',
                            help='CCP components to validate')
        parser.add_argument('-t', '--types',
                            nargs="+",
                            help="List of validation types to perform. "
                                 "If not specified - perform all "
                                 "supported validation types")
        return parser

    def take_action(self, parsed_args):
        if CONF.repositories.clone:
            do_fetch()

        components = parsed_args.components
        if components:
            components = set(components)

        validate.validate(components=components, types=parsed_args.types)


class Cleanup(BaseCommand):
    """Remove all OpenStack resources and destroy CCP deployment"""

    def get_parser(self, *args, **kwargs):
        parser = super(Cleanup, self).get_parser(*args, **kwargs)
        # Making auth url configurable at least until Ingress/LB support will
        # be implemented
        parser.add_argument('--auth-url',
                            help='The URL of Keystone authentication '
                                 'server')
        parser.add_argument('--skip-os-cleanup',
                            action='store_true',
                            help='Skip cleanup of OpenStack environment')
        return parser

    def take_action(self, parsed_args):
        cleanup.cleanup(auth_url=parsed_args.auth_url,
                        skip_os_cleanup=parsed_args.skip_os_cleanup)


class ShowDep(BaseCommand):
    """Show dependencies of CCP components"""

    def get_parser(self, *args, **kwargs):
        parser = super(ShowDep, self).get_parser(*args, **kwargs)
        parser.add_argument('components',
                            nargs='+',
                            help='CCP components to show dependencies')
        return parser

    def take_action(self, parsed_args):
        if CONF.repositories.clone:
            do_fetch()
        dependencies.show_dep(parsed_args.components)


def signal_handler(signo, frame):
    sys.exit(-signo)


class CCPApp(app.App):
    CONSOLE_MESSAGE_FORMAT = \
        '%(asctime)s %(levelname)-8s %(name)-15s %(message)s'

    def __init__(self, **kwargs):
        super(CCPApp, self).__init__(
            description='Containerized Control Plane tool',
            version=fuel_ccp.__version__,
            command_manager=commandmanager.CommandManager('ccp.cli'),
            **kwargs
        )
        self.config_file = None

    @staticmethod
    def add_config_file_argument(parser):
        parser.add_argument(
            '--config-file',
            metavar='PATH',
            help=('Path to a config file to use.'))

    @staticmethod
    def get_config_file(argv):
        parser = argparse.ArgumentParser(add_help=False)
        CCPApp.add_config_file_argument(parser)
        parsed_args, _ = parser.parse_known_args(argv)
        if parsed_args.config_file:
            return os.path.abspath(os.path.expanduser(parsed_args.config_file))
        else:
            return config.find_config()

    def run(self, argv):
        self.config_file = self.get_config_file(argv)
        config.setup_config(self.config_file)
        self.add_config_file_argument(self.parser)
        defaults = {k: CONF[k] for k in ['debug', 'verbose_level', 'log_file']}
        if CONF.debug:  # We're used to having DEBUG logging with debug conf
            defaults['verbose_level'] = 2
        self.parser.set_defaults(**defaults)
        return super(CCPApp, self).run(argv)

    def configure_logging(self):
        super(CCPApp, self).configure_logging()
        if self.config_file:
            LOG.debug('Loaded config from file %s', self.config_file)
        else:
            LOG.debug('No config file loaded')


def main(argv=None):
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    if argv is None:
        argv = sys.argv[1:]
    CCPApp().run(argv)


if __name__ == '__main__':
    main()
