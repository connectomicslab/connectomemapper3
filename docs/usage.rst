*********************
BIDS App: User's Guide
*********************

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
======================
To run the docker image in participant level mode (for one participant) ::

    docker run -it --rm \
            -v /home/localadmin/data/ds001:/tmp \
            -v /media/localadmin/data/ds001/derivatives:/tmp/derivatives \
            -v /usr/local/freesurfer/license.txt:/tmp/code/license.txt \
            sebastientourbier/connectomemapper3:latest \
            /tmp /tmp/derivatives participant --participant_label 01 \
          	--anat_pipeline_config /tmp/code/ref_anatomical_config.ini \
            (--dwi_pipeline_config /tmp/code/ref_diffusion_config.ini \)
            (--func_pipeline_config /tmp/code/ref_fMRI_config.ini \)


.. note:: The local directory of the input BIDS dataset (here: ``/home/localadmin/data/ds001``) and the output directory (here: ``/media/localadmin/data/ds001/derivatives``) used to process have to be mapped to the folders ``/tmp`` and ``/tmp/derivatives`` respectively using the ``-v`` docker run option.

.. note:: At least a configuration file describing the processing stages of the anatomical pipeline should be provided. Diffusion and/or Functional MRI pipeline are performed only if a configuration file is set.

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

Eager to contribute?
===============================================

See contributing_ for more details.
