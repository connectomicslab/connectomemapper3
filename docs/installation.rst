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

Manual installation of the Connectome Mapper 3 BIDS App
---------------------------------------

Installation of the Connectome Mapper 3 has been facilicated through the distribution of a BIDSApp relying on the Docker sofware container technology.

* Get the latest release of the BIDS App

  $ docker pull sebastientourbier/connectomemapper-bidsapp:latest

* To display all docker images available

  $ docker images

  You should see the docker image "connectomemapper-bidsapp" with tag "latest" is now available.


.. _manual-install-cmpbidsappmanager:

Manual installation of the Connectome Mapper 3 BIDS App
---------------------------------------

Manual installation is divided between the Python libraries needed by the Connectome Mapper and the CMTKlib and the libraries needed by the DTB binaries. Files for manual installation is the zipped archive of the Connectome Mapper.

* Download the zipped archive from `here <download.html>`_
* As we will use `easy_install` in order to have access to the latest libraries even on older systems the python-setuptools package is needed. Ipython is strongly recommended for debugging purposes. Debian/Ubuntu command::

	sudo apt-get install python-setuptools ipython

* Python libraries needed: traits, traitsui, pyface, nibabel, numpy, networkx, scipy. Easy_install command::

	sudo easy_install traits traitsui pyface nibabel numpy networkx scipy nose

* Install our forked version of Nipype (http://nipy.sourceforge.net/nipype/). For now, we require a modified vesion Nipype interfaces that is available on our Github repository (https://github.com/LTS5/nipype). To install it clone to your machine the nipype fork by typing `git clone git://github.com/LTS5/nipype.git` from your home folder, and run the install script with `sudo python setup.py install`. You will have to remove already installed versions of nipype if they were installed through apt-get (installation location: `/usr/lib/pyshared`) as it will take precedence over versions installed through the setup.py script.
* Libraries needed by the DTB binaries: boost (module program-options), nifti, blitz: `sudo apt-get install libboost-program-options-dev libnifti-dev libblitz0-dev`
* Extract the source code and install the Connectome Mapper from the Bash Shell using following commands::

	tar xzf <cmp-release>.tar.gz
	cd <cmp-release>/
	sudo python setup.py install

Help/Questions
--------------

If you run into any problems or have any questions, you can post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_. Code bugs can be reported by creating a "New Issue" on the `public repository <https://github.com/LTS5/cmp/issues>`_.
