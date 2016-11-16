#!/bin/bash -eu

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

NAMESPACE="$1"
LOG_DIR="$2"

mkdir -p "$LOG_DIR"
echo ">>> Collect logs in $LOG_DIR directory..."

for pod in $(get_pods); do
    for cont in $(get_containers "$pod"); do
        echo ">>> Logs for $pod $cont"
        kubectl -n "$NAMESPACE" logs "$pod" "$cont" > "$LOG_DIR/pod-$pod-cont-$cont.log"
    done
done
