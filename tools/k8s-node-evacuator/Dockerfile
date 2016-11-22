FROM DOCKER_REGISTRY_HOST_PORT_CHANGE_ME/DOCKER_REGISTRY_NAMESPACE_CHANGE_ME/openstack-base
MAINTAINER MOS Microservices <mos-microservices@mirantis.com>

RUN useradd --user-group --create-home --home-dir /var/lib/k8s-node-evacuator k8s-node-evacuator \
    && usermod -a -G microservices k8s-node-evacuator

COPY k8s-node-evacuator.py /opt/ccp/bin

USER k8s-node-evacuator

CMD python /opt/ccp/bin/k8s-node-evacuator.py
