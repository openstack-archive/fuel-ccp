import multiprocessing
import os

from oslo_config import cfg

DEFAULT_REPOS = ['fuel-ccp-entrypoint',
                 'fuel-ccp-debian-base',
                 'fuel-ccp-aodh',
                 'fuel-ccp-ceilometer',
                 'fuel-ccp-ceph',
                 'fuel-ccp-cinder',
                 'fuel-ccp-designate',
                 'fuel-ccp-elasticsearch',
                 'fuel-ccp-glance',
                 'fuel-ccp-grafana',
                 'fuel-ccp-heat',
                 'fuel-ccp-horizon',
                 'fuel-ccp-ironic',
                 'fuel-ccp-influxdb',
                 'fuel-ccp-keystone',
                 'fuel-ccp-kibana',
                 'fuel-ccp-stacklight',
                 'fuel-ccp-magnum',
                 'fuel-ccp-manila',
                 'fuel-ccp-mariadb',
                 'fuel-ccp-memcached',
                 'fuel-ccp-mistral',
                 'fuel-ccp-mongodb',
                 'fuel-ccp-murano',
                 'fuel-ccp-neutron',
                 'fuel-ccp-nova',
                 'fuel-ccp-openstack-base',
                 'fuel-ccp-openvswitch',
                 'fuel-ccp-rabbitmq',
                 'fuel-ccp-sahara',
                 'fuel-ccp-swift',
                 'fuel-ccp-tempest',
                 'fuel-ccp-toolbox',
                 'fuel-ccp-trove',
                 'fuel-ccp-zaqar']

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
                    default='review.openstack.org',
                    help='Git server hostname to pull repositories from'),
    cfg.PortOpt('port', default=29418, help='Git server port'),
    cfg.StrOpt('protocol',
               choices=['ssh', 'git', 'http', 'https'],
               default='ssh',
               help='Git access protocol'),
    cfg.StrOpt('project',
               default='openstack',
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
