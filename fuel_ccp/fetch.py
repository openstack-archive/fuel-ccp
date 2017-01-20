import logging
import os

from concurrent import futures
import git

from fuel_ccp import config


CONF = config.CONF

LOG = logging.getLogger(__name__)

FETCH_TIMEOUT = 2 ** 16  # in seconds

STATUSES = {
    'fetch_alredy_existed': 'AlreadyExist',
    'fetch_failed': 'Failure',
    'fetch_succeeded': 'Success'
}


def fetch_repository(repository_def):
    name = repository_def['name']
    dest_dir = os.path.join(CONF.repositories.path, name)
    result = {'name': name, 'status': STATUSES['fetch_failed']}
    if os.path.isdir(dest_dir):
        LOG.debug('%s: Repository is already cloned, skipping', name)
        result.update(status=STATUSES['fetch_alredy_existed'])
        return result
    git_url = repository_def['git_url']
    git_ref = repository_def.get('git_ref')
    LOG.debug('%s: Cloning repository %s to %s', name, git_url, dest_dir)
    try:
        repo = git.Repo.clone_from(git_url, dest_dir)
    except git.exc.InvalidGitRepositoryError:
        LOG.error('%s: Repository does not exist', name)
        return result
    if git_ref and repo:
        LOG.debug('%s: Changing reference to "%s"', name, git_ref)
        try:
            repo.git.checkout(git_ref)
        except git.exc.CheckoutError:
            LOG.error('%s: Failed to checkout %s', name, git_ref)
            return result
    LOG.info('%s: Repository has been cloned', name)
    result.update(status=STATUSES['fetch_succeeded'])
    return result


def _get_summary(fetch_info):
    LOG.info('#' * 50)
    LOG.info('Summary:')
    fetch_succeeded = [info['name'] for info in fetch_info
                       if info['status'] == 'Success']
    fetch_failed = [info['name'] for info in fetch_info
                    if info['status'] == 'Failure']
    fetch_alredy_existed = [info['name'] for info in fetch_info
                            if info['status'] == 'AlreadyExist']
    if fetch_succeeded:
        LOG.info('%d repository(s) cloning succeeded: %s' % (
            len(fetch_succeeded), ', '.join(fetch_succeeded)))
    if fetch_alredy_existed:
        LOG.info('%d repository(s) is(are) already cloned: %s' % (
            len(fetch_alredy_existed), ', '.join(fetch_alredy_existed)))
    if fetch_failed:
        LOG.info('%d repository(s) cloning failed: %s' % (
            len(fetch_failed), ', '.join(fetch_failed)))
    LOG.info('#' * 50)
    if fetch_failed:
        raise Exception("Failed to fetch %d repos" % len(fetch_failed))


def fetch_repositories(repository_defs=None):
    if repository_defs is None:
        repository_defs = CONF.repositories.repos

    LOG.info('Cloning repositories into %s', CONF.repositories.path)

    with futures.ThreadPoolExecutor(
            max_workers=CONF.repositories.clone_concurrency) as executor:
        future_list = []
        try:
            for repository_def in repository_defs:
                future_list.append(executor.submit(
                    fetch_repository, repository_def
                ))

            fetch_statuses = []
            for future in future_list:
                # we need to use timeout because in this case python
                #  thread wakes up time to time to check timeout and don't
                #  block signal processing
                fetch_statuses.append(future.result(timeout=FETCH_TIMEOUT))
        except SystemExit:
            for future in future_list:
                future.cancel()
            raise
    _get_summary(fetch_statuses)
