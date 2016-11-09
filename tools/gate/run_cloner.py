from __future__ import print_function

import os
import subprocess
import sys
import tempfile

from six.moves import shlex_quote
from six.moves.urllib import parse as urlparse
import yaml

from fuel_ccp import config


def get_clonemap_and_repos():
    clonemap = []
    repos = []
    base_dest = config.CONF.repositories.path
    for repo_def in config.CONF.repositories.repos:
        path = urlparse.urlparse(repo_def['git_url']).path[1:]
        clonemap.append({
            'dest': os.path.join(base_dest, repo_def['name']),
            'name': path,
        })
        repos.append(path)
    return {'clonemap': clonemap}, repos


def main(config_file, cloner, args):
    config.setup_config(config_file)
    clonemap, repos = get_clonemap_and_repos()
    with tempfile.NamedTemporaryFile('w+') as f:
        yaml.dump(clonemap, f, default_flow_style=False)
        f.flush()
        f.seek(0)
        print("Dumped clonemap at", f.name, ":", file=sys.stderr)
        print(f.read(), file=sys.stderr)
        cmd = [cloner, '-m', f.name] + args + repos
        print("Running command:", ' '.join(map(shlex_quote, cmd)),
              file=sys.stderr)
        subprocess.check_call(cmd)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
