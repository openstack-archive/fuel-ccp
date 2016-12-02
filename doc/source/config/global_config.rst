.. _config_global_config:

=============
Global config
=============

Optional config with global overrides for all services. Use it only if you need
to override some defaults.

File location
~~~~~~~~~~~~~

You can provide a path to file that you want to use as ``--config-file``
argument to ccp tool, otherwise it will be taken from the first existing
location out of the following ones:

* :file:`~/.ccp.yaml`
* :file:`~/.ccp/ccp.yaml`
* :file:`/etc/ccp.yaml`
* :file:`/etc/ccp/ccp.yaml`

Note that you can use only one config file, if you want to split your file into
several, you should use :ref:`includes <includes>`.

Format
~~~~~~

Every config file is a simple YAML file with any number of YAML documents
separated with ``---`` line::

  config_a: 1
  config_b:
    config_c: 2
  ---
  config_b:
    config_d: 3

All documents are deeply merged into one (only dicts are deeply merged, not
lists or other structures). So above config will be equivalent to::

  config_a: 1
  config_b:
    config_c: 2
    config_d: 3

.. _includes:

Includes
~~~~~~~~

If you want to split your config over several files (e.g. keep sentitive config
arguments separately or have a general config file part for several
deployments) you can use includes. An include is a separate YAML document with
``!include`` tag and a list of files to be included in its place::

  !include
  - file_a
  - file_b

If files are specified with relative paths, they are considered to be relative
to file with includes. Absolute paths are taken as is.

All documents from files in include list are substituted in place of an include
in order of appearance, so values from the latest file take precedence over
values in former ones.

Note that include is just another YAML document in config file, so you can
override values from include in following documents::

  basic_value: 1
  ---
  !include
  - override_basic_value
  ---
  override_value: from_include

Configuration file sections
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here you can find description of configuration parameters in these sections:

.. toctree::

  types
