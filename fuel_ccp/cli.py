from __future__ import print_function

import argparse
import logging
import os.path
import signal
import sys

from cliff import app
from cliff import command
from cliff import commandmanager
from cliff import lister
from cliff import show

import fuel_ccp
from fuel_ccp import action
from fuel_ccp import build
from fuel_ccp import cleanup
from fuel_ccp.common import utils
from fuel_ccp import config
from fuel_ccp import dependencies
from fuel_ccp import deploy
from fuel_ccp import fetch
from fuel_ccp import status
from fuel_ccp import validate
from fuel_ccp.validation import service as validation_service

CONF = config.CONF
LOG = logging.getLogger(__name__)

ACTION_FIELDS = ("name", "component", "date", "status", "restarts")


class BaseCommand(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super(BaseCommand, self).get_parser(*args, **kwargs)
        parser.set_defaults(**CONF.action._dict)
        return parser

    def _fetch_repos(self):
        if CONF.repositories.clone:
            do_fetch()


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
        self._fetch_repos()
        config.load_component_defaults()
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
        self._fetch_repos()
        config.load_component_defaults()
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
        validation_service.validate_service_versions(
            components_map, components)
        deploy.deploy_components(components_map, components)


def do_fetch():
    fetch.fetch_repositories()


class Fetch(BaseCommand):
    """Fetch all repos with components definitions"""

    def take_action(self, parsed_args):
        do_fetch()


class Validate(BaseCommand):
    """Validate CCP components"""

    def get_parser(self, *args, **kwargs):
        parser = super(Validate, self).get_parser(*args, **kwargs)
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
        self._fetch_repos()
        config.load_component_defaults()

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
        cert = parser.add_mutually_exclusive_group()
        cert.add_argument('--insecure',
                          action='store_true',
                          help='Skip CA certificate verification')
        cert.add_argument('--ca-cert',
                          help='Path to CA certificate file')
        return parser

    def take_action(self, parsed_args):
        config.load_component_defaults()
        cleanup.cleanup(auth_url=parsed_args.auth_url,
                        skip_os_cleanup=parsed_args.skip_os_cleanup,
                        verify=parsed_args.ca_cert or not parsed_args.insecure)


class ShowDep(BaseCommand):
    """Show dependencies of CCP components"""

    def get_parser(self, *args, **kwargs):
        parser = super(ShowDep, self).get_parser(*args, **kwargs)
        parser.add_argument('components',
                            nargs='+',
                            help='CCP components to show dependencies')
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        config.load_component_defaults()
        dependencies.show_dep(parsed_args.components)


class ConfigDump(BaseCommand):
    """Dump full current configuration to stdout"""

    def get_parser(self, *args, **kwargs):
        parser = super(ConfigDump, self).get_parser(*args, **kwargs)
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        config.load_component_defaults()
        config.dump_yaml(self.app.stdout)


class ShowStatus(lister.Lister):
    """Show status of deployment"""

    def get_parser(self, *args, **kwargs):
        parser = super(ShowStatus, self).get_parser(*args, **kwargs)
        parser.set_defaults(**CONF.action._dict)

        parser.add_argument("-l", "--long",
                            action="store_true",
                            help="show all components status")
        parser.add_argument("-s", "--short",
                            action="store_true",
                            help="show cluster status (ready or not)")
        parser.add_argument("components",
                            nargs="*",
                            help="CCP conponents to show status")
        return parser

    def take_action(self, parsed_args):
        config.load_component_defaults()
        if parsed_args.long:
            return status.show_long_status()
        elif parsed_args.short:
            return status.show_short_status()
        else:
            return status.show_long_status(parsed_args.components)


class ImagesList(BaseCommand, lister.Lister):
    """Get images matching list of components"""

    def get_parser(self, *args, **kwargs):
        parser = super(ImagesList, self).get_parser(*args, **kwargs)
        parser.add_argument('components',
                            nargs='*',
                            help='CCP components to get images for')
        return parser

    def take_action(self, parsed_args):
        dockerfiles = build.get_dockerfiles(match=not parsed_args.components)
        for component in parsed_args.components:
            build.match_dockerfiles_by_component(dockerfiles, component)
        return (
            ('Name',),
            sorted((d['name'],) for d in dockerfiles.values() if d['match']),
        )


class DomainsList(BaseCommand, lister.Lister):
    """Get Ingress domains that will be used for external access"""

    def get_parser(self, *args, **kwargs):
        parser = super(DomainsList, self).get_parser(*args, **kwargs)
        parser.add_argument('components',
                            nargs='*',
                            help='CCP components to get domains for')
        return parser

    def take_action(self, parsed_args):
        config.load_component_defaults()
        domains_list = utils.get_ingress_domains(parsed_args.components)
        return ('Ingress Domain',), zip(domains_list)


# action commands

class ActionList(BaseCommand, lister.Lister):
    """Get list of available actions"""

    def get_parser(self, *args, **kwargs):
        parser = super(ActionList, self).get_parser(*args, **kwargs)
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        config.load_component_defaults()
        actions = action.list_actions()
        return ("Name", "Component"), [(a.name, a.component) for a in actions]


class ActionLog(BaseCommand):
    """Show action container stdout"""

    def get_parser(self, *args, **kwargs):
        parser = super(ActionLog, self).get_parser(*args, **kwargs)
        parser.add_argument("action",
                            help="Show action container stdout")
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        action_obj = action.get_action_status_by_name(parsed_args.action)
        print(action_obj.log())


class ActionShow(BaseCommand, show.ShowOne):
    """Show action"""

    def get_parser(self, *args, **kwargs):
        parser = super(ActionShow, self).get_parser(*args, **kwargs)
        parser.add_argument("action",
                            help="Show details of the action")
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        action_obj = action.get_action(parsed_args.action)
        return (
            ("Name",
             "Component",
             "Image"),
            (action_obj.name,
             action_obj.component,
             action_obj.image))


class ActionStatus(BaseCommand, lister.Lister):
    """Show list of executed actions"""

    def get_parser(self, *args, **kwargs):
        parser = super(ActionStatus, self).get_parser(*args, **kwargs)
        parser.add_argument("action",
                            help="Show action status"
                                 "Select 'all' for show all statuses"
                            )
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        if not parsed_args.action or parsed_args.action == "all":
            return (
                ACTION_FIELDS,
                ((a.name, a.component, a.date, a.status, a.restarts)
                 for a in action.list_action_status(parsed_args.action))
            )
        else:
            action_obj = action.get_action_status_by_name(parsed_args.action)
            return (
                ACTION_FIELDS,
                (action_obj.name, action_obj.component, action_obj.date,
                 action_obj.status, action_obj.restarts))


class ActionRun(BaseCommand, show.ShowOne):
    """Run action"""

    def get_parser(self, *args, **kwargs):
        parser = super(ActionRun, self).get_parser(*args, **kwargs)
        parser.add_argument("action",
                            help="Run action")
        return parser

    def take_action(self, parsed_args):
        self._fetch_repos()
        config.load_component_defaults()
        action_name = action.run_action(parsed_args.action)
        action_obj = action.get_action_status_by_name(action_name)
        return (
            ACTION_FIELDS,
            (action_obj.name, action_obj.component, action_obj.date,
             action_obj.status, action_obj.restarts))


def signal_handler(signo, frame):
    sys.exit(-signo)


class CCPApp(app.App):
    CONSOLE_MESSAGE_FORMAT = \
        '%(asctime)s %(levelname)-8s %(name)-15s %(message)s'

    def __init__(self, **kwargs):
        ccp_version = "%s, dsl version %s" % (fuel_ccp.__version__,
                                              fuel_ccp.dsl_version)
        super(CCPApp, self).__init__(
            description='Containerized Control Plane tool',
            version=ccp_version,
            command_manager=commandmanager.CommandManager('ccp.cli'),
            deferred_help=True,
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
        if not CONF.debug:
            for level in CONF.default_log_levels:
                mod, sep, level_name = level.partition("=")
                logger = logging.getLogger(mod)
                logger.setLevel(level_name)


def main(argv=None):
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    if argv is None:
        argv = sys.argv[1:]
    return CCPApp().run(argv)


if __name__ == '__main__':
    sys.exit(main())
