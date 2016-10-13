.. _ironic:

============
Ironic guide
============

This guide provides an instruction for adding Ironic support for
CCP deployment.

Underlay
~~~~~~~~

.. NOTE:: That it's not the CCP responsibility to manage networking for baremetal servers.
   Ironic assumes that networking is properly configured in underlay.

Prerequirements
---------------

* Ironic conductor has access to IPMI of baremetal servers
  or to hypervisor when baremetal server is simulated by VM.
* Baremetal servers are attached to physical baremetal network.
* Swift, Ironic API endpoints, neutron-dhcp-agent, PXE/iPXE services
  are accessible from baremetal network.
* Swift and Ironic API endpoints has valid SSL certificate
  or Ironic deploy driver allows unverified connections.
* Baremetal network is accessible from Ironic conductor.

Neutron
~~~~~~~

Prerequirements
---------------

Ironic requires single flat network in Neutron which has L2 connectivity to physical baremetal network
and appropriate L3 settings.

Example case when required access to Ironic services provided via Neutron external network:

::

    # Create external network
    neutron net-create ext --router:external true --shared --provider:network_type flat --provider:physical_network physnet1

    # Create subnet in external network, here 10.200.1.1 - is provider gateway
    neutron subnet-create --name ext --gateway 10.200.1.1 --allocation-pool start=10.200.1.10,end=10.200.1.200 ext 10.200.1.0/24

    # Create internal network, here physnet2 is mapped to physical baremetal network
    neutron net-create --shared --provider:network_type flat --provider:physical_network physnet2 baremetal

    # Create subnet in internal network, here 10.200.2.1 - is address of Neutron router, 10.11.0.174 - is address of DNS server which can resolve external endpoints
    neutron subnet-create --name baremetal --gateway 10.200.2.1 --allocation-pool start=10.200.2.10,end=10.200.2.200 --dns-nameserver 10.11.0.174 baremetal 10.200.2.0/24

    # Create router and connect networks
    neutron router-create r1
    neutron router-gateway-set r1 ext
    neutron router-interface-add r1 baremetal

Example case when required access to Ironic services provided directly from baremetal network:

::

    # Create internal network, here physnet2 is mapped to physical baremetal network
    neutron net-create --shared --provider:network_type flat --provider:physical_network physnet2 baremetal

    # Create subnet in internal network, here 10.200.2.1 - is address Underlay router, which provides required connectivity
    neutron subnet-create --name baremetal --gateway 10.200.2.1 --allocation-pool start=10.200.2.10,end=10.200.2.200 --dns-nameserver 10.11.0.174 baremetal 10.200.2.0/24

Swift
~~~~~

Prerequirements
---------------

Make sure that Radosgw is deployed, available and configured in Glance as default Swift storage backend.
Refer to :doc:`ceph` guide for deploy Radosgw and configure Glance.

Ironic
~~~~~~

Prerequirements
---------------

* Underlay networking
* Neutron networking
* Glance/Swift configuration

Deploy CCP with Ironic
======================

In order to deploy CCP with Ironic you have to deploy following components:
* ironic-api
* ironic-conductor
* nova-compute-ironic

.. NOTE:: nova-compute-ironic is same as regular nova-compute service,
   but with special compute_driver required for integration Nova with Ironic.
   It requires neutron-openvswitch-agent running on same host.
   Is not possible to deploy nova-compute-ironic and regular nova-compute on same host.
   nova-compute-ironic has no significant load and can be deployed on controller node.

Ironic requires single endpoints for Swift and API accessible from remote baremetal network,
Ingress should be configured.

Example of ccp.yaml:

::

    roles:
      controller:
        - ironic-api
        - ironic-conductor
        - nova-compute-ironic
    configs:
      neutron:
        physnets:
          - name: "physnet1"
            bridge_name: "br-ex"
            interface: "ens8"
            flat: true
            vlan_range: "1001:1030"
          - name: "physnet2"
            bridge_name: "br-bm"
            interface: "ens9"
            flat: true
            vlan_range: "1001:1030"
      ceph:
        fsid: "a1adbec9-98cb-4d75-a236-2c595b73a8de"
        mon_host: "10.11.0.214"
      radosgw:
        key: "AQCDIStYGty1ERAALFeBif/6Y49s9S/hyVFXyw=="
      glance:
        swift:
          enable: true
      ingress:
        enabled: true

Now you’re ready to deploy Ironic to existing CCP cluster.

::

    ccp deploy -c ironic-api ironic-conductor nova-compute-ironic


Provision baremetal instance
============================

Depends on selected deploy driver, provision procedure may differ.
Basically provision require following steps:
* Upload service and user's images to Glance
* Create baremetal node in Ironic
* Create node port in Ironic
* Create appropriate flavor in Nova
* Boot instance

Example with agent_ssh driver:

.. NOTE:: Agent drivers will download images from Swift endpoint,
   in case you using self-signed certificates, make sure that agent allows unverified SSL connections.

Upload service kernel/ramdisk images, required for driver:

::

    wget https://tarballs.openstack.org/ironic-python-agent/tinyipa/files/tinyipa-stable-newton.vmlinuz
    wget https://tarballs.openstack.org/ironic-python-agent/tinyipa/files/tinyipa-stable-newton.gz

    glance image-create --name kernel \
    --visibility public \
    --disk-format aki --container-format aki \
    --file tinyipa-stable-newton.vmlinuz

    glance image-create --name ramdisk \
    --visibility public \
    --disk-format ari --container-format ari \
    --file tinyipa-stable-newton.gz

Upload user's image, which should be provisioned on baremetal node:

::

    wget http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img

    glance image-create --name cirros \
    --visibility public \
    --disk-format qcow2 \
    --container-format bare \
    --file cirros-0.3.4-x86_64-disk.img \
    --property hypervisor_type='baremetal' \
    --property cpu_arch='x86_64'

Create baremetal node with port in Ironic:

::

    ironic node-create \
    -n vm_node1 \
    -d agent_ssh \
    -i deploy_kernel=2fe932bf-a961-4d09-b0b0-72806edf05a4 \  # UUID of uploaded kernel image
    -i deploy_ramdisk=5546dead-e8a4-4ebd-93cf-a118580c33d5 \ # UUID of uploaded ramdisk image
    -i ssh_address=10.11.0.1 \ # address of hypervisor with VM (simulated baremetal server)
    -i ssh_username=user \ # credentials for ssh access to hypervisor
    -i ssh_password=password \
    -i ssh_virt_type=virsh \
    -p cpus=1 \
    -p memory_mb=3072 \
    -p local_gb=150 \
    -p cpu_arch=x86_64

    ironic port-create -n vm_node1 -a 52:54:00:a4:eb:d5 # MAC address of baremetal server

Verify that node is available as Nova hypervisor:

::

    ironic node-validate vm_node1 # Should has no errors in management, power interfaces
    nova hypervisor-show 1 # Should output correct information about resources (cpu, mem, disk)

Create nova flavor:

::

    nova flavor-create bm_flavor auto 3072 150 1
    nova flavor-key bm_flavor set cpu_arch=x86_64

Boot baremetal instance:

::

    nova boot --flavor bm_flavor \
    --image 11991c4e-95fd-4ad1-87a3-c67ec31c46f3 \ # Uploaded Cirros image
    --nic net-id=0824d199-5c2a-4c25-be2c-14b5ab5a2838 \ # UUID of Neutron baremetal network
    bm_inst1

Troubleshooting
---------------

If something goes wrong, please ensure first:
* You understand how Ironic works
* Underlay networking is configured properly

For more information about issues, you may enable ironic.logging_debug
and check logs of following pods:
- nova-scheduler
- nova-compute-ironic
- ironic-api
- ironic-conductor
- neutron-server
