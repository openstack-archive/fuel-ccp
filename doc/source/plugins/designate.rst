.. _designate:

==================================
Designate CCP plugin documentation
==================================

This is Fuel-CCP plugin for OpenStack Designate service.

Original designate service developer docs are
placed `here <http://docs.openstack.org/developer/designate/>`_.

Overview
~~~~~~~~

Designate provides DNSaaS services for OpenStack. Designate architecture has
next components:

* ``designate-api`` – provides the standard OpenStack style REST API service;

* ``designate-central`` –  is the service that handles RPC requests via the MQ,
  it coordinates the persistent storage of data and applies business logic to
  data from the API;

* ``designate-mdns`` – is the service that sends DNS NOTIFY and answers zone
  transfer (AXFR) requests;

* ``designate-pool-manager`` – is a service that handles the states of the DNS
  servers Designate manages. Since mitaka replaced with ``designate-worker``
  service;

* ``designate-zone-manager`` – is a service that handles all periodic tasks
  related to the zone shard it is responsible for;

* ``designate-sink`` – is an optional service which listens for event
  notifications, such as compute.instance.create.end. Currently supports Nova
  and Neutron;

* ``designate-agent`` – pool manager agent backend. This is an optional
  service. Agent uses an extension of the DNS protocol to send management
  requests to the remote agent processes, where the requests will be processed.

CCP components comprises next services:

* ``designate-api``;

* ``designate-central``;

* ``designate-mdns``, which contains three containers: ``designate-mdns``
  service, ``designate-worker`` and ``designate-backend-bind9`` - container,
  which implements bind9 backend for designate. All of them works in
  collaboration and provide ability to create and manage zones and records;

* ``designate-agent``;

* ``designate-sink``;

* ``designate-pool-manager``;

* ``designate-zone-manager``.

Three last services are optional and can't be omitted during deployment.

Configuration
~~~~~~~~~~~~~

Designate has configurable options for each component, which could be
set for specific node with :ref:`nodes` configs section. These options
are: `workers` and `threads`. They are placed in
`designate.service.<service name>.<workers or threads>` configs path. Also,
designate CCP plugin allows to configure defaults of domain purge: `interval`,
`batch_size` and `time threshold`.

CCP designate plugin has bind9 backend implemented; it enabled by default with
option `designate.backend`. If you want to turn off any backend, clear option's
value - then fake backend, which has no effect for designate will be enabled.

Installation
~~~~~~~~~~~~

Currently designate CCP plugin is not supported by default, so
installation has next steps:

#. Add next item to ``repositories.repos`` list of CCP configuration file:

   ::

     - git_url: https://git.openstack.org/openstack/fuel-ccp-designate
       name: fuel-ccp-designate

#. Add designate components to roles list. Next components are required:

   ::

     - designate-api
     - designate-central
     - designate-mdns

   Components ``designate-sink``, ``designate-agent``,
   ``designate-zone-manager`` and ``designate-pool-manager`` are optional and
   could not be deployed.

#. Fetch, build, deploy components.

#. Install `python-designateclient` and also install/update
   `python-openstackclient` with pip:

   ::

      pip install --user -U python-designateclient python-openstackclient


Dashboard plugin
~~~~~~~~~~~~~~~~

Designate has horizon dashboard plugin, which allows to create and manage
domains and records. It is already available in horizon and is activated when
designate is on board. Domain panel is placed in ``Projects`` menu.
