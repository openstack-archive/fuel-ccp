import os

import jinja2
from fuel_ccp import config


def str_to_bool(text):
    return text is not None and text.lower() in ['true', 'yes']


def cross_repository_loader(relative_path):
    """
    Load a template source located at any fetched
    repository by the relative path, e.g.:

    fuel-ccp-messaging/generic_template.j2

    :param relative_path: the path to template
    """
    repos_path = config.CONF.repositories.path
    base_path = os.path.join(repos_path, os.path.dirname(relative_path))
    filename = os.path.basename(relative_path)
    loader = jinja2.FileSystemLoader(base_path)
    return loader.get_source(None, filename)


def jinja_render(path, context, functions=()):
    env = jinja2.Environment(loader=jinja2.ChoiceLoader([
        jinja2.FileSystemLoader(path),
        jinja2.FunctionLoader(cross_repository_loader)]),
        undefined=jinja2.StrictUndefined)

    env.filters['bool'] = str_to_bool
    for func in functions:
        env.globals[func.__name__] = func
    content = env.get_template(os.path.basename(path)).render(context)
    return content
