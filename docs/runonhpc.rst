============================================================
Running on a cluster (HPC)
============================================================

Before the Connectome Mapper 3 BIDS App can be run on a cluster, it first needs to be saved to an Singularity-compatible image file (Please check the `Singularity documentation website <https://sylabs.io/docs/>`_ for more details).


------------------------------------
Conversion to a Singularity image
------------------------------------

It actually exists two options for Docker to Singularity container image conversion. Let's say we want to store Singularity-compatible image file in ``~/Softwares/singularity/``.


*********************************************************************
Option 1 (recommended): Using the Docker image docker2singularity
*********************************************************************

1. Build locally in a `/tmp/test` folder:

	.. parsed-literal::
		$ mkdir -p /tmp/test
		$ docker run -v /var/run/docker.sock:/var/run/docker.sock -v /tmp/test:/output --privileged -t --rm singularityware/docker2singularity --name cmp-|release|.simg sebastientourbier/connectomemapper-bidsapp:|release|


2. Move the converted image `cmp-|release|` to the `~/Softwares/singularity` folder on the cluster (via ssh using scp for instance)

	.. parsed-literal::
		$ scp -v /tmp/test/cmp-|release|.simg <your_cluster_user_login>@<cluster_url>:~/Softwares/singularity/cmp-|release|.simg


**Advantage(s):** Has never failed

**Disadvantage(s):** Have to make a-priori the conversion locally on a workstation where docker is installed and then upload the converted image to the cluster


*********************************************************************
Option 2 : Using singularity directly
*********************************************************************

.. parsed-literal::
	$ singularity build ~/Softwares/singularity/cmp-|release|.simg docker://sebastientourbier/connectomemapper-bidsapp:|release|

This command will directly download the latest version release of the Docker image from the DockerHub and convert it to a Singularity image.

**Advantage(s):** Can be executed on the cluster directly

**Disadvantage(s):** Has shown to fail because of some docker/ singularity version uncompatibilities



------------------------------------
Running the singularity image
------------------------------------

The following example shows how to call from the terminal the Singularity image of the CMP3 BIDS App to perform both anatomical and diffusion pipelines for `sub-01`, `sub-02` and `sub-03` of a BIDS dataset whose root directory is located at ``${localDir}``:

.. parsed-literal::
	$ singularity run --bind ${localDir}:/bids_dir --bind ${localDir}/derivatives:/output_dir \\
	~/Softwares/singularity/cmp-|release|.simg \\
	/bids_dir /output_dir participant --participant_label 01 02 03 \\
	--anat_pipeline_config /bids_dir/code/ref_anatomical_config.ini \\
	--dwi_pipeline_config /bids_dir/code/ref_diffusion_config.ini \\
	--fs_license /bids_dir/code/license.txt \\
	--number_of_participants_processed_in_parallel 3


------------------------------------
Useful singularity commands
------------------------------------

	* Display a container's metadata:

		.. parsed-literal::
			$ singularity inspect ~/Softwares/singularity/cmp-|release|.simg

	* Clean cache:

		.. parsed-literal::
			$ singularity cache clean


Created by Sebastien Tourbier - 2020 Mar 04 - Latest update: 2020 Jun 03

