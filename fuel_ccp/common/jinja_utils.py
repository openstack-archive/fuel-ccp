import os

from fuel_ccp import config
import jinja2


class SilentUndefined(jinja2.Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''

    __add__ = __radd__ = __mul__ = __rmul__ = __div__ = __rdiv__ = \
        __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = \
        __mod__ = __rmod__ = __pos__ = __neg__ = __call__ = \
        __getitem__ = __lt__ = __le__ = __gt__ = __ge__ = __int__ = \
        __float__ = __complex__ = __pow__ = __rpow__ = \
        _fail_with_undefined_error


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


def jinja_render(path, context, functions=(), ignore_undefined=False):
    kwargs = {}
    if ignore_undefined:
        kwargs['undefined'] = SilentUndefined
    else:
        kwargs['undefined'] = jinja2.StrictUndefined

    env = jinja2.Environment(loader=jinja2.ChoiceLoader([
        jinja2.FileSystemLoader(os.path.dirname(path)),
        jinja2.FunctionLoader(cross_repository_loader)]), **kwargs)
    env.filters['bool'] = str_to_bool
    for func in functions:
        env.globals[func.__name__] = func
    content = env.get_template(os.path.basename(path)).render(context)
    return content
