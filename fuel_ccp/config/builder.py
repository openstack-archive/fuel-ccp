import multiprocessing

from oslo_config import cfg


CONF = cfg.CONF
builder_opts = [
    cfg.IntOpt('workers',
               default=multiprocessing.cpu_count(),
               help='Number of workers which build docker images'),
    cfg.BoolOpt('keep-image-tree-consistency',
                default=True,
                help='Rebuild all descendant images to keep consistent state '
                     'of image tree'),
    cfg.BoolOpt('build-base-images-if-not-exist',
                default=True,
                help='Make sure that all base images required for target '
                     'image building are ready and prebuild them if they are '
                     'not'),
    cfg.BoolOpt('push',
                default=False,
                help='Push to the Docker registry'),
    cfg.BoolOpt('no-cache',
                default=False,
                help='Dont use docker cache')
]
builder_opt_group = cfg.OptGroup(name='builder',
                                 title='Images builder')
CONF.register_group(builder_opt_group)
CONF.register_cli_opts(builder_opts, builder_opt_group)
CONF.register_opts(builder_opts, builder_opt_group)

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
        'properties': {
            'workers': {'type': 'integer'},
            'keep_image_tree_consistency': {'type': 'boolean'},
            'build_base_images_if_not_exist': {'type': 'boolean'},
            'push': {'type': 'boolean'},
            'no_cache': {'type': 'boolean'},
        },
    },
}
