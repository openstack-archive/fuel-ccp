.. _services:

==================
"services" section
==================

You would want to have dedicated DB/messaging/memcached/etc for some of your
services. Or you could have several backends and want to switch between them
easily. This guide will describe how to make proper configuration for both
cases.

All required configuration is located under `services` config group and can be
propagated via :file:`ccp.yaml`.

The following abstractions are being used all over the CCP:

* database
* rpc
* notifications

You should explicitly define backends for them before deployment. For example:

::

    services:
      database:
        service_def: galera
      rpc:
        service_def: rabbitmq
      notifications:
        service_def: rabbitmq

Those services can be used in topology definition. You don't have to define
anything else. By default will be assumed that service has a name of service
definition.

In the following example will be created dedicated databases for keystone and
glance, dedicated memcached for keystone and horizon and those services will
be connected through `mapping` section.

::

    services:
      database:
        service_def: mariadb
      keystone-db:
        service_def: mariadb
      glance-db:
        service_def: mariadb

      keystone-memcached:
        service_def: memcached
      horizon-memcached:
        service_def: memcached

      rpc:
        service_def: rabbitmq
      notifications:
        service_def: rabbitmq

      keystone:
        service_def: keystone
        mapping:
          database: keystone-db
          memcached: keystone-memcached
      glance-api:
        service_def: glance-api
        mapping:
          database: glance-db
      glance-registry:
        service_def: glance-registry
        mapping:
          database: glance-db
      horizon:
        service_def: horizon
        mapping:
          memcached: horizon-memcached
