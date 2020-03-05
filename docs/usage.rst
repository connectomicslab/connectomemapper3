***********************
Commandline Usage
***********************

Introduction
=============================

The ``Connectome Mapper 3`` BIDS App takes as principal input the path of the dataset
that is to be processed.
The input dataset is required to be in valid :abbr:`BIDS (Brain Imaging Data
Structure)` format, and it must include at least one T1w or MPRAGE structural image.
We highly recommend that you validate your dataset with the free, online
`BIDS Validator <http://bids-standard.github.io/bids-validator/>`_.

Commandline Arguments
=============================

The command to run ``Connectome Mapper 3`` follow the `BIDS-Apps
<https://github.com/BIDS-Apps>`_ definition with additional options for loading pipeline configuration files.

.. argparse::
		:ref: cmp.parser.get
		:prog: connectomemapper3



Participant Level Analysis
===========================
To run the docker image in participant level mode (for one participant):

  .. parsed-literal::

    $ docker run -t --rm -u $(id -u):$(id -g) \\
            -v /home/localadmin/data/ds001:/bids_dir \\
            -v /media/localadmin/data/ds001/derivatives:/output_dir \\
            (-v /usr/local/freesurfer/license.txt:/bids_dir/code/license.txt \\)
            sebastientourbier/connectomemapper3:|release| \\
            /bids_dir /output_dir participant --participant_label 01 \\(--session_label 01 \\)
          	--anat_pipeline_config /bids_dir/code/ref_anatomical_config.ini \\)
            (--dwi_pipeline_config /bids_dir/code/ref_diffusion_config.ini \\)
            (--func_pipeline_config /bids_dir/code/ref_fMRI_config.ini \\)
            (--number_of_participants_processed_in_parallel 1)

.. note:: The local directory of the input BIDS dataset (here: ``/home/localadmin/data/ds001``) and the output directory (here: ``/media/localadmin/data/ds001/derivatives``) used to process have to be mapped to the folders ``/bids_dir`` and ``/output_dir`` respectively using the ``-v`` docker run option. 

.. important:: The user is requested to use its own Freesurfer license (`available here <https://surfer.nmr.mgh.harvard.edu/registration.html>`_). CMP expects by default to find a copy of the FreeSurfer ``license.txt`` in the ``code/`` folder of the BIDS directory. However, one can also mount with the ``-v`` docker run option a freesurfer ``license.txt``, which can be located anywhere on its computer (as in the example above, i.e. ``/usr/local/freesurfer/license.txt``) to the ``code/`` folder of the BIDS directory inside the docker container (i.e. ``/bids_dir/code/license.txt``). 

.. note:: At least a configuration file describing the processing stages of the anatomical pipeline should be provided. Diffusion and/or Functional MRI pipeline are performed only if a configuration file is set. The generation of such configuration files, the execution of the BIDS App docker image and output inpection are facilitated through the use of the Connectome Mapper GUI, i.e. cmpbidsappmanager (see `dedicated documentation page <bidsappmanager.html>`_)

Debugging
=========

Logs are outputted into
``<output dir>/cmp/sub-<participant_label>/sub-<participant_label>_log-cmpbidsapp.txt``.

Support and communication
=========================

The documentation of this project is found here: https://connectome-mapper-3.readthedocs.io/en/latest/.

All bugs, concerns and enhancement requests for this software can be submitted here:
https://gitlab.com/connectomicslab/connectomemapper3/issues.


If you run into any problems or have any questions, you can post to the `CMTK-users group <http://groups.google.com/group/cmtk-users>`_.


Not running on a local machine? - Data transfer
===============================================

If you intend to run ``connectomemapper3`` on a remote system, you will need to
make your data available within that system first. Comprehensive solutions such as `Datalad
<http://www.datalad.org/>`_ will handle data transfers with the appropriate
settings and commands. Datalad also performs version control over your data.
