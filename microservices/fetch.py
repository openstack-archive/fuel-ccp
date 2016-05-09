import os

import git
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('auth', 'microservices.config.auth')
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)


def fetch_repositories(components=None):
    if components is None:
        components = CONF.repositories.components

    LOG.info('Cloning repositories into %s', CONF.repositories.path)

    for component in components:
        dest_dir = os.path.join(CONF.repositories.path, component)
        if os.path.isdir(dest_dir):
            LOG.info('%s was already cloned, skipping', component)
            continue
        git_url = getattr(CONF.repositories, component.replace('-', '_')) % \
            CONF.auth.gerrit_username
        git.Repo.clone_from(git_url, dest_dir)
        LOG.info('Cloned %s repo', component)
