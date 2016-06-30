import os

import jinja2
from oslo_config import cfg


CONF = cfg.CONF
CONF.import_group('builder', 'microservices.config.builder')
CONF.import_group('images', 'microservices.config.images')
CONF.import_group('registry', 'microservices.config.registry')


def str_to_bool(text):
    return text is not None and text.lower() in ['true', 'yes']


def jinja_render(path):
    variables = {k: v for k, v in CONF.images.items()}

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        os.path.dirname(path)))
    env.filters['bool'] = str_to_bool

    content = env.get_template(os.path.basename(path)).render(variables)

    return content
