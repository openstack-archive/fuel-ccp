.. _docker:

=======================
CCP Docker images guide
=======================

This guide covers CCP specific requirements for defining Docker images.

Docker files location
=====================

All docker files should be located in ``docker/<component_name>`` directory,
for example:

::

    docker/horizon
    docker/keystone

The docker directory may contain multiple components.

Docker directory structure
==========================

Each docker directory should contain a ``Dockerfile.j2`` file. Dockerfile.j2
is a file which contains Docker build instructions in a `Jinja2 template`_
format. You can add additional files, which will be used in Dockerfile.j2,
but only Dockerfile.j2 can be a Jinja2 template in this directory.

.. _Jinja2 template: http://jinja.pocoo.org/docs/dev/

Dockerfile format
=================

Please refer to the official `Docker documentation`_ which covers the
Dockerfile format. CCP has some additional requirements, which is:

#. Use as few `layers`_ as possible. Each command in Dockerfile creates a
   layer, so make sure you're grouping multiple RUN commands into one.

#. If it's possible, please run container from the non-root user.

#. If you need to copy some scripts into the image, please use ``/opt/ccp/bin``
   directory.

#. Only one process should be started inside container. Do not use runit,
   supervisord or any other init systems, which will allow to spawn multiple
   processes in container.

#. Do not use CMD and ENTRYPOINT commands in Dockerfile.j2.

#. All OpenStack services should use ``openstack-base`` parent image in FROM
   section. All non-OpenStack services should use ``base-tools`` parent image
   in FROM section.

Here is an example of valid Dockerfile.j2: `Keystone Dockerfile`_

.. _Docker documentation: https://docs.docker.com/engine/reference/builder
.. _layers: https://docs.docker.com/engine/userguide/storagedriver/imagesandcontainers/
.. _Keystone Dockerfile : https://github.com/openstack/fuel-ccp-keystone/blob/master/docker/keystone/Dockerfile.j2

Supported Jinja2 variables
--------------------------

Only specific variables can actually be used in Dockerfile.j2:

#. ``namespace`` - Used in the FROM section, renders into image namespace, by
   default into ``ccp``.

#. ``tag`` - Used in the FROM section, renders into image tag, by default into
   ``latest``.

#. ``maintainer`` - Used in the MAINTAINER section, renders into maintainer
   email, by default into "MOS Microservices
   <mos-microservices@mirantis.com>"

#. ``copy_sources`` - Used anywhere in the Dockerfile. please refer to
   corresponding documentation section below.

#. Additionaly, you could use variables with software versions, please refer
   to :doc:`app_def_guide` for details.

copy_sources
------------

The CCP CLI provides additional feature for Docker images creation, which will
help to use git repositories inside Dockerfile, it's called ``copy_sources``.

This feature uses configuration from ``service/files/defaults.yaml`` from the
same repository or from global config, please refer to :doc:`app_def_guide` for
details.

Testing
=======

After making any changes in docker directory, you should test it via build and
deploy.

To test building, please run:

::

    ccp build -c <component_name>

For example:

::

    ccp build -c keystone

Make sure that image is built without errors.

To test the deployment, please build new images using the steps above and after
run:

::

    ccp deploy

Please refer to :doc:`quickstart` for additional information.
