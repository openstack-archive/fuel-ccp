.. _ceph_cluster:

Ceph cluster deployment
=======================


.. WARNING:: This setup is very simple, limited and not suitable for real
   production use. Use it as an example only.

Using this guide you'll deploy 3 nodes Ceph cluster with RadosGW.

Prerequirements
---------------

- Three nodes with at least one unused disk available.
- In this example we're going to use Ubuntu 16.04 OS, if you're using the
  different one, you have to edit the following configs and commands to suit
  your OS.

In these doc we refering to these nodes as:

- ceph_node_hostname1
- ceph_node_hostname2
- ceph_node_hostname3

Installation
------------

::

  sudo apt install ansible
  git clone https://github.com/ceph/ceph-ansible.git

.. NOTE: You'll need `this patch <https://github.com/ceph/ceph-ansible/pull/1011/>`__
   for proper radosgw setup.

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
  # Pre-created static fsid
  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9 # 
  # interface which ceph should use
  monitor_interface: eth0
  monitor_address: 0.0.0.0
  journal_size: 1024
  # network which you want to use for ceph
  public_network: 10.90.0.0/24
  cluster_network: "{{ public_network }}"

  radosgw_civetweb_bind_ip: "ip_of_ceph_node_hostname1"
  radosgw_keystone: true
  radosgw_keystone_url: http://keystone.ccp.svc.cluster.local:35357
  radosgw_keystone_admin_token: password
  radosgw_keystone_verify_ssl: false
  radosgw_keystone_api_ver: 3
  radosgw_keystone_admin_domain: default
  radosgw_keystone_admin_project: admin
  radosgw_keystone_use_admin_token: false
  radosgw_keystone_use_admin_cred: true
  radosgw_keystone_admin_user: admin
  radosgw_keystone_admin_password: password

Create **group_vars/osds** with:

::

  fsid: afca8524-2c47-4b81-a0b7-2300e62212f9
  # devices to use in ceph on all osd nodes. Make sure it's empty, unused disk.
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
  [rgws]
  ceph_node_hostname1

Deploy
------

Make sure you have passwordless ssh key access to each node and run:

::

  ansible-playbook -e 'host_key_checking=False' -i inventory_file site.yml.sample

Check ceph deployment
---------------------

Go to any ceph node and run with root permissions:

::

  ceph -s

**health** should be HEALTH_OK. If it's HEALTH_WARN - check the error and try
to fix it. If it's HEALTH_ERR this probably means what deployment failed for
some reason.

Check radosgw deployment
------------------------

Go to ceph_node_hostname1 and checks:

::

  systemctl status ceph-radosgw@rgw.node1.service

It should be "Active: active (running)"

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
