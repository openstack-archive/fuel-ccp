.. _CONTRIBUTING:

=================
How To Contribute
=================

General info
============

#. Bugs should be filed on launchpad_, not GitHub.

#. Please follow OpenStack `Gerrit Workflow`_ to contribute to CCP.

#. Since CCP has multiple Git repositories, make sure to use `Depends-On`_
   Gerrit flag to create cross repository dependencies.


.. _launchpad: https://bugs.launchpad.net/fuel-ccp
.. _Gerrit Workflow: http://docs.openstack.org/infra/manual/developers.html#development-workflow
.. _Depends-On: http://docs.openstack.org/infra/manual/developers.html#cross-repository-dependencies


Useful documentation
====================

- Please follow our :doc:`quickstart` guide to deploy your environment and
  test your changes.

- Please refer to :doc:`docker`, while making changes to Docker files.

- Please refer to :doc:`app_def_guide`, while making changes to ``service/*``
  files.
