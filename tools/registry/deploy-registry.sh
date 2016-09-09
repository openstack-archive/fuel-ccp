#!/bin/bash

set -e

function usage {
    local base_name=$(basename $0)
    echo "Usage:"
    echo "  $base_name -s <address>"
    echo "  $base_name -n <namespace>"
}

NAMESPACE_OPT=" --namespace kube-system"

while getopts "s:n:" opt; do
    case $opt in
        "s" )
            SRV_OPT=" -s $OPTARG"
            ;;
        "n" )
            NAMESPACE_OPT=" --namespace $OPTARG"
            ;;
        * )
            usage
            exit 1
            ;;
    esac
done

which kubectl 1>/dev/null

function kube_cmd {
    kubectl $SRV_OPT $NAMESPACE_OPT "$@"
}

workdir=$(dirname $0)

kube_cmd create -f $workdir/registry-pod.yaml
kube_cmd create -f $workdir/registry-service.yaml

# Waiting for status Running
while true; do
    echo "Waiting for 'Running' state"
    cont_running=$(kube_cmd get pod registry -o template --template="{{ .status.phase }}")
    if [ "$cont_running" == "Running" ]; then
        break
    fi
    sleep 3
done

# Waiting for readiness
while true; do
    echo "Waiting for 'Ready' condition"
    cont_ready=$(kube_cmd get pod registry -o template --template="{{ range.status.containerStatuses }}{{ .ready }}{{ end }}")
    if [ "$cont_ready" == "true" ]; then
        break
    fi
    sleep 3
done

echo "Registy service is ready"
