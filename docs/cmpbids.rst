
.. _cmpbids:

*******************************************
Connectome Mapper 3 and the BIDS standard
*******************************************

``Connectome Mapper 3 (CMP3)`` adopts the :abbr:`BIDS (Brain Imaging Data Structure)` standard for data organization and is developed following the BIDS App standard with a Graphical User Interface (GUI).

This means CMP3 can be executed in two different ways:
    1. By running the BIDS App container image directly from the terminal or a script (See :ref:`cmdusage` section for more details).
    2. By using its Graphical User Interface, designed to facilitate the configuration of all pipeline stages, the configuration of the BIDS App run and its execution, and the inspection of the different stage outputs with appropriate viewers (See :ref:`guiusage` section for more details) .

For more information about BIDS and BIDS-Apps, please consult the `BIDS Website <https://bids.neuroimaging.io/>`_, the `Online BIDS Specifications <https://bids-specification.readthedocs.io/en/stable/>`_, and the `BIDSApps Website <https://bids-apps.neuroimaging.io/>`_. `HeuDiConv <https://github.com/nipy/heudiconv>`_ can assist you in converting DICOM brain imaging data to BIDS. A nice tutorial can be found @ `BIDS Tutorial Series: HeuDiConv Walkthrough <http://reproducibility.stanford.edu/bids-tutorial-series-part-2a/>`_ .

.. _bidsexample:

Example BIDS dataset
=======================

For instance, a BIDS dataset with T1w, DWI and rs-fMRI images should adopt the following organization, naming, and file formats:::

    ds-example/

        README
        CHANGES
        participants.tsv
        dataset_description.json

        sub-01/
            anat/
                sub-01_T1w.nii.gz
                sub-01_T1w.json
            dwi/
                sub-01_dwi.nii.gz
                sub-01_dwi.json
                sub-01_dwi.bvec
                sub-01_dwi.bval
            func/
                sub-01_task-rest_bold.nii.gz
                sub-01_task-rest_bold.json

        ...

        sub-<subject_label>/
            anat/
                sub-<subject_label>_T1w.nii.gz
                sub-<subject_label>_T1w.json
            ...
        ...

For an example of a dataset containing T1w, DWI and preprocessed EEG data, please check the public `VEPCON dataset <https://openneuro.org/datasets/ds003505/versions/1.1.1>`_.

.. important::
    Before using any BIDS App, we highly recommend you to validate your BIDS structured dataset with the free, online `BIDS Validator <http://bids-standard.github.io/bids-validator/>`_.
