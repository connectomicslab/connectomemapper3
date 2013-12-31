*********************
Project configuration
*********************

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


Project configuration (folder structure)
========================================

Running the Connectome Mapper opens the main window as well as a menu toolbar on the top of the screen. The only enabled buttons are in the toolbar: the "New Connectome Data..." and "Load Connectome Data..." in the File menu.

* If you have already configured a processing pipeline before, you can load the configuration by selecting the base directory using the "Load Connectome Data..." button.
  Otherwise, click "New Connectome Data..." and select the base directory for the project (i.e. the project that will contain all the processing steps and results for one subject). Selecting a folder will create the following folder structure::

		├── myproject
		│   ├── control001
		│   │   └── tp1 <- Selected folder (base directory)
		│   │       ├── LOG
		│   │       ├── NIFTI
		│   │       ├── NIPYPE
		│   │       ├── RAWDATA
		│   │       │   ├── DSI
		│   │       │   ├── DTI
		│   │       │   ├── HARDI
		│   │       │   ├── T1
		│   │       │   └── T2
		│   │       ├── RESULTS
		│   │       └── STATS
		
  You can also create the folder structure manually before selecting the base directory (existing folders won't be overwritten).

* Copy the diffusion (DSI, DTI, QBALL/HARDI) and morphological (T1, T2) images (DICOM series or single .nii.gz files) in the corresponding RAWDATA folders.
  The T2 images are optional but they improve the registration of the data. 

* Now you can click on "Check input data" button in the main window.

  .. image:: images/mainWindow.png
    	:width: 600

  DICOM sequences will be converted to nifti format and nifti files copied into the NIFTI folder. A dialog box will appear to confirm the successful conversion. If several diffusion modalities are available, you'll be asked to choose which modality to process.

  .. image:: images/checkInputs.png

* Now you can configure the different :doc:`stages <stages>` and hit the *Map connectome!* button. If you don't want to process the whole pipeline at once, you can select which stage to stop at using the "Custom mapping..." button.

* When the processing is finished, connectome tables will be saved in the RESULTS folder, in a folder named after the date and time the data was processed.

If you run into any problems or have any questions, post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_.

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
