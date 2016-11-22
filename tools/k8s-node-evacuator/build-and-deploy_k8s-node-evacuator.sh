#!/bin/bash

set -e

function usage {
    local base_name=$(basename $0)
    echo "Usage:"
    echo "  $base_name -s <address>"
    echo "  $base_name -n <namespace>"
    echo "  $base_name -i <node>"
}

NAMESPACE_OPT=" --namespace kube-system"

while getopts "s:n:i:" opt; do
    case $opt in
        "s" )
            SRV_OPT=" -s $OPTARG"
            ;;
        "n" )
            NAMESPACE_OPT=" --namespace $OPTARG"
            ;;
        "i" )
            NODE="$OPTARG"
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

if [ -z $NODE ]; then
    NODE=$(kubectl get nodes -o template --template="{{ with index .items 0 }}{{ .metadata.name }}{{ end }}")
    echo "K8S node is not specified, using $NODE"
fi

kubectl label node $NODE app=k8s-node-evacuator --overwrite

workdir=$(dirname $0)
pushd ${workdir}

echo "Building Docker image:"
docker build -t k8s-node-evacuator .
docker tag k8s-node-evacuator 127.0.0.1:31500/k8s-node-evacuator
docker push 127.0.0.1:31500/k8s-node-evacuator

echo "Setting variables in pod yaml file:"
POD_YAML_FILE="k8s-node-evacuator-pod.yaml"
sed -e "s/OS_USER_DOMAIN_NAME_CHANGE_ME/${OS_USER_DOMAIN_NAME}/" ${POD_YAML_FILE}
sed -e "s/OS_PROJECT_NAME_CHANGE_ME/${OS_PROJECT_NAME}/" ${POD_YAML_FILE}
sed -e "s/OS_IDENTITY_API_VERSION_CHANGE_ME/${OS_IDENTITY_API_VERSION}/" ${POD_YAML_FILE}
sed -e "s/OS_PASSWORD_CHANGE_ME/${OS_PASSWORD}/" ${POD_YAML_FILE}
sed -e "s#OS_AUTH_URL_CHANGE_ME#${OS_AUTH_URL}#" ${POD_YAML_FILE}
sed -e "s/OS_USERNAME_CHANGE_ME/${OS_USERNAME}/" ${POD_YAML_FILE}
sed -e "s/OS_PROJECT_DOMAIN_NAME_CHANGE_ME/${OS_PROJECT_DOMAIN_NAME}/" ${POD_YAML_FILE}
K8S_API_SERVER_URL=`kubectl cluster-info | awk '/Kubernetes master/ {print $NF}'`
sed -e "s#K8S_API_SERVER_URL_CHANGE_ME#${K8S_API_SERVER_URL}#" ${POD_YAML_FILE}

echo "Deploying  k8s-node-evacuator pod:"
kube_cmd create -f k8s-node-evacuator-pod.yaml

# Waiting for status Running
while true; do
    echo "Waiting for 'Running' state..."
    cont_running=$(kube_cmd get pod k8s-node-evacuator -o template --template="{{ .status.phase }}")
    if [ "$cont_running" == "Running" ]; then
        break
    fi
    sleep 3
done

echo "k8s-node-evacuator is ready."
