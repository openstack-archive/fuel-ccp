#!/bin/bash

# Simple script to deploy local registry
# Usage:
#       ./deploy-registry.sh
#       or
#       ./deploy-registry.sh <k8s_server:k8s_port>
# registry will be exposed on port 31500 at every node


KUBE_CMD=`which kubectl`

set -e

if [ -z $KUBE_CMD ]; then
    echo "kubectl not found"
    exit 1
fi

if [ $# -ne 0 ];then
  SRV_OPT=" -s $1 "
fi

$KUBE_CMD create $SRV_OPT -f registry-pod.yaml
$KUBE_CMD create $SRV_OPT -f registry-service.yaml
