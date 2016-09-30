#!/bin/bash -ex

# WIP

CUSTOM_NAMESPACE="ccp-1"
SSH_OPTIONS="-o StrictHostKeyChecking=no -o UserKnownhostsFile=/dev/null"
sudo sed -i "s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/" /etc/resolv.conf
ssh $SSH_OPTIONS node2 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
exit
ssh $SSH_OPTIONS node3 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
ssh $SSH_OPTIONS node4 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
ssh $SSH_OPTIONS node5 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
ssh $SSH_OPTIONS node6 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
ssh $SSH_OPTIONS node7 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
ssh $SSH_OPTIONS node8 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
ssh $SSH_OPTIONS node9 sudo sed -i \'s/search default/search ${CUSTOM_NAMESPACE}.svc.cluster.local default/\' /etc/resolv.conf
