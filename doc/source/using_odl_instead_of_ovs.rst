.. _using_odl_instead_of_ovs:

==========================================
Using OpenDaylight instead of Open vSwitch
==========================================

This guide describes how to deploy and run OpenStack environment with
OpenDaylight ML2 Neutron plugin instead of the reference openvswitch ML2 on top
of Kubernetes cluster using fuel-ccp.

Introduction
~~~~~~~~~~~~

OpenDaylight (ODL) is a modular Open SDN platform for networks of any size and
scale. OpenStack can use OpenDaylight as its network management provider
through the Modular Layer 2 (ML2) north-bound plug-in. OpenDaylight manages
the network flows for the OpenStack compute nodes via the OVSDB south-bound
plug-in.

Deployment will look like this:

* new Docker container and service: opendaylight
* openvswitch service on nodes is configured to be managed by ODL
* neutron is configured to use ``networking-odl`` ML2 plugin.
* neutron openvswitch and l3 agent pods are removed from the deployment
topology.

What is needed to deploy CCP with ODL network plugin:

* Runnning K8s environment with ODL network plugin (for a tested,
  recommended setup please check out
  `this guide <http://fuel-ccp.readthedocs.io/en/latest/quickstart.html>`__).
* CCP installed on a machine with access to ``kube-apiserver`` (e.g. K8s
  master node).
* CCP CLI config file with custom deployment topology.

Sample deployment
~~~~~~~~~~~~~~~~~

Sample CCP configuration
------------------------

Let's write CCP CLI configuration file now, make sure you have the following
in your configuration file (let's say it's ``ccp.yaml``):

::

    builder:
      push: True
    registry:
      address: "127.0.0.1:31500"
    repositories:
      skip_empty: True
    nodes:
      node1:
        roles:
          - controller
          - openvswitch
          - opendaylight
      node[2-3]:
        roles:
          - compute
          - openvswitch
    roles:
      controller:
        - etcd
        - glance-api
        - glance-registry
        - heat-api
        - heat-engine
        - horizon
        - keystone
        - mariadb
        - memcached
        - neutron-dhcp-agent
        - neutron-metadata-agent
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
        - openvswitch-db
        - openvswitch-vswitchd
      opendaylight:
        - opendaylight
    configs:
        private_interface: eth1
        public_interface: eth2
        neutron:
          plugin_agent: "opendaylight"

Now let's build images and push them to registry if you have not done this
already:

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

Creating networks and instances in OpenStack
--------------------------------------------

After CCP deployment is complete we can create Neutron networks and run VMs.

Install openstack-client:

::

    pip install python-openstackclient

``openrc`` file for current deployment was created in the current working
directory. To use it run:

::

    source openrc-ccp

Run test environment deploy script:

::

    bash fuel-ccp/tools/deploy-test-vms.sh -a create -c -n NUMBER_OF_VMS

This script will create flavor, upload cirrios image to glance, create network
and subnet and launch bunch of cirrios based VMs.

Uninstalling and undoing customizations
---------------------------------------

To destroy deployment environment ``ccp cleanup`` command can be used:

::

    ccp --config-file ccp.yaml ccp cleanup
