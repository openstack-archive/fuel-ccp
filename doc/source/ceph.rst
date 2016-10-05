.. _ceph:

====================
Ceph and Swift guide
====================

This guide provides an instruction for adding Ceph and Swift support for
CCP deployment.

.. NOTE:: That it's not the CCP responsibility to deploy Ceph cluster, so it's
   expected that working Ceph cluster is already available and accessible from
   the all k8s nodes. If you don't have Ceph cluster, but still want to try CCP
   with Ceph, you can use :doc:`ceph_cluster` guide for deploying simple 3
   node Ceph cluster.

Ceph
~~~~

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

In order to deploy CCP with Ceph you have to edit ``ccp.yaml`` the file:

::

    configs:
      ceph:
        fsid: "FSID_OF_THE_CEPH_CLUSTER"
        initial_members: "INITIAL_MEMBERS_OF_CEPH_CLUSTER"
        mon_host: "CEPH_MON_HOSTNAME"
      cinder:
        enable: true
        key: "CINDER_CEPH_KEY"
        rbd_secret_uuid: "RANDOM_UUID"
      glance:
        enable: true
        key: "GLANCE_CEPH_KEY"
      nova:
        enable: true

Example:

::

    configs:
      ceph:
        fsid: "afca8524-2c47-4b81-a0b7-2300e62212f9"
        initial_members: "ceph1"
        mon_host: "10.90.0.5"
      cinder:
        enable: true
        key: "AQBShfJXID9pFRAAm4VLpbNXa4XJ9zgAh7dm2g=="
        rbd_secret_uuid: "b416770d-f3d4-4ac9-b6db-b6a7ac1c61c0"
      glance:
        enable: true
        key: "AQBShfJXzXyNBRAA5kqXzCKcFoPBn2r6VDYdag=="
      nova:
        enable: true


- ``fsid`` - Should be the same as ``fsid`` variable in the Ceph cluster
  ``ceph.conf`` file.
- ``initial_members`` - Should be the same as ``mon_initial_members``
  variable in the Ceph cluster ``ceph.conf`` file.
- ``mon_host`` - Should contain any Ceph mon node IP or hostname.
- ``key`` - Should be taken from the corresponding Ceph user. You can
  use the ``ceph auth list`` command on the Ceph node to fetch list of all
  users and their keys.
- ``rbd_secret_uuid`` - Should be randomly generated. You can use the
  ``uuidgen`` command for this.

Now you’re ready to deploy CCP with Ceph support.

Swift
~~~~~

Prerequirements
---------------

Make sure that Ceph has a RadosGW deployed and that is RadosGW configured to
use Keystone v3 authentetication.

Working RadosGW keystone config should looks like this:

::

  rgw keystone api version = 3
  rgw keystone admin domain = default
  rgw keystone admin project = admin
  rgw keystone url = http://keystone.ccp.svc.cluster.local:35357
  rgw keystone accepted roles = Member, _member_, admin
  rgw keystone verify ssl = False
  rgw keystone admin user = admin
  rgw keystone admin password = password

Make sure that all credentials are correct and that the Keystone url points to
the Keystone admin interface.

Deploy CCP with Swift
---------------------

.. NOTE:: Currently, in CCP, only Glance supports Swift as a backend.

In order to deploy CCP with Swift you have to edit ``ccp.yaml`` the file:

::

  keystone:
    swift:
      enable: true
      radosgw:
        host: "IP_OF_RADOSGW"
        port: "PORT_OF_RADOSGW"
  glance:
    swift:
      enable: true
      store_create_container_on_put: true

Example:

::

  keystone:
    swift:
      enable: true
      radosgw:
        host: "10.90.0.2"
        port: "8080"
  glance:
    swift:
      enable: true
      store_create_container_on_put: true

Troubleshooting
---------------

If the Glance image upload failed, you should check few things:

- Glance-api pod logs
- RadosGW logs
- Keystone pod logs

