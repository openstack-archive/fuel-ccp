import multiprocessing
import os

import git
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('auth', 'microservices.config.auth')
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)


def fetch_repository(component):
    dest_dir = os.path.join(CONF.repositories.path, component)
    if os.path.isdir(dest_dir):
        LOG.info('%s was already cloned, skipping', component)
        return
    git_url = getattr(CONF.repositories, component.replace('-', '_')) % \
        CONF.auth.gerrit_username
    git.Repo.clone_from(git_url, dest_dir)
    LOG.info('Cloned %s repo', component)


def fetch_repositories(components=None):
    if components is None:
        components = CONF.repositories.components

    LOG.info('Cloning repositories into %s', CONF.repositories.path)

    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())

    tasks = [pool.apply_async(fetch_repository, (component,))
             for component in components]
    for task in tasks:
        task.wait()
