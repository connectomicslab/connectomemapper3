.. _installation:

************************************
Installation Instructions for Users
************************************

.. warning:: This software is for research purposes only and shall not be used for
             any clinical use. This software has not been reviewed or approved by
             the Food and Drug Administration or equivalent authority, and is for
             non-clinical, IRB-approved Research Use Only. In no event shall data
             or images generated through the use of the Software be used in the
             provision of patient care.


The Connectome Mapper 3 is composed of a Docker image, namely the Connectome Mapper 3 BIDS App, and a Python Graphical User Interface, namely the Connectome Mapper BIDS App Manager.

* Installation instructions for the Connectome mapper 3 BIDS App are found in :ref:`manual-install-cmpbidsapp`.
* Installation instructions for the Connectome mapper 3 BIDS App Manager are found in :ref:`manual-install-cmpbidsappmanager`.

..
    The steps to add the NeuroDebian repository are explained at http://neuro.debian.net/ .

Make sure that you have installed the following prerequisites.

.. important::

    On Mac and Windows, if you want to track the carbon emission incurred by the processing with the ``--track_carbon_footprint`` option flag, you will need to install in addition the `Intel Power Gadget` tool available `here <https://www.intel.com/content/www/us/en/developer/articles/tool/power-gadget.html>`_.


The Connectome Mapper 3 BIDSApp
===============================

.. _manual-install-docker:

Prerequisites
-------------

* Install Docker Engine depending of your system:

  * For Ubuntu 14.04/16.04/18.04, follow the instructions at
    https://docs.docker.com/install/linux/docker-ce/ubuntu/

  * For Mac OSX (>=10.10.3), get the .dmg installer at
    https://store.docker.com/editions/community/docker-ce-desktop-mac

  * For Windows (>=10), get the installer at
    https://store.docker.com/editions/community/docker-ce-desktop-windows

.. note:: Connectome Mapper 3 BIDSApp has been tested only on Ubuntu and MacOSX.
    In principles, it should also run on Windows but it might require a few patches
    to make it work.


* Manage Docker as a non-root user

  * Open a terminal

  * Create the docker group::

    $ sudo groupadd docker

  * Add the current user to the docker group::

    $ sudo usermod -G docker -a $USER

  * Reboot

    After reboot, test if docker is managed as non-root::

      $ docker run hello-world


.. _manual-install-cmpbidsapp:

Installation
---------------------------------------

Installation of the Connectome Mapper 3 has been facilitated through the distribution of a BIDSApp relying on the Docker software container technology.

* Open a terminal

* Get the latest release (|release|) of the BIDS App:

  .. parsed-literal::

    $ docker pull sebastientourbier/connectomemapper-bidsapp:|release|

* To display all docker images available::

  $ docker images

You should see the docker image "connectomemapper-bidsapp" with tag "|release|" is now available.

* You are ready to use the Connectome Mapper 3 BIDS App from the terminal. See its `commandline usage <usage.html>`_.


The Connectome Mapper 3 BIDSApp Manager (GUI)
==============================================

Prerequisites
---------------

* Install miniconda3 (Python 3) from https://conda.io/miniconda.html

  Download the Python 3 installer corresponding to your 32/64bits MacOSX/Linux/Win system.


.. _manual-install-cmpbidsappmanager:

Installation
---------------------------------------
The installation of the Connectome Mapper 3 BIDS App Manager (CMPBIDSAPPManager) consists of a clone of the source code repository, the creation of conda environment with all python dependencies installed, and eventually the installation of the CMPBIDSAPPManager itself, as follows:

* Open a terminal

* Go to the folder in which you would like to clone the source code repository::

  $ cd <INSTALLATION DIRECTORY>

* Clone the source code repository::

  $ git clone https://github.com/connectomicslab/connectomemapper3.git connectomemapper3

* Create a branch and checkout the code corresponding to this version release:

  .. parsed-literal::

    $ cd connectomemapper3
    $ git fetch
    $ git checkout tags/|release| -b |release|

.. note::
  If a few bugs related to the Graphical User Interface were fixed after releasing the version, you might want to use the code at its latest version on the master branch (i.e. ``git checkout master``).

* Create a miniconda3 environment where all python dependencies will be installed::

    $ cd connectomemapper3
    $ conda env create -f conda/environment.yml

.. important::
  It seems there is no conda package for `git-annex` available on Mac.
  For your convenience, we created an additional `conda/environment_macosx.yml`
  miniconda3 environment where the line `- git-annex=XXXXXXX` has been removed.
  Git-annex should be installed on MacOSX using `brew <https://brew.sh/index_fr>`_
  i.e. ``brew install git-annex``. See https://git-annex.branchable.com/install/ for more details.

  Note that `git-annex` is only necessary if you wish to use BIDS datasets managed by Datalad (https://www.datalad.org/).

* Activate the conda environment::

  $ source activate py37cmp-gui

  or::

  $ conda activate py37cmp-gui

* Install the Connectome Mapper BIDS App Manager from the Bash Shell using `pip`::

    (py37cmp-gui)$ cd connectomemapper3/
    (py37cmp-gui)$ pip install .

* You are ready to use the Connectome Mapper 3 (1) via its Graphical User Interface (GUI) aka CMP BIDS App Manager
  (See :ref:`guiusage` for the user guide), (2) via its python ``connectomemapper3_docker`` and
  ``connectomemapper3_singularity`` wrappers (See :ref:`wrapperusage` for commandline usage), or (3) by
  interacting directly with the Docker / Singularity Engine (See :ref:`<containerusage` for commandline usage).

.. admonition:: In the future

    If you wish to update Connectome Mapper 3 and the Connectome Mapper 3 BIDS App Manager,
    this could be easily done by (1) updating the git repository to a new tag with `git fetch` and
    `git checkout tags/|release| -b |release|` and (2) running `pip install .`.

Help/Questions
--------------

If you run into any problems or have any questions, you can post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_.
Code bugs can be reported by creating a "New Issue" on the `source code repository <https://github.com/connectomicslab/connectomemapper3/issues>`_.
