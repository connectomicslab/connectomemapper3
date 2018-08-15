## Connectome Mapper 3 BIDS App
### Description
This BIDS app implements full anatomical/diffusion/functional MRI processing pipeline using Connectome Mapper 3,
from raw Diffusion/T1/T2/BOLD data to multi-resolution connection matrices.
The Connectome Mapper 3 is part of the Connectome Mapping Toolkit.

Copyright (C) 2009-2018, Ecole Polytechnique Fédérale de Lausanne (EPFL) and
Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland

This software is distributed under the open-source license Modified BSD.

###Credits
* Jean-Philippe Thiran
* Reto Meuli
* Patric Hagmann (pahagman)
* Xavier Gigandet
* Leila Cammoun
* Alessandro Daducci (daducci)
* Alia Lemkaddem (allem)
* Stephan Gerhard (unidesigner)
* Christophe Chênes (Cwis)
* Alessandra Griffa (agriffa)
* Oscar Esteban (oesteban)
* Adrien Birbaumer
* David Romascano
* Sebastien Tourbier (sebastientourbier)

###Contributors
Collaboration Children's Hospital Boston

* Ellen Grant
* Daniel Ginsburg (danginsburg)
* Rudolph Pienaar (rudolphpienaar)
* Nicolas Rannou (NicolasRannou)

### Usage
This App has the following command line arguments:

        $ docker -ti --rm sebastientourbier/connectomemapper3 --help

        usage: run_connectomemapper3.py [-h]
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
          -v, --version         show program's version number and exit

#### Participant level
To run it in participant level mode (for one participant):

    		docker run -ti --rm \
    		-v /Users/filo/data/ds005:/bids_dataset:ro \
    		-v /Users/filo/outputs:/outputs \
    		-v /Users/filo/freesurfer_license.txt:/license.txt \
    		bids/freesurfer \
    		/bids_dataset /outputs participant --participant_label 01 \
    		--license_file "/license.txt"
