.. _ceph:

==========
Ceph Guide
==========

This guide provides a step by step instruction of how to add Ceph support
for CCP deployment.

Prerequirements
===============

It's not the CCP responsibility to deploy Ceph cluster, so it's expected that
working Ceph cluster is already available and accessible from the all k8s
nodes.

Additionally, you need to ensure that these pools are created:

* images
* volumes
* vms

And what users "glance" and "cinder" are created and have this permissions:

::

  client.cinder
        caps: [mon] allow r
        caps: [osd] allow rwx pool=volumes, allow rwx pool=vms, allow rx pool=images
  client.glance
        caps: [mon] allow r
        caps: [osd] allow rwx pool=images, allow rwx pool=vms

.. NOTE:: If you don't have Ceph cluster, but still want to try CCP with Ceph,
   you can find an instruction for deploying simple 3 node Ceph cluster below
   in this guide.

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

Ceph cluster deployment
=======================


.. WARNING:: This setup is very simple, limited and not suitable for real
   production use. Use it as an example only.

Prerequirements
---------------

- Three nodes with at least one unused disk available.
- In this example we're going to use Ubuntu 16.04 OS, if you're using the
  different one, you have to edit the following configs and commands to suit
  your OS.

Installation
------------

::

  sudo apt install ansible
  git clone https://github.com/ceph/ceph-ansible.git

Configuration
-------------

cd into ceph-ansible directory:
::

  cd ceph-ansible

Create **group_vars/all** with:

::

  ceph_origin: upstream
  ceph_stable: true
  ceph_stable_key: https://download.ceph.com/keys/release.asc
  ceph_stable_release: jewel
  ceph_stable_repo: "http://download.ceph.com/debian-{{ ceph_stable_release }}"
  cephx: true
  generate_fsid: false
  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9
  monitor_interface: eth0
  monitor_address: 0.0.0.0
  journal_size: 1024
  public_network: 10.90.0.0/24
  cluster_network: "{{ public_network }}"
  common_single_host_mode: true

Create **group_vars/osds** with:

::

  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9
  # devices to use in ceph on all osd nodes. Use the name you used in the "Adding a disk for osd" step.
  devices:
  - /dev/sdb
  # Journal placement selection: this one means that journal will be on the same drive but another partition
  journal_collocation: true

Create **group_vars/mons** with:

::

  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9
  monitor_secret: AQAjn8tUwBpnCRAAU8X0Syf+U8gfBvnbUkDPyg==

Create inventory file with:

::

  [mons]
  ceph_node_hostname1
  ceph_node_hostname2
  ceph_node_hostname3
  [osds]
  ceph_node_hostname1
  ceph_node_hostname2
  ceph_node_hostname3

Deploy
------

Make sure you have passwordless ssh key access to each node and run:

::

  ansible-playbook -e 'host_key_checking=False' -i inventory_file site.yml.sample

Check deployment
----------------

Go to any ceph node and run with root permissions:

::

  ceph -s

**health** should be HEALTH_OK. If it's HEALTH_WARN - check the error and try
to fix it. If it's HEALTH_ERR this probably means what deployment failed for
some reason.

Configure pools and users
-------------------------

On any Ceph node run:

::

  rados mkpool images
  rados mkpool volumes
  rados mkpool vms

::

  ceph-authtool /etc/ceph/ceph.client.glance.keyring -C --gen-key --name client.glance --cap mon 'allow r' --cap osd 'allow rwx pool=images, allow rwx pool=vms'
  ceph auth add client.glance -i /etc/ceph/ceph.client.glance.keyring
   
  ceph-authtool /etc/ceph/ceph.client.cinder.keyring -C --gen-key --name client.cinder --cap mon 'allow r' --cap osd 'allow rwx pool=volumes, allow rwx pool=vms, allow rx pool=images'
  ceph auth add client.cinder -i /etc/ceph/ceph.client.cinder.keyring

To list all user with permission and keys, run:

::

  ceph auth list

Now you're ready to use this Ceph cluster with CCP.
