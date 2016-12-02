.. app_def_guide:

=========================================
Application definition contribution guide
=========================================

This document gives high overview of component repository structure.

Overview
========

CCP provides wide spectr of operations for manipulating microserverses on
Kubernetes cluster. Each microserver is a independent component with
common architecture. Whole data releated with component can be found in the
corresponding repository. The full list of the related components can be found
by `link`_, where each repository has prefix ``fuel-ccp-*``.

Structure
=========

Component repositories has common structure:

1. Docker image related data
----------------------------
   ``docker`` folder with Docker files, which will be used for building docker
   images. Each subfolder will be processed as a separate image for building.
   See detailed instructions are available in the :doc:`docker`.

2. Application definition files
-------------------------------
   All application definition files should be located in the ``service/``
   directory, as a ``component_name.yaml`` file, for example:

   ::

    service/keystone.yaml

   Please refer to :doc:`dsl` for detailed description of CCP DSL syntax.

3. Application related scripts and configs
------------------------------------------

   All templates, such as configs, scripts, etc, which will be used for this
   service, should be located in ``service/<component_name>/files``, for example:

   ::

    service/files/keystone.conf.j2

   All files inside this directory are Jinja2 templates, except file with
   default variables. Default variables for these templates should be located
   in ``service/component_name/files/defaults.yaml`` inside the ``configs``
   key. Description of available values can be found in follow guide
   :doc:`config/index`.

.. _link: https://github.com/openstack?q=fuel-ccp-
