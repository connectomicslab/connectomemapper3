Adopting Datalad for collaboration
===================================================

-  Created by Sebastien Tourbier - 2019 Jan 8

Move original BIDS dataset to server
------------------------------------

::

    rsync -P -v -avz -e 'ssh' --exclude 'derivatives' --exclude 'code' --exclude '.datalad' --exclude '.git' --exclude '.gitattributes' /media/localadmin/HagmannHDD/Seb/ds-newtest2/* tourbier@<SERVER_IP_ADDRESS>:/home/tourbier/Data/ds-newtest2

Datalad setup and dataset creation on Server (accessible via ssh)
-----------------------------------------------------------------

Connect to server
~~~~~~~~~~~~~~~~~

::

    ssh tourbier@<SERVER_IP_ADDRESS>

Install liblzma-dev (datalad pylzma depnendency) and Datalad
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    sudo apt-get install liblzma-dev
    pip install datalad[all]
    pip install datalad_containers
    pip install datalad_neuroimaging
    pip install datalad_revolution

Go to source dataset directory, create a Datalad dataset and save all
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    cd /home/tourbier/Data/ds-newtest2
    datalad rev-create -f -D "Original test dataset on lab server"
    datalad rev-save -m 'Source (Origin) BIDS dataset' --version-tag origin

Report on the state of dataset content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad rev-status --recursive

Processing using the Connectome Mapper BIDS App on a local workstation
----------------------------------------------------------------------

Dataset installation
~~~~~~~~~~~~~~~~~~~~

::

    datalad install -s ssh://tourbier@<SERVER_IP_ADDRESS>:/home/tourbier/Data/ds-newtest2  \
    /home/localadmin/Data/ds-newtest2

    cd /home/localadmin/Data/ds-newtest2

Get T1w and Diffusion images to be processed, written in a bash script for reproducibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad get -J 4 sub-*/ses-*/anat/sub-*_T1w.nii.gz
    datalad get -J 4 sub-*/ses-*/dwi/sub-*_dwi.nii.gz
    datalad get -J 4 sub-*/ses-*/dwi/sub-*_dwi.bvec
    datalad get -J 4 sub-*/ses-*/dwi/sub-*_dwi.bval

Write datalad get commands to get\_required\_files\_for\_analysis.sh::

    mkdir code
    echo "datalad get -J 4 sub-*/ses-*/anat/sub-*_T1w.nii.gz" > code/get_required_files_for_analysis.sh
    echo "datalad get -J 4 sub-*/ses-*/dwi/sub-*_dwi.nii.gz" >> code/get_required_files_for_analysis.sh
    echo "datalad get -J 4 sub-*/ses-*/dwi/sub-*_dwi.bvec" >> code/get_required_files_for_analysis.sh
    echo "datalad get -J 4 sub-*/ses-*/dwi/sub-*_dwi.bval" >> code/get_required_files_for_analysis.sh

Add all content in the code/ directory directly to git::

    datalad add --to-git code

Add the container image of the connectome mapper to the dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad containers-add connectomemapper-bidsapp-|release| \
    --url dhub://sebastientourbier/connectomemapper-bidsapp:|release| \
    --update

Save the state of the dataset prior to analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad rev-save -m "Seb's test dataset on local \
    workstation ready for analysis with connectomemapper-bidsapp:|release|" \
    --version-tag ready4analysis-<date>-<time>

Run Connectome Mapper on all subjects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad containers-run --container-name connectomemapper-bidsapp-|release| \
    '/tmp' '/tmp/derivatives' participant \
    --anat_pipeline_config '/tmp/code/ref_anatomical_config.ini' \
    --dwi_pipeline_config '/tmp/code/ref_diffusion_config.ini' \

Save the state
~~~~~~~~~~~~~~

::

    datalad rev-save -m "Seb's test dataset on local \
    workstation processed by connectomemapper-bidsapp:|release|, {Date/Time}" \
    --version-tag processed-<date>-<time>

Report on the state of dataset content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad rev-status --recursive

With DataLad with don’t have to keep those inputs around – without losing the ability to reproduce an analysis. Let’s uninstall them – checking the size on disk before and after
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad uninstall sub-*/*

Local collaboration with Bob for Electrical Source Imaging
---------------------------------------------------------------------------------------

Processed dataset installation on Bob's workstation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad install -s (ssh://)localadmin@HOS51827:/home/localadmin/Data/ds-newtest2  \
    /home/bob/Data/ds-newtest2

    cd /home/bob/Data/ds-newtest2

Get connectome mapper output files (Brain Segmentation and Multi-scale Parcellation) used by Bob in his analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_mask.nii.gz
    datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_class-*_dseg.nii.gz
    datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_scale*_atlas.nii.gz

Write datalad get commands to
get\_required\_files\_for\_analysis\_by\_bob.sh for reproducibility::

    echo "datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_mask.nii.gz" > code/get_required_files_for_analysis_by_bob.sh
    echo "datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_class-*_dseg.nii.gz" >> code/get_required_files_for_analysis_by_bob.sh
    echo "datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_scale*_atlas.nii.gz" >> code/get_required_files_for_analysis_by_bob.sh

Add all content in the code/ directory directly to git::

    datalad add --to-git code

Update derivatives
~~~~~~~~~~~~~~~~~~

::

    cd /home/bob/Data/ds-newtest2
    mkdir derivatives/cartool ...

Save the state
~~~~~~~~~~~~~~

::

    datalad rev-save -m "Bob's test dataset on local \
    workstation processed by cartool:|release|, {Date/Time}" \
    --version-tag processed-<date>-<time>

Report on the state of dataset content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad rev-status --recursive

With DataLad with don’t have to keep those inputs around – without losing the ability to reproduce an analysis. Let’s uninstall them – checking the size on disk before and after
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    datalad uninstall sub-*/*
    datalad uninstall derivatives/cmp/*
    datalad uninstall derivatives/freesurfer/*
    datalad uninstall derivatives/nipype/*
