#!/bin/bash
#
# Sample script to deploy env, please adjust to your needs.

set -ex
export ENV_NAME="kargo-test-9-nodes-new"
export IMAGE_PATH="/home/ubuntu/packer-ubuntu-1604-server-big.qcow2" # path to VM image file built in previous step
export DONT_DESTROY_ON_SUCCESS=1
#export VLAN_BRIDGE="vlan456" # full name e.g. "vlan450"
export DEPLOY_METHOD="kargo"
export SLAVES_COUNT=9
export SLAVE_NODE_MEMORY=6144
export SLAVE_NODE_CPU=2
export WORKSPACE="/home/ubuntu/workspace"
export CUSTOM_YAML='hyperkube_image_repo: "quay.io/coreos/hyperkube"
hyperkube_image_tag: "v1.4.0_coreos.1"
kube_version: "v1.4.0"'
mkdir -p $WORKSPACE
echo "Running on $NODE_NAME: $ENV_NAME"
cd /home/ubuntu/fuel-ccp-installer
bash -x "./utils/jenkins/run_k8s_deploy_test.sh"
