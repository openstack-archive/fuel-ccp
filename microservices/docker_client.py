import docker
import os
from docker.utils import kwargs_from_env

def get():
    return docker.Client(**kwargs_from_env(assert_hostname=False))
