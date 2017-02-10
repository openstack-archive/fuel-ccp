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

===========   ===========  ===========  ======================================
Component     Min Version  Max Version  Comment
===========   ===========  ===========  ======================================
Kubernetes    1.5.1        1.5.x
Docker        1.10.0       1.13.x
Calico-node   0.20.0       1.0.x
===========   ===========  ===========  ======================================

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

.. NOTE:: Some commands below may require root permissions and require
  a few packages to be installed by the provisioning underlay:

  * python-pip
  * python-dev
  * python3-dev
  * python-netaddr
  * software-properties-common
  * python-setuptools
  * gcc

If you're deploying CCP from non-root user, make sure your user are in the
``docker`` group. Check if user is added to docker group

::

  id -Gn | grep docker

If not added you can add your user to docker group via:

::

  sudo usermod -a -G docker your_user_name

To clone the CCP CLI repo:

::

    git clone https://git.openstack.org/openstack/fuel-ccp

To install CCP CLI and Python dependencies use:

::

    sudo pip install fuel-ccp/

Create a local registry service (optional):

::

    bash fuel-ccp/tools/registry/deploy-registry.sh

When you deploy a local registry using that script, the registry
address is 127.0.0.1:31500.

Create CCP CLI configuration file:

::

    cat > ~/.ccp.yaml << EOF
    builder:
      push: True
    registry:
      address: "127.0.0.1:31500"
    repositories:
      skip_empty: True
    EOF

If you're using some other registry, please use its address instead.

Append default topology and edit it, if needed:

::

    cat fuel-ccp/etc/topology-example.yaml >> ~/.ccp.yaml

For example, you may want to install Stacklight to collect Openstack logs.
See :doc:`monitoring_and_logging` for the deployment of monitoring and
logging services.

Append global CCP configuration:

::

    cat >> ~/.ccp.yaml << EOF
    configs:
        private_interface: eth0
        public_interface: eth1
        neutron:
          physnets:
            - name: "physnet1"
              bridge_name: "br-ex"
              interface: "ens8"
              flat: true
              vlan_range: "1001:1030"
    EOF

Make sure to adjust it to your environment, since the network configuration of
your environment may be different.

- ``private_interface`` - should point to eth with private ip address.
- ``public_interface`` - should point to eth with public ip address (you can
  use private iface here, if you want to bind all services to internal
  network)
- ``neutron.physnets`` - should contain description of Neutron physical
  networks. If only internal networking with VXLAN segmentation required,
  this option can be empty.
  ``name`` is name of physnet in Neutron.
  ``bridge_name`` is name of OVS bridge.
  ``interface`` should point to eth without ip addr.
  ``flat`` allow to use this network as flat, without segmentation.
  ``vlan_range`` is range of allowed VLANs, should be false if VLAN
  segmenantion is not allowed.

For the additional info about bootstrapping configuration please read the
:doc:`bootstrapping`.

Append replicas configuration:

::

    cat >> ~/.ccp.yaml << EOF
    replicas:
      galera: 3
      rabbitmq: 3
    EOF

This will sets the number of replicas to create for each service. We need 3
replicas for galera and rabbitmq cluster.

Fetch CCP components repos:

::

    ccp fetch

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

    ccp deploy -c etcd galera keystone memcached

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
