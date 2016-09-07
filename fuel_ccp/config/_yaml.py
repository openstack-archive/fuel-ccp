import six
import yaml


# NOTE(yorik-sar): Don't implement full dict interface to avoid name conflicts
class AttrDict(object):
    def __init__(self, *args, **kwargs):
        self._dict = dict(*args, **kwargs)

    def __getattr__(self, name):
        try:
            return self._dict[name]
        except KeyError:
            raise AttributeError(name)

    def __getitem__(self, name):
        return self._dict[name]

    def __setitem__(self, name, value):
        self._dict[name] = value

    def _update(self, *args, **kwargs):
        self._dict.update(*args, **kwargs)

    def _items(self):
        return six.iteritems(self._dict)

    def __eq__(self, other):
        if isinstance(other, AttrDict):
            return self._dict == other._dict
        elif isinstance(other, dict):
            return self._dict == other
        else:
            return NotImplemented

    def __repr__(self):
        return 'AttrDict({})'.format(self._dict)


class Loader(yaml.SafeLoader):
    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return AttrDict(loader.construct_pairs(node))

Loader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping,
)


def load(stream):
    return yaml.load(stream, Loader=Loader)
