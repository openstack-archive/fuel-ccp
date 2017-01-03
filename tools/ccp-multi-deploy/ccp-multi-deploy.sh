#!/bin/bash
#
# This script semit-automates deployment of multiple OpenStack environemtns
# within single K8s cluster using mcp/ccp tool.
# This is PoC.
# Usage: tox -e multi-deploy -- --help
#
# (c) mzawadzki@mirantis.com


set -e
# Config (defaults):
NUMBER_OF_ENVS=1  # Requires 3 K8s nodes per env
BUILD_IMAGES=true # Set to true if run for the first time
: ${CONFIG_DIR:="tools/ccp-multi-deploy/config"}
: ${VERSION:="master"}
NAMESPACE_PREFIX="ccp-${VERSION}"

# Functions:
function usage {
    cat <<EOF
Usage: $0 [OPTION]
Deploy multiple OpenStack environments with fuel-ccp.
Options:
-h, --help
        print usage and exit
-n, --number-of-envs=NUMBER
        deploy NUMBER of parallel environments (default: 1)
-s, --skip-building-images
        do not build Docker images for OpenStack services
        (rely on existing local registry, default: false)
-v, --openstack-version=VERSION
        set openstack version newton or master (default: master)
-d, --debug
        create diagnostic snapshot if deployment fail
EOF
    exit
}

function ccp_wait_for_deployment_to_finish {
    cnt=0
    until [[ `${CCP} status -s -f value -c status` == "ok" ]]; do
        echo "Waiting for OpenStack deployment to finish..."
        sleep 5
        cnt=$((cnt + 1))
        if [ ${cnt} -eq 300 ]; then
            echo "Max time exceeded"
            if [ -n "${DEBUG}" ]; then
                ./tools/diagnostic-snapshot.sh -n "${1}" -l "~/ccp-diag"
            fi
            exit 1
        fi
    done
    echo "...................................."
    echo "Jobs and pods in namespace: $1"
    kubectl --namespace $1 get jobs
    kubectl --namespace $1 get pods
    echo "openrc file: openrc-$1"
    cat openrc-${1}
    echo "...................................."
}

function display_horizon_access_info {
    HORIZON_EXT_ADDRESS=$($CCP status horizon -f value -c links)
    echo "Hint - to access horizon from your workstation please use the following address $HORIZON_EXT_ADDRESS"
}

function run_openstack_tests {
    source openrc-$1
    ./tools/deploy-test-vms.sh -k $1 -a create
    ./tools/deploy-test-vms.sh -k $1 -a destroy
}


# Parse command line arguments:
OPTS=`getopt -o 'hdsn:v:' --long help,debug,skip-building-images,number-of-envs:,openstack-version: -n 'parse-options' -- ${@}`
if [ ${?} != 0 ] ; then
    echo "Failed parsing options."
    exit 1
fi
eval set -- ${OPTS}

while true; do
    case ${1} in
        -h|--help ) usage; shift ;;
        -n|--number-of-envs ) NUMBER_OF_ENVS=${2}; shift; shift ;;
        -s|--skip-building-images ) BUILD_IMAGES=false; shift ;;
        -v|--openstack-version ) VERSION="${2}"; NAMESPACE_PREFIX="ccp-${2}"; shift; shift ;;
        -d|--debug ) DEBUG="yes"; shift ;;
        -- ) shift; break ;;
        * ) break ;;
    esac
done


# Check some basic requirements and exit explicitly if they are not met:
if [ ! -f "${CONFIG_DIR}/ccp-cli-${VERSION}-config-1.yaml" ]; then
    echo "Config file not found, did you set CONFIG_DIR correctly?"
    exit 1
fi
which kubectl || exit 1
groups | grep docker || exit 1
if [ `kubectl get nodes | grep node | wc -l` -lt $(($NUMBER_OF_ENVS * 3)) ]; then
    echo "Your K8s cluster is too small, you need NUMBER_OF_ENVS * 3 nodes."
    exit 1
fi

# add k8s_address to config
default_iface=$(ip ro sh | awk '/^default via [0-9]+.[0-9]+.[0-9]+.[0-9]+ dev/ {print $5}')
ext_ipaddr=$(ip addr show $default_iface | awk '/inet / {print substr($2, 1, length($2)-3)}')
cat >${CONFIG_DIR}/ccp-hw-config.yaml << EOF
configs:
    k8s_external_ip: "$ext_ipaddr"
EOF

if [ -n "${APT_CACHE_SERVER}" ]; then
    cat >>"${CONFIG_DIR}"/ccp-configs-common.yaml << EOF
url:
    debian: ${APT_CACHE_SERVER}/debian
    debian_security: ${APT_CACHE_SERVER}/security
    ceph:
      debian:
        repo: ${APT_CACHE_SERVER}/ceph
    mariadb:
      debian:
        repo: ${APT_CACHE_SERVER}/mariadb
EOF
fi

# Fetch CCP repos
CCP="ccp --verbose --debug --config-file ${CONFIG_DIR}/ccp-cli-${VERSION}-config-1.yaml"
${CCP} fetch


# Create internal Docker registry for CCP,
# build and push CCP images:
if [ "${BUILD_IMAGES}" = "true" ]; then
    kubectl delete pod registry || true
    kubectl delete service registry || true
    ./tools/registry/deploy-registry.sh -n default
    ${CCP} build
fi

# Deploy envs:
for n in $(seq 1 ${NUMBER_OF_ENVS}); do
    CCP="ccp --verbose --debug --config-file ${CONFIG_DIR}/ccp-cli-${VERSION}-config-${n}.yaml"
    ${CCP} deploy
    ccp_wait_for_deployment_to_finish ${NAMESPACE_PREFIX}-${n}
    display_horizon_access_info ${NAMESPACE_PREFIX}-${n}
    run_openstack_tests ${NAMESPACE_PREFIX}-${n}
    echo "CCP cleanup command: ccp --verbose --debug --config-file ${CONFIG_DIR}/ccp-cli-${VERSION}-config-${n} cleanup"
done
