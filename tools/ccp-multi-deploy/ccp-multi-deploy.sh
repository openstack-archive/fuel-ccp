#!/bin/bash -ex
#
# This script semit-automates deployment of multiple OpenStack environemtns
# within sinlge K8s cluster using mcp/ccp tool.
# This is PoC.
#
# (c) mzawadzki@mirantis.com

# Config:
NUMBER_OF_ENVS=3  # Requires 3 K8s nodes per env
BUILD_IMAGES=true # Set to true if run for the first time
NAMESPACE_PREFIX="ccp"
: ${CONFIG_DIR:="`pwd`/config"}
TMP_DIR=$(mktemp --directory --tmpdir ccp-tmp-XXX)

# Functions:
function ccp_wait_for_deployment_to_finish {
    until kubectl --namespace $1 get jobs | awk '$3 ~ 0 {print}' | wc -l | grep "^0$"
    do
        echo "Waiting for jobs to finish..."
        sleep 1m
	set +e
    done
    echo "...................................."
    echo "Jobs and pods in namespace: $1"
    kubectl --namespace $1 get jobs
    kubectl --namespace $1 get pods
    echo "openrc file: openrc-$1"
    cat openrc-$1
    echo "...................................."
    set -e
}

function display_horizon_access_info {
	HORIZON_NODEPORT=`kubectl --namespace $1 get service horizon -o yaml | awk '/nodePort: / {print $NF}'`
	echo "To access horizon from you laptop please run:"
	echo "ssh USER@LAB_HOST_IP -L 18080:127.0.0.1:18080 ssh -L8080:NODE1_IP:${HORIZON_NODEPORT} vagrant@NODE1_IP"
}

function run_openstack_tests {
	source $1
	${TMP_DIR}/fuel-ccp/tools/deploy-test-vms.sh -a create
	# FIXME(mzawadzki): workaround for some minor error during networking destroy (minor b/c it works manually)
	${TMP_DIR}/fuel-ccp/tools/deploy-test-vms.sh -a destroy || true
}


# Check some basic requirements:
which git virtualenv kubectl || exit 1
groups | grep docker || exit 1
if [ `kubectl get nodes | grep node | wc -l` -lt $(($NUMBER_OF_ENVS * 3)) ];
then
	echo "Your K8s cluster is too small, you need NUMBER_OF_ENVS * 3 nodes."
	exit 1
fi


# Clone and install CCP + tools:
cd ${TMP_DIR}
virtualenv ccp-venv
source ccp-venv/bin/activate
pip install python-openstackclient
git clone https://git.openstack.org/openstack/fuel-ccp
cd fuel-ccp
# FIXME(mzawadzki): apply patches for namespace support:
pip install -U .


# Fetch CCP repos
CCP="ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-config-1.yaml"
${CCP} fetch


# Create internal Docker registry for CCP,
# build and push CCP images:
if [ ${BUILD_IMAGES} = true ];
then
	kubectl delete pod registry || true
	kubectl delete service registry || true
	sleep 10
	kubectl create -f ${CONFIG_DIR}/registry-pod.yaml
	kubectl create -f ${CONFIG_DIR}/registry-service.yaml
	${CCP} build
fi


# Deploy envs:
cd ${CONFIG_DIR}
for n in $(seq 1 ${NUMBER_OF_ENVS}) 
do
	CCP="ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-config-${n}.yaml"
	${CCP} deploy
	ccp_wait_for_deployment_to_finish ${NAMESPACE_PREFIX}-${n}
	display_horizon_access_info ${NAMESPACE_PREFIX}-${n}
	run_openstack_tests openrc-${NAMESPACE_PREFIX}-${n}
	echo "CCP cleanup command: ccp --debug --config-file ${CONFIG_DIR}/ccp-cli-config-${n} cleanup"
done


# Cleanup:
deactivate
rm -rf ${TMP_DIR}
