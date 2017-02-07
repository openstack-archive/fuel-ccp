.. _external_access:

=======
Ingress
=======

One of the ways to make services in Kubernetes externally-reachable is to use
Ingress. This page describes how it can be enabled and used in CCP.

Ingress controller
~~~~~~~~~~~~~~~~~~

In order to make Ingress work, the cluster should have an Ingress controller.
You can use any implementation of it, the only requirement is that it should
be configured to use TLS.

There is a script :file:`deploy-ingress-controller.sh` in
:file:`fuel-ccp/tools/ingress` directory for testing purposes that can do it
for you. It will deploy traefik ingress controller and expose it as a k8s
service. The only required parameter is one of the k8s nodes IP which need to
be specified with `-i`. Ingress controller will be configured to use TLS. If
certificate and key were not provided with script parameters, the will be
generated automatically.

Enable Ingress in CCP
~~~~~~~~~~~~~~~~~~~~~

The following parameters are responsible for Ingress configuration:

::

    configs:
      ingress:
        enabled: False
        domain: external
        port: 8443

Ingress is disabled by default. To enable it, `enabled` config option should
be set to `True`. Optionally domain and port can be changed.

.. NOTE:: There's no option to run Ingress without TLS.

.. NOTE:: `port` parameter should match HTTPS port of Ingress controller.

.. NOTE:: For multiple OpenStack deployments highly recommended to use
          different `domain`s or run multiple Ingress controllers with
          configured namespace isolation.

To get all Ingress domains of the current deployment you can run
:command:`ccp domains list` command:

::

    +------------------------------+
    | Ingress Domain               |
    +------------------------------+
    | application-catalog.external |
    | identity.external            |
    | orchestration.external       |
    | image.external               |
    | object-store.external        |
    | network.external             |
    | ironic.external              |
    | volume.external              |
    | console.external             |
    | data-processing.external     |
    | horizon.external             |
    | compute.external             |
    | search.external              |
    +------------------------------+

All of them should be resolved to the exposed IP of the Ingress controller.
It could be done with DNS or /etc/hosts.

The following command will prepare /etc/hosts for you. Only IP of the Ingress
controller (and configuration file if needed) should be specified:

::

    echo INGRESS_CONTROLLER_IP $(ccp domains list -q -f value) | sudo tee -a /etc/hosts


Expose a service with Ingress
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To expose one of the ports of a service with Ingress, `ingress` parameter with
subdomain should be specified in the config section associated with that port:

::

    configs:
      public_port:
        cont: 5000
        ingress: identity

During the :command:`ccp deploy` command execution Ingress objects will be
created and all :ref:`address` occurrences with enabled `external` flag will be
substituted with proper Ingress domains.
