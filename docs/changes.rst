
Changes
========

****************************
Version 3.0.0-beta-20200227
****************************

Date: February 27, 2020

This version addresses multiple issues to make successful conversion and run of the CMP3 BIDS App on HPC (Clusters) using Singularity.

* Revised the build of the master and BIDS App images:

	* Install locales and set `$LC_ALL` and `$LANG` to make freesurfer hippocampal subfields and brainstem segmentation (matlab-based) modules working when run in the converted SIngularity image
  	
  	* BIDS input and output directories inside the BIDS App container are no longer the `/tmp` and `/tmp/derivatives` folders but `/bids_dir` and `/output_dir`.
  	.. warning:: this might affect the use of Datalad container (To be confirmed.)
  	
  	* Fix the branch of mrtrix3 to check out

  	* Updated metadata

* Fix the configuration of CircleCI to not use Docker layer cache feature anymore as this feature is not included anymore in the free plan for open source projects.

* Improved documentation where the latest version should be dynamically generated everywhere it should appear.



****************************
Version 3.0.0-beta-20200206
****************************

Date: February 06, 2020

* Implementation of an in-house Nipype interface to AFNI 3DBandPass which can handle to check output as ..++orig.BRIK or as ..tlrc.BRIK (The later can occur with HCP preprocessed fmri data)


****************************
Version 3.0.0-beta-20200124
****************************

Date: January 24, 2020

* Updated multi-scale parcellation with a new symmetric version:

	1. The right hemisphere labels were projected in the left hemisphere to create a symmetric version of the multiscale cortical parcellation proposed by Cammoun2012_.
	2. For scale 1, the boundaries of the projected regions over the left hemisphere were matched to the boundaries of the original parcellation for the left hemisphere.
	3. This transformation was applied for the rest of the scales.

	.. _Cammoun2012: https://doi.org/10.1016/j.jneumeth.2011.09.031

* Updated documentation with list of changes