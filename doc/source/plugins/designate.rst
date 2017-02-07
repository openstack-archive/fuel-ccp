.. _designate:

==================================
Designate CCP plugin documentation
==================================

This is Fuel-CCP plugin for OpenStack Designate service.

Original designate service developer docs
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

* ``designate-pool-manager`` – is a service that manages the states of the DNS
  servers Designate manages;

* ``designate-zone-manager`` – is a service that handle all periodic tasks
  relating to the zone shard it is responsible for;

* ``designate-sink`` – is an optional service which listens for event
  Notifications, such as compute.instance.create.end, handlers are available
  for Nova and Neutron;

* ``designate-agent`` – is an optional service for pool-manager. This backend
  uses an extension of the DNS protocol itself to send management requests to
  the remote agent processes, where the requests will be actioned.

CCP components have names of components above and ``designate-sink`` and
``designate-agent`` components are *optional*.

Configuration
~~~~~~~~~~~~~

Designate have configurable options for each component, which could be
specified for specific node with :ref:`nodes` configs section. These optins
are: `workers` and `threads`. They are place in
`designate.service.<service name>.<workers or threads>` configs path. Also,
designate CCP plugin allows to configure defaults of domain purge: `interval`,
`batch_size` and `time threshold`.

Installation
~~~~~~~~~~~~

Currently designate fuel-ccp plugin is not supported by default, so
installation has next steps:

#. Add to CCP configuration file to ``repositories.repos`` list next item:

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
domains and records. It already available in horizon and activates, when
designate is on board. Domain panel places in ``Projects`` menu.

Unfortunately, domain requires at least one server, created by designate with
command :command:`designate server-create`, so you cannot only use horizon for
full dns managing.
