.. _searchlight:

====================================
Searchlight CCP plugin documentation
====================================

This is Fuel-CCP plugin for OpenStack Searchlight service.

Original searchlight service developer docs
placed `here <http://docs.openstack.org/developer/searchlight/>`_.

The Searchlight project provides indexing and search capabilities across
OpenStack resources. Its goal is to achieve high performance and flexible
querying combined with near real-time indexing. It uses Elasticsearch, a
real-time distributed indexing and search engine built on Apache Lucene, but
adds OpenStack authentication and Role Based Access Control to provide
appropriate protection of data.

Dependencies
------------

Searchlight depends on several services:

 * Elasticsearch. Searchlight services depends on elasticsearch service, which
   should be deployed on env before searchlight installation.

 * Indexed services. Searchlight builds index on observed services, so should
   be deployed after them - index will be not complete with all resources from
   observed resources instead.

Installation
------------

To install and configure searchlight service, you should follow next steps:

#. Ensure, that elasticsearch is ready to use. You can, for example,
   list all indices:

   `curl -X GET <elasticip>:<elasticport>/_cat/indices?v`

   You'll get table with next header (if you don't use elasticsearch before,
   table will be empty):

   `health status index pri rep docs.count docs.deleted store.size pri.store.size`

#. Add *searchlight-api* and *searchlight-listener* services to `.ccp.yaml`
   configuration file.

#. Build and deploy these components (or deploy all components, if you want)
   and wait until their won't be available.

#. Configure services you want to add in index and search. Detailed information
   about changing config files you find `here <http://docs.openstack.org/
   developer/searchlight/index.html#search-plugins>`_. Don't forget to restart
   configured services.

#. Install `python-searchlightclient` and update `python-openstackclient` with
   it.

#. Check availability of searchlight with command `openstack stack resource
   type list`, which will display all supported resource types to search.
