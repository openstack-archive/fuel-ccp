#!/bin/bash
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
export CUSTOM_YAML='hyperkube_image_repo: "artifactory.mcp.mirantis.net:5002/hyperkube-amd64"
hyperkube_image_tag: "v1.5.0-alpha.0-397-gfb58d_81"
upstream_dns_servers: [172.18.176.6, 172.18.16.10]
nameservers: [8.8.8.8, 172.18.176.6]
searchdomains: [mcp.mirantis.net, mirantis.net]
use_hyperkube_cni: true'
mkdir -p $WORKSPACE
echo "Running on $NODE_NAME: $ENV_NAME"
cd /home/ubuntu/fuel-ccp-installer
bash -x "./utils/jenkins/run_k8s_deploy_test.sh"
