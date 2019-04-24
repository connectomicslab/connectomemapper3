## Connectome Mapper 3 BIDS App (UNDER DEVELOPMENT)
### Description
This BIDS app implements full anatomical/diffusion/functional MRI processing pipeline using Connectome Mapper (CMP) 3,
from raw Diffusion / T1 / T2 / BOLD data to multi-resolution connection matrices.

![Image not found](https://connectome-mapper-3.readthedocs.io/en/latest/_images/flowchart.jpg)

The Connectome Mapper 3 is part of the Connectome Mapping Toolkit (CMTK).

### Documentation

More information and documentation can be found at [https://connectome-mapper-3.readthedocs.io](https://connectome-mapper-3.readthedocs.io)

### License
This software is distributed under the open-source license Modified BSD. See [license](docs/LICENSE) for more details.

All trademarks referenced herein are property of their respective holders.

Copyright (C) 2009-2019, Hospital Center and University of Lausanne (UNIL-CHUV), Ecole Polytechnique Fédérale de Lausanne (EPFL), Hospital Center and University of Geneva (UNIGE-HUG), Switzerland.

### Usage
This App has the following command line arguments:

        $connectomemapper3 --help

        <!-- usage: run_connectomemapper3.py [-h]
                                        [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]]
                                        [--anat_pipeline_config ANAT_PIPELINE_CONFIG]
                                        [--dwi_pipeline_config DWI_PIPELINE_CONFIG]
                                        [--func_pipeline_config FUNC_PIPELINE_CONFIG]
                                        [-v]
                                        bids_dir output_dir {participant,group}

        Example BIDS App entrypoint script.

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
          --anat_pipeline_config ANAT_PIPELINE_CONFIG
                                Configuration .txt file for processing stages of the
                                anatomical MRI processing pipeline
          --dwi_pipeline_config DWI_PIPELINE_CONFIG
                                Configuration .txt file for processing stages of the
                                diffusion MRI processing pipeline
          --func_pipeline_config FUNC_PIPELINE_CONFIG
                                Configuration .txt file for processing stages of the
                                fMRI processing pipeline
          -v, --version         show program's version number and exit -->

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

* Adrien Birbaumer
* Sebastien Tourbier (sebastientourbier)
* Yasser Aleman-Gomez ()
* Alessandra Griffa (agriffa)
* Patric Hagmann (pahagman)
* Meritxell Bach Cuadra
* Reto Meuli


### Contributors

Collaboration Signal Processing Laboratory (LTS5) EPFL Lausanne

* Jean-Philippe Thiran
* Xavier Gigandet
* Leila Cammoun
* Alia Lemkaddem (allem)
* Alessandro Daducci (daducci)
* Stephan Gerhard (unidesigner)
* Christophe Chênes (Cwis)
* Oscar Esteban (oesteban)
* David Romascano

Collaboration Children's Hospital Boston

* Ellen Grant
* Daniel Ginsburg (danginsburg)
* Rudolph Pienaar (rudolphpienaar)
* Nicolas Rannou (NicolasRannou)

### Funding

Work supported by the [Sinergia SNFNS-170873 Grant](http://p3.snf.ch/Project-170873).
