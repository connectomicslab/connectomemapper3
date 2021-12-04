## Connectome Mapper 3 BIDS App
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
This neuroimaging processing pipeline software is developed by the Connectomics Lab at the University Hospital of Lausanne (CHUV) for use within the [SNF Sinergia Project 170873](http://p3.snf.ch/project-170873), as well as for open-source software distribution.

![GitHub release (latest by date)](https://img.shields.io/github/v/release/connectomicslab/connectomemapper3) ![GitHub Release Date](https://img.shields.io/github/release-date/connectomicslab/connectomemapper3?color=orange) [![DOI](https://zenodo.org/badge/183162514.svg)](https://zenodo.org/badge/latestdoi/183162514) ![Docker Image Version (latest semver)](https://img.shields.io/docker/v/sebastientourbier/connectomemapper-bidsapp?color=orange&label=docker%20version) [![Docker Pulls](https://img.shields.io/docker/pulls/sebastientourbier/connectomemapper-bidsapp)](https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp) [![CircleCI](https://circleci.com/gh/connectomicslab/connectomemapper3.svg?style=shield)](https://circleci.com/gh/connectomicslab/connectomemapper3) [![Code Coverage](https://app.codacy.com/project/badge/Coverage/658266303c3046e8896769670e6988eb)](https://www.codacy.com/gh/connectomicslab/connectomemapper3?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=connectomicslab/connectomemapper3&amp;utm_campaign=Badge_Coverage) [![Documentation Status](https://readthedocs.org/projects/connectome-mapper-3/badge/?version=latest)](https://connectome-mapper-3.readthedocs.io/en/latest/?badge=latest) [![Code Quality Review](https://app.codacy.com/project/badge/Grade/658266303c3046e8896769670e6988eb)](https://www.codacy.com/gh/connectomicslab/connectomemapper3?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=connectomicslab/connectomemapper3&amp;utm_campaign=Badge_Grade)

### Description
Connectome Mapper 3 is an open-source Python3 image processing pipeline software that implements full anatomical, diffusion and resting-state MRI processing pipelines, from raw Diffusion / T1 / T2 / BOLD data to multi-resolution connection matrices.

![Image not found](https://connectome-mapper-3.readthedocs.io/en/latest/_images/flowchart_bidsapp.png)

Connectome Mapper 3 pipelines use a combination of tools from well-known software packages, including [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki), [FreeSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/FreeSurferWiki), [ANTs](http://stnava.github.io/ANTs/), [MRtrix3](http://www.mrtrix.org/), [Dipy](https://nipy.org/dipy/) and [AFNI](https://afni.nimh.nih.gov/), orchestrated by the [Nipype](https://nipype.readthedocs.io/en/latest/) dataflow library. These pipelines were designed to provide the best software implementation for each state of processing, and will be updated as newer and better neuroimaging software become available.

This tool allows you to easily do the following:

  * Take T1 / Diffusion / resting-state MRI data from raw to multi-resolution connection matrices.
  * Implement tools from different software packages.
  * Achieve optimal data processing quality by using the best tools available
  * Automate and parallelize processing steps, providing a significant speed-up from typical linear, manual processing.

Reproducibility and replicatibility is achieved through the distribution of a BIDSApp, a software container image which takes BIDS datasets as inputs and which provides a frozen environment where versions of all external softwares and libraries are fixed.

### Resources

  * **Documentation:** [https://connectome-mapper-3.readthedocs.io](https://connectome-mapper-3.readthedocs.io)
  * **Mailing list:** [https://groups.google.com/forum/#!forum/cmtk-users](https://groups.google.com/forum/#!forum/cmtk-users)
  * **Source:** [https://github.com/connectomicslab/connectomemapper3](https://github.com/connectomicslab/connectomemapper3)
  * **Bug reports:** [https://github.com/connectomicslab/connectomemapper3/issues](https://github.com/connectomicslab/connectomemapper3/issues)

### Usage
This BIDS App has the following command line arguments:

        $ docker run -it sebastientourbier/connectomemapper-bidsapp -h

        usage: run.py [-h]
              [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]]
              [--session_label SESSION_LABEL [SESSION_LABEL ...]]
              [--anat_pipeline_config ANAT_PIPELINE_CONFIG]
              [--dwi_pipeline_config DWI_PIPELINE_CONFIG]
              [--func_pipeline_config FUNC_PIPELINE_CONFIG]
              [--number_of_threads NUMBER_OF_THREADS]
              [--number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL]
              [--mrtrix_random_seed MRTRIX_RANDOM_SEED]
              [--ants_random_seed ANTS_RANDOM_SEED]
              [--ants_number_of_threads ANTS_NUMBER_OF_THREADS]
              [--fs_license FS_LICENSE] [--coverage] [--notrack] [-v]
              bids_dir output_dir {participant,group}

        Entrypoint script of the BIDS-App Connectome Mapper version v3.0.0-RC3

        positional arguments:
          bids_dir              The directory with the input dataset formatted
                                according to the BIDS standard.
          output_dir            The directory where the output files should be stored.
                                If you are running group level analysis this folder
                                should be prepopulated with the results of the
                                participant level analysis.
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
          --number_of_threads NUMBER_OF_THREADS
                                The number of OpenMP threads used for multi-threading
                                by Freesurfer (Set to [Number of available CPUs -1] by default).
          --number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL
                                The number of subjects to be processed in parallel
                                (One by default).
          --mrtrix_random_seed MRTRIX_RANDOM_SEED
                                Fix MRtrix3 random number generator seed to the
                                specified value
          --ants_random_seed ANTS_RANDOM_SEED
                                Fix ANTS random number generator seed to the specified
                                value
          --ants_number_of_threads ANTS_NUMBER_OF_THREADS
                                Fix number of threads in ANTs. If not specified ANTs
                                will use the same number as the number of OpenMP
                                threads (see `----number_of_threads` option flag)
          --fs_license FS_LICENSE
                                Freesurfer license.txt
          --coverage            Run connectomemapper3 with coverage
          --notrack             Do not send event to Google analytics to report BIDS
                                App execution, which is enabled by default.
          -v, --version         show program's version number and exit


### Credits

*   Sebastien Tourbier (sebastientourbier)
*   Yasser Aleman-Gomez (yasseraleman)
*   Alessandra Griffa (agriffa)
*   Adrien Birbaumer (abirba)
*   Patric Hagmann (pahagman)
*   Meritxell Bach Cuadra (meribach)

### Collaborators

Collaboration Signal Processing Laboratory (LTS5) EPFL Lausanne

*   Jean-Philippe Thiran
*   Xavier Gigandet
*   Leila Cammoun
*   Alia Lemkaddem (allem)
*   Alessandro Daducci (daducci)
*   David Romascano (davidrs06)
*   Stephan Gerhard (unidesigner)
*   Christophe Chênes (Cwis)
*   Oscar Esteban (oesteban)

Collaboration Children's Hospital Boston

*   Ellen Grant
*   Daniel Ginsburg (danginsburg)
*   Rudolph Pienaar (rudolphpienaar)
*   Nicolas Rannou (NicolasRannou)

### Funding

Work supported by the [Sinergia SNFNS-170873 Grant](http://p3.snf.ch/Project-170873).

### License
This software is distributed under the open-source license Modified BSD. See [license](docs/LICENSE) for more details.

All trademarks referenced herein are property of their respective holders.

Copyright (C) 2009-2021, Hospital Center and University of Lausanne (UNIL-CHUV), Ecole Polytechnique Fédérale de Lausanne (EPFL), Switzerland & Contributors.

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/sebastientourbier"><img src="https://avatars.githubusercontent.com/u/22279770?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Sébastien Tourbier</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=sebastientourbier" title="Code">💻</a> <a href="#design-sebastientourbier" title="Design">🎨</a> <a href="#infra-sebastientourbier" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=sebastientourbier" title="Tests">⚠️</a> <a href="#example-sebastientourbier" title="Examples">💡</a> <a href="#ideas-sebastientourbier" title="Ideas, Planning, & Feedback">🤔</a> <a href="#mentoring-sebastientourbier" title="Mentoring">🧑‍🏫</a> <a href="#projectManagement-sebastientourbier" title="Project Management">📆</a> <a href="https://github.com/connectomicslab/connectomemapper3/pulls?q=is%3Apr+reviewed-by%3Asebastientourbier" title="Reviewed Pull Requests">👀</a> <a href="#tutorial-sebastientourbier" title="Tutorials">✅</a> <a href="#talk-sebastientourbier" title="Talks">📢</a></td>
    <td align="center"><a href="https://github.com/joanrue"><img src="https://avatars.githubusercontent.com/u/13551804?v=4?s=100" width="100px;" alt=""/><br /><sub><b>joanrue</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/issues?q=author%3Ajoanrue" title="Bug reports">🐛</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=joanrue" title="Code">💻</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=joanrue" title="Tests">⚠️</a> <a href="#ideas-joanrue" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/Katharinski"><img src="https://avatars.githubusercontent.com/u/20595787?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Katharina Glomb</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/issues?q=author%3AKatharinski" title="Bug reports">🐛</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=Katharinski" title="Code">💻</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=Katharinski" title="Tests">⚠️</a> <a href="#ideas-Katharinski" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://www.linkedin.com/in/aniltuncel/"><img src="https://avatars.githubusercontent.com/u/7026020?v=4?s=100" width="100px;" alt=""/><br /><sub><b>anilbey</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=anilbey" title="Code">💻</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=anilbey" title="Tests">⚠️</a> <a href="#ideas-anilbey" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=anilbey" title="Documentation">📖</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!