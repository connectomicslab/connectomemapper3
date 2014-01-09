************************
Installation Instruction
************************

.. warning:: This software is for research purposes only and shall not be used for
             any clinical use. This software has not been reviewed or approved by
             the Food and Drug Administration or equivalent authority, and is for
             non-clinical, IRB-approved Research Use Only. In no event shall data
             or images generated through the use of the Software be used in the
             provision of patient care.


Installation instructions for the Connectome mapper are found in :ref:`manual-install`.

..
	The steps to add the NeuroDebian repository are explained here::
	
		firefox http://neuro.debian.net/
	
But before, make sure that you have installed the following prerequisites.

Prerequisites
-------------

* Installed version of Diffusion Toolkit::

	firefox http://trackvis.org/dtk/
	
  Diffusion toolkit executables ('dtk', 'odf_recon', ...) should be in the `$PATH` environmental variable, and `$DSI_PATH` needs to be set to the folder containing the diffusion matrices.

* Installed and configured version of Freesurfer (http://surfer.nmr.mgh.harvard.edu/)::

	firefox http://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall
	
  `$FREESURFER_HOME` should have been declared and the Freesurfer setup script should have been sourced as described here: http://surfer.nmr.mgh.harvard.edu/fswiki/SetupConfiguration.

* Installed and configured version of FSL (http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/). Installation can be done through the NeuroDebian repository::

	sudo apt-get install fsl fslview fslview-doc

  `$FSLDIR` should have been declared and the FSL setup script should have been sourced as described under "Installation" here: http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FSL%20FAQ

* Installed version of MRTrix::

	firefox http://www.brain.org.au/software/mrtrix/install/index.html
	
* Installed version of Camino::

	firefox http://cmic.cs.ucl.ac.uk/camino/index.php?n=Main.Installation
	
* Installed versions of Dipy and Camino-Trackvis converter::

	sudo apt-get install python-dipy
	firefox http://sourceforge.net/projects/camino-trackvis/
	
* Installed version of the gibbs tracker::

	firefox http://mitk.org/Download

* At this point, make sure that you have setup the environment variables correctly for the external packages such as Freesurfer and Diffusion Toolkit (The FSL environment variables should be set automatically when installing FSL as described above). You should have the environment variables: FREESURFER_HOME, DTDIR, DSI_DIR and FSLDIR. You can check this if you enter in the bash shell (terminal), they should give you the correct path to your packages::

    echo $FREESURFER_HOME
    echo $FSLDIR
    echo $DTDIR

  In case, you can update your bash configuration to automatically declare the variables::

    gedit /home/username/.bashrc

  It should contain something similar as (adapted to your installation paths)::

	# FREESURFER configuration
	export FREESURFER_HOME="/usr/share/freesurfer"
	source "${FREESURFER_HOME}/SetUpFreeSurfer.sh"

	# DIFFUSION TOOLKIT configuration
	export DTDIR="/usr/share/dtk"
	export DSI_PATH="/usr/share/dtk/matrices"
	export PATH="${DTDIR}:${PATH}"

	# FSL configuration
	source /etc/fsl/4.1/fsl.sh
	
	# Camino to trackvis
	export CAMINO2TRK=/usr/share/camino-trackvis-0.2.8.1/bin/
	
	# Update PATH
	export PATH="${DTDIR}:${CAMINO2TRK}:${PATH}"

..
	.. _debian-install:
	
	
	Debian package installation (Ubuntu >=11.10)
	--------------------------------------------
	
	Installation is composed of a :doc:`debian package file <download>` (cmp_2.x.x_all.deb, containing the python cmp and cmtklib packages) and compiled binaries (32/64 bit versions available).
	
	.. |dtb_download| raw:: html
	
		<tt class="xref download docutils literal"><a class="reference download internal" href="_downloads/DTB.tar.gz" onmousedown="_gaq.push(['_trackEvent', 'DTB', 'download']);">Download</a></tt>
	
	* :doc:`Download <download>` the .deb package and install it with the Ubuntu Software Center (default if you double click on the package on Ubuntu) or using the dpkg command (sudo dpkg -i cmp_2.x.x_all.deb). This will install all the needed dependencies.
	* |dtb_download| the compiled binaries needed by the Connectome Mapper and install them by putting them somewhere in the PATH (e.g. copy all the executable of the archive to /usr/local/bin). If you run into any trouble when running the connectome mapper, try recompiling the executables from the "src" folder.
	* Install our forked version of Nipype (http://nipy.sourceforge.net/nipype/). For now, we require a modified version of Nipype interfaces that is available on our Github repository (https://github.com/LTS5/nipype). To install it clone to your machine the nipype fork by typing `git clone git://github.com/LTS5/nipype.git`, and run the install script with `sudo python setup.py install`. You will have to remove already installed versions of nipype if they were installed through apt-get (installation location: `/usr/lib/pyshared`) as it will take precedence over versions installed through the setup.py script.
    	
.. _manual-install:

Manual installation (all distributions)
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

If you run into any problems or have any questions, you can post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_. Code bugs can be reported by creating a "New Issue" on the `github repository <https://github.com/LTS5/cmp_nipype/issues>`_.

