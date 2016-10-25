import logging
import os

from concurrent import futures
import git

from fuel_ccp import config


CONF = config.CONF

LOG = logging.getLogger(__name__)

FETCH_TIMEOUT = 2 ** 16  # in seconds


def fetch_repository(repository_def):
    name = repository_def['name']
    dest_dir = os.path.join(CONF.repositories.path, name)
    if os.path.isdir(dest_dir):
        LOG.debug('%s: Repository is already cloned, skipping', name)
        return
    git_url = repository_def['git_url']
    git_ref = repository_def.get('git_ref')
    LOG.debug('%s: Cloning repository %s to %s', name, git_url, dest_dir)
    repo = git.Repo.clone_from(git_url, dest_dir)
    if git_ref:
        LOG.debug('%s: Changing reference to "%s"', name, git_ref)
        repo.git.checkout(git_ref)
    LOG.info('%s: Repository has been cloned', name)


def fetch_repositories(repository_defs=None):
    if repository_defs is None:
        repository_defs = CONF.repositories.repos

    LOG.info('Cloning repositories into %s', CONF.repositories.path)

    errors = 0
    with futures.ThreadPoolExecutor(
            max_workers=CONF.repositories.clone_concurrency) as executor:
        future_list = []
        try:
            for repository_def in repository_defs:
                future_list.append(executor.submit(
                    fetch_repository, repository_def
                ))

            for future in future_list:
                try:
                    # we need to use timeout because in this case python
                    # thread wakes up time to time to check timeout and don't
                    # block signal processing
                    future.result(timeout=FETCH_TIMEOUT)
                except Exception as ex:
                    LOG.error("Failed to fetch: %s" % ex)
                    errors += 1
        except SystemExit:
            for future in future_list:
                future.cancel()
            raise
    if errors:
        raise Exception("Failed to fetch %d repos" % errors)
