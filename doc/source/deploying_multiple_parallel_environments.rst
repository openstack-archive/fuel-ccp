.. _deploying_multiple_parallel_environments:

========================================
Deploying Mutliple Parallel Environments
========================================

This guide describes how to deploy and run in parallel more than one
OpenStack environment on a single Kubernetes cluster.

.. WARNING:: This functionality may not work correctly until this Calico bug is
   fixed: https://github.com/projectcalico/libcalico/issues/148

Introduction
============

From the Kubernetes (K8s) perspective, CCP is just another application,
therefore it should be possible to run multiple CCP deployments within
a single K8s cluster.
This also promotes flexibility as there is no need to deploy separate
K8s clusters to run parallel but isolated OpenStack clouds.
A sample use-case may include 3 clouds: development, staging and production -
all run on a single K8s cluster and managed from one place.

How deployments are isolated:

* logically by K8s namespaces (including individual FQDNs for each CCP service
  in each namespace)
* on a Docker level for services that can share hosts (e.g. ``keystone``)
* on a host level for services that can be run 1 per host only (e.g.
  ``nova-libvirt``)

.. WARNING:: Network isolation for parallel deployments depends on networking
   solution deployed in the K8s cluster. E.g. in case of Calico it offers
   tenant isolation but it may not be yet available for particular K8s
   deployment methods (e.g. Kargo).
   Please be aware that if that is the case, pods in different CCP deployments
   can access networks of each other.

What is needed to deploy mutliple CCPs in parallel:

* runnning K8s environment (for a tested, recommended setup please check out
  `this guide <http://fuel-ccp.readthedocs.io/en/latest/quickstart.html>`__)
* CCP installed on a machine with access to ``kube-apiserver`` (e.g. K8s
  master node)
* CCP CLI config file for each deployment
* CCP topology YAML file for each deployment


Quick start
===========

To quickly deploy 2 parallel OpenStack environments, run these commands
on your K8s master node:

::

    git clone https://git.openstack.org/openstack/fuel-ccp
    cd fuel-ccp
    tox -e multi-deploy -- --number-of-envs 2


Sample deployment model
=======================

Following is an example of 3 parallel CCP deployments. Here is breakdown
of services assignment to nodes (please note this isn't yet CCP topology file):

::

    node1:
      - openvswitch[1]
      - controller-net-host[1]
      - controller-net-bridge[.*]
    node[2-3]
      - openvswitch[1]
      - compute[1]
      - controller-net-bridge[.*]
    node4:
      - openvswitch[2]
      - controller-net-host[2]
      - controller-net-bridge[.*]
    node[5-6]
      - openvswitch[2]
      - compute[2]
      - controller-net-bridge[.*]
    node7:
      - openvswitch[3]
      - controller-net-host[3]
      - controller-net-bridge[.*]
    node[8-9]
      - openvswitch[3]
      - compute[3]
      - controller-net-bridge[.*]

Deployments 1-3 are marked by numbers in brackets ([]).
For each deployment we dedicate:

* 1 node for net-host Controller services + Open vSwitch (e.g. node1 in
  deployment #1, node4 in deployment #2, node7 in deployment #3)
* 2 nodes for Computes + Open vSwich (e.g. node2 and node3 in deployment #1,
  node5 and node6 in deployment #2, etc.)


Sample CCP configuration
========================

Let's now write the deployment model described in previous section into
specific CCP configuration files. For each of 3 deployments we need 2 separate
config files (1 for CLI configuration and 1 with topology) + 2 shared config
files for common configuration options and roles definitions.

::

    cat > ccp-cli-config-1.yaml << EOF
    !include
    - ccp-configs-common.yaml
    - ccp-roles.yaml
    - ccp-topology-1.yaml
    ---
    kubernetes:
      namespace: "ccp-1"
    EOF


::

    cat > ccp-cli-config-2.yaml << EOF
    !include
    - ccp-configs-common.yaml
    - ccp-roles.yaml
    - ccp-topology-2.yaml
    ---
    kubernetes:
      namespace: "ccp-2"
    EOF


::

    cat > ccp-cli-config-3.yaml << EOF
    !include
    - ccp-configs-common.yaml
    - ccp-roles.yaml
    - ccp-topology-3.yaml
    ---
    kubernetes:
      namespace: "ccp-3"
    EOF


::

    cat > ccp-configs-common.yaml << EOF
    ---
    builder:
      push: True
    registry:
      address: "127.0.0.1:31500"
    repositories:
      path: /tmp/ccp-repos
      skip_empty: True
    configs:
        private_interface: eth0
        public_interface: eth1
        neutron_external_interface: eth2
    EOF

::

    cat > ccp-roles.yaml << EOF
    ---
    roles:
      controller-net-host:
        - neutron-dhcp-agent
        - neutron-l3-agent
        - neutron-metadata-agent
      controller-net-bridge:
        - etcd
        - glance-api
        - glance-registry
        - heat-api
        - heat-engine
        - horizon
        - keystone
        - mariadb
        - memcached
        - neutron-server
        - nova-api
        - nova-conductor
        - nova-consoleauth
        - nova-novncproxy
        - nova-scheduler
        - rabbitmq
      compute:
        - nova-compute
        - nova-libvirt
      openvswitch:
        - neutron-openvswitch-agent
        - openvswitch-db
        - openvswitch-vswitchdvv
    EOF


::

    cat > ccp-topology-1.yaml << EOF
    ---
    nodes:
      node[1,2-3,4,5-6,7,8-9]:
        roles:
          - controller-net-bridge
      node1:
        roles:
          - openvswitch
          - controller-net-host
      node[2-3]:
        roles:
          - openvswitch
          - compute
    EOF


::

    cat > ccp-topology-2.yaml << EOF
    ---
    nodes:
      node[1,2-3,4,5-6,7,8-9]:
        roles:
          - controller-net-bridge
      node4:
        roles:
          - openvswitch
          - controller-net-host
      node[5-6]:
        roles:
          - openvswitch
          - compute
    EOF


::

    cat > ccp-topology-3.yaml << EOF
    ---
    nodes:
      node[1,2-3,4,5-6,7,8-9]:
        roles:
          - controller-net-bridge
      node7:
        roles:
          - openvswitch
          - controller-net-host
      node[8-9]:
        roles:
          - openvswitch
          - compute
    EOF



Since we will use the same Docker OpenStack images for all 3 deployments it is
sufficient to build them (and push to local registry) only once:

::

    ccp build --config-file ccp-cli-config-1.yaml

We can now deploy CCP as usually:

::

    ccp deploy --config-file ccp-cli-config-1.yaml
    ccp deploy --config-file ccp-cli-config-2.yaml
    ccp deploy --config-file ccp-cli-config-3.yaml

CCP will create 3 K8s namespaces (ccp-1, ccp-2 and ccp-3) and corresponding
jobs, pods and services in each namespace. Finally, it will create openrc files
in current working directory for each deployment, named ``openrc-ccp-1``,
``openrc-ccp-2`` and ``openrc-ccp-3``. These files (or nodePort of horizon
K8s service in each namespace) can be used to access each OpenStack cloud
separately. To know when each deployment is ready to be accessed
``kubectl get jobs`` command can be used (all jobs should finish):

::

    kubectl --namespace ccp-1 get jobs
    kubectl --namespace ccp-2 get jobs
    kubectl --namespace ccp-3 get jobs

To destroy selected deployment environments ``ccp cleanup`` command can be
used, e.g. to destroy deployment #2:

::

    ccp --namespace ccp-2 cleanup
