#!/bin/bash

set -e

# Simple script to deploy local registry
# Usage:
#       ./deploy-registry.sh
#       or
#       ./deploy-registry.sh <k8s_server:k8s_port>
# registry will be exposed on port 31500 at every node


KUBE_CMD="kubectl"

if [ -x ./kubectl ];then
    KUBE_CMD="./kubectl"
elif ! type "kubectl" > /dev/null; then
    wget "https://storage.googleapis.com/kubernetes-release/release/v1.2.6/bin/linux/amd64/kubectl"
    chmod +x kubectl
    KUBE_CMD="./kubectl"
fi

if [ $# -ne 0 ];then
  SRV_OPT=" -s $1 "
fi


$KUBE_CMD create $SRV_OPT -f registry-pod.yaml
$KUBE_CMD create $SRV_OPT -f registry-service.yaml
