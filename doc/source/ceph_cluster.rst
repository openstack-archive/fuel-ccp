.. _ceph_cluster:

=======================
Ceph cluster deployment
=======================


.. WARNING:: This setup is very simple, limited, and not suitable for real
   production use. Use it as an example only.

Using this guide you'll deploy a 3 nodes Ceph cluster with RadosGW.

Prerequirements
~~~~~~~~~~~~~~~

- Three nodes with at least one unused disk available.
- In this example we're going to use Ubuntu 16.04 OS, if you're using a
  different one, you have to edit the following configs and commands to suit
  your OS.

In this doc we refer to these nodes as

- ceph_node_hostname1
- ceph_node_hostname2
- ceph_node_hostname3

Installation
~~~~~~~~~~~~

::

  sudo apt install ansible
  git clone https://github.com/ceph/ceph-ansible.git

.. NOTE: You'll need `this patch <https://github.com/ceph/ceph-ansible/pull/1011/>`__
   for proper radosgw setup.

Configuration
~~~~~~~~~~~~~

cd into ceph-ansible directory:
::

  cd ceph-ansible

Create ``group_vars/all`` with:

::

  ceph_origin: upstream
  ceph_stable: true
  ceph_stable_key: https://download.ceph.com/keys/release.asc
  ceph_stable_release: jewel
  ceph_stable_repo: "http://download.ceph.com/debian-{{ ceph_stable_release }}"
  cephx: true
  generate_fsid: false
  # Pre-created static fsid
  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9
  # interface which ceph should use
  monitor_interface: NAME_OF_YOUR_INTERNAL_IFACE
  monitor_address: 0.0.0.0
  journal_size: 1024
  # network which you want to use for ceph
  public_network: 10.90.0.0/24
  cluster_network: "{{ public_network }}"

Make sure you change the ``NAME_OF_YOUR_INTERNAL_IFACE`` placeholder to the
actual interface name, like ``eth0`` or ``ens*`` in modern OSs.

Create ``group_vars/osds`` with:

::

  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9
  # Devices to use in ceph on all osd nodes.
  # Make sure the disk is empty and unused.
  devices:
  - /dev/sdb
  # Journal placement option.
  # This one means that journal will be on the same drive but another partition
  journal_collocation: true

Create ``group_vars/mons`` with:

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
~~~~~~

Make sure you have passwordless ssh key access to each node and run:

::

  ansible-playbook -e 'host_key_checking=False' -i inventory_file site.yml.sample

Check Ceph deployment
~~~~~~~~~~~~~~~~~~~~~

Go to any ceph node and run with root permissions:

::

  ceph -s

``health`` should be HEALTH_OK. HEALTH_WARN signify non-critical error, check
the description of the error to get the idea of how to fix it. HEALTH_ERR
signify critical error or a failed deployment.

Configure pools and users
~~~~~~~~~~~~~~~~~~~~~~~~~

On any Ceph node run:

::

  rados mkpool images
  rados mkpool volumes
  rados mkpool vms

::

  ceph auth get-or-create client.glance osd 'allow rwx pool=images, allow rwx pool=vms' mon 'allow r' -o /etc/ceph/ceph.client.glance.keyring
  ceph auth get-or-create client.cinder osd "allow class-read object_prefix rbd_children, allow rwx pool=volumes, allow rwx pool=vms, allow rwx pool=images" mon "allow r"
  ceph auth get-or-create client.cinder osd 'allow rwx pool=volumes, allow rwx pool=vms, allow rx pool=images' mon 'allow r' -o /etc/ceph/ceph.client.cinder.keyring
  ceph auth get-or-create client.radosgw.gateway osd 'allow rwx' mon 'allow rwx' -o /etc/ceph/ceph.client.radosgw.keyring

To list all user with permission and keys, run:

::

  ceph auth list

Now you're ready to use this Ceph cluster with CCP.
