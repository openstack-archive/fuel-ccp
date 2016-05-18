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

    fetch_action = subparsers.add_parser('fetch')
    fetch_action.add_argument('-c', '--components',
                              nargs='+',
                              help='MCP component to fetch')


CONF.register_cli_opt(cfg.SubCommandOpt('action',
                                        handler=add_parsers))
