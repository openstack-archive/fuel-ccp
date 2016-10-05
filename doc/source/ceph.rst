.. _ceph:

====================
Ceph and Swift guide
====================

This guide provides an instruction of how to add Ceph and Swift support for
CCP deployment. Please note, that it's not the CCP responsibility to deploy
Ceph cluster, so it's expected that working Ceph cluster is already available
and accessible from the all k8s nodes.

.. NOTE:: If you don't have Ceph cluster, but still want to try CCP with Ceph,
   you can use :doc:`ceph_cluster` guide for deploying simple 3 node Ceph
   cluster.

Ceph
====

Prerequirements
---------------

You need to ensure that these pools are created:

* images
* volumes
* vms

And that users "glance" and "cinder" are created and have these permissions:

::

  client.cinder
        caps: [mon] allow r
        caps: [osd] allow rwx pool=volumes, allow rwx pool=vms, allow rx pool=images
  client.glance
        caps: [mon] allow r
        caps: [osd] allow rwx pool=images, allow rwx pool=vms


Deploy CCP with Ceph
====================

In order to deploy CCP with Ceph you have to edit **ccp.yaml**:

::

    configs:
      ceph:
        fsid: "FSID_OF_THE_CEPH_CLUSTER"
        initial_members: "INITIAL_MEMBERS_OF_CEPH_CLUSTER"
        mon_host: "ANY_CEPH_MON_HOSTNAME"
        cinder_enable: true
        cinder_key: "CINDER_CEPH_KEY"
        cinder_rbd_secret_uuid: "RANDOM_UUID"
        glance_enable: true
        glance_key: "GLANCE_CEPH_KEY"
        nova_enable: true

Example:

::

    configs:
      ceph:
        fsid: "afca8524-2c47-4b81-a0b7-2300e62212f9"
        initial_members: "ceph1"
        mon_host: "10.90.0.5"
        cinder_enable: true
        cinder_key: "AQBShfJXID9pFRAAm4VLpbNXa4XJ9zgAh7dm2g=="
        cinder_rbd_secret_uuid: "b416770d-f3d4-4ac9-b6db-b6a7ac1c61c0"
        glance_enable: true
        glance_key: "AQBShfJXzXyNBRAA5kqXzCKcFoPBn2r6VDYdag=="
        nova_enable: true


- **fsid** - Should be the same as **fsid** variable in the ceph cluster
  **ceph.conf** file.
- **initial_members** - Should be the same as **mon_initial_members**
  variable in the ceph cluster **ceph.conf** file.
- **mon_host** - Should contain any ceph mon node IP or hostname.
- ***_key** - Should be taken from the corresponding Ceph user. You can
  use **ceph auth list** command on the Ceph node to fetch list of all users
  and their keys.
- **cinder_rbd_secret_uuid** - Should be randomly generated. You can use
  **uuidgen** command for this.

Now you’re ready to deploy CCP with Ceph support.

Swift
=====

Prerequirements
---------------

Make sure that Ceph has a RadosGW deployed and that RadosGW configured to use
Keystone v3 authentetication.

Keystone v3 RadosGW configuration could be tricky, since it's really bad
documented. Working RadosGW keystone config should looks like this:

::

  rgw keystone api version = 3
  rgw keystone admin domain = default
  rgw keystone admin project = admin
  rgw keystone url = http://keystone.ccp.svc.cluster.local:35357
  rgw keystone accepted roles = Member, _member_, admin
  rgw keystone verify ssl = False
  rgw keystone admin user = admin
  rgw keystone admin password = password

Make sure that all credentials are correct and that Keystone url points to the
Keystone admin interface.

Deploy CCP with Swift
=====================

.. NOTE:: Currentrly, in CCP, only Glance supports Swift as a backend.

In order to deploy CCP with Swift you have to edit **ccp.yaml**:

::

  swift:
    glance_store_create_container_on_put: true
    keystone_enable: true
    glance_enable: true
    radosgw_host: "IP_OF_RADOSGW"
    radosgw_port: "PORT_OF_RADOSGW"

Example:

::

  swift:
    glance_store_create_container_on_put: true
    keystone_enable: true
    glance_enable: true
    radosgw_host: "10.90.0.2"
    radosgw_port: "8080"

Troubleshooting
---------------

If Glance image upload failed, you should check few things:

- Glance-api pod logs
- RadosGW logs
- Keystone pod logs

