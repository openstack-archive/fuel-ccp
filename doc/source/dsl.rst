===============================
Application definition language
===============================

There is a description of current syntax of application definition framework.

Application definition template
-------------------------------

.. sourcecode:: yaml

    service:
        name: service-name
        kind: DaemonSet
        ports:
            - internal-port:external-port
        hostNetwork: true
        hostPID: true
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
----------------------

.. _service:

**service**

+---------------+-----------------------------------------------+----------+------------------+------------+
| Name          | Description                                   | Required | Schema           | Default    |
+===============+===============================================+==========+==================+============+
| name          | Name of the service.                          | true     | string           |            |
+---------------+-----------------------------------------------+----------+------------------+------------+
| kind          | Kind of k8s object to use for containers      | false    | one of:          | Deployment |
|               | deployment                                    |          | ["Deployment",   |            |
|               |                                               |          | "Daemonset",     |            |
|               |                                               |          | "PetSet"]        |            |
+---------------+-----------------------------------------------+----------+------------------+------------+
| containers    | List of containers under multi-container pod  | true     | container_ array |            |
+---------------+-----------------------------------------------+----------+------------------+------------+
| ports         | k8s Service will be created if specified      | false    | internal-port:   |            |
|               | (with NodePort type for now)                  |          | external-port    |            |
|               | Only internal or both internal:external ports |          | array            |            |
|               | can be specified                              |          |                  |            |
+---------------+-----------------------------------------------+----------+------------------+------------+
| hostNetwork   | Use the host’s network namespace              | false    | boolean          | false      |
+---------------+-----------------------------------------------+----------+------------------+------------+
| hostPID       | Use the host’s pid namespace                  | false    | boolean          | false      |
+---------------+-----------------------------------------------+----------+------------------+------------+

.. _container:

**container**

+---------+--------------------------------------------+----------+------------------+---------+
| Name    | Description                                | Required | Schema           | Default |
+=========+============================================+==========+==================+=========+
| name    | Name of the container. It will be used to  | true     | string           |         |
|         | track status in etcd                       |          |                  |         |
+---------+--------------------------------------------+----------+------------------+---------+
| image   | Name of the image. registry, namespace,    | true     | string           |         |
|         | tag will be added by framework             |          |                  |         |
+---------+--------------------------------------------+----------+------------------+---------+
| probes  | Readiness, liveness or both checks can be  | false    | dict with        |         |
|         | defined. Exec action will be used for both |          | two keys:        |         |
|         | checks                                     |          |   liveness: cmd  |         |
|         |                                            |          |   readiness: cmd |         |
+---------+--------------------------------------------+----------+------------------+---------+
| volumes |                                            | false    | volume_ array    |         |
+---------+--------------------------------------------+----------+------------------+---------+
| pre     | List of commands that need to be executed  | false    | command_ array   |         |
|         | before daemon process start                |          |                  |         |
+---------+--------------------------------------------+----------+------------------+---------+
| daemon  |                                            | true     | command_         |         |
+---------+--------------------------------------------+----------+------------------+---------+
| post    | The same as for “pre” except that post     | false    | command_ array   |         |
|         | commands will be executed after daemon     |          |                  |         |
|         | process has been started                   |          |                  |         |
+---------+--------------------------------------------+----------+------------------+---------+
| env     | An array of environment variables defined  | false    | env_ array       |         |
|         | in kubernetes way.                         |          |                  |         |
|         |                                            |          |                  |         |
+---------+--------------------------------------------+----------+------------------+---------+

.. _env: http://kubernetes.io/docs/api-reference/v1/definitions/#_v1_envvar

.. _volume:

**volume**

+------------+-------------------------------------------+----------+-----------------------+---------+
| Name       | Description                               | Required | Schema                | Default |
+============+===========================================+==========+=======================+=========+
| name       | Name of the volume                        | true     | string                |         |
+------------+-------------------------------------------+----------+-----------------------+---------+
| type       | host and empty-dir type supported for now | true     | one of:               |         |
|            |                                           |          | ["host", "empty-dir"] |         |
+------------+-------------------------------------------+----------+-----------------------+---------+
| path       | Host path that should be mounted          | false    | string                |         |
|            | (only if type = "host")                   |          |                       |         |
+------------+-------------------------------------------+----------+-----------------------+---------+
| mount-path | Mount path in container                   | false    | string                | path    |
+------------+-------------------------------------------+----------+-----------------------+---------+
| readOnly   | Mount mode of the volume                  | false    | bool                  | False   |
+------------+-------------------------------------------+----------+-----------------------+---------+

.. _command:

**command**

+--------------+--------------------------------------------+----------+----------------------+---------+
| Name         | Description                                | Required | Schema               | Default |
+==============+============================================+==========+======================+=========+
| name         | Name of the command. Required only for     |    --    | string               |         |
|              | `pre` and `post` with type `single`        |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| command      |                                            | true     | string               |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| dependencies | These keys will be polled from etcd        | false    | string array         |         |
|              | before commands execution                  |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| type         | type: single means that this command       | false    | one of:              | local   |
|              | should be executed once per openstack      |          | ["single", "local"]  |         |
|              | deployment. For commands with              |          |                      |         |
|              | type: single Job object will be created    |          |                      |         |
|              |                                            |          |                      |         |
|              | type: local (or if type is not specified)  |          |                      |         |
|              | means that command will be executed        |          |                      |         |
|              | inside the same container as a             |          |                      |         |
|              | daemon process.                            |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| files        | List of the files that maps to the keys    | false    | file_ keys array     |         |
|              | of files dict. It defines which files will |          |                      |         |
|              | be rendered inside a container             |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| user         |                                            | false    | string               |         |
+--------------+--------------------------------------------+----------+----------------------+---------+

.. _files:

**files**

+------------------------------+-------------+----------+-------------+---------+
| Name                         | Description | Required | Schema      | Default |
+==============================+=============+==========+=============+=========+
| Name of the file to refer in |             | false    | file_ array |         |
| files list of commands       |             |          |             |         |
+------------------------------+-------------+----------+-------------+---------+

.. _file:

**file**

+---------+------------------------------------------------+----------+--------+---------+
| Name    | Description                                    | Required | Schema | Default |
+=========+================================================+==========+========+=========+
| path    | Destination path inside a container            | true     | string |         |
+---------+------------------------------------------------+----------+--------+---------+
| content | Name of the file under                         | true     | string |         |
|         | {{ service_repo }}/service/files directory.    |          |        |         |
|         | This file will be rendered inside a container  |          |        |         |
|         | and moved to the destination defined with path |          |        |         |
+---------+------------------------------------------------+----------+--------+---------+
| perm    |                                                | false    | string |         |
+---------+------------------------------------------------+----------+--------+---------+
| user    |                                                | false    | string |         |
+---------+------------------------------------------------+----------+--------+---------+
