import os

import jinja2
from oslo_config import cfg


CONF = cfg.CONF
CONF.import_group('images', 'fuel_ccp.config.images')


def str_to_bool(text):
    return text is not None and text.lower() in ['true', 'yes']


def jinja_render(path, context):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        os.path.dirname(path)))
    env.filters['bool'] = str_to_bool
    content = env.get_template(os.path.basename(path)).render(context)
    return content


def jinja_render_str(content, jvars, name='dafault_name'):
    env = jinja2.Environment(loader=jinja2.DictLoader({name: content}))
    env.filters['bool'] = str_to_bool
    return env.get_template(name).render(jvars)
