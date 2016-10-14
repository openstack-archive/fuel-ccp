.. _config_repositories:

========================
``repositories`` section
========================

This section contains information about repositories with component definitions
that should be cloned by :command:`ccp fetch` command or used by other
:command:`ccp` commands.

Section-level parameters
========================

.. describe:: clone

  Run :command:`ccp fetch` analogue before running other commands. Default:
  ``true``

.. describe:: clone_concurrency

  Number of threads to use while cloning repos. Defaults to number of CPU cores
  available.

.. describe:: repos

  List of repository definitions (see :ref:`below <config_repo_def>`) that
  should be used by CCP tool. Defaults to a list of repos provided by CCP
  upstream.

.. _config_repo_path:

.. describe:: path

  Path to a dir where all repos are to be cloned or should be expected to be
  present.

.. describe:: skip_empty

  Ignore empty repositories. Default: ``true``

.. _config_repo_def:

Repository definitions
======================

Every item from this list describes one component repository that should be
downloaded or used by CCP tool.

.. describe:: name

  The name of the component, this is used as a name of directory in
  :ref:`path <config_repo_path>` to clone or find component repo.

.. describe:: git_url

  The URL where repo should be cloned from

.. describe:: git_ref

  Git ref that should be checked out
