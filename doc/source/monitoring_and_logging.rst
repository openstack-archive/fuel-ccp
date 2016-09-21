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

Stacklight CLI toolbox
======================

Additionally, you may want to use a simple ES searcher script shipped with
the elasticsearch docker image out of box. For example:

::

    $ espod=$(kubectl get pods --namespace ccp --selector=app=elasticsearch \
    >   --output=jsonpath={.items..metadata.name})
    $ kubectl exec --namespace ccp $espod -- curl -s 'localhost:9200/_cat/indices'

The command gives you a list of ES indices. Next, you can issue a search
request against a given index, or all of them (by default):

::

    $ kubectl exec --namespace ccp $espod env ESIND=log-2016.09.21 SIZE=100 -- \
    >   es_search.sh "*:*"

This matches all events and limits the result output to a 100 log records, ordered
by a ascending timestamps. Or via the docker CLI and using a regex matcher:

::

    $ esip=$(kubectl get pods --namespace ccp --selector=app=elasticsearch \
    >   --output=jsonpath={.items..status.podIP})
    $ docker run --rm -e ESIP=$esip 127.0.0.1:31500/ccp/elasticsearch \
    >   es_search.sh "/.*/"

Note that a search query will be executed for logged messages' payload and
severity level and other types of indexed fields, like OpenStack request ID:

::

    $ docker run --rm -e ESIP=$esip 127.0.0.1:31500/ccp/elasticsearch \
    >   es_search.sh "*WARN*"

The default search pattern is a regex ``/error|alert|trace.*|crit.*|fatal/``.
See also `ES official docs <https://www.elastic.co/guide/en/elasticsearch/reference/current/search-uri-request.html>`_
