.. _config_types:

=======================
Configuration key types
=======================

List of keys
============

Each config could contain several keys:

- ``configs``

- ``versions``

- ``sources``

- ``nodes``

- ``network_topology``

- ``repositories``

Each key has its own purpose and isolation, so you have to add your variable
to the right key to make it work.

configs key
-----------

Isolation:

- Used in service templates files (service/files/).

- Used in application definition file service/component_name.yaml.

Allowed content:

- Any types of variables allowed.

Example:

::

    configs:
      keystone_debug: false

So you could add "{{ keystone_debug }}" variable to you templates, which will
be rendered into "false" in this case.

versions key
------------

Isolation:

- Used in Dockerfile.j2 only.

Allowed content:

- Only versions of different software should be kept here.

For example:

::

    versions:
     influxdb_version: "0.13.0"

So you could add this to influxdb Dockerfile.j2:

::

    curl https://dl.influxdata.com/influxdb/releases/influxdb_{{ influxdb_version }}_amd64.deb

sources key
-----------

Isolation:

- Used in Dockerfile.j2 only.

Allowed content:

- This key has a restricted format, examples below.

Remote git repository example:

::

    sources:
      openstack/keystone:
        git_url: https://github.com/openstack/keystone.git
        git_ref: master

Local git repository exaple:

::

    sources:
      openstack/keystone:
        source_dir: /tmp/keystone

So you could add this to Dockerfile.j2:

::

    {{ copy_sources("openstack/keystone", "/keystone") }}

CCP will use the chosen configuration, to copy git repository into Docker
container, so you could use it latter.

network_topology key
--------------------

Isolation:

- Used in service templates files (service/files/).

Allowed content:

- This key is auto-created by entrypoint script and populated with container
  network topology, based on the following variables: ``private_interface`` and
  ``public_interface``.

You could use it to get the private and public eth IP address. For example:

::

    bind = network_topology["private"]["address"]
    listen = network_topology["public"]["address"]

nodes and roles key
-------------------

Isolation:

- Not used in any template file, only used by the CCP CLI to create a cluster
  topology.

Allowed content:

- This key has a restricted format, example of this format can be found in
  ``fuel-ccp`` git repository in ``etc/topology-example.yaml`` file.

"CCP_*" env variables
---------------------

Isolation:

- Used in service templates files (service/files/).

Allowed content:

- This variables are created from the application definition ``env`` key.
  Only env keys which start with "CCP\_" will be passed to config hash.

This is mainly used to pass some k8s related information to container, for
example, you could use it to pass k8s node hostname to container via this
variable:

Create env key:

::

      env:
        - name: CCP_NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName

Use this variable in some config:

::

    {{ CCP_NODE_NAME }}


repositories key
----------------

:doc:`repositories`
