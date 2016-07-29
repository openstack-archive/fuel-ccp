from oslo_config import cfg


CONF = cfg.CONF


def add_parsers(subparsers):
    build_action = subparsers.add_parser('build')
    build_action.add_argument('-c', '--components',
                              nargs='+',
                              help='MCP component to build')

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

    cleanup_action = subparsers.add_parser('cleanup')
    # Making auth url configurable at least until Ingress/LB support will
    # be implemented
    cleanup_action.add_argument('--auth-url',
                                help='The URL of Keystone authentication '
                                     'server')
    cleanup_action.add_argument('--skip-os-cleanup',
                                action='store_true',
                                help='Skip cleanup of OpenStack environment')


CONF.register_cli_opt(cfg.SubCommandOpt('action',
                                        handler=add_parsers))

common_opts = [
    cfg.StrOpt('deploy-config', help='Cluster-wide configuration overrides')
]
CONF.register_cli_opts(common_opts)
