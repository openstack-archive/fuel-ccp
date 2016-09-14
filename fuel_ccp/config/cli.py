

def add_parsers(subparsers):
    build_action = subparsers.add_parser('build')
    build_action.add_argument('-c', '--components',
                              nargs='+',
                              help='CCP component to build')

    deploy_action = subparsers.add_parser('deploy')
    deploy_action.add_argument('-c', '--components',
                               nargs='+',
                               help='CCP component to deploy')
    deploy_action.add_argument("--dry-run",
                               action='store_true',
                               help="Print k8s objects definitions without"
                                    "actual creation")
    deploy_action.add_argument('--export-dir',
                               help='Directory to export created k8s objects')

    subparsers.add_parser('fetch')

    cleanup_action = subparsers.add_parser('cleanup')
    # Making auth url configurable at least until Ingress/LB support will
    # be implemented
    cleanup_action.add_argument('--auth-url',
                                help='The URL of Keystone authentication '
                                     'server')
    cleanup_action.add_argument('--skip-os-cleanup',
                                action='store_true',
                                help='Skip cleanup of OpenStack environment')

    show_dep_action = subparsers.add_parser('show-dep')
    show_dep_action.add_argument('components',
                                 nargs='+',
                                 help='CCP components to show dependencies')

DEFAULTS = {
    'deploy_config': None,
    'action': {
        'components': None,
        'dry_run': False,
        'export_dir': None,
        'auth_url': None,
        'skip_os_cleanup': False,
    },
}

SCHEMA = {
    'deploy_config': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
    'action': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {k: {'anyOf': [v, {'type': 'null'}]} for k, v in {
            'name': {'type': 'string'},
            'components': {
                'type': 'array',
                'items': {'type': 'string'},
            },
            'dry_run': {'type': 'boolean'},
            'export_dir': {'type': 'string'},
            'auth_url': {'type': 'string'},
            'skip_os_cleanup': {'type': 'boolean'},
        }.items()},
    },
}
