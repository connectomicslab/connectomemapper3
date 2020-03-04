============================================================
Running the Connectome Mapper 3 BIDS App on a cluster (HPC)
============================================================

Before a BIDS App can be run on a cluster, it first needs to be saved to an Singularity-compatible image file (Please check the `Singularity documentation website <https://sylabs.io/docs/>`_ for more details). 

------------------------------------
Conversion to a Singularity image
------------------------------------

Let's say we want to store the converted Singularity image in ``~/Softwares/singularity/`` :

.. parsed-literal::

	$ singularity build ~/Softwares/singularity/cmp-|release|.simg docker://sebastientourbier/connectomemapper-bidsapp:|release|

This command will directly download the latest version release of the Docker image from the DockerHub and convert it to a Singularity image.

------------------------------------
Running the singularity image
------------------------------------

Here is an example of commandline usage which runs the CMP3 Singularity to perform both anatomical and diffusion pipelines for `sub-01`, `sub-02` and `sub-03` of a BIDS dataset whose root directory is located at ``${localDir}``:

.. parsed-literal::

	$ singularity run --bind ${localDir}:/bids_dir --bind ${localDir}/derivatives:/output_dir \\
	~//Softwares/singularity/cmp-v3.0.0-beta-20200227.simg \\
	/bids_dir /output_dir participant --participant_label 01 02 03 \\
	--anat_pipeline_config /bids_dir/code/ref_anatomical_config.ini \\
	--dwi_pipeline_config /bids_dir/code/ref_diffusion_config.ini \\
	--fs_license /bids_dir/code/license.txt \\
	--number_of_participants_processed_in_parallel 3


------------------------------------
Useful singularity commands
------------------------------------

* Clean cache::
	$ singularity cache clean

* Display a container's metadata::
	$ singularity inspect ~/Softwares/singularity/cmp-|release|.simg
