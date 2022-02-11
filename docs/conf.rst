*********************
Project configuration
*********************

Sample dataset
==============

To get you started, we provide one sample dataset structured following the `Brain Imaging Data Structure standard <https://bids-specification.readthedocs.io/en/stable/>`. The dataset structure is as follow::

		├── myproject  <------ Your selected folder (base directory)
		│   ├── sub-001
		│   │       ├── anat
		│   │       |    ├── sub-001_T1w.nii.gz
		│   │       |    ├── sub-001_T1w.json
		│   │       ├── dwi
		│   │       |    ├── sub-001_acq-DSI_dwi.nii.gz
		│   │       |    ├── sub-001_acq-DSI_dwi.json
		│   │       |    ├── sub-001_acq-DTI_dwi.nii.gz
		│   │       |    ├── sub-001_acq-DTI_dwi.json
		│   │       |    ├── sub-001_acq-multishell_dwi.nii.gz
		│   │       |    ├── sub-001_acq-multishell_dwi.json
		│   │       ├── func
		│   │       |    ├── sub-001_task-rest_bold.nii.gz
		│   │       |    ├── sub-001_task-rest_bold.json



You can find the `raw dataset online <http://cmtk.org/datasets/rawdata/>`_


..	test_dsi
..    	*sub-001* with timepoint *tp1* and DSI, T1 raw data

.. If you produce any connectome dataset that you want to share with the community, we provide a curated
.. `cffdata repository on GitHub <http://github.com/LTS5/cffdata>`_.


Run the Connectome Mapper Graphical User Interface
==================================================

Now, you are ready to start the Graphical User Interface of Connectome Mapper from a Bash Shell::

    $ conda activate py27cmp-gui
    (py27cmp-gui)$ cmpbidsappmanager


Project configuration (folder structure)
========================================

Running the Connectome Mapper opens the main window as well as a menu toolbar on the top of the screen. The only enabled button is in the toolbar: the "Load BIDS Dataset..." in the File menu. If necessary, Copy the diffusion (DSI, DTI, Multi-Shell) and morphological T1 images (.nii.gz + .json files as specified by BIDS) in the corresponding folders.

* Click the "Load BIDS Dataset..." button. and select the base directory of the bids dataset
  Selecting a folder will create the following folder structure::

		├── myproject  <------ Your selected folder (base directory)
		│   ├── sub-001
		│   │       ├── anat
		│   │       |    ├── sub-001_T1w.nii.gz
		│   │       |    ├── sub-001_T1w.json
		│   │       ├── dwi
		│   │       |    ├── sub-001_acq-DSI_dwi.nii.gz
		│   │       |    ├── sub-001_acq-DSI_dwi.json
		│   │       |    ├── sub-001_acq-DTI_dwi.nii.gz
		│   │       |    ├── sub-001_acq-DTI_dwi.json
		│   │       |    ├── sub-001_acq-multishell_dwi.nii.gz
		│   │       |    ├── sub-001_acq-multishell_dwi.json
		│   │       ├── func
		│   │       |    ├── sub-001_task-rest_bold.nii.gz
		│   │       |    ├── sub-001_task-rest_bold.json
		│   ├── derivatives
		│   │   ├── cmp-<version-tag>
		│   │   |    ├── sub-001
	  	|	│   │    |    ├── anat
	  	|	│   │    |    ├── dwi
	  	|	│   │    |    ├── func
	  	|	│   │    |    ├── connectivity
		│   │   ├── freesurfer-<version-tag>
		│   │   |    ├── sub-001
	  	|	│   │    |    ├── mri
 	 	|	│   │    |    ├── surf
	  	|	│   │    |    ├── ...
		│   │   ├── nipype-<version-tag>
		│   │   |    ├── anatomical_pipeline
		│   │   |    ├── diffusion_pipeline
		│   │   |    ├── functional_pipeline

  You can also create the folder structure manually before selecting the base directory (existing folders won't be overwritten).



* Now you can click on "Check input data" button in the main window.

  .. image:: images/mainWindow.png
    	:width: 600

  DICOM sequences will be converted to nifti format and nifti files copied into the NIFTI folder. A dialog box will appear to confirm the successful conversion. If several diffusion modalities are available, you'll be asked to choose which modality to process.

  .. image:: images/checkInputs.png

* Once the diffusion modality is set, configuration of the pipeline is enabled. You can :doc:`configure the processing stages <stages>` by clicking on the respective buttons on the left. Pipeline information as base directory and last processing information are displayed on the right. You can also set the number of cores for multithreading the pipeline processing.

  .. image:: images/mainWindow_inputsChecked.png
  	  :width: 600

* When the pipeline is configured, you can run the *Map connectome!* button. If you don't want to process the whole pipeline at once, you can select which stage to stop at using the "Custom mapping..." button.

* When the processing is finished, connectome tables will be saved in the RESULTS folder, in a subfolder named after the date and time the data was processed.

If you run into any problems or have any questions, post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_.

Staring the pipeline without GUI
================================

This can be useful if you want to automatically process different subjects or timepoints with the same configuration, or one subject with different configurations, etc...

Configure the pipeline as described previously, and instead of running it, save the configuration by clicking on the "Configuration" -> "Save configuration file..." button in the toolbar.

To run the analysis for a single subject, type::

	connectomemapper input_folder config_file

To batch over a set of subject, you can make a bash script like this one::

	#!/bin/bash
	subjects_folders=(path/to/subject1/folder path/to/subject2/folder path/to/subject3/folder)
	config_file = path/to/configfile.ini
	for subject in "${subjects_folders[@]}"; do
	   connectomemapper "${subject}" "${config_file}"
	done

Save the file as `batch.sh` and run it from the terminal::

	./batch.sh

..
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
