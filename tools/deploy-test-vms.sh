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

function get_pods {
    kubectl get pod -n "$K8S_NAMESPACE" --show-all -o template --template="
        {{ range .items -}}
            {{ .metadata.name }}
        {{ end }}"
}

function get_containers {
    local pod_name="$1"
    kubectl get pod -n "$K8S_NAMESPACE" "$pod_name" -o template --template="
        {{ range .spec.containers }}
            {{ .name }}
        {{ end }}"
}


create() {
    if [ -z "${NUMBER}" ]; then
        NUMBER=2
    fi

    curl -o /tmp/cirros.img http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img
    openstack image create --disk-format qcow2 --public --file /tmp/cirros.img cirros
    rm -f /tmp/cirros.img
    NETID="$(openstack network show int-net -f value -c id)"
    openstack server create --flavor m1.tiny --image cirros --nic net-id="$NETID" --min $NUMBER --max $NUMBER --wait test_vm
    openstack server list

    for pod in $(get_pods); do
        for cont in $(get_containers "$pod"); do
            echo "\n\n\n\n\n>>> Logs for $pod $cont"
            kubectl -n "$K8S_NAMESPACE" logs "$pod" "$cont"
        done
    done
    
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

while getopts ":a:n:k:h" opt; do
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
