SCHEMA = {
    'sources': {
        'additionalProperties': False,
        'properties': {
            'git_url': {'type': 'string'},
            'git_ref': {'type': 'string'},
            'source_dir': {'type': 'string'},
        },
        'oneOf': [
            {'required': ['git_url', 'git_ref']},
            {'required': ['source_dir']},
        ],
    }
}

DEFAULTS = {
    'sources': {},
}
