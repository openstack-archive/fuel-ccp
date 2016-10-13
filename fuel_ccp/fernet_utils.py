import base64
from cryptography import fernet
import os
import subprocess
import yaml

import pykube

from fuel_ccp import config
from fuel_ccp import kubernetes

CONF = config.CONF


def get_secret():
    client = kubernetes.get_client()
    secret = pykube.Secret.objects(client).filter(namespace='ccp')
    return secret.get_by_name(CONF.fernet.secret_name)


def fernet_rotate():
    secret = get_secret()

    # Remove annotations if exists to prevent errors with kubectl apply
    try:
        secret.obj.pop('annotations')
    except Exception:
        pass

    keys = secret.obj.get('data')
    if keys is None:
        initialize_key_repository()
        return

    data = _rotate_keys(secret.obj['data'])
    secret.obj['data'] = data
    _kubectl_apply(secret.obj)


def initialize_key_repository():
    keys = dict()
    null_key = _create_new_key()
    keys['0'] = null_key.encode('utf-8')
    keys = _rotate_keys(keys)

    secret = get_secret()
    secret.obj['data'] = keys
    secret.update()


def _kubectl_apply(secret_config):
    with open('/tmp/fernet-keys-secret.yaml', 'w') as outfile:
        yaml.dump(secret_config, outfile)

    # TODO(mnikolaenko): whether this can be done using pykube?
    command = 'kubectl apply -f /tmp/fernet-keys-secret.yaml'
    p = subprocess.Popen(command.split())
    p.wait()

    if os.path.exists('/tmp/fernet-keys-secret.yaml'):
        os.remove('/tmp/fernet-keys-secret.yaml')


def _create_new_key():
    key = fernet.Fernet.generate_key().encode('utf-8')
    # files in secret must be base64 encoded
    key = base64.b64encode(key)
    return key.encode('utf-8')


def _rotate_keys(keys):
    number_keys = keys.keys()
    sorted(number_keys, key=int)
    current_primary_key = number_keys[-1]
    new_primary_key = str(int(current_primary_key) + 1)
    keys[new_primary_key] = keys['0']
    number_keys = list(number_keys)
    number_keys.append(new_primary_key)

    old_keys_amount = len(number_keys) - CONF.fernet.max_active_keys

    # purge excess keys
    for i in range(1, old_keys_amount + 1):
        keys.pop(number_keys[i])

    keys['0'] = _create_new_key()

    return keys
