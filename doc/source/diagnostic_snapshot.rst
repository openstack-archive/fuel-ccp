.. diagnostic_snapshot:

==================================
Diagnostic snapshot
==================================

In ``fuel-ccp/tools`` directory you can find tool called ``diagnostic-snapshot.sh``. This tool helps to collect some debug data about your environment. You can run it with:

::

    ./tools/diagnostic_snapshot -n <namespace> -o <output_dir> -c <ccp_config>

.. _parameters:

parameters
---------

.. list-table::
   :widths: 10 13 30
   :header-rows: 1

   * - Short option
     - Long option
     - Description
   * - -n
     - --namespace
     - deployment namespace
   * - -o
     - --output-dir
     - directory where diagnostic snapshot will be saved
   * - -c
     - --config
     - should point to Fuel-ccp config file
   * - -h
     - --help
     - print help

This tool collect some basic data about:

-  k8s objects in kube-system and ccp namespaces:

   - pods
   - services
   - jobs
   - kubelet logs

-  system:

   - diskspace
   - network configuration
   - cpu info/load
   - sysctl info

-  docker:

   - logs
   - list of images
   - running containers
   - stats

-  ccp:

   - status output


This script automatically create directory provided as parameter for -o option and archive file in it with all collected data. The name of this file is created with template: <datetime>-diagnostic.tar.gz

