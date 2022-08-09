.. _cmdusage:

***********************
Commandline Usage
***********************

``Connectome Mapper 3 (CMP3)`` is distributed as a BIDS App which adopts the :abbr:`BIDS (Brain Imaging Data Structure)` standard for data organization and takes as principal input the path of the dataset that is to be processed. The input dataset is required to be in valid `BIDS` format, and it must include at least a T1w or MPRAGE structural image and a DWI and/or resting-state fMRI image and/or preprocessed EEG data. See :ref:`cmpbids` page that provides links for more information about BIDS and BIDS-Apps as well as an example for dataset organization and naming.

.. warning::
    As of ``CMP3 v3.0.0-RC2``, the BIDS App includes a **tracking** system that anonymously reports the run of the BIDS App. This feature has been introduced to support us in the task of fund finding for the development of CMP3 in the future. However, users are still free to opt-out using the ``--notrack`` commandline argument.

.. important:: Since ``v3.0.0-RC4``, configuration files adopt the `JSON` format. If you have your configuration files still in the *old* `INI` format,
    do not worry, the CMP3 BIDS App will convert them to the new `JSON` format automatically for you.

Commandline Arguments
=============================

The command to run ``CMP3`` follows the `BIDS-Apps <https://github.com/BIDS-Apps>`_ definition standard with additional options for loading pipeline configuration files.

.. argparse::
		:ref: cmp.parser.get
		:prog: connectomemapper3

.. important::
    Before using any BIDS App, we highly recommend you to validate your BIDS structured dataset with the free, online `BIDS Validator <http://bids-standard.github.io/bids-validator/>`_.

Participant Level Analysis
===========================

You can run ``CMP3`` using the lightweight Docker or Singularity wrappers we created for convenience or you can interact directly with the Docker / Singularity Engine via the docker or singularity run command.

.. role:: raw-html(raw)
    :format: html

.. admonition:: New in v3.0.2 ✨

    You can now be aware about the adverse impact of your processing on the environment :raw-html:`&#x1F30D;`:raw-html:`&#x1f333;`!

    With the new `--track_carbon_footprint` option of the `connectomemapper3_docker` and `connectomemapper3_singularity` BIDS App python wrappers, you can use `codecarbon <https://codecarbon.io>`_ to estimate the amount of carbon dioxide (CO2) produced to execute the code by the computing resources and save the results in ``<bids_dir>/code/emissions.csv``.

    Then, to visualize, interpret and track the evolution of the CO2 emissions incurred, you can use the visualization tool of `codecarbon` aka `carbonboard` that takes as input the `.csv` created::

        $ carbonboard --filepath="<bids_dir>/code/emissions.csv" --port=xxxx

.. _wrapperusage:

With the wrappers
-------------------

When you run ``connectomemapper3_docker``, it will generate a Docker command line for you, print it out for reporting purposes, and then execute it without further action needed, e.g.:

    .. code-block:: console

       $ connectomemapper_docker \
            "/home/user/data/ds001" "/home/user/data/ds001/derivatives" \
            participant --participant_label 01 --session_label 01 \
            --fs_license "/usr/local/freesurfer/license.txt" \
            --config_dir "/home/user/data/ds001/code" \
            --track_carbon_footprint \
            --anat_pipeline_config "ref_anatomical_config.json" \
            (--dwi_pipeline_config "ref_diffusion_config.json" \)
            (--func_pipeline_config "ref_fMRI_config.json" \)
            (--eeg_pipeline_config "ref_EEG_config.json" \)
            (--number_of_participants_processed_in_parallel 1)
            
When you run ``connectomemapper3_singularity``, it will generate a Singularity command line for you, print it out for reporting purposes, and then execute it without further action needed, e.g.:

    .. code-block:: console

       $ connectomemapper3_singularity \
            "/home/user/data/ds001" "/home/user/data/ds001/derivatives" \
            participant --participant_label 01 --session_label 01 \
            --fs_license "/usr/local/freesurfer/license.txt" \
            --config_dir "/home/user/data/ds001/code" \
            --track_carbon_footprint \
            --anat_pipeline_config "ref_anatomical_config.json" \
            (--dwi_pipeline_config "ref_diffusion_config.json" \)
            (--func_pipeline_config "ref_fMRI_config.json" \)
            (--eeg_pipeline_config "ref_EEG_config.json" \)
            (--number_of_participants_processed_in_parallel 1)

.. _containerusage:

With the Docker / Singularity Engine
--------------------------------------

If you need a finer control over the container execution, or you feel comfortable with the Docker or Singularity Engine, avoiding the extra software layer of the wrapper might be a good decision.

Docker 
------

For instance, the previous call to the ``connectomemapper3_docker`` wrapper corresponds to:

  .. parsed-literal::

    $ docker run -t --rm -u $(id -u):$(id -g) \\
            -v /home/user/data/ds001:/bids_dir \\
            -v /home/user/data/ds001/derivatives:/output_dir \\
            (-v /usr/local/freesurfer/license.txt:/bids_dir/code/license.txt) \\
            sebastientourbier/connectomemapper-bidsapp:|release| \\
            /bids_dir /output_dir participant --participant_label 01 (--session_label 01) \\
            --anat_pipeline_config /bids_dir/code/ref_anatomical_config.json \\
            (--dwi_pipeline_config /bids_dir/code/ref_diffusion_config.json \\)
            (--func_pipeline_config /bids_dir/code/ref_fMRI_config.json \\)
            (--eeg_pipeline_config /bids_dir/code/ref_EEG_config.json \\)
            (--number_of_participants_processed_in_parallel 1)
            
Singularity
-----------

For instance, the previous call to the ``connectomemapper3_singularity`` wrapper corresponds to:

  .. parsed-literal::

    $ singularity run  --containall \\
            --bind /home/user/data/ds001:/bids_dir \\
            --bind /home/user/data/ds001/derivatives:/output_dir \\
            --bind /usr/local/freesurfer/license.txt:/bids_dir/code/license.txt \\
            library://connectomicslab/default/connectomemapper-bidsapp:|release| \\
            /bids_dir /output_dir participant --participant_label 01 (--session_label 01) \\
            --anat_pipeline_config /bids_dir/code/ref_anatomical_config.json \\
            (--dwi_pipeline_config /bids_dir/code/ref_diffusion_config.json \\)
            (--func_pipeline_config /bids_dir/code/ref_fMRI_config.json \\)
            (--eeg_pipeline_config /bids_dir/code/ref_EEG_config.json \\)
            (--number_of_participants_processed_in_parallel 1)

.. note:: The local directory of the input BIDS dataset (here: ``/home/user/data/ds001``) and the output directory (here: ``/home/user/data/ds001/derivatives``) used to process have to be mapped to the folders ``/bids_dir`` and ``/output_dir`` respectively using the docker ``-v`` / singularity ``--bind`` run option.

.. important:: The user is requested to use its own Freesurfer license (`available here <https://surfer.nmr.mgh.harvard.edu/registration.html>`_). CMP expects by default to find a copy of the FreeSurfer ``license.txt`` in the ``code/`` folder of the BIDS directory. However, one can also mount a freesurfer ``license.txt``  with the docker ``-v`` / singularity ``--bind`` run option. This file can be located anywhere on the computer (as in the example above, i.e. ``/usr/local/freesurfer/license.txt``) to the ``code/`` folder of the BIDS directory inside the docker container (i.e. ``/bids_dir/code/license.txt``).

.. note:: At least a configuration file describing the processing stages of the anatomical pipeline should be provided. Diffusion and/or Functional MRI pipeline are performed only if a configuration file is set. The generation of such configuration files, the execution of the BIDS App docker image and output inpection are facilitated through the use of the Connectome Mapper GUI, i.e. cmpbidsappmanager (see `dedicated documentation page <bidsappmanager.html>`_)


Debugging
=========

Logs are saved into
``<output dir>/cmp/sub-<participant_label>/sub-<participant_label>_log.txt``.

Already have Freesurfer outputs?
================================

If you have already Freesurfer v5 / v6 output data available, CMP3 can use them if there are properly placed in your output / derivatives directory.
Since ``v3.0.3``, CMP3 expects to find a ``freesurfer-7.1.1``, so make sure that your derivatives are organized as
follows::

    your_bids_dataset
      |______ derivatives/
      |         |______ freesurfer-7.1.1/
      |                   |______ sub-01[_ses-01]/
      |                   |           |______ label/
      |                   |           |______ mri/
      |                   |           |______ surf/
      |                   |           |______ ...
      |                   |______ ...
      |______ sub-01/
      |______ ...

Support, bugs and new feature requests
=======================================

If you need any support or have any questions, you can post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_.

All bugs, concerns and enhancement requests for this software are managed on GitHub and can be submitted at `https://github.com/connectomicslab/connectomemapper3/issues <https://github.com/connectomicslab/connectomemapper3/issues>`_.

Not running on a local machine?
================================

If you intend to run ``CMP3`` on a remote system such as a high-performance computing cluster where Docker is not available due to root privileges, a Singularity image is also built for your convenience and available on `Sylabs.io <https://sylabs.io/>`_. Please see instructions at :ref:`Running on a cluster (HPC) <run-on-hpc>`.

Also, you will need to make your data available within that system first. Comprehensive solutions such as `Datalad <http://www.datalad.org/>`_ will handle data transfers with the appropriate settings and commands. Datalad also performs version control over your data. A tutorial is provided in :ref:`Adopting Datalad for collaboration <datalad-cmp>`.
