#!/bin/bash -ex

# This script is intended to be run from Zuul minion as in OpenStack Infra.

MY_DIR="$(dirname "$(readlink -nf "$0")")"
: ${WORKSPACE:=${MY_DIR}}
CONFIG_FILE="${WORKSPACE}/config.yaml"

tee "${CONFIG_FILE}" <<EOF
debug: True
repositories:
  path: "${WORKSPACE}"
EOF

tox -e venv -- ccp --config-file "${CONFIG_FILE}" config dump
tox -e venv -- ccp --config-file "${CONFIG_FILE}" validate
