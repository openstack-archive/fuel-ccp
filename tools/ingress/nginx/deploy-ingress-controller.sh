#!/bin/bash

set -e

function usage {
    local base_name=$(basename $0)
    echo "Usage:"
    echo "  $base_name -i <external IP>"
    echo "  $base_name -p <http port (default: 80)>"
    echo "  $base_name -s <https port (default: 8443)>"
    echo "  $base_name -n <namespace> (default: kube-system)"
    echo "  $base_name -k <path to tls key>"
    echo "  $base_name -c <path to tls cert>"
    echo "  $base_name -d <ingress domain (default: external)>"
}

NAMESPACE="kube-system"
DOMAIN="external"
HTTP_PORT=80
HTTPS_PORT=443

while getopts "p:s:w:k:c:d:n:i:h" opt; do
    case $opt in
        "p" )
            HTTP_PORT="$OPTARG"
            ;;
        "s" )
            HTTPS_PORT="$OPTARG"
            ;;
        "k" )
            TLS_KEY="$OPTARG"
            ;;
        "c" )
            TLS_CERT="$OPTARG"
            ;;
        "d" )
            DOMAIN="$OPTARG"
            ;;
        "n" )
            NAMESPACE="$OPTARG"
            ;;
        "i" )
            EXTERNAL_IP="$OPTARG"
            ;;
        "h" )
            usage
            exit 0
            ;;
        * )
            usage
            exit 1
            ;;
    esac
done

which kubectl 1>/dev/null

function kube_cmd {
    kubectl --namespace=${NAMESPACE} "$@"
}

workdir=$(dirname $0)

if [ -z $EXTERNAL_IP ]; then
    echo "External IP should be provided via -i param"
    usage
    exit 1
fi

if [ -z $TLS_KEY ] || [ -z $TLS_CERT ]; then
    TLS_KEY="tls.key"
    TLS_CERT="tls.crt"
    CLEANUP="True"
    CERT_ALTNAME="DNS:*.${DOMAIN},IP:${EXTERNAL_IP}" openssl req -config ${workdir}/openssl.cnf -x509 -nodes -days 365 -newkey rsa:2048 -keyout ${TLS_KEY} -out ${TLS_CERT} -subj "/CN=*.${DOMAIN}"
fi

kube_cmd create secret generic nginx-ingress-controller-cert --from-file=$TLS_CERT --from-file=$TLS_KEY
sleep 1
sed -e "s/\bHTTP_PORT\b/${HTTP_PORT}/g" -e "s/\bHTTPS_PORT\b/${HTTPS_PORT}/g" -e "s/\bNAMESPACE\b/${NAMESPACE}/g" \
    -e "s/\bEXTERNAL_IP\b/${EXTERNAL_IP}/g" -e "s/DOMAIN/${DOMAIN}/g" \
    ${workdir}/controller.yaml | kubectl --namespace=${NAMESPACE} create -f -
if [ -n "${CLEANUP}" ]; then
    rm $TLS_KEY $TLS_CERT
fi