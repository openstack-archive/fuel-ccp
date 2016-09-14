import multiprocessing

DEFAULTS = {
    'builder': {
        'workers': multiprocessing.cpu_count(),
        'keep_image_tree_consistency': True,
        'build_base_images_if_not_exist': True,
        'push': False,
        'no_cache': False,
    },
}

SCHEMA = {
    'builder': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {k: {'anyOf': [v, {'type': 'null'}]} for k, v in {
            'workers': {'type': 'integer'},
            'keep_image_tree_consistency': {'type': 'boolean'},
            'build_base_images_if_not_exist': {'type': 'boolean'},
            'push': {'type': 'boolean'},
            'no_cache': {'type': 'boolean'},
        }.items()},
    },
}
