from oslo_config import cfg


CONF = cfg.CONF


def add_parsers(subparsers):
    build_action = subparsers.add_parser('build')
    build_action.add_argument('-c', '--components',
                              nargs='+',
                              help='MCP component to build')

    validate_action = subparsers.add_parser('validate')
    validate_action.add_argument('objects',
                                 nargs="*",
                                 help="List of objects to validate."
                                      "If not specfied - validate all "
                                      "supported objects")

    deploy_action = subparsers.add_parser('deploy')
    deploy_action.add_argument('-c', '--components',
                               nargs='+',
                               help='MCP component to deploy')
    deploy_action.add_argument("--dry-run",
                               action='store_true',
                               help="Print k8s objects definitions without"
                                    "actual creation")

    fetch_action = subparsers.add_parser('fetch')
    fetch_action.add_argument('-c', '--components',
                              nargs='+',
                              help='MCP component to fetch')


CONF.register_cli_opt(cfg.SubCommandOpt('action',
                                        handler=add_parsers))

common_opts = [
    cfg.StrOpt('deploy-config', help='Cluster-wide configuration overrides')
]
CONF.register_cli_opts(common_opts)
