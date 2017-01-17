SCHEMA = {
    'storage': {
        'type': 'object',
        'additionalProperties': {
            'additionalProperties': False,
            'properties': {
                'glusterfs': {
                    'type': 'object',
                    'additionalProperties': {
                        'additionalProperties': False,
                        'properties': {
                            'enable': {'type': 'boolean'},
                            'url': {'type': 'string'},
                            'auth': {
                                'type': 'object',
                                'additionalProperties': {
                                    'additionalProperties': False,
                                    'properties': {
                                        'enable': {'type': 'boolean'},
                                        'username': {'type': 'string'},
                                        'password': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

DEFAULTS = {
    'storage': {
        'glusterfs': {
            'enable': False,
            'url': 'http://localhost:8081',
            'auth': {
                'enable': False,
                'username': '',
                'password': ''
            }
        }
    }
}
