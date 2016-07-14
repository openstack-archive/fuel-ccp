===============================
Application definition language
===============================

There is a description of current syntax of application definition framework.

Application definition template
-------------------------------

.. sourcecode:: yaml

    service:
        name: service-name
        ports:
            - internal-port:external-port
        daemonset: true
        host-net: true
        node-selector:
            openstack-controller: "true"
            openstack-compute: "true"
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

+---------------+-----------------------------------------------+----------+------------------+---------+
| Name          | Description                                   | Required | Schema           | Default |
+===============+===============================================+==========+==================+=========+
| name          | Name of the service.                          | true     | string           |         |
+---------------+-----------------------------------------------+----------+------------------+---------+
| containers    | List of containers under multi-container pod  | true     | container_ array |         |
+---------------+-----------------------------------------------+----------+------------------+---------+
| ports         | k8s Service will be created if specified      | false    | internal-port:   |         |
|               | (with NodePort type for now)                  |          | external-port    |         |
|               | Only internal or both internal:external ports |          | array            |         |
|               | can be specified                              |          |                  |         |
+---------------+-----------------------------------------------+----------+------------------+---------+
| node-selector |                                               | false    | array of labels  |         |
+---------------+-----------------------------------------------+----------+------------------+---------+
| daemonset     | Create DaemonSet instead of Deployment        | false    | boolean          | false   |
+---------------+-----------------------------------------------+----------+------------------+---------+
| host-net      |                                               | false    | boolean          | false   |
+---------------+-----------------------------------------------+----------+------------------+---------+

.. _container:

**container**

+---------+--------------------------------------------+----------+-----------------+---------+
| Name    | Description                                | Required | Schema          | Default |
+=========+============================================+==========+=================+=========+
| name    | Name of the container. It will be used to  | true     | string          |         |
|         | track status in etcd                       |          |                 |         |
+---------+--------------------------------------------+----------+-----------------+---------+
| image   | Name of the image. registry, namespace,    | true     | string          |         |
|         | tag will be added by framework             |          |                 |         |
+---------+--------------------------------------------+----------+-----------------+---------+
| probes  | Readiness, liveness or both checks can be  | false    | readiness: cmd  |         |
|         | defined. Exec action will be used for both |          | liveness: cmd   |         |
|         | checks                                     |          |                 |         |
+---------+--------------------------------------------+----------+-----------------+---------+
| volumes |                                            | false    | volume_ array   |         |
+---------+--------------------------------------------+----------+-----------------+---------+
| pre     | List of commands that need to be executed  | false    | command_ array  |         |
|         | before daemon process start                |          |                 |         |
+---------+--------------------------------------------+----------+-----------------+---------+
| daemon  |                                            | false    | command_        |         |
+---------+--------------------------------------------+----------+-----------------+---------+
| post    | The same as for “pre” except that post     | false    | command_ array  |         |
|         | commands will be executed after daemon     |          |                 |         |
|         | process has been started                   |          |                 |         |
+---------+--------------------------------------------+----------+-----------------+---------+

.. _volume:

**volume**

+------+-------------------------------------------+----------+-----------------------+---------+
| Name | Description                               | Required | Schema                | Default |
+======+===========================================+==========+=======================+=========+
| name | Name of the volume                        | true     | string                |         |
+------+-------------------------------------------+----------+-----------------------+---------+
| type | host and empty-dir type supported for now | true     | one of:               |         |
|      |                                           |          | ["host", "empty-dir"] |         |
+------+-------------------------------------------+----------+-----------------------+---------+
| path | Mount path in container                   | true     | string                |         |
+------+-------------------------------------------+----------+-----------------------+---------+

.. _command:

**command**

+--------------+--------------------------------------------+----------+----------------------+---------+
| Name         | Description                                | Required | Schema               | Default |
+==============+============================================+==========+======================+=========+
| name         | Name of the command                        | true     | string               |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| command      |                                            | true     | string               |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| dependencies | These keys will be polled from etcd        | false    | sting array          |         |
|              | before commands execution                  |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| type         | type: single means that this command       | false    | one of:              |         |
|              | should be executed once per openstack      |          | ["single", "local"]  |         |
|              | deployment. For commands with              |          |                      |         |
|              | type: single Job object will be created    |          |                      |         |
|              |                                            |          |                      |         |
|              | type: local (or if type is not specified)  |          |                      |         |
|              | means that command will be executed        |          |                      |         |
|              | inside the same container as a             |          |                      |         |
|              | daemon process.                            |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| files        | List of the files that maps to the keys    | false    | files_ keys array    |         |
|              | of files dict. It defines which files will |          |                      |         |
|              | be rendered inside a container             |          |                      |         |
+--------------+--------------------------------------------+----------+----------------------+---------+
| user         |                                            | false    | string               |         |
+--------------+--------------------------------------------+----------+----------------------+---------+

.. _files:

**files**

key-value pairs.
key = name of the file to refer in files list of commands

value =

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
