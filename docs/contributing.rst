.. _contributing:

====================================
Contributing to Connectome Mapper 3
====================================

.. contents::

Philosophy
----------

The development philosophy for this new version of the Connectome Mapper is to:

I. Enhance interoperability by working with datasets structured following the Brain Imaging Data Structure structured dataset.

II. Keep the code of the processing as much as possible outside of the actual main Connectome Mapper code,
    through the use and extension of existing Nipype interfaces and an external library (dubbed cmtklib).

III. Separate the code of the graphical interface and the actual main Connectomer Mapper code
     through inheritance of the classes of the actual main stages and pipelines.

IV. Enhance portability by freezing the computing environment with all software dependencies installed,
    through the adoption of the BIDS App framework relying on light software container technologies.

V. Adopt best modern open-source software practices that includes to continuously test the build and execution of the BIDS App
   with code covergae and to follow the PEP8 and PEP257 conventions for python code and docstring style conventions.

VI. Follow the `all contributors  <https://allcontributors.org/>`_ specification to acknowledge any kind of contribution.


This means that contributions in many different ways (discussed in the following subsections) are welcome and will be properly ackowledged!
If you have contributed to ``CMP3`` and are not listed as contributor, please add yourself and make a pull request.

This also means that further development, typically additions of other tools and configuration options should go in this direction.

Contribution Types
-------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/connectomicslab/connectomemapper3/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Possible enhancements are probably to be included in the following list:

I. Adding of a configuration option to an existing stage
II. Adding a new interface to `cmtklib`
III. Adding of a new stage
IV. Adding of a new pipeline

The adding of newer configuration options to existing stages should be self-
understandable. If the addition is large enough to be considered a "sub-module"
of an existing stage, see the Diffusion stage example.

Adding a new stage implies the addition of the stage folder to the `cmp/stages` and `cmp/bidsappmanager/stages`
directory and according modification of the parent pipeline along with insertion
of a new image in `cmp/bidsappmanager/stages`. Copy-paste of existing stage (such as segmentation stage) is
recommended.

Adding a new pipeline implies the creation of a new pipeline script and folder
in the `cmp/pipelines` and `cmp/bidsappmanager/pipelines` directories Again copy-pasting an existing pipeline is the
better idea here. Modification of `cmp/project.py` and `cmp/bidsappmanager/project.py` file is also needed.

Each new module, class or function should be properly documented with a docstring.

Write Documentation
~~~~~~~~~~~~~~~~~~~

``CMP3`` could always use more documentation, whether as part of the
official CMP3 docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to create an issue at https://github.com/connectomicslab/connectomemapper3/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up ``Connectome Mapper 3`` for local development.

1. Fork the `connectomemapper3` repo on GitHub.

2. Clone your fork locally::

    git clone git@github.com:your_name_here/connectomemapper3.git
    cd connectomemapper3

3. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

4. Now you can make your changes locally. If you add a new node in a pipeline or a completely new pipeline, we encourage you to rebuild the BIDS App Docker image (See :ref:`BIDS App build instructions <instructions_bisapp_build>`).

.. note::
	Please keep your commit the most specific to a change it describes. It is highly advice to track unstaged files with ``git status``, add a file involved in the change to the stage one by one with ``git add <file>``. The use of ``git add .`` is highly disencouraged. When all the files for a given change are staged, commit the files with a brieg message using ``git commit -m "[COMMIT_TYPE]: Your detailed description of the change."`` that describes your change and where ``[COMMIT_TYPE]`` can be ``[FIX]`` for a bug fix, ``[ENH]`` for a new feature, ``[MAINT]`` for code maintenance and typo fix, ``[DOC]`` for documentation, ``[CI]`` for continuous integration testing.

5. When you're done making changes, push your branch to GitHub::

    git push origin name-of-your-bugfix-or-feature

6. Submit a pull request through the GitHub website.

Pull Request Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before you submit a pull request, check that it meets these guidelines:

1. If the pull request adds functionality, the docs and tests should be updated (See :ref:`documentation build instructions <instructions_docs_build>`).

2. Python code and docstring should comply with `PEP8 <https://www.python.org/dev/peps/pep-0008/>`_ and `PEP257 <https://www.python.org/dev/peps/pep-0257/>`_ standards.

3. The pull request should pass all tests on GitHub.

.. _instructions_bisapp_build:

How to build the BIDS App locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to the clone directory of your fork and run the script ``build_bidsapp.sh`` ::

    cd connectomemapper3
    sh build_bidsapp.sh

.. note::
	Tag of the version of the image is extracted from ``cmp/info.py``. You might want to change the version in this file to not overwrite an other existing image with the same version.

.. _instructions_docs_build:

How to build the documentation locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install the CMP3 conda environment ``py37cmp-gui`` with sphinx and all extensions to generate the documentation::

    cd connectomemapper3
    conda env create -f environment.yml

2. Activate CMP3 conda environment ``py37cmp-gui`` and install ``connectomemapper3`` ::

    conda activate py37cmp-gui
    (py37cmp-gui) python setup.py install

3. Run the script ``build_docs.sh`` to generate the HTML documentation in ``docs/_build/html``::

    (py37cmp-gui) bash build_docs.sh

.. note::
	Make sure to have activated the conda environment ``py37cmp-gui`` before running the script ``build_docs.sh``.

------------

:Authors: Sebastien Tourbier, Adrien Birbaumer
:Version: Revision: 2
:Copyright: Copyright (C) 2017-2021, Ecole Polytechnique Federale de Lausanne (EPFL)
            the University Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland,
            & Contributors,
            All rights reserved.

.. topic:: Acknowledgments

    We thanks the authors of `these great contributing guidelines  <https://github.com/dPys/PyNets/blob/master/CONTRIBUTING.rst>`_,
    from which part of this document has been inspired and adapted.