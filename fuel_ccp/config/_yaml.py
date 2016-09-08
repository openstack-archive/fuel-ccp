import collections
import os

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

    def _merge(self, other):
        for key, other_value in other._items():
            try:
                value = self._dict[key]
            except KeyError:
                merge = False
            else:
                merge = isinstance(value, AttrDict)
            if merge:
                value._merge(other_value)
            else:
                self._dict[key] = other_value


class Loader(yaml.SafeLoader):
    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return AttrDict(loader.construct_pairs(node))

Loader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping,
)

Includes = collections.namedtuple('Includes', 'lst')


def construct_includes(loader, node):
    return Includes(loader.construct_sequence(node))

Loader.add_constructor('!include', construct_includes)


def load(stream):
    return yaml.load(stream, Loader=Loader)


def load_all(stream):
    return yaml.load_all(stream, Loader=Loader)


def load_with_includes(filename):
    with open(filename) as f:
        docs = load_all(f)
    base_dir = os.path.dirname(filename)
    res = AttrDict()
    for doc in docs:
        if isinstance(doc, Includes):
            for inc_file in doc.lst:
                if not os.path.isabs(inc_file):
                    inc_file = os.path.join(base_dir, inc_file)
                inc_res = load_with_includes(inc_file)
                res._merge(inc_res)
        else:
            res._merge(doc)
    return res
