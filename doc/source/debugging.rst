.. debugging:

==================================
Debugging microservice/application
==================================

This part of the documentation contains some practice recommendations, which
can be used for debugging some issues in service code.

Problem description
===================

Workable service is perfect, but sometimes user may be in situation, when
application does not work as expected or fails with some unknown status.
Obviously if service can not provide clear traceback or logs, there is no
another option except debug this service. Let's take a look on some useful
how to do it and use heat-engine service as example.

How to debug
============

#. Create a local copy of the source code related project.

   ::

    cd /tmp
    git clone http://github.com/openstack/heat

#. Do all necessary changes, i.e. add breakpoint and etc., in this source code.

#. Update global configuration file by using local source for heat service.

   ::

    sources:
      openstack/heat:
        source_dir: /tmp/heat

#. Build new image and re-deploy heat service:

   ::

    ccp build -c heat-engine
    ccp deploy -c heat-engine

#. Login in container and enjoy debugging.

.. NOTE:: This approach is really pure for understanding, but has one issue.
          If you want to change code again you need to repeat all operations
          from building image again.

Another way to debug
====================

The idea is to run new process with necessary changes in code (breakpoints)
inside already created container for current service. Execute
follow commands to run bash in container with heat-engine service:

::

 kubectl get pods | grep heat-engine
 kubectl exec -it <id of pod from previous command> bash

So now bash is run in container. There are two new issues here:

#. It's not possible to change service source files, because we are logged
   as ``heat`` user.

#. If heat-engine process be killed, Kubernetes detect it and re-create
   container.

Both issues can be solved by changing Docker image and Service definition.

- First of all change user ``heat`` used in container to ``root``. It should be
  done in file: ``fuel-ccp-heat/docker/heat-engine/Dockerfile.j2``.

- The next step is to change run command in service definition:
  ``fuel-ccp-heat/service/heat-engine.yaml``. Find key word ``command``,
  comment it and write follow code:

  ::

    command: sleep 1h

  It will allow to run container for 1 hour without real heat-engine process,
  it's usually enough for leisurely debugging.

To ship new container to the CCP is necessary to build new image and then
re-deploy it:

::

 ccp build -c heat-engine
 ccp deploy -c heat-engine

When re-deploy is finished, run bash in new container again.
The source code is placed in follow directory:

::

 /var/lib/microservices/venv/lib/python2.7/site-packages/

Change it by adding necessary breakpoints.

.. NOTE:: Text editor ``vim`` can work incorrect from container. For fixing it
          try to execute command: export TERM=xterm

The last step is to run updated service code. Execute command, which was
commented in service definition file, in the current example it's:

::

 heat-engine --config-file /etc/heat/heat.conf

Now patched service is active and can be used for debugging.
