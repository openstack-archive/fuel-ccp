=========================
Deploying k8s using Kargo
=========================

This guide provides a step by step instruction of how to deploy k8s cluster on
bare metal or a virtual machine using
`Kargo <https://github.com/kubespray/kargo>`__.

Node requirements
=================

The recommended deployment target requirements:

- At least 3 nodes
- At least 8Gb of RAM per node
- At least 20Gb of disk space on each node.

Deploy k8s cluster
------------------

Clone fuel-ccp-installer repository:

::

    git clone https://review.openstack.org/openstack/fuel-ccp-installer

Create deployment script:

.. NOTE:: HA setup is not supported right now

::

    cat > ~/create-kargo-env.sh << EOF
    #!/bin/bash
    set -ex

    # CHANGE ADMIN_IP AND SLAVE_IPS TO MATCH YOUR ENVIRONMENT
    export ADMIN_IP="10.90.0.2"
    export SLAVE_IPS="10.90.0.2 10.90.0.3 10.90.0.4"
    export DEPLOY_METHOD="kargo"
    export WORKSPACE="~/workspace"

    mkdir -p $WORKSPACE
    cd ~/fuel-ccp-installer
    bash -x "~/utils/jenkins/run_k8s_deploy_test.sh"
    EOF

- ``ADMIN_IP`` - IP of the node which will run ansible. This node must have ssh
  key access to all SLAVE_IPS nodes. May be one of the SLAVE_IPS.
- ``SLAVE_IPS`` - IPs of the k8s nodes.

Run script:

::

    bash ~/create-kargo-env.sh
