FROM DOCKER_REGISTRY_HOST_PORT_CHANGE_ME/DOCKER_REGISTRY_NAMESPACE_CHANGE_ME/openstack-base
MAINTAINER MOS Microservices <mos-microservices@mirantis.com>

COPY k8s-node-evacuator.py /opt/ccp/bin
CMD python /opt/ccp/bin/k8s-node-evacuator.py
