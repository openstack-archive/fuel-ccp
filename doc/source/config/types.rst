.. _config_types:

=======================
Configuration key types
=======================

Overview
~~~~~~~~

Each config could contain several keys. Each key has its own purpose and
isolation, so you have to add your variable to the right key to make it work.
For optimization description all keys will be splitted on several groups based
on purpose.

CCP specific
~~~~~~~~~~~~

Current list contains keys for configuration logging in the CCP CLI.

- :ref:`debug`
- :ref:`default_log_levels`
- :ref:`log_file`
- :ref:`verbose_level`

Build options
~~~~~~~~~~~~~

The biggest group of keys configures build process, i.e. `how to build`,
`which sources and images to use`.

- :ref:`builder`
- :ref:`versions`
- :ref:`repositories`
- :ref:`sources`
- :ref:`url`
- :ref:`images`

Deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

This group is dedicated to describe topology of deployment, configuration
of the microservices and credentials for connecting to Kubernetes cluster.

- :ref:`configs`
- :ref:`files`
- :ref:`kubernetes`
- :ref:`nodes_roles`
- :ref:`replicas`

Other specific variables
~~~~~~~~~~~~~~~~~~~~~~~~

The last group includes keys, which should be described, but could not be
a part of groups mentioned erlier.

- :ref:`registry`
- :ref:`action`
- :ref:`network_topology`
- :ref:`ccp_node`
- :ref:`ccp_pod`

List of keys
~~~~~~~~~~~~

.. _debug:

debug
-----

Isolation:

- Not used in any template file, only used by the CCP CLI.

Allowed content:

- Boolean value (default: False).

Option enable debug messages and tracebacks during **ccp** commands execution

.. _default_log_levels:

default_log_levels
------------------

Isolation:

- Not used in any template file, only used by the CCP CLI.

Allowed content:

- Array of string values.
  Default value:

  ::

   [
    'glanceclient=INFO',
    'keystoneauth=INFO',
    'neutronclient=INFO',
    'novaclient=INFO',
    'requests=WARN',
    'stevedore=INFO',
    'urllib3=WARN'
   ]

This array describes log levels for different components used by the CCP.
Messages from these componenets will be written to **ccp** debug logs.

.. _log_file:

log_file
--------

Isolation:

- Not used in any template file, only used by the CCP CLI.

Allowed content:

- String value (default: None).

Full path with file name for storing **ccp** execution logs. If only file name
is specified, then CCP will try to find this file in the current directory.

.. _verbose_level:

verbose_level
-------------

Isolation:

- Not used in any template file, only used by the CCP CLI.

Allowed content:

- Integer value. (default: 1)

This option allows to specify verbose level for **ccp** debug logging.

.. _builder:

builder
-------

Isolation:

- Not used in any template file, only used by the CCP CLI for building images.

Allowed content:

- This key has the following list of sub-keys:

+--------------------------------+----------------------------------+----------+------------+
| Name                           | Description                      | Schema   | Default    |
+================================+==================================+==========+============+
| workers                        | Number of the workers, which     | integer  | number of  |
|                                | will be used during building     |          | CPU in the |
|                                | component images.                |          | system     |
+--------------------------------+----------------------------------+----------+------------+
| keep_image_tree_consistency    | Rebuld dependent images, if base | boolean  | True       |
|                                | image was rebuilt.               |          |            |
+--------------------------------+----------------------------------+----------+------------+
| build_base_images_if_not_exist | Forces base image building.      | boolean  | True       |
+--------------------------------+----------------------------------+----------+------------+
| push                           | Push images to docker registry.  | boolean  | False      |
+--------------------------------+----------------------------------+----------+------------+
| no_cache                       | Do not use docker caching during |          |            |
|                                | building images.                 | boolean  | False      |
+--------------------------------+----------------------------------+----------+------------+

.. _versions:

versions
--------

Isolation:

- Used in Dockerfile.j2.

- Used in `Global Config` file.

Allowed content:

- Only versions of different software should be kept here.

For example:

::

    versions:
     influxdb_version: "0.13.0"

So you could add this to influxdb Dockerfile.j2:

::

    curl https://dl.influxdata.com/influxdb/releases/influxdb_{{ influxdb_version }}_amd64.deb

.. _repositories:

repositories
------------

Isolation:

- Not used in any template file, only used by the CCP CLI to fetch service
  repositories, e.g. fuel-ccp-* (nova, cinder and etc).

Detailed explanation can be found in :doc:`repositories`.

.. _sources:

sources
-------

Isolation:

- Used in Dockerfile.j2.

- Used in `Global Config` file.

Allowed content:

- This key has a restricted format, examples below.

Remote git repository example:

::

    sources:
      openstack/keystone:
        git_url: https://github.com/openstack/keystone.git
        git_ref: master

Local git repository example:

::

    sources:
      openstack/keystone:
        source_dir: /tmp/keystone

So you could add this to Dockerfile.j2:

::

    {{ copy_sources("openstack/keystone", "/keystone") }}

CCP will use the chosen configuration, to copy git repository into Docker
container, so you could use it later.

.. _url:

url
---

Isolation:

- Used in Dockerfile.j2.

- Used in `Global Config` file.

Allowed content:

- Only repos for artifacts (e.g. Deb, Pypi repos). Can be specific for
  different components.

Data which will be used by **ccp** during docker image building.
For example for mariadb:

::

  url:
    mariadb:
      debian:
        repo: "http://lon1.mirrors.digitalocean.com/mariadb/repo/10.1/debian"
        keyserver: "hkp://keyserver.ubuntu.com:80"
        keyid: "0xcbcb082a1bb943db"

.. _images:

images
------

Isolation:

- Not used in any template file, only used by the CCP CLI to build base images.

Allowed content:

- This key has the following list of sub-keys:

+--------------+----------------------------------+----------+----------------------------------------------------+
| Name         | Description                      | Schema   | Default                                            |
+==============+==================================+==========+====================================================+
| namespace    | Namespace which should be used   | string   | ccp                                                |
|              | for **ccp** related images.      |          |                                                    |
+--------------+----------------------------------+----------+----------------------------------------------------+
| tag          | Tag for **ccp** related images.  | string   | latest                                             |
+--------------+----------------------------------+----------+----------------------------------------------------+
| base_distro  | Base image for building **ccp**  | string   | debian                                             |
|              | images.                          |          |                                                    |
+--------------+----------------------------------+----------+----------------------------------------------------+
| base_tag     | Tag of the base image for bulding| string   | jessie                                             |
|              | **ccp** images.                  |          |                                                    |
+--------------+----------------------------------+----------+----------------------------------------------------+
| base_images  | Names of base images.            | array of | ['base']                                           |
|              |                                  | strings  |                                                    |
+--------------+----------------------------------+----------+----------------------------------------------------+
| maintainer   | Maintainer of **ccp** images.    | string   | MOS Microservices <mos-microservices@mirantis.com> |
+--------------+----------------------------------+----------+----------------------------------------------------+
| image_specs  | Extra keys for building images.  | json     |                                                    |
+--------------+----------------------------------+----------+----------------------------------------------------+

.. _configs:

configs
-------

Isolation:

- Used in service templates files (service/files/).

- Used in application definition file service/component_name.yaml.

- Used in `Global Config` file.

Allowed content:

- Any types of variables are allowed.

Example:

::

    configs:
      keystone_debug: false

So you could add "{{ keystone_debug }}" variable to you templates, which will
be rendered into "false" in this case.

.. _files:

files
-----

- Used in `Global Config` file.

  .. NOTE:: This section is used in component repositories for configuration
            files references. In case `Global Config` usage is tricky for you,
            custom config files for a particular service can be set
            in ~/.ccp.yaml.

  .. WARNING:: This section has the different format from same section used in
               component defitinions (i.e. in fuel-ccp-* repositories).

Allowed content:

- Strict format mentioned below:

::

 files:
  file_name: /path

.. _kubernetes:

kubernetes
----------

Isolation:

- Not used in any template file, only used by the CCP CLI to operate with
  Kubernetes cluster.

Allowed content:

- This key has the following list of sub-keys:

+----------------+----------------------------------+----------+-----------------------+
| Name           | Description                      | Schema   | Default               |
+================+==================================+==========+=======================+
| server         | URL for accessing of Kubernetes  | string   | http://localhost:8080 |
|                | API.                             |          |                       |
+----------------+----------------------------------+----------+-----------------------+
| namespace      | Namespace which will be created  | string   | ccp                   |
|                | and used for deploying Openstack.|          |                       |
+----------------+----------------------------------+----------+-----------------------+
| ca_cert        | Path of CA TLS certificate(s)    | string   |                       |
|                | used to verify the Kubernetes    |          |                       |
|                | server's certificate.            |          |                       |
+----------------+----------------------------------+----------+-----------------------+
| key_file       | Path of client key to use in SSL | string   |                       |
|                | connection.                      |          |                       |
+----------------+----------------------------------+----------+-----------------------+
| cert_file      | Path of certificate file to use  | string   |                       |
|                | in SSL connection.               |          |                       |
+----------------+----------------------------------+----------+-----------------------+
| insecure       | Explicitly allow **ccp**         | boolean  | False                 |
|                | to perform "insecure SSL"        |          |                       |
|                | (https) requests.                |          |                       |
+----------------+----------------------------------+----------+-----------------------+
| cluster_domain | Name of the cluster domain.      | string   | cluster.local         |
+----------------+----------------------------------+----------+-----------------------+


.. _replicas:

replicas
--------

Isolation:

- Not used in any template file, only used by the CCP CLI to create a cluster
  topology.

Allowed content:

- JSON object where keys are service names with value equal number of
  replicas which should be run after deploy.

.. NOTE:: For services defined with kind: DaemonSet replicas number can't be
          specified and will be always equal to number of nodes this service
          assigned to.

For example:

::

 replicas:
   heat-engine: 3

.. _nodes_roles:

nodes and roles key
-------------------

Isolation:

- Not used in any template file, only used by the CCP CLI to create a cluster
  topology.

Allowed content:

- This key has a restricted format, example of this format can be found in
  ``fuel-ccp`` git repository in ``etc/topology-example.yaml`` file.

.. _registry:

registry
--------

Isolation:

- Not used in any template file, only used by the CCP CLI to configure
  docker registry, which will be used for deployment.

Allowed content:

- This key has the following list of sub-keys:

+-----------+------------------------------------+----------+-----------+
| Name      | Description                        | Schema   | Default   |
+===========+====================================+==========+===========+
| address   | Address of registry service.       | string   |           |
+-----------+------------------------------------+----------+-----------+
| insecure  | Use insecure connection or not.    | boolean  | False     |
+-----------+------------------------------------+----------+-----------+
| username  | Username to access docker registry.| string   |           |
+-----------+------------------------------------+----------+-----------+
| password  | Password to access docker registry.| string   |           |
+-----------+------------------------------------+----------+-----------+
| timeout   | Value, which specifies how long    | integer  | 300       |
|           | the CCP waits response from        |          |           |
|           | registry.                          |          |           |
+-----------+------------------------------------+----------+-----------+

This is used to pass information for accessing docker registry.
Example can be found in :doc:`quickstart`.

.. _action:

action
------

.. WARNING:: This option was deprecated in favor of CLI parameters, so please
             don't use it, because it will be removed in future.

.. _network_topology:

network_topology
----------------

Isolation:

- Used in service templates files (service/files/).

Allowed content:

- This key is auto-created by entrypoint script and populated with container
  network topology, based on the following variables: ``private_interface`` and
  ``public_interface``.

You could use it to get the private and public eth IP address. For example:

::

    bind = "{{ network_topology["private"]["address"] }}"
    listen = "{{ network_topology["public"]["address"] }}"

.. _ccp_node:

node_name
---------

Isolation:

- Used in service templates files (service/files/).

Allowed content:

- This key is auto-created by entrypoint script based on kubernetes downward
  api.

You could use it to get the name of the node on which container is deployed.
For example:

::

    my_node = "{{ node_name }}"

.. _ccp_pod:

pod_name
--------

Isolation:

- Used in service templates files (service/files/).

Allowed content:

- This key is auto-created by entrypoint script based on kubernetes downward
  api.

You could use it to get the name of the pod on which container is deployed.
For example:

::

    my_pod = "{{ pod_name }}"
