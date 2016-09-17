#!/bin/bash
set -ex

workdir=$(dirname $0)
yamllint -c $workdir/yamllint.yaml $(find . -not -path '*/\.*' -type f -name '*.yaml')
