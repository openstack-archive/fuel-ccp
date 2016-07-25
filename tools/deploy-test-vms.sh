#!/bin/bash

# Simple script, which is going to create network, flavor, download cirros
# image and launch some VMs. Could be used for test purposes.
set -e

if [ -z "$1" ]; then
  echo "You must pass number of VMs as a first arg"
  exit 1
fi

# Check if needed vars are set
for var in "$OS_PROJECT_DOMAIN_NAME" "$OS_USER_DOMAIN_NAME" "$OS_PROJECT_NAME"\
 "$OS_USERNAME" "$OS_PASSWORD" "$OS_AUTH_URL" "$OS_IDENTITY_API_VERSION"
do
  if [ -z $var ]; then
    echo "Please make sure you set all needed variables using the openrc file"
    echo -e "Needed vars are:\nOS_PROJECT_DOMAIN_NAME\nOS_USER_DOMAIN_NAME\nOS_PROJECT_NAME\nOS_USERNAME\nOS_PASSWORD\nOS_AUTH_URL\nOS_IDENTITY_API_VERSION"
    exit 1
  fi
done

openstack flavor create --ram 512 --disk 0 --vcpus 1 tiny
openstack network create --provider-network-type vxlan --provider-segment 77 testnetwork
openstack subnet create --subnet-range 192.168.1.0/24 --gateway none --network testnetwork testsubnetwork
curl -o /tmp/cirros.img http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img && \
openstack image create --disk-format qcow2 --public --file /tmp/cirros.img cirros
NETID="$(openstack network list | awk '/testnetwork/ {print $2}')"
openstack server create --flavor tiny --image cirros --nic net-id="$NETID" --min $1 --max $1 --wait test_vm
openstack server list
