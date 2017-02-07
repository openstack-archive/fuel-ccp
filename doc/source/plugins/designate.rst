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
  servers Designate manages;

* ``designate-zone-manager`` – is a service that handles all periodic tasks
  related to the zone shard it is responsible for;

* ``designate-sink`` – is an optional service which listens for event
  notifications, such as compute.instance.create.end. Currently supports Nova
  and Neutron;

* ``designate-agent`` – pool manager agent backend. This is an optional
  service. Agent uses an extension of the DNS protocol to send management
  requests to the remote agent processes, where the requests will be processed.

CCP components have names of components above, ``designate-sink`` and
``designate-agent`` components are *optional*.

Configuration
~~~~~~~~~~~~~

Designate has configurable options for each component, which could be
set for specific node with :ref:`nodes` configs section. These options
are: `workers` and `threads`. They are placed in
`designate.service.<service name>.<workers or threads>` configs path. Also,
designate CCP plugin allows to configure defaults of domain purge: `interval`,
`batch_size` and `time threshold`.

Installation
~~~~~~~~~~~~

Currently designate fuel-ccp plugin is not supported by default, so
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
     - designate-pool-manager
     - designate-zone-manager


   Components ``designate-sink`` and ``designate-agent`` are optional and could
   not be deployed.

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

Unfortunately, domain requires at least one server, created by designate with
command :command:`designate server-create`, so you cannot use only horizon for
full dns management.
