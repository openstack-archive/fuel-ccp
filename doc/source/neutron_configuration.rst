.. _neutron_configuration:

=====================
Neutron Configuration
=====================

This guide provides instructions on configuring Neutron with Fuel-CCP.

Tenant network types
====================

By default Neutron is configured to use VxLAN segmentation but it is possible
to specify other network types like VLAN or flat.

To do so add the following lines to the ``configs.neutron`` section of the CCP
configuration file:

::

    ml2:
      tenant_network_types:
        - "vlan"
        - "vxlan"

Here ``tenant_network_types`` is an ordered list of network types to allocate as
tenant networks. Enabling several network types allows creating networks with
``--provider:network_type`` equalling one of these types, if ``--provider:network_type``
is not specified then the first type from the ``tenant_network_types`` list will
be used.

It is also possible to specify VxLAN VNI and VLAN ID ranges.

VxLAN VNI ranges are configured in ``configs.neutron.ml2`` section with default range
being "1:1000".

::

    ml2:
      tenant_network_types:
        - "vxlan"
      vni_ranges:
        - "1000:5000"

VLAN ranges are configured per each physical network in the ``configs.neutron.physnets`` section:

::

    physnets:
      - name: "physnet1"
        bridge_name: "br-ex"
        interface: "eno2"
        flat: false
        vlan_range: "1050:2050"
        dpdk: false

For more information on configuring physical networks refer to the `QuickStart Guide`_.

.. _QuickStart Guide: http://fuel-ccp.readthedocs.io/en/latest/quickstart.html
