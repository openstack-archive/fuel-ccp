#!/bin/bash

# Simple script to deploy local registry
# Usage:
#       ./deploy-registry.sh
#       or
#       ./deploy-registry.sh <k8s_server:k8s_port>
# registry will be exposed on port 31500 at every node


KUBE_CMD=`which kubectl`

if [ -z $KUBE_CMD ]; then
    echo "kubectl not found"
    exit 1
fi

if [ $# -ne 0 ];then
  SRV_OPT=" -s $1 "
fi

$KUBE_CMD create $SRV_OPT -f registry-pod.yaml
if [ $? -ne 0 ]; then
    exit
fi

$KUBE_CMD create $SRV_OPT -f registry-service.yaml
if [ $? -ne 0 ]; then
    exit
fi

# Waiting for status Running
while true; do
    echo "Waiting for 'Running' status"
    $KUBE_CMD describe pod registry | grep -q "Status:.*Running"
    if [ $? -eq 0 ]; then
        break
    fi
    sleep 3

done

# Waiting for readiness
while true; do
    echo "Waiting for 'Ready' condition"
    EXIT_LOOP=1
    for STATUS in `${KUBE_CMD} describe pod registry | grep  Ready | tr -d ':' | awk '{print $2}'`;
    do
        if [ "$STATUS" != "True" ]
        then
            EXIT_LOOP=0
        fi
    done

    if [ "$EXIT_LOOP" -eq 1 ]; then
        break
    fi
    sleep 1
done

echo "Registy service is done"
