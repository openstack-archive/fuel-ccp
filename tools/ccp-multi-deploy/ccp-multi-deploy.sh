#!/bin/bash -ex
#
# This script semit-automates deployment of multiple OpenStack environemtns
# within single K8s cluster using mcp/ccp tool.
# This is PoC.
#
# (c) mzawadzki@mirantis.com


# Config:
NUMBER_OF_ENVS=3  # Requires 3 K8s nodes per env
BUILD_IMAGES=true # Set to true if run for the first time
NAMESPACE_PREFIX="ccp"
: ${CONFIG_DIR:="`pwd`/tools/ccp-multi-deploy/config"}
TMP_DIR=$(mktemp --directory --tmpdir ccp-tmp-XXX)


# Functions:
function ccp_wait_for_deployment_to_finish {
    set +x
    until kubectl --namespace $1 get jobs | awk '$3 ~ 0 {print}' | wc -l | grep "^0$"; do
        echo "Waiting for jobs to finish..."
        sleep 1m
    done
    echo "...................................."
    echo "Jobs and pods in namespace: $1"
    kubectl --namespace $1 get jobs
    kubectl --namespace $1 get pods
    echo "openrc file: openrc-$1"
    cat openrc-$1
    echo "...................................."
    set -x
}

function display_horizon_access_info {
    HORIZON_NODEPORT=`kubectl --namespace $1 get service horizon -o yaml | awk '/nodePort: / {print $NF}'`
    echo "Hint - to access horizon from your workstation please run:"
    echo "ssh USER@LAB_HOST_IP -L 18080:127.0.0.1:18080 ssh -L8080:NODE1_IP:${HORIZON_NODEPORT} vagrant@NODE1_IP"
}

function run_openstack_tests {
    source $1
    ${TMP_DIR}/fuel-ccp/tools/deploy-test-vms.sh -a create
    # FIXME(mzawadzki): workaround for some minor error during networking destroy (minor b/c it works manually)
    ${TMP_DIR}/fuel-ccp/tools/deploy-test-vms.sh -a destroy || true
}


# Check some basic requirements and exit explicitly if they are not met:
which git virtualenv tox kubectl || exit 1
groups | grep docker || exit 1
if [ `kubectl get nodes | grep node | wc -l` -lt $(($NUMBER_OF_ENVS * 3)) ]; then
    echo "Your K8s cluster is too small, you need NUMBER_OF_ENVS * 3 nodes."
    exit 1
fi


# Clone and install CCP + tools:
pushd ${TMP_DIR}
git clone https://git.openstack.org/openstack/fuel-ccp
pushd fuel-ccp
# Ensure newest version of openstackclient
tox -e venv -- pip install python-openstackclient
tox -e venv -- pip install -U .
popd
popd


# Fetch CCP repos
CCP="tox -e venv -- ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-config-1.yaml"
${CCP} fetch


# Create internal Docker registry for CCP,
# build and push CCP images:
if [ ${BUILD_IMAGES} = true ]; then
    kubectl delete pod registry || true
    kubectl delete service registry || true
    sleep 10
    pushd ${TMP_DIR}/fuel-ccp/tools/registry
    ./deploy-registry.sh -n default
    popd
    ${CCP} build
fi


# Deploy envs:
for n in $(seq 1 ${NUMBER_OF_ENVS}); do
    CCP="tox -e venv -- ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-config-${n}.yaml"
    ${CCP} deploy
    ccp_wait_for_deployment_to_finish ${NAMESPACE_PREFIX}-${n}
    display_horizon_access_info ${NAMESPACE_PREFIX}-${n}
    run_openstack_tests openrc-${NAMESPACE_PREFIX}-${n}
    echo "CCP cleanup command: ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-config-${n} cleanup"
done


# Cleanup:
rm -rf ${TMP_DIR}
