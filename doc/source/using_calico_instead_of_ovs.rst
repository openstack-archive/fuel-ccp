.. _using_calico_instead_of_ovs:

====================================
Using Calico instead of Open vSwitch
====================================

This guide describes how to deploy and run OpenStack environment with Calico
ml2 Neutron plugin instead of OVS on top of Kubernetes cluster and how to
integrate OpenStack and Kubernetes workloads.

Introduction
------------

Calico's pure L3 approach to data center networking integrates seamlessly with
cloud orchestration systems (such as OpenStack) to enable secure IP
communication between virtual machines, containers, or bare metal workloads.

By using Calico network plugin for both Kubernetes and OpenStack Containerized
Control Plane (CCP) we can provide pure L3 fabric and cross-workload security
for mixed workloads.

Deployment diagram:

  .. image:: ccp-calico.png
     :scale: 60%

Deployment will look like this:

* Neutron is configured to use ``networking-calico`` ML2 plugin.
* Neutron DHCP agent is replaced with Calico DHCP agent.
* Open vSwitch pods are removed from the deployment topology.
* Additional Kubernetes proxy service is required to provide the connectivity
  from CCP pods to the main Etcd cluster (they cannot connect to etcd-proxy
  on a localhost since some containers are running in isolated network space,
  for example neutron-server).
* CCP Calico components are connected to the same Etcd DB as Calico services
  providing networking for Kubernetes.
* Calico/felix from ``calico/node`` container has reporting enabled.

What is needed to deploy mutliple CCP with Calico network plugin:

* runnning K8s environment with Calico network plugin (for a tested,
  recommended setup please check out
  `this guide <http://fuel-ccp.readthedocs.io/en/latest/quickstart.html>`__)
* CCP installed on a machine with access to ``kube-apiserver`` (e.g. K8s
  master node)
* CCP CLI config file with custom deployment topology

Sample deployment model
-----------------------

Following is an example of CCP deployment with Calico networking integrated with
Kubernetes Calico components. Here is breakdown of services assignment to nodes
(please note this isn't yet CCP topology file):

::

    node1:
      - controller
      - neutron-server with Calico ML2 plugin
      - neutron-metadata-agent
    node[2-3]
      - compute
      - calico-dhcp-agent


Configuring requirements in Kubernetes cluster
----------------------------------------------

Before deploying CCP we should run etcd proxy service in the same namespace:

::

    cat > etcd-calico-svc.yaml << EOF
    kind: "Endpoints"
    apiVersion: "v1"
    metadata:
      name: "etcd-calico"
    subsets:
      - addresses:
        - ip: "10.210.1.11"
        - ip: "10.210.1.12"
        - ip: "10.210.1.13"
        ports:
          - port: 2379
            name: "etcd-calico"
    ---
    apiVersion: "v1"
    kind: "Service"
    metadata:
      name: "etcd-calico"
    spec:
      ports:
      - name: "etcd-calico"
        port: 2379
        protocol: TCP
      sessionAffinity: None
      type: NodePort
    status:
      loadBalancer: {}
    EOF

    kubectl --namespace=ccp create -f /var/tmp/etcd-calico-svc.yaml

We also need to enable reporting in Felix:

::

    etcdctl set /calico/v1/config/ReportingIntervalSecs 60

And add some custom export filters for BGP agent:

::

    cat << EOF | etcdctl set /calico/bgp/v1/global/custom_filters/v4/tap_iface
      if ( ifname ~ "tap*" ) then {
        accept;
      }
    EOF

Sample CCP configuration
------------------------

Let's write CCP CLI configuration file now:

::

    cat > ccp.yaml << EOF
    builder:
      push: True
    registry:
      address: "127.0.0.1:31500"
    kubernetes:
      namespace: "ccp"
    images:
      namespace: "ccp"
    repositories:
      skip_empty: True
      protocol: https
      port: 443

    configs:
      neutron:
        plugin_agent: "calico"
        calico:
          etcd_host: "etcd-calico"
          etcd_port: "2379"

    nodes:
      node1:
        roles:
          - controller
          - neutron-agents
      node[2-3]:
        roles:
          - compute
          - calico

    roles:
      controller:
        - etcd
        - glance-api
        - glance-registry
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
      neutron-agents:
        - neutron-metadata-agent
      compute:
        - nova-compute
        - nova-libvirt
      calico:
        - calico-dhcp-agent

Now let's build images and push them to registry:

::

    ccp deploy --config-file ccp.yaml build

We can now deploy CCP as usually:

::

    ccp deploy --config-file ccp.yaml deploy

CCP will create namespace named ``ccp`` and corresponding jobs, pods and services
in it. To know when deployment is ready to be accessed ``kubectl get jobs``
command can be used (all jobs should finish):

::

    kubectl --namespace ccp get jobs

To destroy deployment environment ``ccp cleanup`` command can be used:

::

    ccp --config-file ccp.yaml ccp cleanup
