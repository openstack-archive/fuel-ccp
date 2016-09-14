import logging
import os

from concurrent import futures
import git

from fuel_ccp import config


CONF = config.CONF

LOG = logging.getLogger(__name__)

FETCH_TIMEOUT = 2 ** 16  # in seconds


def fetch_repository(repository_name):
    dest_dir = os.path.join(CONF.repositories.path, repository_name)
    if os.path.isdir(dest_dir):
        LOG.info('%s was already cloned, skipping', repository_name)
        return
    git_url = getattr(CONF.repositories, repository_name.replace('-', '_'))
    if git_url is None:
        username = CONF.repositories.username
        if username is None:
            username = ''
        else:
            username = username + '@'
        fmt = '{0.protocol}://{1}{0.hostname}:{0.port}/{0.project}/{2}'
        git_url = fmt.format(CONF.repositories, username, repository_name)
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
