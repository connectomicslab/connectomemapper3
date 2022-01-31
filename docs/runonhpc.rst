.. _run-on-hpc:

============================================================
Running on a cluster (HPC)
============================================================

Connectome Mapper 3 BIDS App can be run on a cluster using Singularity.

For your convenience, the Singularity image is automatically built along
the docker image using Singularity ``3.8.4`` and deployed to
`Sylabs.io <https://sylabs.io/>`_  (equivalent of DockerHub for Singularity)
during continuous integration on CircleCI. It can be freely downloaded
with the following command:

.. parsed-literal::
    $ singularity pull library://connectomicslab/default/connectomemapper-bidsapp:latest

If you prefer, you can still build the Singularity image on your side using
one of the 2 methods described in :ref:`Conversion to a Singularity image <simg_conversion>`.

A list of useful singularity command can be found in :ref:`Useful singularity commands <singularity-cmds>`.
For more documentation about Singularity, please check the `official documentation website <https://sylabs.io/docs/>`_.

**Happy Large-Scale Connectome Mapping!**


--------------
Prerequisites
--------------

* Singularity must be installed.
  Check the `official documentation webpage <https://sylabs.io/guides/3.7/user-guide/quick_start.html#quick-installation-steps>`_
  for installation instructions.

.. note::If you wish to build the singularity image then you need to
    have Docker installed.
    See :ref:`Prerequisites of Connectome Mapper 3 <manual-install-docker>`
    for more installation instructions.


.. _run_singularity:

------------------------------------
Running the singularity image
------------------------------------

The following example shows how to call from the
terminal the Singularity image of the CMP3 BIDS App
to perform both anatomical and diffusion pipelines for
`sub-01`, `sub-02` and `sub-03` of a BIDS dataset whose
root directory is located at ``${localDir}``::

    $ singularity run --containall \
            --bind ${localDir}:/bids_dir --bind ${localDir}/derivatives:/output_dir \
	        library://connectomicslab/default/connectomemapper-bidsapp:|release| \
	        /bids_dir /output_dir participant --participant_label 01 02 03 \
	        --anat_pipeline_config /bids_dir/code/ref_anatomical_config.json \
	        --dwi_pipeline_config /bids_dir/code/ref_diffusion_config.json \
	        --fs_license /bids_dir/code/license.txt \
	        --number_of_participants_processed_in_parallel 3

.. note::
    As you can see, the `singularity run` command is slightly different from the `docker run`. The docker option flag ``-v`` is replaced by the singularity ``--bind`` to map local folders inside the container. Last but not least, while docker containers are executed in total isolation, singularity images MUST run with the option flag `--containall`. Otherwise your $HOME and $TMP directories or your local environment variables might be shared inside the container.


.. _simg_conversion:

------------------------------------
Conversion to a Singularity image
------------------------------------

It actually exists two options for Docker to Singularity container image conversion. Let's say we want to store Singularity-compatible image file in ``~/Softwares/singularity/``.


*********************************************************************
Option 1 (recommended): Using the Docker image docker2singularity
*********************************************************************

1. Build locally in a ``/tmp/test`` folder:

	.. parsed-literal::
		$ mkdir -p /tmp/test
		$ docker run -v /var/run/docker.sock:/var/run/docker.sock  \\
                     -v /tmp/test:/output --privileged -t --rm  \\
                     singularityware/docker2singularity  \\
                     --name cmp-|release|.simg  \\
                     sebastientourbier/connectomemapper-bidsapp:|release|


2. Move the converted image `cmp-|release|` to the ``~/Softwares/singularity`` folder on the cluster (via ssh using scp for instance)

	.. parsed-literal::
		$ scp -v /tmp/test/cmp-|release|.simg <user>@<cluster_url>:~/Softwares/singularity/cmp-|release|.simg


**Advantage(s):** Has never failed

**Disadvantage(s):** Have to make a-priori the conversion locally on a workstation where docker is installed and then upload the converted image to the cluster


*********************************************************************
Option 2 : Using singularity directly
*********************************************************************

.. parsed-literal::
	$ singularity build ~/Softwares/singularity/cmp-|release|.simg  \\
                docker://sebastientourbier/connectomemapper-bidsapp:|release|

This command will directly download the latest version release of the Docker image from the DockerHub and convert it to a Singularity image.

**Advantage(s):** Can be executed on the cluster directly

**Disadvantage(s):** Has shown to fail because of some docker / singularity version incompatibilities


.. _singularity-cmds:

------------------------------------
Useful singularity commands
------------------------------------

	* Display a container's metadata:

		.. parsed-literal::
			$ singularity inspect ~/Softwares/singularity/cmp-|release|.simg

	* Clean cache:

		.. parsed-literal::
			$ singularity cache clean

------------

:Authors: Sebastien Tourbier
:Version: Revision: 2 (Last modification: 2021 Jan 04)
