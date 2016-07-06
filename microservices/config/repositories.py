import multiprocessing
import os

from oslo_config import cfg

DEFAULT_REPOS = ['ms-ext-config',
                 'ms-debian-base',
                 'ms-aodh',
                 'ms-ceilometer',
                 'ms-ceph',
                 'ms-cinder',
                 'ms-designate',
                 'ms-elasticsearch',
                 'ms-glance',
                 'ms-grafana',
                 'ms-heat',
                 'ms-horizon',
                 'ms-ironic',
                 'ms-influxdb',
                 'ms-keystone',
                 'ms-kibana',
                 'ms-lma',
                 'ms-magnum',
                 'ms-manila',
                 'ms-mariadb',
                 'ms-memcached',
                 'ms-mistral',
                 'ms-mongodb',
                 'ms-murano',
                 'ms-neutron',
                 'ms-nova',
                 'ms-openstack-base',
                 'ms-rabbitmq',
                 'ms-sahara',
                 'ms-swift',
                 'ms-tempest',
                 'ms-toolbox',
                 'ms-trove',
                 'ms-zaqar']

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
               default=os.path.expanduser('~/microservices-repos/'),
               help='Path where the microservice repositories are cloned'),
    cfg.HostnameOpt('hostname',
                    default='review.fuel-infra.org',
                    help='Git server hostname to pull repositories from'),
    cfg.PortOpt('port', default=29418, help='Git server port'),
    cfg.StrOpt('protocol',
               choices=['ssh', 'git', 'http', 'https'],
               default='ssh',
               help='Git access protocol'),
    cfg.StrOpt('project',
               default='nextgen',
               help='Gerrit project'),
    cfg.ListOpt('names',
                default=DEFAULT_REPOS,
                help='List of repository names'),
]

for repo in DEFAULT_REPOS:
    option = cfg.StrOpt(repo, default='%s://%s@%s:%i/%s/' + repo)
    repositories_opts.append(option)

repositories_opt_group = cfg.OptGroup(name='repositories',
                                      title='Git repositories for components')
CONF.register_group(repositories_opt_group)
CONF.register_cli_opts(repositories_opts, repositories_opt_group)
CONF.register_opts(repositories_opts, repositories_opt_group)
