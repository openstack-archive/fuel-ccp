#!/bin/bash -ex

# This script is intended to be run from Zuul minion as in OpenStack Infra.

MY_DIR="$(dirname "$(readlink -nf "$0")")"
: ${WORKSPACE:=${MY_DIR}}
: ${ZUUL_CLONER:=/usr/zuul-env/bin/zuul-cloner}
CONFIG_FILE="${WORKSPACE}/config.yaml"

tee "${CONFIG_FILE}" <<EOF
debug: True
repositories:
  path: "${WORKSPACE}"
services:
  database:
    service_def: galera
  rpc:
    service_def: rabbitmq
  notifications:
    service_def: rabbitmq
EOF

tox -e venv -- python "${MY_DIR}/run_cloner.py" "${CONFIG_FILE}"  "${ZUUL_CLONER}" --cache-dir /opt/git https://git.openstack.org
tox -e venv -- ccp --config-file "${CONFIG_FILE}" config dump
tox -e venv -- ccp --config-file "${CONFIG_FILE}" validate
