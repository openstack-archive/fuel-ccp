.. _monitoring_and_logging:

======================================
Monitoring and Logging with StackLight
======================================

This section provides information on deploying StackLight, the monitoring and
logging system for CCP.

.. WARNING:: StackLight requires Kubernetes 1.4 or higher, and its deployment
   will fail with Kubernetes 1.3 and lower. So before deploying StackLight make
   sure you use an appropriate version of Kubernetes.

Overview
========

StackLight is composed of several components. Some components are related to
logging, and others are related to monitoring.

The "logging" components:

* ``heka`` – for collecting logs
* ``elasticsearch`` – for storing/indexing logs
* ``kibana`` – for exploring and visualizing logs

The "monitoring" components:

* ``stacklight-collector`` – composed of Snap and Hindsight for collecting and
  processing metrics
* ``influxdb`` – for storing metrics as time-series
* ``grafana`` – for visualizing time-series

For fetching the StackLight repo (``fuel-ccp-stacklight``) and building the
StackLight Docker images please refer to the :ref:`quickstart` section as
StackLight is not different from other CCP components for that matter.  If you
followed the :ref:`quickstart` the StackLight images may be built already.

The StackLight Docker images are the following:

* ``ccp/cron``
* ``ccp/elasticsearch``
* ``ccp/grafana``
* ``ccp/heka``
* ``ccp/hindsight``
* ``ccp/influxdb``
* ``ccp/kibana``

Deploy StackLight
=================

The StackLight components are regular CCP components, so the deployment of
StackLight is done through the CCP CLI like any other CCP component. Please
read the :ref:`quickstart` section and make sure the CCP CLI is installed and
you know how to use it.

StackLight may be deployed together with other CCP components, or independently
as a separate deployment process. You may also want to deploy just the
"logging" components of StackLight, or just the "monitoring" components. Or you
may want to deploy all the StackLight components at once.

In any case you will need to create StackLight-related roles in your CCP
configuration file (e.g. ``/etc/ccp/ccp.yaml``) and you will need to assign
these roles to nodes.

For example:

::

    nodes:
      node1:
        roles:
          - stacklight-backend
          - stacklight-collector
      node[2-3]:
        roles:
          - stacklight-collector
    roles:
      stacklight-backend:
        - influxdb
        - grafana
      stacklight-collector:
        - stacklight-collector

In this example we define two roles: ``stacklight-backend`` and
``stacklight-collector``. The role ``stacklight-backend`` is assigned to
``node1``, and it defines where ``influxdb`` and ``grafana`` will run. The role
``stacklight-collector`` is assigned to all the nodes (``node1``, ``node2`` and
``node3``), and it defines where ``stacklight-collector`` will run. In most
cases you will want ``stacklight-collector`` to run on every cluster node, for
node-level metrics to be collected for every node.

With this, you can now deploy ``influxdb``, ``grafana`` and
``stacklight-collector`` with the following CCP command:

::

    ccp deploy -c influxdb grafana stacklight-collector

Here is another example, in which both the "monitoring" and "logging"
components will be deployed:

::

    nodes:
      node1:
        roles:
          - stacklight-backend
          - stacklight-collector
      node[2-3]:
        roles:
          - stacklight-collector
    roles:
      stacklight-backend:
        - influxdb
        - grafana
        - elasticsearch
        - kibana
      stacklight-collector:
        - stacklight-collector
        - heka
        - cron

And this is the command to use to deploy all the StackLight services:

::

    ccp deploy -c influxdb grafana elasticsearch kibana stacklight-collector heka cron

To check the deployment status you can run:

::

    kubectl --namespace ccp get pod -o wide

and check that all the StackLight-related pods have the ``RUNNING`` status.

Accessing the Grafana and Kibana interfaces
===========================================

As already explained in :ref:`quickstart` CCP does not currently include an
external proxy (such as Ingress), so for now the Kubernetes ``nodePort``
feature is used to be albe to access services such as Grafana and Kibana from
outside the Kubernetes cluster.

This is how you can get the node port for Grafana:

::

    $ kubectl get service grafana -o yaml | awk '/nodePort: / {print $NF}'
    31124

And for Kibana:

::

    $ kubectl get service kibana -o yaml | awk '/nodePort: / {print $NF}'
    31426

ElasticSearch cluster
=====================

Documentation above describes using elasticsearch as one node service without
ability to scale --- stacklight doesn't require elasticsearch cluster. This one
node elasticsearch is master-eligible, so could be scaled with any another
master, data or client node.

For more details about master, data and client node types please read
`elasticsearch node documentation <https://www.elastic.co/guide/en/
elasticsearch/reference/5.2/modules-node.html>`_.

CCP implementation of elasticsearch cluster contains three available services:

* ``elasticsearch`` --- master-eligible service, represents master node;

* ``elasticsearch-data`` --- data (non-master) service, represents data node,
  contains `elasticsearch-data` volume for storing data;

* ``elasticsearch-client`` --- special type of coordinating only node that can
  connect to multiple clusters and perform search and other operations across
  all connected clusters. Represents tribe node type.

All these services can be scaled and deployed on several nodes with replicas -
they will form cluster. It can be checked with command:

::

    $ curl -X GET http://elasticsearch.ccp.svc.cluster.local:9200/_cluster/health?pretty

which will print total number of cluster nodes and number of data nodes. More
detailed info about each cluster node called with command:

::

   $ curl -X GET http://elasticsearch.ccp.svc.cluster.local:9200/_cluster/state?pretty
