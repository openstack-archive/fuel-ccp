.. _bootstrap:

======================
Resource Bootstrapping
======================

Current section describes what and how can be bootstrapped in the CCP.
There are several services, which have bootstrapping. It's:

- :ref:`networks`
- :ref:`images`
- :ref:`flavors`

.. _networks:

Network bootstrapping
~~~~~~~~~~~~~~~~~~~~~

This section allows to configure internal and external networking in neutron.
Snippet below demonstrates all available options:

::

 configs:
   neutron:
     bootstrap:
       internal:
         enable: true
         net_name: int-net
         subnet_name: int-subnet
         network: 10.0.1.0/24
         gateway: 10.0.1.1
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
       router:
         name: ext-router

First part configures internal network. All options have default values:

.. list-table:: **Internal network configuration options**
   :widths: 10 25 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - enable
     - boolean flag, which turns on/off bootstrap.
     - true
   * - net_name
     - Name of the internal network, which will be created in neutron.
     - int-net
   * - subnet_name
     - Name of the subnet in internal network, which will be created in
       neutron.
     - int-subnet
   * - network
     - CIDR of the internal network for allocating internal IP addresses.
     - 10.0.1.0/24
   * - gateway
     - Gateway for subnet in the internal network.
     - 10.0.1.1

Second part describes external network configuration. Bootstrapping for
external network is disabled by default and user should specify all options
after turning it on, because most of them don't have default values.

.. list-table:: **External network configuration options**
   :widths: 10 25 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - enable
     - boolean flag, which turns on/off bootstrap.
     - false
   * - net_name
     - Name of the external network, which will be created in neutron. Default
       value can be used.
     - ext-net
   * - subnet_name
     - Name of the subnet in external network, which will be created in
       neutron. Default value can be used.
     - ext-subnet
   * - physnet
     - Name of the physnet, which was defined in **physnets** section.
     - --
   * - network
     - CIDR of the external network for allocating external IP addresses.
     - --
   * - gateway
     - Gateway for subnet in the external network.
     - --
   * - nameserver
     - DNS server for subnet in external network.
     - --
   * - pool
     - Pool of the addresses from external network, which can be used for
       association with Openstack VMs. Should be specified by using nested
       keys: **start** and **end**, which requires corresponding IP addresses.
     - --

The last section is a router configuration. It allows to specify name of the
router, which will be created in neutron. Both networks will be connected with
this router by default (except situation, when bootstrapping only for internal
network is enabled).
If bootstrapping is enabled at least for one network, router will be
automatically created. In case, when user does not want to change default
router name (**ext-router**) this section can be skipped in config.

Creation of the networks is handled by neutron post deployment jobs
**neutron-bootstrap-***, which call openstackclient with specified parameters.

Example
-------

As a simple example let's use snippet below:

::

 configs:
   neutron:
     physnets:
       - name: ext-physnet
         bridge_name: br-ex
         interface: ens5
         flat: true
         vlan_range: false
     bootstrap:
       # external network parameters
       external:
         enable: true
         physnet: ext-physnet
         network: 10.90.2.0/24
         gateway: 10.90.2.1
         nameserver: 8.8.8.8
         pool:
           start: 10.90.2.10
           end: 10.90.2.250

Now go through all options and comments, what and why was choosen.
First of all need to note, that interface **ens5** and bridge **br-ex**
are used for creation physnet. Then in bootstrap section name of created
physnet is used for providing references for external network.
Google public DNS server (*8.8.8.8*) is used as a **nameserver**.
The main tricky thing here is an IP range and a gateway. In the current example
Host for Kubernetes cluster has interface with IP address equal to specified IP
in the gateway field. It's usually necessary for providing access from
Openstack VMs to service APIs.
At the end don't forget to be careful with pool of available external
addresses. It should not contain IPs outside of cluster.

.. _images:

Image bootstrapping
~~~~~~~~~~~~~~~~~~~

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

This snippet adds **bootstrap** section for glance service and enables it.
Note, that by default **enable** option is False. So if user wants to use
bootstrapping he should explicitly set it to True.

The last part of the snippet describes image specific options.
All options should be specified, otherwise it will cause an error during job
execution:

.. list-table:: **Glance image bootstrapping default configuration options**
   :widths: 10 25 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - url
     - url, which will be used for downloading image.
     - http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img
   * - disk_format
     - format of the image which will be used during image creation in the
       glance.
     - qcow2
   * - name
     - name of the image, which will be created in the glance.
     - cirros

Creation of the image is handled by glance post deployment job
**glance-cirros-image-upload**, which uses Bash script from fuel-ccp-glance
repository: ``service/files/glance-cirros-image-upload.sh.j2``.

.. _flavors:

Flavor bootstrapping
~~~~~~~~~~~~~~~~~~~~

The CCP automatically creates list of the default flavors, which are mentioned
in the table below:

========== == ====== ===== =====
 Name      ID  RAM    Disk VCPUs
========== == ====== ===== =====
 m1.test    0  128    1    1
 m1.tiny    1  512    1    1
 m1.small   2  2048   20   1
 m1.medium  3  4096   40   2
 m1.large   4  8192   80   4
 m1.xlarge  5  16384  160  8
========== == ====== ===== =====

The corresponding section in the config file looks like:

::

 configs:
   nova:
     bootstrap:
       enable: true
       flavors:
         - name: m1.test
           id: 0
           ram: 128
           disk: 1
           vcpus: 1
         - name: m1.tiny
           id: 1
           ram: 512
           disk: 1
           vcpus: 1
         - name: m1.small
           id: 2
           ram: 2048
           disk: 20
           vcpus: 1
         - name: m1.medium
           id: 3
           ram: 4096
           disk: 40
           vcpus: 2
         - name: m1.large
           id: 4
           ram: 8192
           disk: 80
           vcpus: 4
         - name: m1.xlarge
           id: 5
           ram: 16384
           disk: 160
           vcpus: 8

Creation of the flavors is handled by nova post deployment job
**nova-bootstrap-flavors**, which uses Bash script from fuel-ccp-nova
repository: ``service/files/create-flavors.sh.j2``.

User also can specify to bootstrap custom flavors. Similarly previous sections
it can be done by adding the following snippet to ~/.ccp.yaml:

::

 configs:
   nova:
     bootstrap:
       enable: true
       flavors:
         - name: custom_name1
           id: 42
           ram: 1024
           disk: 1
           vcpus: 1
         - name: custom_name2
           id: 43
           ram: 2024
           disk: 2
           vcpus: 2

.. WARNING:: New list of custom flavors will overwrite default flavors and
             they will not be created. To avoid it, just copy paste definition
             of default flavors to your config and then extend it by new custom
             flavors.

This snippet adds **bootstrap** section for nova service. Note, that by default
**enable** option is True. So if user doesn't want to use bootstrapping he
should explicitly set it to False.

The last part of the snippet describes list of flavors with related options.
All options should be specified, otherwise it will cause an error during job
execution:

.. list-table:: **Nova flavor bootstrapping configuration options**
   :widths: 10 25 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - name
     - Name of the custom flavor.
     - --
   * - id
     - Indentifier of the flavor.
     - --
   * - ram
     - Vaqlue of the RAM memory for the current flavor.
     - --
   * - disk
     - Disk size for the curretn flavor.
     - --
   * - vcpus
     - Number of the vcpus for the current flavor.
     - --
