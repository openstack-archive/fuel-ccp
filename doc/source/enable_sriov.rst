.. _enable_sriov:

============
SR-IOV guide
============

This guide provides an instruction for enabling SR-IOV functionality in Fuel CCP.

Introduction
============

The SR-IOV specification defines a standardized mechanism to virtualize PCIe devices. This mechanism can virtualize
a single PCIe Ethernet controller to appear as multiple PCIe devices. Each device can be directly assigned to
an instance, bypassing the hypervisor and virtual switch layer. As a result, users are able to achieve low latency and
near-line wire speed.

The following terms are used throughout this document:

====  ======================================================================================
Term  Definition
====  ======================================================================================
PF    Physical Function. The physical Ethernet controller that supports SR-IOV.
VF    Virtual Function. The virtual PCIe device created from a physical Ethernet controller.
====  ======================================================================================

Prerequirements
---------------

1. Ensure that a host has a SR-IOV capable device. One way of identifying whether a device supports SR-IOV is to check
for an SR-IOV capability in the device configuration. The device configuration also contains the number of VFs
the device can support.  The example below shows a simple test to determine if the device located at the bus, device,
and function number 1:00.0 can support SR-IOV.

::

    # lspci -vvv -s 02:00.0 | grep -A 9 SR-IOV
        Capabilities: [160 v1] Single Root I/O Virtualization (SR-IOV)
                IOVCap: Migration-, Interrupt Message Number: 000
                IOVCtl: Enable+ Migration- Interrupt- MSE+ ARIHierarchy+
                IOVSta: Migration-
                Initial VFs: 32, Total VFs: 32, Number of VFs: 7, Function Dependency Link: 00
                VF offset: 16, stride: 1, Device ID: 154c
                Supported Page Size: 00000553, System Page Size: 00000001
                Region 0: Memory at 0000000090400000 (64-bit, prefetchable)
                Region 3: Memory at 0000000092c20000 (64-bit, prefetchable)
                VF Migration: offset: 00000000, BIR: 0

2. Enable IOMMU in Linux by adding `intel_iommu=on` to the kernel parameters, for example, using GRUB.

3. Bring up the PF.

::

    # ip l set dev ens2f1 up

4. Allocate the VFs, for example via the PCI SYS interface:

::

    # echo '7' > /sys/class/net/ens2f1/device/sriov_numvfs

5. Verify that the VFs have been created.

::

    # ip l show ens2f1
    5: ens2f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000
    link/ether 0c:c4:7a:bd:42:ac brd ff:ff:ff:ff:ff:ff
    vf 0 MAC 00:00:00:00:00:00, spoof checking on, link-state auto
    vf 1 MAC 00:00:00:00:00:00, spoof checking on, link-state auto
    vf 2 MAC 00:00:00:00:00:00, spoof checking on, link-state auto
    vf 3 MAC 00:00:00:00:00:00, spoof checking on, link-state auto
    vf 4 MAC 00:00:00:00:00:00, spoof checking on, link-state auto
    vf 5 MAC 00:00:00:00:00:00, spoof checking on, link-state auto
    vf 6 MAC 00:00:00:00:00:00, spoof checking on, link-state auto


Deploy CCP with SR-IOV
======================

Neutron
-------

In OpenStack SR-IOV doesn't work with VxLAN tunneling, that is why it is required to enable either VLAN of
flat tenant network type in the `configs.neutron` section of the CCP configuration file:

::

    ml2:
      tenant_network_types:
        - "vlan"

All Neutron SR-IOV specific parameters are located in the `configs.neutron.sriov` section. Example configuration:

::

    sriov:
      enabled: true
      devices:
        - name: "ens2f1"
          physnets:
            - "physnet1"
          exclude_vfs:
            - 0000:02:00.2
            - 0000:02:00.3

* `enabled` - Boolean. Enables and disables the SR-IOV in Neutron, `false` by default.

* `devices` - List. A node-specific list of SR-IOV devices. Each element of the list has 2 mandatory fields: `name` and `physnets`.
    * `name` is a name of the SR-IOV interface.
    * `physnets` is a list of of names of physical networks a given device maps to.
    * If `exclude_vfs` is omitted all the VFs associated with a given device may be configured by the agent. To exclude specific VFs, add them to the `exclude_devices` parameter as shown above.

A new role should be added to compute nodes: `neutron-sriov-nic-agent`.

Nova
----

All Nova SR-IOV specific parameters are located in the `configs.nova.sriov` section. Example configuration:

::

    sriov:
      enabled: true
      pci_alias:
        - name: "82599ES"
          product_id: "10fb"
          vendor_id: "8086"
        - name: "X710"
          product_id: "1572"
          vendor_id: "8086"
      pci_passthrough_whitelist:
         - devname: "ens2f1"
           physical_network: "physnet1"

* `enabled` - Boolean. Enables and disables the SR-IOV in Nova, `false` by default.

* `pci_alias` - List, optional. An alias for a PCI passthrough device requirement. This allows users to specify the alias in the
extra_spec for a flavor, without needing to repeat all the PCI property requirements.

* `pci_passthrough_whitelist` - List. White list of PCI devices available to VMs.
    * `devname` is a name of the SR-IOV interface.
    * `physical_network` - name of a physical network to map a device to.

Additionally it is required to add `PciPassthroughFilter` to the list of enable filters in Nova scheduler:

::

   scheduler:
     enabled_filters:
       - RetryFilter
       - AvailabilityZoneFilter
       - RamFilter
       - DiskFilter
       - ComputeFilter
       - ComputeCapabilitiesFilter
       - ImagePropertiesFilter
       - ServerGroupAntiAffinityFilter
       - ServerGroupAffinityFilter
       - SameHostFilter
       - DifferentHostFilter
       - PciPassthroughFilter

Sample CCP configuration
------------------------
::

    services:
      database:
        service_def: galera
      rpc:
        service_def: rabbitmq
      notifications:
        service_def: rabbitmq
    nodes:
      node1:
        roles:
          - db
          - messaging
          - controller
          - openvswitch
      node[2-3]:
        roles:
          - db
          - messaging
          - compute
          - openvswitch
    roles:
      db:
        - database
      messaging:
        - rpc
        - notifications
      controller:
        - etcd
        - glance-api
        - glance-registry
        - heat-api-cfn
        - heat-api
        - heat-engine
        - horizon
        - keystone
        - memcached
        - neutron-dhcp-agent
        - neutron-l3-agent
        - neutron-metadata-agent
        - neutron-server
        - nova-api
        - nova-conductor
        - nova-consoleauth
        - nova-novncproxy
        - nova-scheduler
      compute:
        - neutron-sriov-nic-agent
        - nova-compute
        - nova-libvirt
      openvswitch:
        - neutron-openvswitch-agent
        - openvswitch-db
        - openvswitch-vswitchd
    configs:
      private_interface: ens1f0
      neutron:
        physnets:
          - name: "physnet1"
            bridge_name: "br-ex"
            interface: "ens1f1"
            flat: false
            vlan_range: "50:1030"
        ml2:
          tenant_network_types:
            - "vlan"
        sriov:
          enabled: true
          devices:
            - name: "ens2f1"
              physnets:
                - "physnet1"
              exclude_vfs:
                - 0000:02:00.2
                - 0000:02:00.3
      nova:
        sriov:
          enabled: true
          pci_alias:
            - name: "82599ES"
              product_id: "10fb"
              vendor_id: "8086"
            - name: "X710"
              product_id: "1572"
              vendor_id: "8086"
          pci_passthrough_whitelist:
             - devname: "ens2f1"
               physical_network: "physnet1"
        scheduler:
          enabled_filters:
            - RetryFilter
            - AvailabilityZoneFilter
            - RamFilter
            - DiskFilter
            - ComputeFilter
            - ComputeCapabilitiesFilter
            - ImagePropertiesFilter
            - ServerGroupAntiAffinityFilter
            - ServerGroupAffinityFilter
            - SameHostFilter
            - DifferentHostFilter
            - PciPassthroughFilter


Known limitations
=================

* When using Quality of Service (QoS), `max_burst_kbps` (burst over `max_kbps`) is not supported. In addition, `max_kbps` is rounded to Mbps.
* Security groups are not supported when using SR-IOV, thus, the firewall driver is disabled.
* SR-IOV is not integrated into the OpenStack Dashboard (horizon). Users must use the CLI or API to configure SR-IOV interfaces.
* Live migration is not supported for instances with SR-IOV ports.
