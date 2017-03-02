.. _zmq:

============
ZeroMQ Guide
============

This guide provides information about how to enable usage of zmq in CCP.

To use zmq as an rpc backend the following steps required:

1. `fuel-ccp-zmq` repository should be added to the repositories list:

::

    repositories:
      repos:
        - git_url: https://git.openstack.org/openstack/fuel-ccp-zmq
          name: zmq

2. `zmq-proxy` and `redis` images should be built:

::

    ccp build -c zmq-proxy redis

3. `rpc` service should be configured to use zmq:

::

    services:
      rpc:
        service_def: zmq-proxy

4. `rpc` and `redis` services should be added to topology. Example of such
   topology provided in :file:`fuel-ccp/etc/topology-with-zmq-example.yaml`

5. `configs` should be extended with the following values:

::

    configs:
      messaging:
        backend:
          rpc: zmq

Pretty much the same steps required to enable zmq as a notifications backend:

::

    services:
      notifications:
        service_def: zmq-proxy

    configs:
      messaging:
        backend:
          notifications: zmq
