import os
import sys

from concurrent import futures
import git
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
CONF.import_group('auth', 'microservices.config.auth')
CONF.import_group('repositories', 'microservices.config.repositories')
CONF.import_opt("action", "microservices.config.cli")
CONF.import_opt("fetch_pull", "microservices.config.cli")

LOG = logging.getLogger(__name__)


def fetch_repository(repository_name):
    dest_dir = os.path.join(CONF.repositories.path, repository_name)
    git_url = getattr(CONF.repositories, repository_name.replace('-', '_'))
    git_url = git_url % (CONF.repositories.protocol,
                         CONF.auth.gerrit_username,
                         CONF.repositories.hostname,
                         CONF.repositories.port,
                         CONF.repositories.project)
    if os.path.isdir(dest_dir) and CONF.fetch_pull:
        LOG.info('%s was already cloned and --pull-origin flag found,'
                 ' pulling origin', repository_name)
        repo = git.Repo(dest_dir)
        if repo.active_branch.name == "master":
            repo.remotes.origin.pull()
            LOG.info('Pulled %s repo', repository_name)
        else:
            LOG.info('Current branch in "%s" repo is "%s", skipping',
                     repository_name, repo.active_branch.name)
    elif os.path.isdir(dest_dir):
        LOG.info('%s was already cloned, skipping', repository_name)
        return
    else:
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
