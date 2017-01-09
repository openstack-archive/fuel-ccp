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
            'cat /proc/cpuinfo'
            'journalctl -u kubelet'
            'journalctl -u docker')

k8s_tests=('get pods'
            'get svc'
            'get jobs')

function usage {
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
            ssh $f -o StrictHostKeyChecking=no "${c}" > ${LOG_DIR}/system/${f}-${c//[^[:alpha:]]/}.log 2>&1
        done
        set -e
    done
}

function k8s_data {
    for c in "${k8s_tests[@]}"; do
        echo -e "\n ${DIVIDER} ${NAMESPACE} namespace $c ${DIVIDER} \n"
        kubectl -n ${NAMESPACE} ${c}
    done

    echo -e "\n ${DIVIDER} kube-system namespace POD ${DIVIDER} \n"
    kubectl -n "kube-system" get pods
    echo -e "\n ${DIVIDER} kube-system namespace SVC ${DIVIDER} \n"
    kubectl -n "kube-system" get svc
}

function get_pods {
    kubectl get pod -n "$NAMESPACE" --show-all -o template --template="
        {{ range .items -}}
            {{ .metadata.name }}
        {{ end }}"
}

function get_containers {
    local pod_name="$1"
    kubectl get pod -n "$NAMESPACE" "$pod_name" -o template --template="
        {{ range .spec.containers }}
            {{ .name }}
        {{ end }}"
}


function ccp_data {
    CCP="ccp --verbose --debug"
    set +e
    ${CCP} status
    for pod in $(get_pods); do
        kubectl -n "${NAMESPACE}" describe pod "${pod}" >> ${LOG_DIR}/logs/${pod}.log 2>&1
        for cont in $(get_containers "${pod}"); do
            kubectl -n "$NAMESPACE" logs "${pod}" "${cont}" > "${LOG_DIR}/logs/pod-${pod}-cont-${cont}.log"
        done
    done
    set -e
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
mkdir -p ${LOG_DIR}/logs
mkdir -p ${LOG_DIR}/system

k8s_data > ${LOG_DIR}/${K8S_LOG} 2>&1
ccp_data > ${LOG_DIR}/${CCP_LOG} 2>&1
get_shell > ${LOG_DIR}/${SYSTEM_LOG} 2>&1


ARCHIVE_NAME="`date +%Y-%m-%d_%H-%M-%S`-diagnostic.tar.gz"

tar -zcvf ${LOG_DIR}/${ARCHIVE_NAME} ${LOG_DIR}/*

echo "Snapshot created: ${LOG_DIR}/${ARCHIVE_NAME}"
