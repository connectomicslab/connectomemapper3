.. _datalad-cmp:

===================================================
Adopting Datalad for collaboration
===================================================

Datalad is a powerful tool for the versioning and sharing of raw
and processed data as well as for the tracking of data provenance
(i.e. the recording on how data was processed). This page was
created with the intention to share with the user how we adopted
datalad to manage and process datasets with Connectome Mapper 3
in in our lab, following the YODA principles to our best.

You may ask "What are the YODA principles?". They are basic principles
behind creating, sharing, and publishing reproducible, understandable,
and open data analysis projects with DataLad.

For more details and tutorials on Datalad and YODA, please check the
recent `Datalad Handbook <http://handbook.datalad.org/en/latest/>`_
and the `YODA principles <https://handbook.datalad.org/en/latest/basics/101-127-yoda.html>`_.

**Happy Collaborative and Reproducible Data Processing!**

.. note:: This was tested on ``Ubuntu 16.04`` with ``Datalad 0.14.0``, its extensions ``datalad-container 1.1.2``, ``datalad-neuroimaging 0.3.1``, and ``git-annex 8.20210127``.

Install Datalad and all dependencies
------------------------------------

On Ubuntu/Debian install `git-annex` the proper dependencies::

    sudo apt-get install git-annex liblzma-dev

.. note:: If you are using Mac OS, start from `installing the Homebrew <https://brew.sh/>`_,
    then install other dependencies::

        brew install git-annex xz

Then install Datalad and its extensions::

    sudo apt-get install git-annex liblzma-dev
    pip install datalad[all]==0.14.0
    pip install datalad-container==1.1.2
    pip install datalad-neuroimaging==0.3.1

Copy BIDS dataset to server
------------------------------------

Copy the raw BIDS dataset using `rsync`::

    rsync -P -avz -e 'ssh' \
    --exclude 'derivatives' \
    --exclude 'code' \
    --exclude '.datalad' \
    --exclude '.git' \
    --exclude '.gitattributes' \
    /path/to/ds-example/* \
    <SERVER_USERNAME>@<SERVER_IP_ADDRESS>:/archive/data/ds-example

where:

    * `-P` is used to show progress during transfer
    * `-v` increases verbosity
    * `-e` specifies the remote shell to use (ssh)
    * `-a` indicates archive mode
    * `-z` enables file data compression during the transfer
    * `--exclude DIR_NAME` exclude the specified `DIR_NAME` from the copy

Remote datalad dataset creation on Server
-----------------------------------------

Connect to Server
~~~~~~~~~~~~~~~~~

To connect with SSH::

    ssh <SERVER_USERNAME>@<SERVER_IP_ADDRESS>

Creation of Datalad dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to the source dataset directory::

    cd /archive/data/ds-example

Initialize the Datalad dataset::

    datalad create -f -c text2git -D "Original example dataset on lab server" -d .

where:

    * `-f` forces to create the datalad dataset if not empty
    * `-c text2git` configures Datalad to use git to manage text file
    * `-D <DESCRIPTION>` gives a brief description of the dataset
    * `-d <PATH>` specify the location where the Datalad dataset is created

Track all files contained in the dataset with Datalad::

    datalad save -m "Source (Origin) BIDS dataset" --version-tag origin

where:

    * `-m MESSAGE` is the description of the state or
      the changes made to the dataset
    * `--version-tag` tags the state of the Dataset

Report on the state of dataset content::

    datalad status -r
    git log

Processing using the Connectome Mapper BIDS App on Alice's workstation
----------------------------------------------------------------------

To make the most of Datalad, we
YODA-compliant data analysis project, you will not only have theoretical
knowledge about the YODA principles, but also gain practical experience.

Processed dataset creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initialize a datalad dataset with the YODA procedure::

    datalad create -c text2git -c yoda \
    -D "Processed example dataset by Alice with CMP3" \
    /home/alice/data/ds-example-processed

This will create a datalad dataset with:

    * a code directory in your dataset
    * three files for human consumption (`README.md`, `CHANGELOG.md`)
    * everything in the `code/` directory configured to be tracked by Git, not git-annex
    * `README.md` and `CHANGELOG.md` configured in the root of the dataset to be tracked by Git
    * Text files configured to be tracked by Git

Go to the created dataset directory::

    cd /home/alice/data/ds-example-processed

Create the `derivatives` output directory:

    mkdir derivatives

Raw BIDS dataset installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the remove datalad dataset `ds-example` in `/home/alice/data/ds-example-processed/input/`::

    datalad install -d . -s ssh://<SERVER_USERNAME>@<SERVER_IP_ADDRESS>:/archive/data/ds-example \
    /home/alice/data/ds-example-processed/input/

where:

    * `-s SOURCE` specifies the URL or local path of the installation source

Get T1w and Diffusion images to be processed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For reproducibility, create and write datalad get commands to `get_required_files_for_analysis.sh`::

    echo "datalad get input/sub-*/ses-*/anat/sub-*_T1w.nii.gz" > code/get_required_files_for_analysis.sh
    echo "datalad get input/sub-*/ses-*/dwi/sub-*_dwi.nii.gz" >> code/get_required_files_for_analysis.sh
    echo "datalad get input/sub-*/ses-*/dwi/sub-*_dwi.bvec" >> code/get_required_files_for_analysis.sh
    echo "datalad get input/sub-*/ses-*/dwi/sub-*_dwi.bval" >> code/get_required_files_for_analysis.sh

Save the script to the dataset’s history::

    datalad save -m "Add script to get the files required for analysis by Alice"

Execute the script::

    sh code/get_required_files_for_analysis.sh

Link the container image with the dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add Connectome Mapper's container image to the datalad dataset::

    datalad containers-add connectomemapper-bidsapp-<VERSION_TAG> \
    --url dhub://sebastientourbier/connectomemapper-bidsapp:<VERSION_TAG> \
    -d . \
    --call-fmt \
    "docker run --rm -t \
        -v "$(pwd)/input":/bids_dir \
        -v "$(pwd)/code":/bids_dir/code \
        -v "$(pwd)"/derivatives:/output_dir \
        -u "$(id -u)":"$(id -g)" \
        sebastientourbier/connectomemapper-bidsapp:<VERSION_TAG> {cmd}"

where:

* `--call-fmt` specifies a custom docker run command. The current directory
  is assumed to be the BIDS root directory and retrieve with `"$(pwd)"/input` and the
  output directory is inside the `derivatives/` folder.

.. important:: The name of the container-name registered to Datalad cannot have dot
    as character so that a `<VERSION_TAG>` of `v3.X.Y` would need to be rewritten as `v3-X-Y`

Copy existing reference pipeline configuration files to `code` folder::

    cp /path/to/existing/ref_anatomical_config.json \
    code/ref_anatomical_config.json
    cp /path/to/existing/ref_diffusion_config.json \
    code/ref_diffusion_config.json

Save the state of the dataset prior to analysis::

    datalad save -m "Alice's test dataset on local \
    workstation ready for analysis with connectomemapper-bidsapp:<VERSION_TAG>" \
    --version-tag ready4analysis-<date>-<time>

Run Connectome Mapper with Datalad
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run Connectome Mapper on all subjects::

    datalad containers-run --container-name connectomemapper-bidsapp-<VERSION_TAG> \
    --input code/ref_anatomical_config.json \
    --input code/ref_diffusion_config.json \
    --output derivatives \
    /bids_dir /output_dir participant \
    --anat_pipeline_config '/bids_dir/{inputs[0]}' \
    --dwi_pipeline_config '/bids_dir/{inputs[1]}'

Save the state::

    datalad save -m "Alice's test dataset on local \
    workstation processed by connectomemapper-bidsapp:<VERSION_TAG>, {Date/Time}" \
    --version-tag processed-<date>-<time>

Report on the state of dataset content::

    datalad status -r
    git log

Configure a datalad dataset target on the Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a remote dataset repository and configures it
as a dataset sibling to be used as a publication target::

    datalad create-sibling --name remote -d . \
    <SERVER_USERNAME>@<SERVER_IP_ADDRESS>:/archive/data/ds-example-processed

See the documentation of `datalad create-sibling <http://docs.datalad.org/en/stable/generated/man/datalad-create-sibling.html>`_
command for more details.

Update the remote datalad dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Push the datalad dataset with data derivatives to the server::

    datalad push -d . --to remote


.. note:: `--to remote` specifies the `remote` dataset sibling i.e.
    ``ssh://<SERVER_USERNAME>@<SERVER_IP_ADDRESS>:/archive/data/ds-example-processed``
    previously configured.

Uninstall all files accessible from the remote
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With DataLad we don’t have to keep those inputs around – without losing the ability to reproduce an analysis.
Let’s uninstall them – checking the size on disk before and after::

    datalad uninstall sub-*/*

Local collaboration with Bob for Electrical Source Imaging
---------------------------------------------------------------------------------------

Processed dataset installation on Bob's workstation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the processed datalad dataset `ds-example-processed` in `/home/bob/data/ds-example-processed``::

    datalad install -s ssh://<SERVER_USERNAME>@<SERVER_IP_ADDRESS>:/archive/data/ds-example-processed  \
    /home/bob/data/ds-example-processed

Go to datalad dataset clone directory::

    cd /home/bob/data/ds-example-processed

Get connectome mapper output files (Brain Segmentation and Multi-scale Parcellation) used by Bob in his analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For reproducibility, write datalad get commands to `get_required_files_for_analysis_by_bob.sh`::

    echo "datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_mask.nii.gz" \
    > code/get_required_files_for_analysis_by_bob.sh
    echo "datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_class-*_dseg.nii.gz" \
    >> code/get_required_files_for_analysis_by_bob.sh
    echo "datalad get -J 4 derivatives/cmp/sub-*/ses-*/anat/sub-*_scale*_atlas.nii.gz" \
    >> code/get_required_files_for_analysis_by_bob.sh

Save the script to the dataset’s history::

    datalad save -m "Add script to get the files required for analysis by Bob"

Execute the script::

    sh code/get_required_files_for_analysis_by_bob.sh

Update derivatives
~~~~~~~~~~~~~~~~~~

Update derivatives with data produced by Cartool::

    cd /home/bob/data/ds-example
    mkdir derivatives/cartool
    cp [...]

Save the state::

    datalad save -m "Bob's test dataset on local \
    workstation processed by cartool:<CARTOOL_VERSION>, {Date/Time}" \
    --version-tag processed-<date>-<time>

Report on the state of dataset content::

    datalad status -r
    git log

Update the remote datalad dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Update the remote datalad dataset with data derivatives::

    datalad push -d . --to origin


.. note:: `--to origin` specifies the `origin` dataset sibling i.e.
    ``ssh://<SERVER_USERNAME>@<SERVER_IP_ADDRESS>:/archive/data/ds-example-processed``
    from which it was cloned.

Uninstall all files accessible from the remote
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Again, with DataLad we don’t have to keep those inputs around – without losing the ability to reproduce an analysis.
Let’s uninstall them – checking the size on disk before and after::

    datalad uninstall sub-*/*
    datalad uninstall derivatives/cmp/*
    datalad uninstall derivatives/freesurfer/*
    datalad uninstall derivatives/nipype/*

-  Created by Sebastien Tourbier (2019 Jan 08)
-  Last modification: 2021 Feb 18
