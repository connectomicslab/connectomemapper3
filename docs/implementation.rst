*******************************
Implementation
*******************************

The structural and functional processing pipelines of the Connectome Mapper are written in Python and uses Nipype (Gorgolewski 2011) to interface with `FSL <https://fsl.fmrib.ox.ac.uk/fsl/fslwiki>`_, `FreeSurfer <https://surfer.nmr.mgh.harvard.edu/>`_, `ANTs <http://stnava.github.io/ANTs/>`_, `MRtrix3 <http://www.mrtrix.org/>`_, `Dipy <https://nipy.org/dipy/>`_ and `AFNI <https://afni.nimh.nih.gov/>`_ and the included Connectome Mapping Toolkit library. The pipelines take BIDS formatted datasets as inputs, using the `PyBIDS library <https://github.com/bids-standard/pybids>`_.

The pipelines are encapsulated in a BIDS App (Gorgolewski 2017), a framework (which promotes portability and reproducibility. The container image of the BIDS App is built using Docker container technology (Merkel 2014). Releases are available at `sebastientourbier/connectomemapper-bidsapp on the Docker Hub <https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp>`_, but can be easily converted into a Singularity image (Kurtzer 2017) for large scale processing on clusters.


BIDS formatted datasets
------------------------

The Connectome Mapper 3 BIDS App pipelines takes as principal input the path of the dataset that is to be processed. The input dataset is required to be in valid `Brain Imaging Data Structure format <https://bids-specification.readthedocs.io/en/stable/>`, and it must include at least one T1w or MPRAGE structural image. We highly recommend that you validate your dataset with the free, online `BIDS Validator <https://bids-standard.github.io/bids-validator/>`.


To get you started, we provide one sample BIDS formatted dataset. The dataset structure is as follow::

        ├── cmpsample
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


Architecture
-------------

TBC

Pipelines
----------

Anatomical
+++++++++++

Taking as input BIDS datasets (Gorgolewski 2016) that include an anatomical scan (T1w or MPRAGE), the Connectome Mapper interfaces with FreeSurfer 6.0.1 to perform resampling to isotropic resolution, Desikan-Killiany brain parcellation (Desikan, 2004), brainstem parcellation (Van Leemput 2015), and hippocampal subfields segmentation (Iglesias 2015). Then, using the new version of CMTK, it performs cortical brain parcellation at 5 different scales (Cammoun 2012), probabilistic atlas-based segmentation of the thalamic nuclei (Najdenovska 2018), and combination of all segmented structures, to create the final parcellation at each scale.

Example results
^^^^^^^^^^^^^^^^

* *Segmentation*

.. figure:: images/ex_segmentation1.png
    :width: 600

    Surfaces extracted using Freesurfer


.. figure:: images/ex_segmentation2.png
    :width: 600

    Freesurfer brain segmentation


* *Parcellation*

.. figure:: images/ex_parcellation2.png
    :width: 600

    Cortical and subcortical brain parcellation


Diffusion
++++++++++

TBC

Example results
^^^^^^^^^^^^^^^^

* *Registration*

    Registration of T1 to Diffusion space (b0).

    .. figure:: images/ex_registration.png
        :width: 600

    T1 in copper overlayed to the b0 image.

* *Tractography*

    DSI Tractography results displayed with TrackVis.

    .. image:: images/ex_tractography1.png
        :width: 600

    .. image:: images/ex_tractography2.png
        :width: 600

* *Connection matrices*

    Connection matrices displayed using a:
    1. matrix layout with pyplot

    .. image:: images/ex_connectionmatrix.png
        :width: 600

    2. circular layout with pyplot and MNE

    .. image:: images/ex_connectioncircular.png
        :width: 600

Functional
+++++++++++

TBC

Example results
^^^^^^^^^^^^^^^^

* *Average time-courses per cortical and subcortical parcel*

    .. figure:: images/ex_rsfMRI.png
        :width: 600

        Average time-courses are displayed with Matplotlib.

Outputs
------------

Filenames and folder structure
+++++++++++++++++++++++++++++++++

Outputs (Processed / derivatives data and folder structure) of the Connectome Mapper 3 relies on the following BIDS derivatives extensions:

* the :abbr:`BIDS (brain imaging data structure)` Common Derivatives specification (see `BEP003 <https://docs.google.com/document/d/1Wwc4A6Mow4ZPPszDIWfCUCRNstn7d_zzaWPcfcHmgI4>`_)
* the resting-state fMRI derivatives (see `BEP013 <https://docs.google.com/document/d/1qBNQimDx6CuvHjbDvuFyBIrf2WRFUOJ-u50canWjjaw>`_)
* the affine transforms and the non-linear field warps (see `BEP014 <https://docs.google.com/document/d/11gCzXOPUbYyuQx8fErtMO9tnOKC3kTWiL9axWkkILNE>`_)
* the diffusion weighted imaging derivatives (see `BEP016 <https://docs.google.com/document/d/1cQYBvToU7tUEtWMLMwXUCB_T8gebCotE1OczUpMYW60>`_)
* the structural preprocessing derivatives (see `BEP011 <https://docs.google.com/document/d/1YG2g4UkEio4t_STIBOqYOwneLEs1emHIXbGKynx7V0Y>`_)
* the functional preprocessing derivatives (see `BEP012 <https://docs.google.com/document/d/16CvBwVMAs0IMhdoKmlmcm3W8254dQmNARo-7HhE-lJU>`_)

.. note:: Output filenames and folder structure will be updated as soon as the specifications evolve.

Taking the sample dataset as example, running the Connectome Mapper will result in the following folder structure::

        ├── cmpsample
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
        |   │   │    |    ├── anat
        |   │   │    |    ├── dwi
        |   │   │    |    ├── func
        |   │   │    |    ├── connectivity
        │   │   ├── freesurfer-<version-tag>
        │   │   |    ├── sub-001
        |   │   │    |    ├── mri
        |   │   │    |    ├── surf
        |   │   │    |    ├── ...
        │   │   ├── nipype-<version-tag>
        │   │   |    ├── anatomical_pipeline
        │   │   |    ├── diffusion_pipeline
        │   │   |    ├── functional_pipeline


Main Connectome Mapper Derivatives
+++++++++++++++++++++++++++++++++++++++

Processed, or derivative, data are written to ``<bids_dataset/derivatives>/cmp/sub-<subject_label>/``. In this folder, a configuration file generated and used for processing each participant is saved as ``sub-<subject_label>_anatomical_config.ini``. It summarizes pipeline workflow options and parameters used for processing.

Anatomical derivatives in the original ``T1w`` space are placed in each subject's ``anat`` subfolder including:

- ``anat/sub-<subject_label>_desc-head_T1w.nii.gz``
- ``anat/sub-<subject_label>_desc-brain_T1w.nii.gz``
- ``anat/sub-<subject_label>_desc-brain_mask.nii.gz``

- ``anat/sub-<subject_label>_label-WM_dseg.nii.gz``
- ``anat/sub-<subject_label>_label-GM_dseg.nii.gz``
- ``anat/sub-<subject_label>_label-CSF_dseg.nii.gz``

The five different brain parcellation are saved as:

- ``anat/sub-<subject_label>_label-L2018_desc-<scale_label>_atlas.nii.gz``

where ``<scale_label>`` : ``scale1``, ``scale2``, ``scale3``, ``scale4``, ``scale5`` corresponds to the parcellation scale.

Additionally, the description of parcel labels and the updated FreeSurfer color lookup table are saved as:

- ``anat/sub-<subject_label>_label-L2018_desc-<scale_label>_atlas.graphml``
- ``anat/sub-<subject_label>_label-L2018_desc-<scale_label>_atlas_FreeSurferColorLUT.txt``


Nipype Derivatives
+++++++++++++++++++

A Nipype subjects directory is created in ``<bids_dataset/derivatives>/nipype``, dedicated to all outputs generated by Nipype nodes relatively to their processing stage and pipeline type.

::

    nipype/
        sub-<subject_label>/
            anatomical_pipeline/
                segmentation_stage/
                    reconall/
                        _report/
                        command.txt
                        _inputs.pklz
                        _nodes.pklz
                        result_recon.pklz
                        <hash>.json
                    mgz_convert/
                    ...
                parcellation_stage/
                ...
            diffusion_pipeline/
            ...

FreeSurfer Derivatives
++++++++++++++++++++++++

A FreeSurfer subjects directory is created in ``<bids_dataset/derivatives>/freesurfer-7.2.0``.

::

    freesurfer-7.2.0/
        fsaverage/
            mri/
            surf/
            ...
        sub-<subject_label>/
            mri/
            surf/
            ...
        ...

The ``fsaverage`` subject distributed with the running version of
FreeSurfer is copied into this directory.

Eager to contribute?
---------------------

See `Contributing to Connectome Mapper <contributing>`_ for more details.
