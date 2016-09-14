import multiprocessing
import os

from oslo_config import cfg

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

CONF = cfg.CONF
repositories_opts = [
    cfg.BoolOpt('clone',
                default=True,
                help='Automatic cloning of microservices repositories'),
    cfg.IntOpt('clone-concurrency',
               default=multiprocessing.cpu_count(),
               help="Define how many 'git clone' processes will run "
                    "concurrently"),
    cfg.BoolOpt('skip-empty',
                default=True,
                help='Skip repositories not containing Dockerfiles without '
                     'error'),
    cfg.StrOpt('path',
               default=os.path.expanduser('~/ccp-repos/'),
               help='Path where the Git repositories are cloned'),
    cfg.HostnameOpt('hostname',
                    default='review.openstack.org',
                    help='Git server hostname to pull repositories from'),
    cfg.PortOpt('port', default=443, help='Git server port'),
    cfg.StrOpt('protocol',
               choices=['ssh', 'git', 'http', 'https'],
               default='https',
               help='Git access protocol'),
    cfg.StrOpt('project',
               default='openstack',
               help='Gerrit project'),
    cfg.StrOpt('username',
               default='',
               help='Username when using git or ssh scheme'),
    cfg.ListOpt('names',
                default=DEFAULT_REPOS,
                help='List of repository names'),
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
        'username': '',
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
            'username': {'type': 'string'},
            'names': {'type': 'array', 'items': {'type': 'string'}},
        },
    },
}

for repo in DEFAULT_REPOS:
    url = '$protocol://$username@$hostname:$port/$project/'
    option = cfg.StrOpt(repo, default=url + repo)
    repositories_opts.append(option)
    conf_name = repo.replace('-', '_')
    SCHEMA['repositories']['properties'][conf_name] = {'type': 'string'}
    DEFAULTS['repositories'][conf_name] = url

repositories_opt_group = cfg.OptGroup(name='repositories',
                                      title='Git repositories for components')
CONF.register_group(repositories_opt_group)
CONF.register_cli_opts(repositories_opts, repositories_opt_group)
CONF.register_opts(repositories_opts, repositories_opt_group)
