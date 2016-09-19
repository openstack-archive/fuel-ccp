import multiprocessing
import os

DEFAULT_REPOS = [
    'fuel-ccp-cinder',
    'fuel-ccp-debian-base',
    'fuel-ccp-entrypoint',
    'fuel-ccp-etcd',
    'fuel-ccp-glance',
    'fuel-ccp-heat',
    'fuel-ccp-horizon',
    'fuel-ccp-ironic',
    'fuel-ccp-keystone',
    'fuel-ccp-mariadb',
    'fuel-ccp-memcached',
    'fuel-ccp-murano',
    'fuel-ccp-neutron',
    'fuel-ccp-nova',
    'fuel-ccp-openstack-base',
    'fuel-ccp-rabbitmq',
    'fuel-ccp-sahara',
    'fuel-ccp-searchlight',
    'fuel-ccp-stacklight',
]

DEFAULTS = {
    'repositories': {
        'clone': True,
        'clone_concurrency': multiprocessing.cpu_count(),
        'skip_empty': True,
        'path': os.path.expanduser('~/ccp-repos/'),
        'hostname': 'review.openstack.org',
        'port': 443,
        'protocol': 'https',
        'project': 'openstack',
        'username': None,
        'names': DEFAULT_REPOS,
    },
}

SCHEMA = {
    'repositories': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'clone': {'type': 'boolean'},
            'clone_concurrency': {'type': 'integer'},
            'skip_empty': {'type': 'boolean'},
            'path': {'type': 'string'},
            'hostname': {'type': 'string'},
            'port': {'type': 'integer'},
            'protocol': {'type': 'string'},
            'project': {'type': 'string'},
            'username': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'names': {'type': 'array', 'items': {'type': 'string'}},
        },
    },
}

for repo in DEFAULT_REPOS:
    conf_name = repo.replace('-', '_')
    SCHEMA['repositories']['properties'][conf_name] = \
        {'anyOf': [{'type': 'string'}, {'type': 'null'}]}
    DEFAULTS['repositories'][conf_name] = None
