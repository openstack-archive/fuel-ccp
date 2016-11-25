#!/bin/bash -x

# Simple script, which is going to create network, flavor, download cirros
# image and launch some VMs. Could be used for test purposes.
set -e

usage() {
    cat << EOF
    Usage: $0 -a (create|destroy) [-n NUBER_OF_VMs] [-i IMAGE] [-f]

    -h   Prints this help
    -a   Required action. Choise from "create" and "destroy"
    -n   Number of VMs to spawn (optional)
    -k   Kubernetes namespace (optional)
    -i   Image to boot VMs from (optional, will upload Cirros if ommited)
    -f   Allocate floating IPs and associate with VMs (optional)
    -d   Print debug to stdout
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

vm_error_logs() {
    for v in `openstack server list -f value | awk '/ERROR/ { print $1 }'`; do
        echo "-------------- ${f} ---------------"
        set +e
        kubectl --namespace "${K8S_NAMESPACE}" logs "${f}" | grep "${v}"
        set -e
    done
}

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
    if [ -n "${ADD_FLOATING}" ]; then
        for vm in $(openstack server list -f value -c Name | grep test_vm); do
            floating_ip="$(openstack floating ip create -f value -c floating_ip_address ext-net)"
            openstack server add floating ip "$vm" "$floating_ip"
        done
    fi
    openstack server list
    if [ -z "${K8S_NAMESPACE}" ]; then
        K8S_NAMESPACE=`kubectl get ns | awk '/ccp/ {print $1}'`
    fi
    if openstack server list | grep ERROR; then
        echo "Error while creating vm"
        if [ -n "${PRINT_STD}" ]; then
            for f in `kubectl --namespace=${K8S_NAMESPACE} get pods -o go-template --template="{{ range .items }}{{ println .metadata.name}}{{end}}"`; do
                vm_error_logs
            done
        fi
    fi
    for vm in $(openstack server list -f value -c Name | grep test_vm); do
        echo "Console for ${vm}:"
        openstack console url show "${vm}"
    done
}

destroy() {
    for vm in $(openstack server list -f value -c Name | grep test_vm); do
        echo "Destroying $vm..."
        openstack server delete --wait "${vm}"
    done
    echo "Destroying cirros image..."
    openstack image delete cirros
}

while getopts ":a:n:k:i:fhd" opt; do
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
        f)
            ADD_FLOATING="yes"
            ;;
        d)
            PRINT_STD="yes"
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
