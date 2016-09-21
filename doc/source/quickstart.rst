.. _quickstart:

===========
Quick Start
===========

This guide provides a step by step instruction of how to deploy CCP on bare
metal or a virtual machine.

Recommended Environment
=======================

CCP was tested on Ubuntu 16.04 x64. It will probably work on different OSes,
but it's not officialy supported.

CCP was tested on the environment created by Kargo, via
`fuel-ccp-installer <https://github.com/openstack/fuel-ccp-installer>`__,
which manages k8s, calico, docker and many other things. It will probably work
on different setup, but it's not officialy supported.

Current tested version of different components are:

=====================   ===========  ===========  =========================
Component               Min Version  Max Version  Comment
=====================   ===========  ===========  =========================
Kubernetes              1.2.4        1.3.5        1.3.0 to 1.3.3 won't work
Docker                  1.10.0       1.12.0
Calico-node             0.20.0       0.21.0
=====================   ===========  ===========  =========================

Additionaly, you will need to have working kube-proxy, kube-dns and docker
registry.

If you don't have a running k8s environment, please check out `this guide
<http://fuel-ccp-installer.readthedocs.io/en/latest/quickstart.html>`__

.. WARNING:: All further steps assume that you already have a working k8s
 installation.

Deploy CCP
==========

Install CCP CLI
---------------

.. NOTE:: Some commands below may require root permissions

To clone the CCP CLI repo:

::

    git clone https://git.openstack.org/openstack/fuel-ccp

To install CCP CLI and Python dependencies use:

::

    apt-get install gcc
    pip install fuel-ccp/

Create CCP CLI configuration file with a given example
docker registry address:

::

    mkdir /etc/ccp
    cat > /etc/ccp/ccp.yaml << EOF
    builder:
      push: True
    registry:
      address: "127.0.0.1:31500"
    repositories:
      skip_empty: True
    EOF

Append default topology and edit it, if needed:

::

    cat fuel-ccp/etc/topology-example.yaml >> /etc/ccp/ccp.yaml

Append global CCP configuration:

::

    cat >> /etc/ccp/ccp.yaml << EOF
    configs:
        private_interface: eth0
        public_interface: eth1
        neutron_external_interface: eth2
    EOF

Make sure to adjust it to your environment, since the network configuration of
your environment may be different.

- ``private_interface`` - should point to eth with private ip address.
- ``public_interface`` - should point to eth with public ip address (you can
  use private iface here, if you want to bind all services to internal
  network)
- ``neutron_external_interface`` - should point to eth without ip addr (it
  actually might be non-existing interface, CCP will create it).

Fetch CCP components repos:

::

    ccp fetch

Create a registry service (optional, depends on the given registry address):

::

    bash tools/registry/deploy-registry.sh

Build CCP components and push them into the Docker Registry:

::

    ccp build

Deploy OpenStack:

::

    ccp deploy

If you want to deploy only specific components use:

::

    ccp deploy -c COMPONENT_NAME1 COMPONENT_NAME2

For example:

::

    ccp deploy -c etcd mariadb keystone

Check deploy status
-------------------

By default, CCP deploying all components into "ccp" k8s
`namespace <http://kubernetes.io/docs/user-guide/namespaces/>`__.
You could set context for all kubectl commands to use this namespace:

::

    kubectl config set-context ccp --namespace ccp
    kubectl config use-context ccp

Get all running pods:

::

    kubectl get pod -o wide


Get all running jobs:

::

    kubectl get job -o wide

.. NOTE:: Deployment is successful when all jobs have "1" (Successful) state.

Deploying test OpenStack environment
------------------------------------

Install openstack-client:

::

    pip install python-openstackclient

openrc file for current deployment was created in the current working
directory.
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

Currently, we don't have any external proxy (like Ingress), so, for now, we
have to use k8s service "nodePort" feature to be able to access internal
services.

Get nodePort of horizon service:

::

    kubectl get service horizon -o yaml | awk '/nodePort: / {print $NF}'

Use external ip of any node in cluster plus this port to access horizon.

Get nodePort of nova-novncproxy service:

::

    kubectl get service nova-novncproxy -o yaml | awk '/nodePort: / {print $NF}'

Take the url from Horizon console and replace "nova-novncproxy" string with an
external IP of any node in cluster plus nodeport from the service.

Cleanup deployment
---------------------

To cleanup your environment run:

::

    ccp cleanup

This will delete all VMs created by OpenStack and destroy all neutron networks.
After it's done it will delete all k8s pods in this deployment.
