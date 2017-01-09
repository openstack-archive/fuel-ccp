#!/bin/bash -x

: ${LOG_DIR:="/tmp/ccp-diag"}
: ${NAMESPACE:="ccp"}
CCP_LOG="diag-ccp.log"
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
            ssh $f -o StrictHostKeyChecking=no "${c}" > "${LOG_DIR}/system/${f}-${c//[^[:alpha:]]/}.log" 2>&1
        done
        set -e
    done
}

function k8s_data {
    for c in "${k8s_tests[@]}"; do
        kubectl -n ${NAMESPACE} ${c} > "${LOG_DIR}/k8s/${NAMESPACE}-${c//[^[:alpha:]]/}.log" 2>&1
    done
    kubectl -n "kube-system" get pods > "${LOG_DIR}/k8s/kube-system-get-pod.log" 2>&1
    kubectl -n "kube-system" get svc > "${LOG_DIR}/k8s/kube-system-get-svc.log" 2>&1
}

function get_pods {
    kubectl get pod -n "${NAMESPACE}" --show-all -o template --template="
        {{ range .items -}}
            {{ .metadata.name }}
        {{ end }}"
}

function get_containers {
    local pod_name="${1}"
    kubectl get pod -n "${NAMESPACE}" "${pod_name}" -o template --template="
        {{ range .spec.containers }}
            {{ .name }}
        {{ end }}"
}


function ccp_data {
    CCP="ccp --verbose --debug"
    set +e
    ${CCP} status
    for pod in $(get_pods); do
        kubectl -n "${NAMESPACE}" describe pod "${pod}" >> "${LOG_DIR}/logs/describe-pod-${pod}.log" 2>&1
        for cont in $(get_containers "${pod}"); do
            kubectl -n "$NAMESPACE" logs "${pod}" "${cont}" > "${LOG_DIR}/logs/pod-${pod}-cont-${cont}.log" 2>&1
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

mkdir -p "${LOG_DIR}"
mkdir -p "${LOG_DIR}/logs"
mkdir -p "${LOG_DIR}/system"
mkdir -p "${LOG_DIR}/k8s"

k8s_data
ccp_data > "${LOG_DIR}/${CCP_LOG}" 2>&1
get_shell


ARCHIVE_NAME="`date +%Y-%m-%d_%H-%M-%S`-diagnostic.tar.gz"

tar -zcvf "${LOG_DIR}/${ARCHIVE_NAME}" ${LOG_DIR}/*

echo "Snapshot created: ${LOG_DIR}/${ARCHIVE_NAME}"
