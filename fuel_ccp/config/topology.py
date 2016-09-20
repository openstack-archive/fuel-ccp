DEFAULTS = {
}

ROLES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string",
    },
}

SCHEMA = {
    'nodes': {
        'type': 'array',
        'items': {
            'anyOf' : [
                {
                    'type' : 'object',
                    'additionalProperties': False,
                    'properties' : {
                        'all' : { 'type' : 'boolean' },
                        'roles': ROLES_SCHEMA,
                    },
                },
                {
                    'type' : 'object',
                    'additionalProperties': False,
                    'properties' : {
                        'nodes' : {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                        'except' : { 'type': 'boolean' },
                        'roles': ROLES_SCHEMA,
                    },
                },
                {
                    'type' : 'object',
                    'additionalProperties': False,
                    'properties' : {
                        'regex' : {
                            "type": "string",
                        },
                        'except' : { 'type': 'boolean' },
                        'roles': ROLES_SCHEMA,
                    },
                },
            ],
        },
    },
}
