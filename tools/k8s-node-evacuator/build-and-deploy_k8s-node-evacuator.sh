#!/bin/bash
#
# This script builds Docker container and deploys in a Kubernetes pod
# a simple daemon to handle Kubernetes node evacuation.
# When "unschedulable" event is detected nova-compute service is disabled
# on the node and all VMs are live-migrated away.

set -ex

function usage {
    set +x
    local base_name=$(basename $0)
    echo "Usage (all parameters are optional):"
    echo "  $base_name -s <k8s_api_server_address>"
    echo "  $base_name -n <k8s namespace to deploy pod in>"
    echo "  $base_name -i <node_to_deploy_on>"
    echo "  $base_name -r <Docker registry host:port>"
    echo "  $base_name -k <Docker registry namsespace>"
    set -x
}

NAMESPACE_OPT=" --namespace kube-system"
DOCKER_REGISTRY_HOST_PORT="127.0.0.1:31500"
DOCKER_REGISTRY_NAMESPACE="ccp"

while getopts "s:n:i:r:k:" opt; do
    case $opt in
        "s" )
            SRV_OPT=" -s ${OPTARG}"
            ;;
        "n" )
            NAMESPACE_OPT=" --namespace ${OPTARG}"
            ;;
        "i" )
            NODE="${OPTARG}"
            ;;
        "r" )
            DOCKER_REGISTRY_HOST_PORT="${OPTARG}"
            ;;
        "k" )
            DOCKER_REGISTRY_NAMESPACE="${OPTARG}"
            ;;
        * )
            usage
            exit 1
            ;;
    esac
done

which kubectl 1> /dev/null
function kube_cmd {
    kubectl ${SRV_OPT} ${NAMESPACE_OPT} "$@"
}

if [ -z "${NODE}" ]; then
    NODE=$(kube_cmd get nodes -o template --template="{{ with index .items 0 }}{{ .metadata.name }}{{ end }}")
    echo "K8S node was not specified, using ${NODE}"
fi

kube_cmd label node "${NODE}" app=k8s-node-evacuator --overwrite

workdir=$(dirname $0)
pushd ${workdir}

echo "Preparing Dockerfile:"
sed -i "s/DOCKER_REGISTRY_HOST_PORT_CHANGE_ME/${DOCKER_REGISTRY_HOST_PORT}/" Dockerfile
sed -i "s/DOCKER_REGISTRY_NAMESPACE_CHANGE_ME/${DOCKER_REGISTRY_NAMESPACE}/" Dockerfile

echo "Building Docker image:"
docker build -t k8s-node-evacuator .
docker tag k8s-node-evacuator "${DOCKER_REGISTRY_HOST_PORT}"/"${DOCKER_REGISTRY_NAMESPACE}"/k8s-node-evacuator
docker push "${DOCKER_REGISTRY_HOST_PORT}"/"${DOCKER_REGISTRY_NAMESPACE}"/k8s-node-evacuator

echo "Setting variables in pod yaml file:"
POD_YAML_FILE="k8s-node-evacuator-pod.yaml"
sed -i "s/DOCKER_REGISTRY_HOST_PORT_CHANGE_ME/${DOCKER_REGISTRY_HOST_PORT}/" ${POD_YAML_FILE}
sed -i "s/DOCKER_REGISTRY_NAMESPACE_CHANGE_ME/${DOCKER_REGISTRY_NAMESPACE}/" ${POD_YAML_FILE}
sed -i "s/OS_USER_DOMAIN_NAME_CHANGE_ME/${OS_USER_DOMAIN_NAME}/" ${POD_YAML_FILE}
sed -i "s/OS_PROJECT_NAME_CHANGE_ME/${OS_PROJECT_NAME}/" ${POD_YAML_FILE}
sed -i "s/OS_IDENTITY_API_VERSION_CHANGE_ME/\"${OS_IDENTITY_API_VERSION}\"/" ${POD_YAML_FILE}
sed -i "s/OS_PASSWORD_CHANGE_ME/${OS_PASSWORD}/" ${POD_YAML_FILE}
sed -i "s#OS_AUTH_URL_CHANGE_ME#${OS_AUTH_URL}#" ${POD_YAML_FILE}
sed -i "s/OS_USERNAME_CHANGE_ME/${OS_USERNAME}/" ${POD_YAML_FILE}
sed -i "s/OS_PROJECT_DOMAIN_NAME_CHANGE_ME/${OS_PROJECT_DOMAIN_NAME}/" ${POD_YAML_FILE}

echo "Deploying  k8s-node-evacuator pod:"
kube_cmd create -f k8s-node-evacuator-pod.yaml

# Waiting for status Running
while true; do
    echo "Waiting for 'Running' state..."
    cont_running=$(kube_cmd get pod k8s-node-evacuator -o template --template="{{ .status.phase }}")
    if [ "${cont_running}" == "Running" ]; then
        break
    fi
    sleep 3
done

echo "k8s-node-evacuator is ready."
