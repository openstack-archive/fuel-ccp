.. app_def_guide:

=========================================
Application definition contribution guide
=========================================

This guide covers CCP specific DSL, which is used by CCP CLI to populate k8s
objects.

Application definition files location
=====================================

All application definition files should be located in ``service/`` directory,
as a ``component_name.yaml`` files, for example:

::

    service/keystone.yaml

All templates, such as configs, scripts, etc, which will be used for this
service, should be located in ``service/component_name/files``, for example:

::

    service/files/keystone.conf.j2

All files inside this directory is a Jinja2 templates. Default variables for
this templates should be located in
``service/component_name/files/defaults.yaml`` inside the ``configs`` key.

Understanding globals and defaults config
=========================================

There is 3 config location, which CCP CLI uses:

#. ``Global defaults`` - fuel_ccp/resources/defaults.yaml
#. ``Component defaults`` - service/component_name/files/defaults.yaml
#. ``Global config`` - Optional. Set path to this config via
   "--deploy-config /path" CCP CLI arg.

Before deployment, CCP will merge all this files into one dict, using the order
above, so "component defaults" will override "global defaults" and
"global config" will override everything.

Global defaults
---------------

This is project wide defaults, CCP keep it inside fuel-ccp repository in
``fuel_ccp/resources/defaults.yaml`` file. This file should contain only
none-component variables, which should be used by all containers, like eth
interface names.

Component defaults
------------------

Each component repository could contain a
``service/component_name/files/defaults.yaml`` file with default config for
this component only.

Global config
-------------

Optional config with global overrides for all services. Use it only if you need
to override some defaults.

Config keys types
=================

Each config could contain 3 keys:

- ``configs``

- ``versions``

- ``sources``

Each key has it's own purpose and isolation, so you have to add your variable
to right key to make it work. 

configs key
------------

Isolation: 

- Used in service templates files (service/component_name/files).

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
------------

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

CCP will use the choisen configuration, to copy git repository into Docker
container, so you could use it latter.


Application definition language
===============================

Please refer to :doc:`dsl` for detailed description of CCP DSL syntax.


