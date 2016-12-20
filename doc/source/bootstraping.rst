.. _bootstrap:

=====================
Resource Bootstraping
=====================

Current section describes what and how can be bootstraped in the CCP.
There are several services, which provides bootstraping. It's:

- :ref:`networks`
- :ref:`images`
- :ref:`flavors`

.. _networks:

Network bootstraping
====================

Example:

::

 bootstrap:
  external:
   enable: false
   net_name: ext-net
   subnet_name: ext-subnet
   physnet: changeme
   network: changeme
   gateway: changeme
   nameserver: changeme
   pool:
     start: changeme
     end: changeme
 internal:
   enable: true
   net_name: int-net
   subnet_name: int-subnet
   network: 10.0.1.0/24
   gateway: 10.0.1.1
 router:
   name: ext-router

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

.. _images:

Image bootstraping
==================

Bootstrap for image allows to create/upload one image after deploying glance
services. To enable it, user needs to add lines mentioned below to ~/.ccp.yaml:

::

 configs:
   glance:
     bootstrap:
       enable: true
       image:
         url: http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img
         disk_format: qcow2
         name: cirros

This snippet adds **bootstrap** section for glance service and enable it.
Note, that by default **enable** option is False. So if user want to use
bootstraping he should explicitly set it to True.

The last part of the snippet describe image specific options.
All options should be specified, othrwise it will cause an error during job
execution:

+-------------+-----------------------------------------------+
| Name        | Description                                   |
+=============+===============================================+
| url         | url, which will be used for downloading image.|
+-------------+-----------------------------------------------+
| disk_format | format of image which will be used during     |
|             | creation image in the glance.                 |
+-------------+-----------------------------------------------+
| name        |  name of image, which will be created         |
|             |  in the glance.                               |
+-------------+-----------------------------------------------+

Creation of the image is handled by post glance deployment job
**glance-cirros-image-upload**, which uses Bash script from fuel-ccp-glance
repository: *service/files/glance-cirros-image-upload.sh.j2*

.. _flavors:

Flavor bootstraping
===================

The CCP automatically creates list of the default flavors, which are mentioned
in the table below:

+-----------+----+-------+------+-------+
| Name      | ID | RAM   | Disk | VCPUs |
+===========+====+=======+======+=======+
| m1.test   |  0 | 128   | 1    | 1     |
+-----------+----+-------+------+-------+
| m1.tiny   |  1 | 512   | 1    | 1     |
+-----------+----+-------+------+-------+
| m1.small  |  2 | 2048  | 20   | 1     |
+-----------+----+-------+------+-------+
| m1.medium |  3 | 4096  | 40   | 2     |
+-----------+----+-------+------+-------+
| m1.large  |  4 | 8192  | 80   | 4     |
+-----------+----+-------+------+-------+
| m1.xlarge |  5 | 16384 | 160  | 8     |
+-----------+----+-------+------+-------+

Creation of the flavors is handled by post nova deployment job
**nova-create-default-flavors**, which uses Bash script from fuel-ccp-nova
repository: *service/files/create-default-flavors.sh.j2*

Right now there is no option to specify custom flavors bootstraping in the
~/.ccp.yaml, but it can be added in future.
