*******************
Stage configuration
*******************

Each stage has a configuration and a "View outputs" panel. The configuration panel allows to set the stage parameters. The "View outputs" panel displays a set of outputs that can be visually checked once the stage processing has finished. The outputs depend on the chosen parameters.
	
Preprocessing
-------------

Preprocessing includes motion and eddy current correction for diffusion data.

.. image:: images/preprocessing.png
	:align: center

*Motion correction*

	Aligns diffusion volumes to the b0 volume using FSL's MCFLIRT.

*Eddy current correction*

	Corrects for eddy current distortions using FSL's Eddy correct tool.
	
*View outputs*

	* Motion corrected image
	* Eddy current corrected image
	* Motion and eddy current corrected image
	
Segmentation
------------

Used you want to compute the Lausanne2008 or Freesurfer parcellations. The segmentation stage runs the Freesurfer processing.  

.. image:: images/segmentation.png
	:align: center

*Freesurfer args*

	Command for Freesurfer processing
	
*Use existing freesurfer data*

	Check this box if you have already Freesurfer output data available. Then select the subject directory and subject id.
	
*View outputs*

	* Brain mask overlaid on T1
	* Segmentation labels overlaid on T1
	* Segmentation and surfaces overlaid on T1
	
Parcellation
------------

Generates the Native Freesurfer or Lausanne2008 parcellation from Freesurfer data.

.. image:: images/segmentation.png
	:align: center
	
*Parcellation scheme*

	Select the desired parcellation scheme: Native Freesurfer or Lausanne2008.
	
*View outputs*

	Parcellation(s) overlaid with T1
	
Registration
------------

.. image:: images/registration.png
	:align: center

*Registration mode*

	* Linear (FSL): perform linear registration from T1 to diffusion b0 using FSL's flirt.
	* BBregister (FS): perform linear registration using Freesurfer BBregister tool.
	* Non-linear (FSL): perform non-linear registration from T1 to b0 (only available if T2 scans are found).
	
*View outputs*

	* Overlay of T1 volume registered to b0 space and the b0 volume.
	
Diffusion and tractography
--------------------------

Performs deterministic, probabilistic or global tractography based on several tools.

.. image:: images/diffusion.png
	:align: center
	
*Resampling*

	Resample diffusion data to F0 x F1 x F2 mm^3

*Processing tool*

	* DTK: performs tensor reconstruction and deterministic fiber tracking.
	* MRtrix: performs tensor and CSD reconstruction as well as deterministic and probabilistic fiber tracking.
	* Camino: performs multi model reconstruction and also deterministic and probabilistic fiber tracking.
	* FSL: performs probabilistic tracking
	* Gibbs: performs global tractography based on FSL tensor or MRtrix CSD reconstruction
	
*View outputs*

	Fiber tracks (when deterministic of global tractography is performed)
	
Connectome
----------

.. image:: images/connectome.png
	:align: center

*Output types*

	Select in which formats the connectivity matrices should be saved.
	
*View outputs*

	Connectivity matrices

******
Nipype 
******

The Connectome Mapper processing relies on nipype. For each stage, a processing folder is created in $Base_directory/NIPYPE/diffusion_pipeline/<stage_name>.

All intermediate steps for the processing are saved in the corresponding stage folders.
	
