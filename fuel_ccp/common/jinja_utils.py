import os

import jinja2
import re


class SilentUndefined(jinja2.Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''

    __add__ = __radd__ = __mul__ = __rmul__ = __div__ = __rdiv__ = \
        __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = \
        __mod__ = __rmod__ = __pos__ = __neg__ = __call__ = \
        __getitem__ = __lt__ = __le__ = __gt__ = __ge__ = __int__ = \
        __float__ = __complex__ = __pow__ = __rpow__ = \
        _fail_with_undefined_error


def jinja_render(path, context, functions=(), ignore_undefined=False):
    kwargs = {}
    if ignore_undefined:
        kwargs['undefined'] = SilentUndefined
    else:
        kwargs['undefined'] = jinja2.StrictUndefined

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        os.path.dirname(path)), **kwargs)
    for func in functions:
        env.globals[func.__name__] = func
    content = env.get_template(os.path.basename(path)).render(context)
    return content


def generate_jinja_imports(filenames):
    """Generate str of jinja imports from list of filenames."""
    imports = []  # list of j2 imports: "{% import 'msg.j2' as msg %}"
    for name in filenames:
        import_as = name.split('.')[0]  # remove file extension
        if not re.match('[a-zA-Z_][a-zA-Z0-9_]*', import_as):
            raise RuntimeError('Wrong templates file naming: the %s cannot be'
                               'imported by jinja with %s name. Please use '
                               'python compatible naming' % (name, import_as))
        imports.append(
            "{% import '" + name + "' as " + import_as + " with context %}")
    return '\n'.join(imports)
