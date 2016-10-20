#!/bin/bash

# Simple script, which is going to create network, flavor, download cirros
# image and launch some VMs. Could be used for test purposes.
set -e

usage() {
    cat << EOF
    Usage: $0 -a (create|destroy) [-c] [-n NUBER_OF_VMs] [-i PUBLIC_ETH_IFACE]

    -h   Prints this help
    -a   Required action. Choise from "create" and "destroy"
    -c   Calico networking insted of OVS
    -n   Number of VMs to spawn. (optional)
    -i   Public eth iface. (optional)
EOF
}

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


create() {
    if [ -z "$NUMBER" ]; then
        NUMBER=2
    fi
    if [ -z "$IFACE" ]; then
        IFACE="eth1"
    fi
    # Check if iface is exist
    if ! ip a show up | fgrep -q $IFACE ; then
        echo "Cant find $IFACE in the list of working interfaces"
        usage
        exit 1
    fi
    EXTIP="`ifconfig $IFACE | grep -Po 'addr:\d+\.\d+\.\d+\.\d+' | awk -F':' '{print $NF}'`"
    VNCP="`kubectl get svc nova-novncproxy -o yaml | awk '/nodePort/ {print $NF}'`"

    if [ "$CALICO" == "True" ]; then
        openstack network create --provider-network-type local testnetwork
    else
        openstack network create --provider-network-type vxlan --provider-segment 77 testnetwork
    fi
    openstack subnet create --subnet-range 192.168.1.0/24 --gateway 192.168.1.1 --network testnetwork testsubnetwork
    openstack flavor create --ram 512 --disk 0 --vcpus 1 tiny
    curl -o /tmp/cirros.img http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img && \
    openstack image create --disk-format qcow2 --public --file /tmp/cirros.img cirros
    rm -f /tmp/cirros.img
    NETID="$(openstack network list | awk '/testnetwork/ {print $2}')"
    openstack server create --flavor tiny --image cirros --nic net-id="$NETID" --min $NUMBER --max $NUMBER --wait test_vm
    openstack server list
    for vm in $(openstack server  list | awk '/test_vm/ {print $4}'); do
        echo "Console for $vm:"
        openstack console url show $vm | sed "s/nova-novncproxy\..*:6080/${EXTIP}:${VNCP}/"
    done
}

destroy() {
    for vm in $(openstack server  list | awk '/test_vm/ {print $4}'); do
        echo "Destroying $vm..."
        openstack server delete $vm
    done
    echo "Destroying testnetwork..."
    openstack network delete testnetwork
    echo "Destroying tiny flavor..."
    openstack flavor delete tiny
    echo "Destroying cirros image..."
    openstack image delete cirros
}

while getopts ":a:n:i:hc" opt; do
    case $opt in
        a)
            ACTION="$OPTARG"
            ;;
        c)
            CALICO="True"
            ;;
        n)
            NUMBER="$OPTARG"
            ;;
        i)
            IFACE="$OPTARG"
            ;;
        h)
            usage
            exit 1
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "$ACTION" ]; then
    usage
    exit 1
elif [ "$ACTION" = "create" ]; then
    create
elif [ "$ACTION" = "destroy" ]; then
    destroy
else
    echo "Wrong action: ${ACTION}. Please choose from "create" and "destroy""
    exit 1
fi
