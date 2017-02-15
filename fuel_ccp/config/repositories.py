import multiprocessing
import os

DEFAULT_REPOS = [
    'fuel-ccp-ceph',
    'fuel-ccp-cinder',
    'fuel-ccp-debian-base',
    'fuel-ccp-entrypoint',
    'fuel-ccp-etcd',
    'fuel-ccp-galera',
    'fuel-ccp-glance',
    'fuel-ccp-grafana',
    'fuel-ccp-heat',
    'fuel-ccp-horizon',
    'fuel-ccp-ironic',
    'fuel-ccp-keystone',
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
        'entrypoint_repo_name': 'fuel-ccp-entrypoint',
        'repos': [{
            'name': name,
            'git_url': 'https://git.openstack.org/openstack/{}'.format(name),
        } for name in DEFAULT_REPOS],
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
            'entrypoint_repo_name': {'type': 'string'},
            'repos': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['name', 'git_url'],
                    'properties': {
                        'name': {'type': 'string'},
                        'git_url': {'type': 'string'},
                        'git_ref': {'type': 'string'},
                    },
                },
            },
        },
    },
}
