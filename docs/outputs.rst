*****************************************
Outputs of Connectome Mapper 3
*****************************************

.. note:: Connectome Mapper 3 outputs are currently being updated to conform to the :abbr:`BIDS (brain imaging data structure)` Common Derivatives specification (see `BIDS Common Derivatives Extension <https://docs.google.com/document/d/1Wwc4A6Mow4ZPPszDIWfCUCRNstn7d_zzaWPcfcHmgI4/edit>`_).

Connectome Mapper Derivatives
==========================================

Processed, or derivative, data are written to ``<bids_dataset/derivatives>/cmp/sub-<subject_label>/``. In this folder, a configuration file generated and used for processing each participant is saved as ``sub-<subject_label>_anatomical_config.ini``. It summarizes pipeline workflow options and parameters used for processing.

Anatomical derivatives
------------------------
* Anatomical derivatives in the original ``T1w`` space are placed in each subject's ``anat`` subfolder including:

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

* Anatomical derivatives in the``DWI`` space produced by the diffusion pipeline are placed in each subject's ``anat`` subfolder including:

    - ``anat/sub-<subject_label>_space-DWI_desc-head_T1w.nii.gz``
    - ``anat/sub-<subject_label>_space-DWI_desc-brain_T1w.nii.gz``
    - ``anat/sub-<subject_label>_space-DWI_desc-brain_mask.nii.gz``

    - ``anat/sub-<subject_label>_space-DWI_label-WM_dseg.nii.gz``

    The five different brain parcellation are saved as:

    - ``anat/sub-<subject_label>_space-DWI_label-L2018_desc-<scale_label>_atlas.nii.gz``

    where ``<scale_label>`` : ``scale1``, ``scale2``, ``scale3``, ``scale4``, ``scale5`` corresponds to the parcellation scale.

    The 5TT image used for Anatomically Constrained Tractorgaphy (ACT) is saved as:

    - ``anat/sub-<subject_label>_space-DWI_label-5TT_probseg.nii.gz``

    The patial volume maps for white matter (WM), gray matter (GM), and Cortical Spinal Fluid (CSF)used for Particale Filtering Tractography (PFT), generated from 5TT image,are saved as:

    - ``anat/sub-<subject_label>_space-DWI_label-WM_probseg.nii.gz``
    - ``anat/sub-<subject_label_space-DWI>_label-GM_probseg.nii.gz``
    - ``anat/sub-<subject_label>_space-DWI_label-CSF_probseg.nii.gz``

    The GM/WM interface used for ACT and PFT seeding is saved as:

     - ``anat/sub-<subject_label>_space-DWI_label-GMWMI_probseg.nii.gz``


Diffusion derivatives
------------------------
Anatomical derivatives in the original ``T1w`` space are placed in each subject's ``anat`` subfolder including:

- ``anat/sub-<subject_label>_desc-head_T1w.nii.gz``
- ``anat/sub-<subject_label>_desc-brain_T1w.nii.gz``
- ``anat/sub-<subject_label>_desc-brain_mask.nii.gz``

- ``anat/sub-<subject_label>_label-WM_dseg.nii.gz``
- ``anat/sub-<subject_label>_label-GM_dseg.nii.gz``
- ``anat/sub-<subject_label>_label-CSF_dseg.nii.gz``

Resting-state fMRI derivatives
-------------------------------
Resting-state fMRI derivatives in the original ``T1w`` space are placed in each subject's ``anat`` subfolder including:

- ``anat/sub-<subject_label>_desc-head_T1w.nii.gz``
- ``anat/sub-<subject_label>_desc-brain_T1w.nii.gz``
- ``anat/sub-<subject_label>_desc-brain_mask.nii.gz``

- ``anat/sub-<subject_label>_label-WM_dseg.nii.gz``
- ``anat/sub-<subject_label>_label-GM_dseg.nii.gz``
- ``anat/sub-<subject_label>_label-CSF_dseg.nii.gz``


FreeSurfer Derivatives
=======================

A FreeSurfer subjects directory is created in ``<bids_dataset/derivatives>/freesurfer``.

::

    freesurfer/
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
