.. _config:

===================
Configuration files
===================

This section will describe configuration format used in CCP.

Understanding global and default configs
========================================

There are three config locations, which the CCP CLI uses:

#. ``Global defaults`` - fuel_ccp/resources/defaults.yaml in ``fuel-ccp`` repo.
#. ``Component defaults`` - service/files/defaults.yaml in each component repo.
#. ``Global config`` - Optional. For more information read the
   :doc:`global_config`.

Before deployment, CCP will merge all these files into one dict, using the
order above, so "component defaults" will override "global defaults" and
"global config" will override everything.

For example, one of common situations is to specify custom options for
networking. To achieve user may overwrite options defined in
``Global defaults`` and ``Component defaults`` by setting new values in
``Global config``.

File ``fuel_ccp/resources/defaults.yaml`` has follow settings:

::

  configs:
    private_interface: eth0
    public_interface: eth1
    ...

And part of the ``fuel-ccp-neutron/service/files/defaults.yaml`` looks like:

::

  configs:
    neutron:
      ...
      bootstrap:
        internal:
          net_name: int-net
          subnet_name: int-subnet
          network: 10.0.1.0/24
          gateway: 10.0.1.1
      ...

User may overwrite these sections by defining the following content in the
~/.ccp.yaml:

::

  debug: true
  configs:
    private_interface: ens10
    neutron:
      bootstrap:
        internal:
          network: 22.0.1.0/24
          gateway: 22.0.1.1

To validate these changes user needs to execute command ``ccp config dump``.
It will return final config file with changes, which user did. So output should
contain the following changes:

::

  debug: true
  ...
  configs:
    private_interface: ens10     <----- it was changed
    public_interface: eth1       <----- it wasn't changed
    neutron:
      bootstrap:
        internal:
          net_name: int-net        <--- it wasn't changed
          subnet_name: int-subnet  <--- it wasn't changed
          network: 22.0.1.0/24   <----- it was changed
          gateway: 22.0.1.1      <----- it was changed


Global defaults
---------------

This is project wide defaults, CCP keeps it inside fuel-ccp repository in
``fuel_ccp/resources/defaults.yaml`` file. This file defines global variables,
that is variables that are not specific to any component, like interface names.

Component defaults
------------------

Each component repository could contain a ``service/files/defaults.yaml`` file
with default config for this component only.

.. _section:

Global config
-------------

See description in :doc:`global_config`.
