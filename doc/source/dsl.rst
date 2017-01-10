===============================
Application definition language
===============================

There is a description of current syntax of application definition framework.

Application definition template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. sourcecode:: yaml

    service:
        name: service-name
        kind: DaemonSet
        ports:
            - internal-port:external-port
        hostNetwork: true
        hostPID: true
        antiAffinity: local
        annotations:
            pod:
              description: frontend ports
            service:
              description: frontend service
        containers:
            - name: container-name
              image: container-image
              probes:
                  readiness: readiness.sh
                  liveness: liveness.sh
              volumes:
                  - name: volume-name
                    type: host
                    path: /path
              pre:
                  - name: service-bootstrap
                    dependencies:
                        - some-service
                        - some-other-service
                    type: single
                    command: /tmp/bootstrap.sh
                    files:
                        - bootstrap.sh
                    user: user
                  - name: db-sync
                    dependencies:
                        - some-dep
                    command: some command
                    user: user
              daemon:
                  dependencies:
                      - demon-dep
                  command: daemon.sh
                  files:
                      - config.conf
                  user: user
              post:
                  - name: post-command
                    dependencies:
                        - some-service
                        - some-other-service
                    type: single
                    command: post.sh
                    files:
                        - config.conf

    files:
        config.conf:
            path: /etc/service/config.conf
            content: config.conf.j2
            perm: "0600"
            user: user
        bootstrap.sh:
            path: /tmp/bootstrap.sh
            content: bootstrap.sh.j2
            perm: "0755"


Parameters description
~~~~~~~~~~~~~~~~~~~~~~

.. _service:

service
-------

.. list-table::
   :widths: 10 35 7 15 7
   :header-rows: 1

   * - Name
     - Description
     - Required
     - Schema
     - Default
   * - name
     - Name of the service.
     - true
     - string
     - --
   * - kind
     - Kind of k8s object to use for containers deployment.
     - false
     - one of: ["Deployment", "DaemonSet", "StatefulSet"]
     - Deployment
   * - containers
     - List of containers under multi-container pod.
     - true
     - container_ array
     - --
   * - ports
     - k8s Service will be created if specified (with NodePort type for now).
       Only internal or both internal:external ports can be specified.
     - false
     - internal-port: external-port array
     - --
   * - hostNetwork
     - Use the host’s network namespace.
     - false
     - boolean
     - false
   * - hostPID
     - Use the host’s pid namespace.
     - false
     - boolean
     - false
   * - strategy
     - The strategy that should be used to replace old Pods by new ones.
     - false
     - one of: ["RollingUpdate", "Recreate"]
     - RollingUpdate
   * - antiAffinity
     - Restrict scheduling of pods on the same host:
       local - within namespace, global - within k8s cluster
     - false
     - one of: [null, "global", "local"]
     - null
   * - annotations
     - pod - annotations for pods, service - annotations for service.
     - false
     - string dict
     - null

.. _container:

container
---------

.. list-table::
   :widths: 10 35 7 15 7
   :header-rows: 1

   * - Name
     - Description
     - Required
     - Schema
     - Default
   * - name
     - Name of the container. It will be used to track status in etcd.
     - true
     - string
     - --
   * - image
     - Name of the image. registry, namespace, tag will be added by framework.
     - true
     - string
     - --
   * - probes
     - Readiness, liveness or both checks can be defined. Exec action will be
       used for both checks.
     - false
     - dict with two keys:

       liveness:
         cmd

       readiness:
         cmd
     - --
   * - volumes
     - --
     - false
     - volume_ array
     - --
   * - pre
     - List of commands that need to be executed before daemon process start.
     - false
     - command_ array
     - --
   * - daemon
     - --
     - true
     - command_
     - --
   * - post
     - The same as for “pre” except that post commands will be executed after
       daemon process has been started.
     - false
     - command_ array
     - --
   * - env
     - An array of environment variables defined in kubernetes way.
     - false
     - env_ array
     - --

.. _env: http://kubernetes.io/docs/api-reference/v1/definitions/#_v1_envvar

.. _volume:

volume
------

.. list-table::
   :widths: 10 35 7 15 7
   :header-rows: 1

   * - Name
     - Description
     - Required
     - Schema
     - Default
   * - name
     - Name of the volume.
     - true
     - string
     - --
   * - type
     - host and empty-dir type supported for now.
     - true
     - one of: ["host", "empty-dir"]
     - --
   * - path
     - Host path that should be mounted (only if type = "host").
     - false
     - string
     - --
   * - mount-path
     - Mount path in container.
     - false
     - string
     - path
   * - readOnly
     - Mount mode of the volume.
     - false
     - bool
     - False

.. _command:

command
-------

.. list-table::
   :widths: 10 35 7 15 7
   :header-rows: 1

   * - Name
     - Description
     - Required
     - Schema
     - Default
   * - name
     - Name of the command. Required only for `pre` and `post` with type
       `single`.
     - --
     - string
     - --
   * - command
     - --
     - true
     - string
     - --
   * - dependencies
     - These keys will be polled from etcd before commands execution.
     - false
     - string array
     - --
   * - type
     - type: single means that this command should be executed once per
       openstack deployment. For commands with type: single Job object will be
       created.

       type: local (or if type is not specified) means that command will be
       executed inside the same container as a daemon process.
     - false
     - one of: ["single", "local"]
     - local
   * - files
     - List of the files that maps to the keys of files dict. It defines which
       files will be rendered inside a container.
     - false
     - file_ keys array
     - --
   * - user
     - --
     - false
     - string
     - --

.. _files:

files
-----

.. list-table::
   :widths: 35 10 7 15 7
   :header-rows: 1

   * - Name
     - Description
     - Required
     - Schema
     - Default
   * - Name of the file to refer in files list of commands
     - --
     - false
     - file_ array
     - --

.. _file:

file
----

.. list-table::
   :widths: 10 35 7 15 7
   :header-rows: 1

   * - Name
     - Description
     - Required
     - Schema
     - Default
   * - path
     - Destination path inside a container.
     - true
     - string
     - --
   * - content
     - Name of the file under {{ service_repo }}/service/files directory. This
       file will be rendered inside a container and moved to the destination
       defined with path.
     - true
     - string
     - --
   * - perm
     - --
     - false
     - string
     - --
   * - user
     - --
     - false
     - string
     - --

DSL versioning
~~~~~~~~~~~~~~

Some changes in CCP framework are backward compatible and some of them are not.
To prevent situations when service definitions are being processed by
incompatible version of CCP framework, DSL versioning has been implemented.

DSL versioning is based on Semantic Versioning model. Version has a format
``MAJOR.MINOR.PATCH`` and is being defined in ``dsl_version`` field of
:file:`fuel_ccp/__init__.py` module. Each service definition contains
``dsl_version`` field with the version of DSL it was implemented/updated for.

During the validation phase of :command:`ccp deploy` those versions will be
compared according to the following rules:

#. if DSL version of ``fuel-ccp`` is less than service's DSL version -
   they are incompatible - error will be printed, deployment will be
   aborted;
#. if ``MAJOR`` parts of these versions are different - they are incompatible
   - error will be printed, deployment will be aborted;
#. otherwise they are compatible and deployment can be continued.

For ``dsl_version`` in ``fuel-ccp`` repository you should increment:

#. MAJOR version when you make incompatible changes in DSL;
#. MINOR version when you make backward-compatible changes in DSL;
#. PATCH version when you make fixes that do not change DSL, but affect
   processing flow.

If you made a change in service definition that is not supposed to work with
the current ```dsl_version```, you should bump it to the minimal appropriate
number.
