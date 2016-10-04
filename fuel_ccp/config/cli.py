DEFAULTS = {
    'action': {
        'components': None,
        'dry_run': False,
        'export_dir': None,
        'auth_url': None,
        'skip_os_cleanup': False,
    },
}

SCHEMA = {
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
            'types': {
                'type': 'array',
                'items': {
                    "enum": ["service-def"]
                }
            }
        }.items()},
    },
}
