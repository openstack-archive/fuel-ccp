===================================
OpenStack Compute node / VMs on K8s
===================================

This document describes approaches for implementing OpenStack Compute node
and running VMs on top of K8s from the prospective of "Hypervisor Pod". It
includes overview of currently selected approach, future steps and alternative
solutions.

Potential solutions
===================

This section consists of a list of potential solutions for implementing
OpenStack VMs on topc K8s. This solutions the case when Neutron ML2 OVS
used for OpenStack networking. Pros and Cons listed for each solution.
Not all possible solutions (with all combinations of pod-container topologies)
listed here, only part that makes sense or needed to show transition from
bad to good options.

1. Everything in one pod
------------------------

Pods and containers
^^^^^^^^^^^^^^^^^^^

Hypervisor / Compute / Networking Pod:

1. QEMU / KVM / Libvirt
2. OVS DB
3. OVS vswitchd
4. nova-compute
5. neutron-ovs-agent

Pros & cons
^^^^^^^^^^^

Pros:

1. One pod will represent the whole OpenStack compute node (very minor
   advantage)

Cons:

1. It's impossible to make upgrade of any service without killing virtual
   machines
2. All containers will have the same characteristics such as net=host, user,
   volumes and etc.


2. Libvirt and VMs baremetal, OpenStack part in one pod
-------------------------------------------------------

Pods and containers
^^^^^^^^^^^^^^^^^^^

Baremetal (not in containers):

1. QEMU / KVM / Libvirt
4. OVS (DB and vswitchd)

Compute / Networking Pod:

1. nova-compute
2. neutron-ovs-agent

Pros & cons
^^^^^^^^^^^

Pros:

1. Restart of docker and docker containers will not affect running VMs as
   libvirt running on baremetal
2. Docker and docker containers downtime will not affect networking as OVS
   running on host, only new rules will not be passed to the host

Cons:

1. External orchestration required to for managing Libvirt on baremetal,
   especially for upgrades
2. It's impossible to update nova without neutron and vice versa.


3. Libvirt and VMs baremetal, pod per OpenStack process
-------------------------------------------------------

Pods and containers
^^^^^^^^^^^^^^^^^^^

Baremetal (not in containers):

1. QEMU / KVM / Libvirt
2. OVS DB / vswitchd

Compute Pod:

1. nova-compute

Networking Pod:

1. neutron-ovs-agent

Pros & cons
^^^^^^^^^^^

Same as option number 3, but it's possible to upgrade nova and neutron
separately.


4. Libvirt and VMs in one pod, pod per OpenStack service
--------------------------------------------------------

Notes
^^^^^

It's a primary approach and it's currently implemented in Fuel CCP. Libvirt
upgrade in such case could only be done by evacuating virtual machines from
the host first, but, for example, nova-compute could be upgraded in place.

Pods and containers
^^^^^^^^^^^^^^^^^^^

Hypervisor pod:

1. QEMU / KVM / Libvirt

OVS DB pod:

1. OVS DB

OVS vswitchd pod:

1. OVS vswitchd

Compute Pod:

1. nova-compute

Networking pod:

1. neutron-ovs-agent

Pros & cons
^^^^^^^^^^^

Pros:

1. No external orchestration required for compute node provisioning
2. All OpenStack parts and dependencies are managed through K8s in such case,
   so it's possible to upgrade any service including libvirt, nova, neutron and
   ovs without external orchestration, just through the K8s API

Cons:

1. Docker or docker containers downtime will affect running VMs or networking


5. Libvirt in pod w/ host pid, pod per OpenStack service, VMs outside of containers
-----------------------------------------------------------------------------------

Notes
^^^^^

It's a "next step" approach based on Pros & Cond. It should be investigated
in details and stability should be verified. If there will be no issues than
it should become regerence approach of OPenStack VMs deployment on K8s.
Potentially, another level of improvements needed to avoid affecting networking
when docker or docker containers restarted.

Pods and containers
^^^^^^^^^^^^^^^^^^^

Hypervisor pod:

1. QEMU / KVM / Libvirt (using host pid)

OVS DB pod:

1. OVS DB

OVS vswitchd pod:

1. OVS vswitchd

Compute Pod:

1. nova-compute

Networking pod:

1. neutron-ovs-agent

Pros & cons
^^^^^^^^^^^

Same as option number 4, but improved to not affect virtual machines when
docker or docker containers restart.


Conclusion
==========

Option number 4 is currently selected as implementation design for Fuel CCP,
while as end goal we'd like to achieve approach where restarting docker and
docker containers will not affect running virtual machines. In future, we'll
need to evaluate additional improvements to guarantee that K8s and docker
downtime doesn't affect running VMs.
