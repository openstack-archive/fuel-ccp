import os

import jinja2


def str_to_bool(text):
    return text is not None and text.lower() in ['true', 'yes']


def jinja_render(path, context, functions=()):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        os.path.dirname(path)))
    env.filters['bool'] = str_to_bool
    for func in functions:
        env.globals[func.__name__] = func
    content = env.get_template(os.path.basename(path)).render(context)
    return content
