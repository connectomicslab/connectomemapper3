## Connectome Mapper 3 BIDS App (Beta release)
This neuroimaging processing pipeline software is developed by the Connectomics Lab at the University Hospital of Lausanne (CHUV) for use within the [SNF Sinergia Project 170873](http://p3.snf.ch/project-170873), as well as for open-source software distribution.

![Docker Image Version (latest by date)](https://img.shields.io/docker/v/sebastientourbier/connectomemapper-bidsapp) ![GitHub Release Date](https://img.shields.io/github/release-date/connectomicslab/connectomemapper3) [![DOI](https://zenodo.org/badge/183162514.svg)](https://zenodo.org/badge/latestdoi/183162514) [![CircleCI](https://circleci.com/gh/connectomicslab/connectomemapper3.svg?style=shield)](https://circleci.com/gh/connectomicslab/connectomemapper3) [![Documentation Status](https://readthedocs.org/projects/connectome-mapper-3/badge/?version=latest)](https://connectome-mapper-3.readthedocs.io/en/latest/?badge=latest) [![Docker Pulls](https://img.shields.io/docker/pulls/sebastientourbier/connectomemapper-bidsapp)](https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp)

### Description
Connectome Mapper 3 implements full anatomical/diffusion/functional MRI processing pipeline using Connectome Mapper (CMP) 3,
from raw Diffusion / T1 / T2 / BOLD data to multi-resolution connection matrices.

![Image not found](https://connectome-mapper-3.readthedocs.io/en/latest/_images/flowchart_bidsapp.png)

Connectome Mapper 3 is distributed as a BIDS App, a container image which takes BIDS datasets as inputs.

### Documentation

More information and documentation can be found at [https://connectome-mapper-3.readthedocs.io](https://connectome-mapper-3.readthedocs.io)

### License
This software is distributed under the open-source license Modified BSD. See [license](docs/LICENSE) for more details.

All trademarks referenced herein are property of their respective holders.

Copyright (C) 2009-2020, Hospital Center and University of Lausanne (UNIL-CHUV), Ecole Polytechnique Fédérale de Lausanne (EPFL), Switzerland & Contributors.

### Usage
This BIDS App has the following command line arguments:

        $connectomemapper3 --help

        <!-- usage: usage: run.py [-h]
              [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]]
              [--session_label SESSION_LABEL [SESSION_LABEL ...]]
              [--anat_pipeline_config ANAT_PIPELINE_CONFIG]
              [--dwi_pipeline_config DWI_PIPELINE_CONFIG]
              [--func_pipeline_config FUNC_PIPELINE_CONFIG]
              [--number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL]
              [--fs_license FS_LICENSE] [-v]
              bids_dir output_dir {participant,group}

        Entrypoint script of the BIDS-App Connectome Mapper version v3.0.0-beta-RC1


        positional arguments:
          bids_dir              The directory with the input dataset formatted
                                according to the BIDS standard.
          output_dir            The directory where the output files should be stored.
                                If you are running group level analysis this folder
                                should be prepopulated with the results of
                                theparticipant level analysis.
          {participant,group}   Level of the analysis that will be performed. Multiple
                                participant level analyses can be run independently
                                (in parallel) using the same output_dir.

       optional arguments:
          -h, --help            show this help message and exit
          --participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]
                                The label(s) of the participant(s) that should be
                                analyzed. The label corresponds to
                                sub-<participant_label> from the BIDS spec (so it does
                                not include "sub-"). If this parameter is not provided
                                all subjects should be analyzed. Multiple participants
                                can be specified with a space separated list.
          --session_label SESSION_LABEL [SESSION_LABEL ...]
                                The label(s) of the session that should be analyzed.
                                The label corresponds to ses-<session_label> from the
                                BIDS spec (so it does not include "ses-"). If this
                                parameter is not provided all sessions should be
                                analyzed. Multiple sessions can be specified with a
                                space separated list.
          --anat_pipeline_config ANAT_PIPELINE_CONFIG
                                Configuration .txt file for processing stages of the
                                anatomical MRI processing pipeline
          --dwi_pipeline_config DWI_PIPELINE_CONFIG
                                Configuration .txt file for processing stages of the
                                diffusion MRI processing pipeline
          --func_pipeline_config FUNC_PIPELINE_CONFIG
                                Configuration .txt file for processing stages of the
                                fMRI processing pipeline
          --number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL
                                The number of subjects to be processed in parallel
                                (One core used by default).
          --fs_license FS_LICENSE
                                Freesurfer license.txt
          -v, --version         show program's version number and exit

<!-- #### Participant level
To run it in participant level mode (for one participant):

        docker run -it --rm \
        -v /home/localadmin/data/ds001:/bids_dataset \
        -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2/derivatives:/outputs \
        -v /home/localadmin/data/ds001/code:/code \
        -v /usr/local/freesurfer/subjects/fsaverage:/bids_dataset/derivatives/freesurfer/fsaverage \
        -v /usr/local/freesurfer/license.txt:/opt/freesurfer/license.txt \
        sebastientourbier/connectomemapper3 \
        /bids_dataset /outputs participant --participant_label 01 \
        --anat_pipeline_config /code/ref_anatomical_config.ini \
        --dwi_pipeline_config /code/ref_diffusion_config.ini \
        --func_pipeline_config /code/ref_fMRI_config.ini -->

### Credits

* Sebastien Tourbier (sebastientourbier)
* Yasser Aleman-Gomez (yasseraleman)
* Alessandra Griffa (agriffa)
* Adrien Birbaumer (abirba)
* Patric Hagmann (pahagman)
* Meritxell Bach Cuadra (meribach)

### Collaborators

Collaboration Signal Processing Laboratory (LTS5) EPFL Lausanne

* Jean-Philippe Thiran
* Xavier Gigandet
* Leila Cammoun
* Alia Lemkaddem (allem)
* Alessandro Daducci (daducci)
* David Romascano (davidrs06)
* Stephan Gerhard (unidesigner)
* Christophe Chênes (Cwis)
* Oscar Esteban (oesteban)

Collaboration Children's Hospital Boston

* Ellen Grant
* Daniel Ginsburg (danginsburg)
* Rudolph Pienaar (rudolphpienaar)
* Nicolas Rannou (NicolasRannou)

### Funding

Work supported by the [Sinergia SNFNS-170873 Grant](http://p3.snf.ch/Project-170873).
