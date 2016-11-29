.. _quickstart:

=====================
Services Known Issues
=====================

This sections describe known issues and corresponding workarounds, if they are.

[Heat] WaitCondition and SoftwareDeployment resources
=====================================================

Problem description
-------------------

CCP deploy Heat services with default configurations, but it is not enough
for several type of resources like OS::Heat::Waitcondition and
OS::Heat::SoftwareDeployment, which require callback to Heat API. Due to
Kubernetes architecture it'd not possible to do such callback on the port
mentioned in config file (or in endpoint of keystone).

Also there is issue with resolving domain name to ip address from VM booted
in Openstack.

Workaround
----------

Before applying workaround please make sure, that current ccp deployment
satisfies follow prerequirements:
 - VM booted in Openstack can be reached via ssh (don't forget to configure
   corresponding security group rules).
 - IP address of host, where heat-api servuce is run, is accessible from VM in
   Openstack.

#. Issue with port access can be solved by getting ``Node Port``. Let's do it
   for all heat API services:

::

   # get Node Port API
   kubectl get service heat-api -o yaml | awk '/nodePort: / {print $NF}'

   # get Node Port API CFN
   kubectl get service heat-api-cfn -o yaml | awk '/nodePort: / {print $NF}'

#. Issue with resolving domain name, will be solved in future by providing
   internal dns server. Right now you can get ``service IP`` by executing
   ``ping`` command from host to domain names of services (e.g.
   ``heat-api.ccp``).

#. The last step is to set these IP and Node ports as internal endpoints for
   corresponding services in keystone, i.e. replace old with domain name and
   base port. It should looks like:

::

  # delete old endpoint
  openstack endpoint delete <id of internal endpoint>

  # create new endpoint for heat-api
  openstack endpoint create --region RegionOne \
  orchestration internal http://<service IP>:<Node Port API>/v1/%\(tenant_id\)s

  # create new endpoint for heat-api-cfn
  openstack endpoint create --region RegionOne \
  cloudformation internal http://<service IP>:<Node Port API CFN>/v1/

.. NOTE:: For validation you can use simple `template`_ with waitconditions.

.. _template: https://github.com/openstack/heat-templates/blob/master/hot/native_waitcondition.yaml
