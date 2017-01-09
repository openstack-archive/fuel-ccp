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
           'df -h')

function get_shell {
    for f in `kubectl get nodes | awk '{print $1}'| tail -n +2`; do
        for c in "${shell_tests[@]}"; do
            echo "${DIVIDER} $f - $c ${DIVIDER}"
            ssh $f -o StrictHostKeyChecking=no "$c"
        done
    done
}

function k8s_data {
    echo "${DIVIDER} ${NAMESPACE} namespace PODS ${DIVIDER}"
    kubectl -n ${NAMESPACE} get pods
    echo "${DIVIDER} ${NAMESPACE} namespace JOBS ${DIVIDER}"
    kubectl -n ${NAMESPACE} get jobs
    echo "${DIVIDER} ${NAMESPACE} namespace SVC ${DIVIDER}"
    kubectl -n ${NAMESPACE} get svc
    echo "${DIVIDER} kube-system namespace POD ${DIVIDER}"
    kubectl -n "kube-system" get pods
    echo "${DIVIDER} kube-system namespace SVC ${DIVIDER}"
    kubectl -n "kube-system" get svc
}

function ccp_data {
    CCP="ccp --verbose --debug"
    ${CCP} status
    for f in `${CCP} status | awk '/wip/{print $2}'`; do
        POD_NAME=`kubectl -n "${NAMESPACE}" get pods | grep "${f}" | awk '{print $1}'`
        if kubectl -n ${NAMESPACE} get pods "${POD_NAME}" -o jsonpath={.spec.containers[*].name}; then
            CONTAINERS_NAMES=`kubectl -n ${NAMESPACE} get pods "${POD_NAME}" -o jsonpath={.spec.containers[*].name}`
            for c in ${CONTAINERS_NAMES}; do
                echo "********* ${c} *********"
                set +e
                kubectl -n "${NAMESPACE}" describe pod "${POD_NAME}"
                kubectl -n "${NAMESPACE}" logs "${POD_NAME}" "${c}"
                set -e
            done
        fi
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

tar -zcvf ${LOG_DIR}/`date +%Y-%m-%d_%H-%M-%S`-diagnostic.tar.gz ${LOG_DIR}/*.log
