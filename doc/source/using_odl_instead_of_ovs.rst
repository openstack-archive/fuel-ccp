.. _using_odl_instead_of_ovs:

==========================================
Using OpenDaylight instead of Open vSwitch
==========================================

This guide describes how to deploy and run OpenStack environment with
OpenDaylight ML2 Neutron plugin instead of the reference OpenVSwitch ML2 on top
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
  recommended setup please check out the `QuickStart Guide`_).
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
    versions:
        ovs_version: "2.5.1"

For the instructions for building images and deploying CCP refer to the
`QuickStart Guide`_.

To build only the opendaylight Docker image run:
::

    ccp deploy --config-file ccp.yaml build -c opendaylight

To deploy only the opendaylight component run:

::

    ccp deploy --config-file ccp.yaml deploy -c opendaylight

Check configuration
-------------------

To check that neutron has been configured to work with OpenDaylight, attach
to neutron-server container and run:
::

    $ cat etc/neutron/plugins/ml2/ml2_conf.ini | grep mechanism_drivers
    mechanism_drivers = opendaylight, logger

OpenDaylight creates only one bridge ``br-int``, with all traffic being managed by
OpenFlow, including routing and applying security group rules. To inspect flows,
attach to an openvswitch-vswitchd container and exec:
::

    ovs-ofctl -O OpenFlow13 dump-flows br-int

To connect to OpenDaylight console run the following command in its container:

::

    ./bin/client

.. _QuickStart Guide: http://fuel-ccp.readthedocs.io/en/latest/quickstart.html
