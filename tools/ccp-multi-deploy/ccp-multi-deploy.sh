#!/bin/bash
#
# This script semit-automates deployment of multiple OpenStack environemtns
# within single K8s cluster using mcp/ccp tool.
# This is PoC.
# Usage: tox -e multi-deploy -- --help
#
# (c) mzawadzki@mirantis.com


set -e
# Config (defaults):
NUMBER_OF_ENVS=1  # Requires 3 K8s nodes per env
BUILD_IMAGES=true # Set to true if run for the first time
: ${CONFIG_DIR:="tools/ccp-multi-deploy/config"}
: ${VERSION:="master"}
NAMESPACE_PREFIX="ccp-${VERSION}"

# Functions:
function usage {
    cat <<EOF
Usage: $0 [OPTION]
Deploy multiple OpenStack environments with fuel-ccp.
Options:
-h, --help
        print usage and exit
-n, --number-of-envs=NUMBER
        deploy NUMBER of parallel environments (default: 1)
-s, --skip-building-images
        do not build Docker images for OpenStack services
        (rely on existing local registry, default: false)
-v, --openstack-version=VERSION
        set openstack version newton or master (default: master)
EOF
    exit
}

function ccp_wait_for_deployment_to_finish {
    until kubectl --namespace $1 get jobs | awk '$3 ~ 0 {print}' | wc -l | grep "^0$"; do
        echo "Waiting for jobs to finish..."
        sleep 1m
    done
    echo "...................................."
    echo "Jobs and pods in namespace: $1"
    kubectl --namespace $1 get jobs
    kubectl --namespace $1 get pods
    echo "openrc file: openrc-$1"
    cat openrc-${1}
    echo "...................................."
}

function display_horizon_access_info {
    HORIZON_NODEPORT=`kubectl --namespace $1 get service horizon -o yaml | awk '/nodePort: / {print $NF}'`
    echo "Hint - to access horizon from your workstation please run:"
    echo "ssh USER@LAB_HOST_IP -L 18080:127.0.0.1:18080 ssh -L8080:NODE1_IP:${HORIZON_NODEPORT} vagrant@NODE1_IP"
}

function run_openstack_tests {
    source $1
    ./tools/deploy-test-vms.sh -a create
    ./tools/deploy-test-vms.sh -a destroy
}


# Parse command line arguments:
OPTS=`getopt -o 'hsn:v:' --long help,skip-building-images,number-of-envs:,openstack-version: -n 'parse-options' -- ${@}`
if [ ${?} != 0 ] ; then
    echo "Failed parsing options."
    exit 1
fi
eval set -- ${OPTS}

while true; do
    case ${1} in
        -h|--help ) usage; shift ;;
        -n|--number-of-envs ) NUMBER_OF_ENVS=${2}; shift; shift ;;
        -s|--skip-building-images ) BUILD_IMAGES=false; shift ;;
        -v|--openstack-version ) VERSION="${2}"; NAMESPACE_PREFIX="ccp-${2}"; shift; shift ;;
        -- ) shift; break ;;
        * ) break ;;
    esac
done


# Check some basic requirements and exit explicitly if they are not met:
if [ ! -f "${CONFIG_DIR}/ccp-cli-${VERSION}-config-1.yaml" ]; then
    echo "Config file not found, did you set CONFIG_DIR correctly?"
    exit 1
fi
which kubectl || exit 1
groups | grep docker || exit 1
if [ `kubectl get nodes | grep node | wc -l` -lt $(($NUMBER_OF_ENVS * 3)) ]; then
    echo "Your K8s cluster is too small, you need NUMBER_OF_ENVS * 3 nodes."
    exit 1
fi


# Fetch CCP repos
CCP="ccp --verbose --debug --config-file ${CONFIG_DIR}/ccp-cli-${VERSION}-config-1.yaml"
${CCP} fetch


# Create internal Docker registry for CCP,
# build and push CCP images:
if [ "${BUILD_IMAGES}" = "true" ]; then
    kubectl delete pod registry || true
    kubectl delete service registry || true
    ./tools/registry/deploy-registry.sh -n default
    ${CCP} build
fi


# Deploy envs:
for n in $(seq 1 ${NUMBER_OF_ENVS}); do
    CCP="ccp --verbose --debug --config-file ${CONFIG_DIR}/ccp-cli-${VERSION}-config-${n}.yaml"
    ${CCP} deploy
    ccp_wait_for_deployment_to_finish ${NAMESPACE_PREFIX}-${n}
    display_horizon_access_info ${NAMESPACE_PREFIX}-${n}
    run_openstack_tests openrc-${NAMESPACE_PREFIX}-${n}
    echo "CCP cleanup command: ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-${VERSION}-config-${n} cleanup"
done
