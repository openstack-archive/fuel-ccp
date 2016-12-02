.. debugging:

==================================
Debugging microservice/application
==================================

This part of the documentation contains some practice recomendations, which
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

The main purpose is to run new process with necessary changes in code
(breakpoints). It can be done from container with current service. Execute
follow commands to run bash in container:

::

 kubectl get pods | grep heat-engine
 kubectl exec -it <id of container from previous command> bash

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

    command: sleep 22d

  It will allow to run container without real heat-engine process.


To ship new container to ccp is necessary to build new image and then deploy 
it:

::

 ccp build -c heat-engine
 ccp build -c heat-engine

When deploy is finished, run bash in new container again.
The source code is placed in follow directory:

::

 /var/lib/microservices/venv/lib/python2.7/site-packages/

Change it by adding necessary breakpoints.

.. NOTE:: Text editor ``vim`` can work incorrect from container. For fixing it
          try to execute command: export TERM=xterm

The last stp is to run updated service code. Execute command, which was
commented in service definition file, in the current example it's:

::

 heat-engine --config-file /etc/heat/heat.conf

Now patched service is acttive and can be used for debugging.
