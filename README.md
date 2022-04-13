## Connectome Mapper 3

This neuroimaging processing pipeline software is developed by the Connectomics Lab at the University Hospital of Lausanne (CHUV) for use within the [SNF Sinergia Project 170873](http://p3.snf.ch/project-170873), as well as for open-source software distribution.

![GitHub release (latest by date)](https://img.shields.io/github/v/release/connectomicslab/connectomemapper3) ![GitHub Release Date](https://img.shields.io/github/release-date/connectomicslab/connectomemapper3?color=orange) [![DOI](https://zenodo.org/badge/183162514.svg)](https://zenodo.org/badge/latestdoi/183162514) [![PyPI](https://img.shields.io/pypi/v/connectomemapper?color=orange)](https://pypi.org/project/connectomemapper/) ![Docker Image Version (latest semver)](https://img.shields.io/docker/v/sebastientourbier/connectomemapper-bidsapp?color=blue&label=docker%20version) [![Docker Pulls](https://img.shields.io/docker/pulls/sebastientourbier/connectomemapper-bidsapp?color=orange)](https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp) [![CircleCI](https://circleci.com/gh/connectomicslab/connectomemapper3.svg?style=shield)](https://circleci.com/gh/connectomicslab/connectomemapper3) [![Code Coverage](https://app.codacy.com/project/badge/Coverage/658266303c3046e8896769670e6988eb)](https://www.codacy.com/gh/connectomicslab/connectomemapper3?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=connectomicslab/connectomemapper3&amp;utm_campaign=Badge_Coverage) [![Documentation Status](https://readthedocs.org/projects/connectome-mapper-3/badge/?version=latest)](https://connectome-mapper-3.readthedocs.io/en/latest/?badge=latest) [![Code Quality Review](https://app.codacy.com/project/badge/Grade/658266303c3046e8896769670e6988eb)](https://www.codacy.com/gh/connectomicslab/connectomemapper3?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=connectomicslab/connectomemapper3&amp;utm_campaign=Badge_Grade) [![All Contributors](https://img.shields.io/badge/all_contributors-12-orange.svg?style=flat-square)](#contributors-)

### Description

Connectome Mapper 3 is an open-source Python3 image processing pipeline software, with a Graphical User Interface, that implements full anatomical, diffusion and resting-state MRI processing pipelines, from raw Diffusion / T1 / BOLD to multi-resolution connection matrices, based on a new version of the Lausanne parcellation atlas, aka `Lausanne2018`.

![Image not found](https://github.com/connectomicslab/connectomemapper3/raw/master/docs/images/flowchart_bidsapp.png)

Connectome Mapper 3 pipelines use a combination of tools from well-known software packages, including [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki), [FreeSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/FreeSurferWiki), [ANTs](http://stnava.github.io/ANTs/), [MRtrix3](http://www.mrtrix.org/), [Dipy](https://nipy.org/dipy/) and [AFNI](https://afni.nimh.nih.gov/), orchestrated by the [Nipype](https://nipype.readthedocs.io/en/latest/) dataflow library. These pipelines were designed to provide the best software implementation for each state of processing at the time conceptualization, and can be updated as newer and better neuroimaging software become available.

To enhance reproducibility and replicatibility, the processing pipelines with all dependencies are encapsulated in a Docker image container, which handles datasets organized following the BIDS standard and is distributed as a `BIDS App` @ [Docker Hub](https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp). For execution on high-performance computing cluster, a Singularity image is also made freely available @ [Sylabs Cloud](https://cloud.sylabs.io/library/_container/5fe4e971bccfe9cf45792495).

To reduce the risk of misconfiguration and improve accessibility, Connectome Mapper 3 comes with an interactive GUI, aka `cmpbidsappmanager`, which supports the user in all the steps involved in the configuration of the pipelines, the configuration and execution of the BIDS App, and the control of the output quality. In addition, to facilitate the use by users not familiar with Docker and Singularity containers, Connectome Mapper 3 provides two Python commandline wrappers (`connectomemapper3_docker` and `connectomemapper3_singularity`) that will generate and run the appropriate command.

Since ``v3.0.3``, CMP3 provides a new pipeline ``cmp.pipelines.functional.eeg.EEGPipeline`` dedicated to EEG modality with a collection of interfaces based on [MNE](https://mne.tools/), [MNE-Connectivity](https://mne.tools/mne-connectivity), and [PyCartool](https://github.com/Functional-Brain-Mapping-Laboratory/PyCartool). Please check [this notebook](docs/notebooks/EEG_pipeline_tutorial.ipynb) for a demonstration of the newly implemented pipeline, using the “VEPCON” dataset, available at https://openneuro.org/datasets/ds003505/versions/1.1.1.

### How to install the python wrappers and the GUI?

You need to have first either Docker or Singularity engine and miniconda installed. We refer to the [dedicated documentation page](https://connectome-mapper-3.readthedocs.io/en/latest/installation.html) for more instruction details.

Then, download the appropriate [environment.yml](https://github.com/connectomicslab/connectomemapper3/raw/master/conda/environment.yml) / [environment_macosx.yml](https://github.com/connectomicslab/connectomemapper3/raw/master/conda/environment_macosx.yml) and create a conda environment `py37cmp-gui` with the following command:

```bash
$ conda env create -f /path/to/environment[_macosx].yml
```

Once the environment is created, activate it and install Connectome Mapper 3 with `PyPI` as follows:

```bash
$ conda activate py37cmp-gui
(py37cmp-gui)$ pip install connectomemapper
```

You are ready to use Connectome Mapper 3!

### Resources

  *   **Documentation:** [https://connectome-mapper-3.readthedocs.io](https://connectome-mapper-3.readthedocs.io)
  *   **Mailing list:** [https://groups.google.com/forum/#!forum/cmtk-users](https://groups.google.com/forum/#!forum/cmtk-users)
  *   **Source:** [https://github.com/connectomicslab/connectomemapper3](https://github.com/connectomicslab/connectomemapper3)
  *   **Bug reports:** [https://github.com/connectomicslab/connectomemapper3/issues](https://github.com/connectomicslab/connectomemapper3/issues)

### Carbon footprint estimation of BIDS App run 🌍🌳✨

In support to the Organisation for Human Brain Mapping (OHBM) 
Sustainability and Environmental Action (OHBM-SEA) group, CMP3 enables you
since `v3.0.3`  to be more aware about the adverse impact of your processing
on the environment!

With the new `--track_carbon_footprint` option of the `connectomemapper3_docker` and `connectomemapper3_singularity`
BIDS App python wrappers, and the new `"Track carbon footprint"` option of the `cmpbidsappmanager` BIDS Interface Window,
you can estimate the carbon footprint incurred by the execution of the BIDS App.
Estimations are conducted using [codecarbon](https://codecarbon.io) to estimate the amount of carbon dioxide (CO2)
produced to execute the code by the computing resources and save the results in ``<bids_dir>/code/emissions.csv``.

Then, to visualize, interpret and track the evolution of the emitted CO2 emissions, you can use the visualization
tool of `codecarbon` aka `carbonboard` that takes as input the `.csv` created::

```bash
$ carbonboard --filepath="<bids_dir>/code/emissions.csv" --port=xxxx
```

Please check [https://ohbm-environment.org](https://ohbm-environment.org) to learn more about OHBM-SEA!

### Usage

Having the `py37cmp-gui` conda environment previously installed activated, the BIDS App can easily be run using `connectomemapper3_docker`, the python wrapper for Docker, as follows:

```output
    usage: connectomemapper3_docker [-h]
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
                            [--fs_license FS_LICENSE] [--coverage]
                            [--notrack] [-v] [--track_carbon_footprint]
                            [--docker_image DOCKER_IMAGE]
                            [--config_dir CONFIG_DIR]
                            bids_dir output_dir {participant,group}

    Entrypoint script of the Connectome Mapper BIDS-App version v3.0.3 via Docker.
    
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
                            by Freesurfer (Set to [Number of available CPUs -1] by
                            default).
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
      --track_carbon_footprint
                            Track carbon footprint with `codecarbon
                            <https://codecarbon.io/>`_ and save results in a CSV
                            file called ``emissions.csv`` in the
                            ``<bids_dir>/code`` directory.
      --docker_image DOCKER_IMAGE
                            The path to the docker image.
      --config_dir CONFIG_DIR
                            The path to the directory containing the configuration
                            files.
```

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
    <td align="center"><a href="https://github.com/jwirsich"><img src="https://avatars.githubusercontent.com/u/7943145?v=4?s=100" width="100px;" alt=""/><br /><sub><b>jwirsich</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/issues?q=author%3Ajwirsich" title="Bug reports">🐛</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=jwirsich" title="Code">💻</a> <a href="#ideas-jwirsich" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/kuba-fidel"><img src="https://avatars.githubusercontent.com/u/92929875?v=4?s=100" width="100px;" alt=""/><br /><sub><b>kuba-fidel</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=kuba-fidel" title="Code">💻</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=kuba-fidel" title="Documentation">📖</a> <a href="#ideas-kuba-fidel" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/stefanches7"><img src="https://avatars.githubusercontent.com/u/17748742?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Stefan</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=stefanches7" title="Code">💻</a> <a href="#tutorial-stefanches7" title="Tutorials">✅</a> <a href="#ideas-stefanches7" title="Ideas, Planning, & Feedback">🤔</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/mschoettner"><img src="https://avatars.githubusercontent.com/u/48212821?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Mikkel Schöttner</b></sub></a><br /><a href="#tutorial-mschoettner" title="Tutorials">✅</a> <a href="https://github.com/connectomicslab/connectomemapper3/commits?author=mschoettner" title="Code">💻</a> <a href="#ideas-mschoettner" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/yasseraleman"><img src="https://avatars.githubusercontent.com/u/7859430?v=4?s=100" width="100px;" alt=""/><br /><sub><b>yasseraleman</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=yasseraleman" title="Code">💻</a> <a href="#ideas-yasseraleman" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/agriffa"><img src="https://avatars.githubusercontent.com/u/557451?v=4?s=100" width="100px;" alt=""/><br /><sub><b>agriffa</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=agriffa" title="Code">💻</a> <a href="#ideas-agriffa" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://github.com/emullier"><img src="https://avatars.githubusercontent.com/u/43587002?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Emeline Mullier</b></sub></a><br /><a href="https://github.com/connectomicslab/connectomemapper3/commits?author=emullier" title="Code">💻</a></td>
    <td align="center"><a href="https://wp.unil.ch/connectomics"><img src="https://avatars.githubusercontent.com/u/411192?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Patric Hagmann</b></sub></a><br /><a href="#ideas-pahagman" title="Ideas, Planning, & Feedback">🤔</a> <a href="#fundingFinding-pahagman" title="Funding Finding">🔍</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

Thanks also goes to all these wonderful people that contributed to Connectome Mapper 1 and 2:

*   Collaborators from Signal Processing Laboratory (LTS5), EPFL, Lausanne:

    *   Jean-Philippe Thiran
    *   Leila Cammoun
    *   Adrien Birbaumer (abirba)
    *   Alessandro Daducci (daducci)
    *   Stephan Gerhard (unidesigner)
    *   Christophe Chênes (Cwis)
    *   Oscar Esteban (oesteban)
    *   David Romascano (davidrs06)
    *   Alia Lemkaddem (allem)
    *   Xavier Gigandet

*   Collaborators from Children's Hospital, Boston:

    *   Ellen Grant
    *   Daniel Ginsburg (danginsburg)
    *   Rudolph Pienaar (rudolphpienaar)
    *   Nicolas Rannou (NicolasRannou)

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

### How to contribute?

Please consult our [Contributing to Connectome Mapper 3](https://connectome-mapper-3.readthedocs.io/en/latest/contributing.html#) guidelines.

### Funding

Work supported by the [Sinergia SNFNS-170873 Grant](http://p3.snf.ch/Project-170873).

### License

This software is distributed under the open-source 3-Clause BSD License. See [license](docs/LICENSE) for more details.

All trademarks referenced herein are property of their respective holders.

Copyright (C) 2009-2022, Hospital Center and University of Lausanne (UNIL-CHUV), Ecole Polytechnique Fédérale de Lausanne (EPFL), Switzerland & Contributors.
