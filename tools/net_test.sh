#!/bin/bash -ex
#
# Basic networking check for K8s, please adjust to your needs.
# Originally adopted from openstack/fuel-ccp-installer
# by kproskurin@mirantis.com


# Configuration:
# e.g. SLAVE_IPS=(node1 node2 node3)
SLAVE_IPS=(changeme)
# e.g. ADMIN_IP=(node1)
ADMIN_IP="changeme"

if [[ "$SLAVE_IPS" == "changeme" || "$ADMIN_IP" == "changeme" ]]; then
    echo "Please set variables SLAVE_IPS and ADMIN_IP."
    exit 1
fi
ADMIN_USER="vagrant"
SSH_OPTIONS="-o StrictHostKeyChecking=no -o UserKnownhostsFile=/dev/null"
kubedns_ip=$(sudo -u vagrant -s ssh $SSH_OPTIONS $ADMIN_USER@$ADMIN_IP kubectl get svc --namespace kube-system kubedns --template={{.spec.clusterIP}})
dnsmasq_ip=$(sudo -u vagrant -s ssh $SSH_OPTIONS $ADMIN_USER@$ADMIN_IP kubectl get svc --namespace kube-system dnsmasq --template={{.spec.clusterIP}})
domain="cluster.local"
internal_test_domain="kubernetes"
external_test_domain="kubernetes.io"
declare -A node_ip_works
declare -A node_internal_dns_works
declare -A node_external_dns_works
declare -A container_dns_works
declare -A container_hostnet_dns_works
failures=0


for node in "${SLAVE_IPS[@]}"; do
    # Check UDP 53 for kubedns
    if sudo -u vagrant -s ssh  $SSH_OPTIONS $ADMIN_USER@$node nc -uzv $kubedns_ip 53 >/dev/null; then
        node_ip_works["${node}"]="PASSED"
    else
        node_ip_works["${node}"]="FAILED"
        (( failures++ ))
    fi
    # Check internal lookup
    if sudo -u vagrant -s ssh  $SSH_OPTIONS $ADMIN_USER@$node nslookup $internal_test_domain $kubedns_ip >/dev/null; then
        node_internal_dns_works["${node}"]="PASSED"
    else
        node_internal_dns_works["${node}"]="FAILED"
        (( failures++ ))
    fi
    # Check external lookup
    if sudo -u vagrant -s ssh  $SSH_OPTIONS $ADMIN_USER@$node nslookup $external_test_domain $dnsmasq_ip >/dev/null; then
        node_external_dns_works[$node]="PASSED"
    else
        node_external_dns_works[$node]="FAILED"
        (( failures++ ))
    fi
    # Check UDP 53 for kubedns in container
    if sudo -u vagrant -s ssh  $SSH_OPTIONS $ADMIN_USER@$node sudo docker run --rm busybox nslookup $external_test_domain $dnsmasq_ip >/dev/null; then
        container_dns_works[$node]="PASSED"
    else
        container_dns_works[$node]="FAILED"
        (( failures++ ))
    fi
    # Check UDP 53 for kubedns in container with host networking
    if sudo -u vagrant -s ssh  $SSH_OPTIONS $ADMIN_USER@$node sudo docker run --net=host --rm busybox nslookup $external_test_domain $dnsmasq_ip >/dev/null; then
        container_hostnet_dns_works[$node]="PASSED"
    else
        container_hostnet_dns_works[$node]="FAILED"
        (( failures++ ))
    fi
done
# Report results
echo "Found $failures failures."
for node in "${SLAVE_IPS[@]}"; do
    echo
    echo "Node $node status:"
    echo "  Node to container communication: ${node_ip_works[$node]}"
    echo "  Node internal DNS lookup (via kubedns): ${node_internal_dns_works[$node]}"
    echo "  Node external DNS lookup (via dnsmasq): ${node_external_dns_works[$node]}"
    echo "  Container internal DNS lookup (via kubedns): ${container_dns_works[$node]}"
    echo "  Container internal DNS lookup (via kubedns): ${container_hostnet_dns_works[$node]}"
done
