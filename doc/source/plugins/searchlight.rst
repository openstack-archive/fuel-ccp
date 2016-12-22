.. _searchlight:

====================================
Searchlight CCP plugin documentation
====================================

This is Fuel-CCP plugin for OpenStack Searchlight service.

Original searchlight service developer docs
placed `here <http://docs.openstack.org/developer/searchlight/>`_.

Overview
~~~~~~~~

The Searchlight project provides indexing and search capabilities across
OpenStack resources. Its goal is to achieve high performance and flexible
querying combined with near real-time indexing. It uses Elasticsearch, a
real-time distributed indexing and search engine built on Apache Lucene, but
adds OpenStack authentication and Role Based Access Control to provide
appropriate protection of data.

CCP plugin has two components for searchlight service:

* ``searchlight-api``
* ``searchlight-listener``

So searchlight docker images are the following:

* ``ccp/searchlight-api``
* ``ccp/searchlight-listener``

You can deploy them with other components using :ref:`quickstart`.

Dependencies
~~~~~~~~~~~~

Searchlight depends on several services:

 * Elasticsearch. Searchlight services depends on elasticsearch service, which
   should be deployed on env before searchlight installation. To deploy
   elasticsearch, it should be specified in CCP config file in components' list
   and (optionally, if you specified repositories manually) add next repo to
   repositories repos' list:

   ::

     git_url: https://git.openstack.org/openstack/fuel-ccp-stacklight
     name: fuel-ccp-stacklight

 * Indexed services. Searchlight builds index on observed services, so should
   be deployed after them - index will be not complete with all resources from
   observed resources instead.

Configuration
~~~~~~~~~~~~~

Searchlight provides indexing and searching for several services, listed
`here <http://docs.openstack.org/developer/searchlight/#search-plugins>`_.
CCP plugin allows to specify, which services searchlight will handle. For
enabling/disabling service, which you want to index and listen for updates,
you need to change value `searchlight.services.<desirable service>` to
`true` in ``services/files/defaults.yaml`` (and `false` to disable). After that
you need to restart searchlight components and corresponding api component of
service you enabled in config, if you already deployed components.

Installation
~~~~~~~~~~~~

To install and configure searchlight service, you should follow next steps:

#. Ensure, that elasticsearch is ready to use. You can, for example,
   list all indices:

   `curl -X GET elasticsearch.ccp:<elasticport>/_cat/indices?v`

   where `elasticport` is elasticsearch port, which can be found with command:

   ::

     kubectl get svc elasticsearch -o yaml | awk '/port:/ {print $NF}'

   and it equals to 9200 by default.

   You'll get table with next header (if you don't use elasticsearch before,
   table will be empty):

   `health status index pri rep docs.count docs.deleted store.size pri.store.size`

#. Add *searchlight-api* and *searchlight-listener* services to your CCP
   configuration file (e.g. `.ccp.yaml`).

#. Deploy these components with command:

   ::

      ccp deploy -c searchlight-api searchlight-listener

   and wait until their won't be available.

#. Install `python-searchlightclient` and also install/update
   `python-openstackclient` with pip:

   ::

      pip install --user -U python-searchlightclient python-openstackclient

#. Check availability of searchlight with command
   :command:`openstack search resource type list`, which will display all
   supported resource types to search.

Dashboard plugin
~~~~~~~~~~~~~~~~

Searchlight has horizon dashboard plugin, which allows you to search and filter
resources and get detailed information about it. It already available in
horizon and activates, when searchlight is on board. Search panel places in
``Projects`` menu.
