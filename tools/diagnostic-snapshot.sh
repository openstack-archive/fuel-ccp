#!/bin/bash

: ${LOG_DIR:="/tmp/ccp-diag"}
: ${NAMESPACE:="ccp"}
K8S_LOG="diag-k8s.log"
CCP_LOG="diag-ccp.log"
SYSTEM_LOG="diag-system.log"
DIVIDER=`printf '%40s\n' | tr ' ' -`


shell_tests=('top -bn1 -c| head -n 15'
            'docker images'
            'docker ps'
            'docker stats --no-stream'
            'df -h'
            'df -i'
            'ip a'
            'sysctl -a'
            'uname -a'
            'cat /proc/cpuinfo')

k8s_tests=('get pods'
            'get svc'
            'get jobs')

function usage() {
    cat << EOF
    Usage: $0 [-o LOG_DIR] [-n NAMESPACE]

    -h   Prints this help
    -l   Logs output directory(optional - default /tmp/ccp-diag)
    -n   Kubernetes namespace (optional - default ccp)
EOF
    exit
}



function get_shell {
    for f in `kubectl get nodes | awk '{print $1}'| tail -n +2`; do
        set +e
        for c in "${shell_tests[@]}"; do
            echo -e "\n ${DIVIDER} $f - $c ${DIVIDER} \n"
            ssh $f -o StrictHostKeyChecking=no "$c"
        done
        set -e
    done
}

function k8s_data {
    mkdir -p ${LOG_DIR}/logs
    for c in "${k8s_tests[@]}"; do
        echo -e "\n ${DIVIDER} ${NAMESPACE} namespace $c ${DIVIDER} \n"
        kubectl -n ${NAMESPACE} ${c}
    done

    echo -e "\n ${DIVIDER} kube-system namespace POD ${DIVIDER} \n"
    kubectl -n "kube-system" get pods
    echo -e "\n ${DIVIDER} kube-system namespace SVC ${DIVIDER} \n"
    kubectl -n "kube-system" get svc
}

function ccp_data {
    CCP="ccp --verbose --debug"
    ${CCP} status
    for f in `${CCP} status | awk '/wip/{print $2}'`; do
        set +e
        for p in `kubectl -n "${NAMESPACE}" get pods | grep "${f}" | awk '{print $1}'`; do
            kubectl -n "${NAMESPACE}" describe pod "${p}" >> ${LOG_DIR}/logs/${f}.log 2>&1
            if kubectl -n ${NAMESPACE} get pods "${p}" -o jsonpath={.spec.containers[*].name}; then
                CONTAINERS_NAMES=`kubectl -n ${NAMESPACE} get pods "${p}" -o jsonpath={.spec.containers[*].name}`
                for c in ${CONTAINERS_NAMES}; do
                    echo "${DIVIDER} ${c} ${DIVIDER}" >> ${LOG_DIR}/logs/${f}.log 2>&1
                    kubectl -n "${NAMESPACE}" logs "${p}" "${c}" >> ${LOG_DIR}/logs/${f}.log 2>&1
                done
            fi
        done
        set -e
    done
}



# Parse command line arguments:
OPTS=`getopt -o 'hl:n:' --long help,log-dir:,namespace: -n 'parse-options' -- ${@}`
if [ ${?} != 0 ] ; then
    echo "Failed parsing options."
    exit 1
fi
eval set -- ${OPTS}

while true; do
    case ${1} in
        -h|--help ) usage; shift ;;
        -l|--log-dir ) LOG_DIR=${2}; shift; shift ;;
        -n|--namespace ) NAMESPACE=${2}; shift ;;
        -- ) shift; break ;;
        * ) break ;;
    esac
done

mkdir -p ${LOG_DIR}

k8s_data > ${LOG_DIR}/${K8S_LOG} 2>&1
ccp_data > ${LOG_DIR}/${CCP_LOG} 2>&1

get_shell > ${LOG_DIR}/${SYSTEM_LOG} 2>&1


ARCHIVE_NAME="`date +%Y-%m-%d_%H-%M-%S`-diagnostic.tar.gz"

tar -zcvf ${LOG_DIR}/${ARCHIVE_NAME} ${LOG_DIR}/*log*

echo "Snapshot created: ${LOG_DIR}/${ARCHIVE_NAME}"
