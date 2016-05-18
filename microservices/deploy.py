import os
import re
import shutil
# TODO(mrostecki): Use python-k8sclient insead of subprocess.
import subprocess
import sys
import tempfile

from oslo_config import cfg
from oslo_log import log as logging

from microservices.common import jinja_utils


CONF = cfg.CONF
CONF.import_group('kubernetes', 'microservices.config.kubernetes')
CONF.import_group('repositories', 'microservices.config.repositories')

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')
YAML_J2_FILE_RE = re.compile(r'\.yaml\.j2$')
J2_FILE_EXTENSION = re.compile(r'\.j2')


def create_rendered_k8s_yaml(k8s_yaml, component, tmp_dir):
    content = jinja_utils.jinja_render(k8s_yaml)

    dest_dir = os.path.join(tmp_dir, component)
    src_file = os.path.basename(k8s_yaml)
    dest_file = J2_FILE_EXTENSION.sub('', src_file)
    full_dest_file = os.path.join(dest_dir, dest_file)

    with open(full_dest_file, 'w') as f:
        f.write(content)

    return full_dest_file


def find_k8s_yamls(component, tmp_dir):
    k8s_yamls = []
    component_dir = os.path.join(CONF.repositories.path, component)

    for root, __, files in os.walk(component_dir):
        matching_files = [os.path.join(root, f)
                          for f in files if YAML_FILE_RE.search(f)]
        k8s_yamls.extend(matching_files)

        matching_j2_files = [os.path.join(root, f)
                             for f in files if YAML_J2_FILE_RE.search(f)]
        rendered_files = [create_rendered_k8s_yaml(j2_file, component, tmp_dir)
                          for j2_file in matching_j2_files]
        k8s_yamls.extend(rendered_files)

    return k8s_yamls


def process_k8s_yaml(k8s_yaml):
    kube_apiserver = CONF.kubernetes.server
    if kube_apiserver:
        cmd = ['kubectl', 'create', '-f', k8s_yaml, '-s', kube_apiserver]
    else:
        cmd = ['kubectl', 'create', '-f', k8s_yaml]
    LOG.info('Executing %r', cmd)
    status = subprocess.call(cmd)
    if status != 0:
        sys.exit(status)


def process_k8s_yamls(k8s_yamls):
    for k8s_yaml in k8s_yamls:
        process_k8s_yaml(k8s_yaml)


def deploy_repositories(components=None):
    if components is None:
        components = CONF.repositories.components

    tmp_dir = tempfile.mkdtemp()

    for component in components:
        os.makedirs(os.path.join(tmp_dir, component))
        k8s_yamls = find_k8s_yamls(component, tmp_dir)
        process_k8s_yamls(k8s_yamls)

    shutil.rmtree(tmp_dir)
