"""
Create diagnostic snapshot of everything
"""

from timmy.modules import local
import timmy.conf
import logging
import os

from fuel_ccp import config

#from timmy.conf import load_conf
from timmy.tools import signal_wrapper
from timmy.modules import fuel
from timmy.nodes import Node, NodeManager
from timmy.env import version

CONF = config.CONF
LOG = logging.getLogger(__name__)

def pretty_run(quiet, msg, f, args=[], kwargs={}):
    if not quiet:
        sys.stdout.write('%s...\r' % msg)
        sys.stdout.flush()
    result = f(*args, **kwargs)
    if not quiet:
        print('%s: done' % msg)
    return result

def node_manager_init(conf):
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s')
    nm = fuel.NodeManager(conf=conf)
    return nm

def diagnostic():
    LOG.info("aaa")
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')
    conf=timmy.conf.init_default_conf()
    rqfile = 'default.yaml'
    conf['ssh_opts'] = ['-oConnectTimeout=2', '-oStrictHostKeyChecking=no',
                        '-oUserKnownHostsFile=/dev/null', '-oLogLevel=error',
                        '-lvagrant', '-oBatchMode=yes']
    conf['rqdir'] = '/home/vagrant/fuel_diag/fuel-ccp/rq'
    conf['rqfile'] = [{'file': os.path.join(conf['rqdir'], rqfile),
                      'default': True}]
    conf['archive_dir'] = '/tmp/timmy/archives'
    conf['env_vars'] = ['OPENRC=/home/vagrant/openrc-ccp', 'LC_ALL="C"', 'LANG="C"','NS="ccp"']
    conf['archive_name'] = 'general.tar.gz'
    nm=local.NodeManager(conf, 'nodes.json')
    nm.run_commands()
    print(conf)
#    for node in nm.nodes.values():
#        print(node.mapscr)
