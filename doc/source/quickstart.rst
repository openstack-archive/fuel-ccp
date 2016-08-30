.. quickstart:

===========
Quick Start
===========

This guide provides a step by step of how to deploy CCP on bare metal or a
virtual machine.

Host machine requirements
=========================

The recommended deployment target requirements:

- At least 3 k8s nodes
- At least 8Gb of RAM per node

Recommended Environment
=======================

CCP tested on Ubuntu 16.04 x64. It will probably work on different OS, but
it's not officialy supported.

CCP tested on the environment created by Kargo, via fuel-ccp-installer, which
manage k8s, calico, docker and many other things. It will probably work on
different setup, but it's not officialy supported.

Current tested version of different components are:

=====================   ===========  ===========  =========================
Component               Min Version  Max Version  Comment
=====================   ===========  ===========  =========================
Kubernetes              1.2.4        1.3.5        1.3.0 to 1.3.3 wont work
Docker                  1.10.0       1.12.0
Calico-node             0.20.0       0.21.0
=====================   ===========  ===========  =========================

Additionaly, you will need to have working kube-proxy, kube-dns and docker
registry.

If you dont have running k8s environment, please check out 
:doc:`deploying-k8s-via-kargo`

.. NOTE:: All further steps assume what you already have a working k8s
 installation.

Install CCP Cli
---------------

To clone the CCP cli repo:

::

    git clone https://git.openstack.org/openstack/fuel-ccp

To install CCP cli and Python dependencies use:

::

    pip install fuel-ccp/

Create CCP cli configuration file:

::

    cat > $HOME/ccp.conf << EOF
    [DEFAULT]
    deploy_config = $HOME/ccp-globals.yaml

    [builder]
    push = True

    [registry]
    address = "127.0.0.1:31500"

    [kubernetes]
    namespace = "ccp"

    [repositories]
    skip_empty = True
    EOF

Create global CCP configuration file:

::

    cat > $HOME/ccp-globals.yaml << EOF
    ---
    configs:
        private_interface: eth0
        public_interface: eth1
        neutron_external_interface: eth2
    EOF

Make sure adjust it to your env, since this network configuration of dev env 
could change.

- ``private_interface`` - should point to eth with private ip addr.
- ``public_interface`` - should point to eth with public ip addr(you can use
  private iface here too, if you want to bind all services to internal network)
- ``neutron_external_interface`` - should point to eth without ip addr (it
  actually might be non-existing interface, CCP will create it).

Copy and edit(if needed) topology file:

::

    cat fuel-ccp/etc/topology-example.yaml >> $HOME/ccp-globals.yaml

Fetch CCP components repos:

::

    ccp --config-file=~/ccp.conf fetch

Build CCP components and push them into docker registry:

::

    ccp --config-file=~/ccp.conf build

Deploy OpenStack:

::

    ccp --config-file=~/ccp.conf deploy

If you want to deploy only specific components use:

::

    ccp --config-file=~/ccp.conf deploy -c COMPONENT_NAME1 COMPONENT_NAME2

Check deploy status
-------------------

Get all running pods:

::

    kubectl get pod --namespace ccp -o wide


Get all running jobs:

::

    kubectl get job --namespace ccp -o wide

.. NOTE:: You have to wait until all jobs will have a "1"(Successful) state.

Deploying test OpenStack environment
------------------------------------

Install openstack-client:

::

    pip install python-openstackclient

openrc file for current deployment was created in the current working dir.
To use it run:

::

    source openrc-ccp


Run test environment deploy script:

::

    bash fuel-ccp/tools/deploy-test-vms.sh -a create -n NUMBER_OF_VMS

This script will create flavor, upload cirrios image to glance, create network
and subnet and launch bunch of cirrios based VMs.


Accessing horizon and nova-vnc
------------------------------

Currently, we don't have any external proxy(like Ingress), so, for now, we
have to use k8s service "nodeport" feature to be able to access internal 
services.

Get nodeport of horizon service:

::

    kubectl get service --namespace ccp horizon -o yaml | awk '/nodePort: / {print $NF}'

Use external ip of any node in cluster plus this port to access horizon.

Get nodeport of nova-novncproxy service:

::

    kubectl get service --namespace ccp nova-novncproxy -o yaml | awk '/nodePort: / {print $NF}'

Take the url from Horizon console and replace "nova-novncproxy" string with an
external ip of any node in cluster plus nodeport from the service.

Destroying deployment
---------------------

To cleanup\destroy your environment run:

::

    ccp ~/ccp.conf cleanup

