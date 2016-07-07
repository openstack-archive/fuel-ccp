import os
import sys

from concurrent import futures
import git
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('auth', 'microservices.config.auth')
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)


def create_git_url(repository_name):
    git_url = '%s://%s%s%s/%s/%s' % (CONF.repositories.protocol,
                                     (CONF.auth.gerrit_username + '@'
                                      if CONF.auth.gerrit_username else ''),
                                     CONF.repositories.hostname,
                                     (':' + str(CONF.repositories.port)
                                      if CONF.repositories.port else ''),
                                     CONF.repositories.project,
                                     repository_name)
    LOG.debug('Git url is: %s', git_url)
    return git_url


def fetch_repository(repository_name):
    dest_dir = os.path.join(CONF.repositories.path, repository_name)
    if os.path.isdir(dest_dir):
        LOG.info('%s was already cloned, skipping', repository_name)
        return
    git_url = create_git_url(repository_name)
    git.Repo.clone_from(git_url, dest_dir)
    LOG.info('Cloned %s repo', repository_name)


def fetch_repositories(repository_names=None):
    if repository_names is None:
        repository_names = CONF.repositories.names

    LOG.info('Cloning repositories into %s', CONF.repositories.path)

    errors = 0
    with futures.ThreadPoolExecutor(
            max_workers=CONF.repositories.clone_concurrency) as executor:
        future_list = []
        try:
            for repository_name in repository_names:
                future_list.append(executor.submit(
                    fetch_repository, repository_name
                ))

            for future in future_list:
                try:
                    future.result(timeout=sys.maxint)
                except Exception as ex:
                    LOG.error("Failed to fetch: %s" % ex)
                    errors += 1
        except SystemExit:
            for future in future_list:
                future.cancel()
            raise
    if errors:
        raise Exception("Failed to fetch %d repos" % errors)
