************************
BIDS App Manager: User's Guide
************************

Introduction
=============================

TBC

Step 1: open a terminal, activate the conda environment
=============================

    $ source activate py27cmp

    or

    $ conda activate py27cmp

Step 2: start the Connectome Mapper 3 BIDS App Manager
=============================

    $ cmpbidsappmanager

Step 3: load a BIDS dataset
=============================

The ``Connectome Mapper 3`` BIDS App Manager allows you to:

* load a BIDS dataset stored locally

You only have to select the root directory of your valid BIDS dataset (see note below)

* create a new datalad/BIDS dataset locally from an existing local or remote datalad/BIDS dataset

Select the mode "Install a Datalad/BIDS dataset".

If ssh connection is used, make sure to enable the  "install via ssh" and to provide all connection details (IP address / Remote host name, remote user, remote password)

.. note:: The input dataset MUST be a valid :abbr:`BIDS (Brain Imaging Data
Structure)` structured dataset and must include at least one T1w or MPRAGE structural image.
We highly recommend that you validate your dataset with the free, online
`BIDS Validator <http://bids-standard.github.io/bids-validator/>`_.

Step 4: configure the processing stages of the different processing pipelines
=============================

TBC

Step 5: configure and run the Connectome Mapper 3 BIDS App
=============================

TBC

Step 6: check stages outputs
=============================

TBC
