************************
Installation Instruction
************************

.. warning:: This software is for research purposes only and shall not be used for
             any clinical use. This software has not been reviewed or approved by
             the Food and Drug Administration or equivalent authority, and is for
             non-clinical, IRB-approved Research Use Only. In no event shall data
             or images generated through the use of the Software be used in the
             provision of patient care.


The Connectome Mapper 3 is composed of a Docker image, namely the Connectome Mapper 3 BIDS App, and a Python Graphical User Interface, namely the Connectome Mapper BIDS App Manager.
Installation instructions for the Connectome mapper 3 BIDS App are found in :ref:`manual-install-cmpbidsapp`.
Installation instructions for the Connectome mapper 3 BIDS App are found in :ref:`manual-install-cmpbidsappmanager`.

..
	The steps to add the NeuroDebian repository are explained here::

		firefox http://neuro.debian.net/

But before, make sure that you have installed the following prerequisites.

The Connectome Mapper 3 BIDSApp
===============================

Prerequisites
-------------

* Installed Docker Engine

  firefox https://store.docker.com/search?type=edition&offering=community

* Docker managed as a non-root user

  * Create the docker group::

    $ sudo groupadd docker

  * Add the current user to the docker group::

    $ sudo usermod -G docker -a $USER

  * Reboot

    After reboot, test if docker is managed as non-root::

      $ docker run hello-world

* Installed miniconda2 (Python 2.7)

  firefox https://conda.io/miniconda.html

  Download the Python 2.7 installer corresponding to your system (Windows/MacOSX/Linux)


.. _manual-install-cmpbidsapp:

Manual installation
---------------------------------------

Installation of the Connectome Mapper 3 has been facilicated through the distribution of a BIDSApp relying on the Docker software container technology.

* Get the latest release of the BIDS App::

  $ docker pull sebastientourbier/connectomemapper-bidsapp:latest

* To display all docker images available::

  $ docker images

You should see the docker image "connectomemapper-bidsapp" with tag "latest" is now available.


The Connectome Mapper 3 BIDSApp Manager (GUI)
===============================

Prerequisites
-------------

* Installed miniconda2 (Python 2.7)

  $ firefox https://conda.io/miniconda.html

  Download the Python 2.7 installer corresponding to your system (Windows/MacOSX/Linux)


.. _manual-install-cmpbidsappmanager:

Manual installation
---------------------------------------
The installation of the Connectome Mapper 3 BIDS App Manager (CMPBIDSAPPManager) consists of a clone of the GitHub repository, the creation of conda environment with all python dependencies installed, and eventually the installation of the CMPBIDSAPPManager itself, as follows:

* Clone the GitHub repository::

  $ git clone https://github.com/sebastientourbier/cmpbidsappmanager.git cmpbidsappmanager

* Create a miniconda2 environment where all python dependencies will be installed, this by using the spec list "conda_packages_list.txt" provided by the repository::

	$ conda create --name cmppy27 --file /absolute/path/to/conda_packages_list.txt

* Activate the conda environment::

  $ source activate cmppy27

* Install the Connectome Mapper BIDS App Manager from the Bash Shell using following commands::

	$ cd cmpbidsappmanager/
	$ python setup.py install

Help/Questions
--------------

If you run into any problems or have any questions, you can post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_. Code bugs can be reported by creating a "New Issue" on the `public repository <https://github.com/LTS5/cmp/issues>`_.
