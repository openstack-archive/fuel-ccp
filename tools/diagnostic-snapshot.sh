#!/bin/bash -x

# We want to be sure that script will always give us some output,
# even if it fails in some parts it return some information.
set +e

: ${LOG_DIR:="/tmp/ccp-diag"}
: ${NAMESPACE:="ccp"}
CCP_LOG="ccp-diag.log"
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
            'journalctl -u docker'
            'test_networking.sh')

k8s_tests=('get pods'
            'get svc'
            'get jobs')

function usage {
    cat << EOF
    Usage: $0 [-o LOG_DIR] [-n NAMESPACE]

    -h|--help        Print this help
    -o|--output-dir  Logs output directory (optional - default /tmp/ccp-diag)
    -n|--namespace   Kubernetes namespace  (optional - default ccp)
EOF
    exit
}

function filename_escape {
    echo ${1} | sed s'#[ |/]#_#g'
}



function get_shell {
    for f in `kubectl get nodes | awk '{print $1}'| tail -n +2`; do
        for c in "${shell_tests[@]}"; do
            fname=$(filename_escape "${c}")
            echo "${c}" > "${LOG_DIR}/system/${f}-${fname}.log"
            ssh $f -o StrictHostKeyChecking=no "${c}" >> "${LOG_DIR}/system/${f}-${fname}.log" 2>&1
        done
    done
}

function k8s_data {
    for c in "${k8s_tests[@]}"; do
        fname=$(filename_escape "${c}")
        echo "${c}" > "${LOG_DIR}/k8s/${NAMESPACE}-${fname}.log"
        kubectl -n ${NAMESPACE} ${c} >> "${LOG_DIR}/k8s/${NAMESPACE}-${fname}.log" 2>&1
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
    kubectl get pod -n "${NAMESPACE}" "${1}" -o template --template="
        {{ range .spec.containers }}
            {{ .name }}
        {{ end }}"
}


function ccp_data {
    CCP="ccp --verbose --debug"
    ${CCP} status
    for pod in $(get_pods); do
        kubectl -n "${NAMESPACE}" describe pod "${pod}" >> "${LOG_DIR}/logs/describe-pod-${pod}.log" 2>&1
        for cont in $(get_containers "${pod}"); do
            kubectl -n "${NAMESPACE}" logs "${pod}" "${cont}" > "${LOG_DIR}/logs/pod-${pod}-cont-${cont}.log" 2>&1
        done
    done
}



# Parse command line arguments:
OPTS=`getopt -o 'ho:n:' --long help,output-dir:,namespace: -n 'parse-options' -- ${@}`
if [ ${?} != 0 ] ; then
    echo "Failed parsing options."
    exit 1
fi
eval set -- ${OPTS}

while [ -n "${1}" ]; do
    case ${1} in
        -h|--help ) usage; shift ;;
        -o|--output-dir ) LOG_DIR=${2}; shift; shift ;;
        -n|--namespace ) NAMESPACE=${2}; shift; shift ;;
        -- ) shift; break ;;
        * ) break ;;
    esac
done

mkdir -p "${LOG_DIR}"/{logs,system,k8s} | exit 1

get_shell
k8s_data
ccp_data > "${LOG_DIR}/${CCP_LOG}"

ARCHIVE_NAME="`date +%Y-%m-%d_%H-%M-%S`-diagnostic.tar.gz"

tar -zcvf "${LOG_DIR}/${ARCHIVE_NAME}" "${LOG_DIR}"/*

echo "Snapshot created: ${LOG_DIR}/${ARCHIVE_NAME}"
