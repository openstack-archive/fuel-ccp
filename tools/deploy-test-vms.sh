#!/bin/bash -x

# Simple script, which is going to create network, flavor, download cirros
# image and launch some VMs. Could be used for test purposes.
set -e

usage() {
    cat << EOF
    Usage: $0 -a (create|destroy) [-c] [-n NUBER_OF_VMs] [-i PUBLIC_ETH_IFACE]

    -h   Prints this help
    -a   Required action. Choise from "create" and "destroy"
    -n   Number of VMs to spawn (optional)
    -k   Kubernetes namespace (optional)
    -i   Image to boot VMs from (optional, will upload Cirros if ommited)
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
    if [ -z "${NUMBER}" ]; then
        NUMBER=2
    fi

    if [ -z "${IMAGE}" ]; then
        IMAGE=cirros
        curl -o /tmp/cirros.img http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img
        openstack image create --disk-format qcow2 --public --file /tmp/cirros.img cirros
        rm -f /tmp/cirros.img
    fi
    NETID="$(openstack network show int-net -f value -c id)"
    openstack server create --flavor m1.tiny --image "${IMAGE}" --nic net-id="$NETID" --min $NUMBER --max $NUMBER --wait test_vm
    openstack server list
    for vm in $(openstack server list -f value -c Name | grep test_vm); do
        echo "Console for $vm:"
        openstack console url show $vm
    done
}

destroy() {
    for vm in $(openstack server list -f value -c Name | grep test_vm); do
        echo "Destroying $vm..."
        openstack server delete --wait $vm
    done
    echo "Destroying cirros image..."
    openstack image delete cirros
}

while getopts ":a:n:k:i:h" opt; do
    case $opt in
        a)
            ACTION="$OPTARG"
            ;;
        n)
            NUMBER="$OPTARG"
            ;;
        k)
            K8S_NAMESPACE="$OPTARG"
            ;;
        i)
            IMAGE="$OPTARG"
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
