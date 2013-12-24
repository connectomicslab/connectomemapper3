************************
Installation Instruction
************************

.. warning:: This software is for research purposes only and shall not be used for
             any clinical use. This software has not been reviewed or approved by
             the Food and Drug Administration or equivalent authority, and is for
             non-clinical, IRB-approved Research Use Only. In no event shall data
             or images generated through the use of the Software be used in the
             provision of patient care.

Step-by-Step Guide for Installation on Ubuntu/Debian
====================================================

Installation of the new Connectome Mapper through :ref:`debian-install`. For older versions of Ubuntu / different distributions, please look at the :ref:`manual-install`.

The steps to add the NeuroDebian repository are explained here::

	firefox http://neuro.debian.net/
	
Prerequesites are needed anyway, for all the installation choices.

Prerequisites
-------------

* Installed version of Diffusion Toolkit::

	firefox http://trackvis.org/dtk/
	
Diffusion toolkit executables ('dtk', 'odf_recon', ...) should be in the `$PATH`, and `$DSI_PATH` needs to be set to the folder containing the diffusion matrices.

* Installed and configured version of Freesurfer (http://surfer.nmr.mgh.harvard.edu/)::

	firefox http://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall
	
`$FREESURFER_HOME` should have been declared and the Freesurfer setup script should have been sourced as described here: http://surfer.nmr.mgh.harvard.edu/fswiki/SetupConfiguration.

* Installed and configured version of FSL (http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/). Installation can be done through the NeuroDebian repository::

	sudo apt-get install fsl fslview fslview-doc

`$FSLDIR` should have been declared and the FSL setup script should have been sourced as described under "Installation" here: http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FSL%20FAQ

* At this point, make sure that you have setup the environment variables correctly for the external packages such as Freesurfer and Diffusion Toolkit (The FSL environment variables should be set automatically when installing FSL as described above). You should have the environment variables: FREESURFER_HOME, DTDIR, DSI_DIR and FSLDIR. You can check this if you enter in the bash shell (terminal), they should give you the correct path to your packages::

    echo $FREESURFER_HOME
    echo $FSLDIR
    echo $DTDIR

In case, you can update your bash configuration::

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

.. _debian-install:

Debian package installation (Ubuntu >=11.10)
--------------------------------------------

Installation is composed of a debian package file (cmp_2.x.x_all.deb, containing the python cmp and cmtklib packages) and compiled binaries (32/64 bit versions available).

* Install the .deb package with the Ubuntu Software Center (default if you double click on the package on Ubuntu) or using the dpkg command (sudo dpkg -i cmp_2.x.x_all.deb). This will install all the needed dependencies.
* Install the compiled binaries needed by the Connectome Mapper by putting them somewhere in the PATH (e.g. copy all the files of the archive to /usr/local/bin)
* Install our forked version of Nipype (http://nipy.sourceforge.net/nipype/). For now, we require a modified vesion Nipype interfaces that is available on our Github repository (https://github.com/LTS5/nipype). To install it clone to your machine the nipype fork by typing `git clone git://github.com/LTS5/nipype.git`, and run the install script with `sudo python setup.py install`. You will have to remove already installed versions of nipype if they were installed through apt-get (installation location: `/usr/lib/pyshared`) as it will take precedence over versions installed through the setup.py script.
    	
.. _manual-install:

Manual installation (all distributions)
---------------------------------------

Manual installation is divided between the Python libraries needed by the Connectome Mapper and the CMTKlib and the libraries needed by the DTB binaries. Files for manual installation is the zipped archive of the Connectome Mapper.
* As we will use `easy_install` in order to have access to the latest libraries even on older systems the python-setuptools package is needed. Ipython is strongly recommended for debugging purposes. Debian/Ubuntu command: `sudo apt-get install python-setuptools ipython`
* Python libraries needed: traits, traitsui, pyface, nibabel, numpy, networkx, scipy. Easy_install command: `sudo easy_install traits traitsui pyface nibabel numpy networkx scipy nose`
* Install our forked version of Nipype (http://nipy.sourceforge.net/nipype/). For now, we require a modified vesion Nipype interfaces that is available on our Github repository (https://github.com/LTS5/nipype). To install it clone to your machine the nipype fork by typing `git clone git://github.com/LTS5/nipype.git`, and run the install script with `sudo python setup.py install`. You will have to remove already installed versions of nipype if they were installed through apt-get (installation location: `/usr/lib/pyshared`) as it will take precedence over versions installed through the setup.py script.
* Libraries needed by the DTB binaries: boost (module program-options), nifti, blitz. Debian/Ubuntu 


Now, you are ready to start the Connectome Mapper from the Bash Shell::

    connectomemapper


Sample dataset
==============

To get you started, we provide two Diffusion Spectrum Imaging sample datasets. They already contain the correct
folder structure described below. You can find the two `raw datasets online <http://cmtk.org/datasets/rawdata/>`_::

project01_dsi
    *connectome_0001* with timepoint *tp1* and DSI, T1 and T2 raw data

project02_dsi
    *connectome_0002* with timepoint *tp1* and DSI, T1 raw data

If you produce any connectome dataset that you want to share with the community, we provide a curated
`cffdata repository on GitHub <http://github.com/LTS5/cffdata>`_ .


Project configuration and setup
===============================

Steps to do before executing the pipeline

#. Create the folder structure for your project for DSI data. For DTI data, rename the folder DSI to DTI. For QBALL data, rename the folder DSI to QBALL. 
If you have resting state fMRI data, create a new folder 'fMRI' in RAWDATA.::

	├── myproject
	│   ├── control001
	│   │   └── tp1
	│   │       ├── RAWDATA
	│   │       │   ├── DSI
	│   │       │   ├── T1
	│   │       │   ├── T2
	│   │       │   └── fMRI

#. Copy the Diffusion / MPRAGE (DSI, DTI, QBALL, T1, T2, fMRI) images (DICOM series) in the corresponding folders.
   The T2 images are optional but they improve the registration of the data. The fMRI images are optional.

#. Run the Connectome Mapper and configure it for your project::

    connectomemapper

#. After the first run of the e.g. the first module DICOM Converter, the folder structure should look like this::

	├── myproject
	│   ├── control001
	│   │   └── tp1
	│   │       ├── CMP
	│   │       │   ├── cff
	│   │       │   ├── fibers
	│   │       │   ├── fMRI
	│   │       │   ├── fs_output
	│   │       │   ├── raw_diffusion
	│   │       │   └── scalars
	│   │       ├── FREESURFER
	│   │       │   └── mri
	│   │       ├── LOG
	│   │       ├── NIFTI
	│   │       │   ├── diffusion_metadata
	│   │       │   ├── transformations
	│   │       │   └── wm_correction
	│   │       ├── RAWDATA
	│   │       │   ├── DSI
	│   │       │   ├── T1
	│   │       │   ├── T2
	│   │       │   └── fMRI
	│   │       └── STATS

All the files for your subject will be stored in this folder structure.

In the GUI, now you should setup all the parameters for your your single subject and hit the *Map connectome!* button.
You select the stages you want to run. To produce a connectome, all the stages have to be run in sequential order.

If you have to restart the GUI later and do not want to enter everything again, you can open the LOG folder,
there are so-called pickle files with ending .pkl and you can load them with the *Load* button in the GUI to restore your configuration state.

Alternatively, you can also open a pickle file directly from the Bash shell when starting the Connectome Mapper::

    connectomemapper mypickle.pkl

If you run into any problems or have any questions, post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_.

Starting the pipeline without GUI
=================================
You can start the pipeline also from IPython or in a script. You can find an map_connectome.py example file
in the source code repository in /example/default_project/map_connectome.py.

You can start to modify this script to loop over subjects and/or load the "pickle" file automatically, add::

	from cmp.gui import CMPGUI
	cmpgui = CMPGUI()
	cmpgui.load_state('/path/to/your/pickle/state/LOG/cmp.pkl')

You can set the attributes of the cmpgui configuration object in the script and directly call the pipeline execution engine::

	cmpgui.active_dicomconverter = True
	cmpgui.project_name = '...'
	cmpgui.project_dir = '.../'
	cmpgui.subject_name = '...'
	cmpgui.subject_timepoint = '...'
	cmpgui.subject_workingdir = '.../'
	cmp.connectome.mapit(cmpgui)

For a full list of field names, refer to the `source code <http://github.com/LTS5/cmp/blob/master/cmp/configuration.py>`_.
