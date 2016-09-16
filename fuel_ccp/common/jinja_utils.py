import os

from fuel_ccp import config
import jinja2


def str_to_bool(text):
    return text is not None and text.lower() in ['true', 'yes']


def cross_repository_loader(relative_path):
    """Load a repository-relative template source.

    :param relative_path: template path, e.g:
           fuel-ccp-messaging/generic.j2
    :return: template source or None
    """

    repos_path = config.CONF.repositories.path
    base_path = os.path.join(repos_path, os.path.dirname(relative_path))
    filename = os.path.basename(relative_path)
    if os.path.exists(base_path):
        loader = jinja2.FileSystemLoader(base_path)
        return loader.get_source(None, filename)


def jinja_render(path, context, functions=()):
    env = jinja2.Environment(loader=jinja2.ChoiceLoader([
        jinja2.FileSystemLoader(os.path.dirname(path)),
        jinja2.FunctionLoader(cross_repository_loader)]),
        undefined=jinja2.StrictUndefined)

    env.filters['bool'] = str_to_bool
    for func in functions:
        env.globals[func.__name__] = func
    content = env.get_template(os.path.basename(path)).render(context)
    return content
