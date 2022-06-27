---
title: 'Connectome Mapper 3: A Flexible and Open-Source Pipeline Software for Multiscale Multimodal Human Connectome Mapping'
tags:
  - Python
  - neuroscience
  - pipeline
  - workflow
  - connectome
  - multi-scale
  - MRI
  - BIDS
  - BIDS App
  - containerized workflows
  - nipype
authors:
  - name: Sebastien Tourbier
    orcid: 0000-0002-4441-899X
    affiliation: 1
  - name: Joan Rue-Queralt
    orcid: 0000-0002-9595-4557
    affiliation: 1
  - name: Katharina Glomb
    orcid: 0000-0002-4596-4386
    affiliation: 8
  - name: Yasser Aleman-Gomez
    orcid: 0000-0001-6067-8639
    affiliation: 1
  - name: Emeline Mullier
    orcid: 0000-0001-6209-0791
    affiliation: 1
  - name: Alessandra Griffa
    orcid: 0000-0003-1923-1653
    affiliation: "2,3"
  - name: Mikkel Schöttner
    orcid: 0000-0002-4521-9837 
    affiliation: 1
  - name: Jonathan Wirsich
    orcid: 0000-0003-0588-9710
    affiliation: 4
  - name: M. Anıl Tuncel
    orcid: 0000-0003-0317-2556
    affiliation: 5
  - name: Jakub Jancovic
    orcid: 0000-0002-3312-3918
    affiliation: 6
  - name: Meritxell Bach Cuadra
    affiliation: "7,1"
    orcid: 0000-0003-2730-4285
  - name: Patric Hagmann
    orcid: 0000-0002-2854-6561
    affiliation: 1
affiliations:
 - name: Radiology Department, Centre Hospitalier Universitaire Vaudois and University of Lausanne (CHUV-UNIL), Switzerland
   index: 1
 - name: Department of Clinical Neurosciences, Division of Neurology, Geneva University Hospitals and Faculty of Medicine, University of Geneva, Geneva, Switzerland
   index: 2
 - name: Institute of Bioengineering, Center of Neuroprosthetics, École Polytechnique Fédérale De Lausanne (EPFL), Geneva, Switzerland
   index: 3
 - name: EEG and Epilepsy Unit, University Hospitals and Faculty of Medicine of Geneva, University of Geneva, Geneva, Switzerland
   index: 4
 - name: Blue Brain Project, École polytechnique fédérale de Lausanne (EPFL), Campus Biotech, Geneva, Switzerland
   index: 5
 - name: Foxight, Geneva, Switzerland
   index: 6
 - name: CIBM Center for Biomedical Imaging, Lausanne, Switzerland
   index: 7
 - name: Berlin Institute of Health at Charité; Department of Neurology with Experimental Neurology, Brain Simulation Section, Charité Universitätsmedizin Berlin, corporate member of Freie Universität Berlin and Humboldt-Universität zu Berlin, Berlin, Germany
   index: 8
date: 18 February 2021
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
# aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
# aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Summary

Connectome Mapper 3 (CMP3) is an open-source processing pipeline software, written in Python 3,
  for multi-scale multi-modal connectome mapping of the human brain.
It provides researchers with a unique workflow, implemented in accordance with the Brain Imaging Data Structure (BIDS)
  App framework [@GorgolewskiBIDSMethods:2017], that leverages a number of widely adopted software tools to map a graph
  representation of the structural and functional connections between brain regions, the connectome,
  at multiple scales.
The workflow can take any structural / diffusion / resting-state functional Magnetic Resonance Imaging (MRI)
  dataset structured according to the BIDS standard [@GorgolewskiTheExperiments:2016],
  and is intended to be run via its Docker and Singularity/Apptainer containerized versions.
To improve its accessibility, CMP3 comes with a graphical user interface, which supports
  the user in all the steps involved in the configuration of the pipelines, the configuration and execution of
  the BIDS App, and the control of the output quality.
CMP3 has been successfully employed in a number of research papers, and is currently being extended to
  electroencephalography, to offer a solid multi-modal framework to the community for the investigation of
  brain network function and organization at specific scales, as well as a map that links different spatial
  and temporal scales.
CMP3 is available from the [Python Package Index (PyPI)](https://pypi.org/project/connectomemapper/),
  and the container images are available from [DockerHub](https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp)
  and [Sylabs Cloud](https://cloud.sylabs.io/library/connectomicslab/default/connectomemapper-bidsapp).

# Statement of Need

The field of MRI Connectomics has rapidly expanded since its advent 
  in the 2000s [@HagmannFromConnectomics:2005;@SpornsEditorialConnectomics:2018;@SpornsTheBrain:2005].
It has revolutionized the way to investigate *in vivo*, *non-invasively* and 
  *safely* at different macroscopic scales the structural and functional systems of the 
  brain by modeling connections between brain areas as a graph or network, known as
  `connectome`, and has become a widely used set of methods in Neuroscience [@Bassett2017]. 
While brain areas are usually derived from high resolution structural T1 weighted MRI (sMRI),
  structural brain connectomes are mapped from diffusion MR imaging (dMRI) tractography, and
  functional brain connectomes are usually mapped from resting-state functional MRI (rfMRI).
Connectome Mapper (CMP), an open-source pipeline software with a graphical user interface (GUI),
  was created to simplify the organization, processing, and analysis of
  sMRI, dMRI, and rfMRI from raw data to multi-scale structural weighted and functional
  connectomes [@Daducci:2012], using in a common framework a multi-scale extension with
  hierarchical region grouping [@Cammoun2012:MappingMRI] of the Desikan-Killiany
  parcellation [@Desikan2006AnInterest].

As MRI is increasingly accessible and used in both clinical and research settings,
  multi-modal MRI datasets are being gathered at an unprecedented rate.
The size and organization of these datasets as well as the increasing complexity of the processing
  pipelines to analyze them present important challenges for scalable computing, data sharing,
  reproducibility and transparency of the analysis.
The last ten years have indeed witnessed a number of technical advances and a trend towards the adoption
  of open research practices such as *open data* and *open methods*
  [@EglenTowardNeuroscience:2017;@Kennedy2019;@Nichols:2017;@Poldrack2019ComputationalNeuroimaging].
This has led in particular to the creation of a community standard for dataset organization, known as
  BIDS, designed to ease the practice of sharing raw neuroimaging data [@GorgolewskiTheExperiments:2016]. 
Combined with advances in software virtualization, BIDS has enabled the creation of the BIDS Apps
  framework which uses software container technology to encapsulate neuroimaging processing pipelines
  and ensures portability and reproducibility [@GorgolewskiBIDSMethods:2017].
A large ecosystem of processing pipelines supporting the mapping of connectomes has evolved around this framework.
To the best of our knowledge, it includes  C-PAC [@cpac:2013], NIAK [@BellecNeuroimagingNIAK:2016], fMRIPrep [@Ghosh:2018], dMRIPrep [@dmriprep:2019],
  QSIPREP [@Cieslak:2021], MRtrix3_connectome [@Smith2019:BIDSApp], NDMG [@KiarAVariability:2018],
  PyNets [@PisnerPyNets:2020], and Micapipe [@Rodriguez:2022].
All the existing solutions have demonstrated their capability in addressing the previously-mentioned challenges.
However, none of them provide a direct alternative to CMP when dealing with multimodal datasets
  with the goal to create connectomes at multiple hierarchical scales.

CMP3 builds up on the two preceding versions of CMP and keeps the same philosophy. 
It introduces massive improvements in terms of the underlying codebase, the tools used, and the scope of the functionality
  provided.
This includes migration to Python 3, a revisited and extended multi-scale parcellation scheme, adoption
  of the BIDS standard for data organization, the encapsulation of the processing pipelines in software
  container images, continuous testing in concordance to the BIDS Apps standard, and major upgrades of the diffusion
  and fMRI pipelines.
Despite the recent emergence of electroencephalography (EEG) connectomics and the combination with the structural
  and functional connectome [@GlombNet:2020;@Sadaghiani:2020], no EEG pipeline
  exists to date.
Initiated during OHBM BrainHack 2020 ([https://github.com/ohbm/hackathon2020/issues/214](https://github.com/ohbm/hackathon2020/issues/214)),
  CMP3 is being extended to EEG.

# Design and functionality overview

## A flexible and interoperable workflow for multi-modal human connectome mapping

CMP3 implements a workflow that creates a hierarchical multi-scale
  connectome representation of the structural and functional brain systems, from any
  sMRI / dMRI / rfMRI dataset structured according to the BIDS standard, as illustrated
  by \autoref{fig:cmp3-diagram}.

CMP3's workflow relies on Nipype [@GorgolewskiNipype:2011] and adopts a modular architecture, composed
  of three different pipelines (anatomical, diffusion, and fMRI) dedicated to the processing
  of each modality (sMRI, dMRI, rfMRI).
Each pipeline is represented by a Nipype workflow that takes a BIDS formatted dataset as input, and
  runs a number of sub-workflows (stages).
Each stage can consist of one or multiple tasks, where each task can either interface with 
  a specific tool of FSL [@Jenkinson2012FSL], FreeSurfer [@Fischl2012FreeSurfer],
  ANTs [@AVANTS2008SymmetricBrain], dipy [@Garyfallidis2014DipyData],
  MRtrix3 [@mrtrix3:2019], AFNI [@Cox2012], or be fully
  implemented by CMP3 (\autoref{fig:cmp3-diagram}).
We refer the reader to the [main documentation](https://connectome-mapper-3.readthedocs.io/en/latest/bidsappmanager.html#anatomical-pipeline-stages)
  for more details about the different processing steps and parameters involved in each pipeline.
At the time EEG is being fully integrated in the workflow and in the GUI, CMP3 already provides a
  pipeline dedicated to this modality with a collection of interfaces based on MNE-Python [@GramfortEtAl2013a],
  MNE-Connectivity [@mne-connectivity:2022], and PyCartool [@PyCartool:2019].
A [tutorial notebook](https://connectome-mapper-3.readthedocs.io/en/latest/notebooks/EEG_pipeline_tutorial.html)
  in the documentation shows how one can now map the connectivity at the source level derived from
  EEG in the CMP3 framework.

To guarantee consistent processing in large neuroimaging cohorts,
  pipeline and stage parameters can be set by creating and loading pipeline
  configuration files in `.json` format.
Adopting BIDS allows CMP3 to automatically identify the structure of the input data, and to check the
  availability of sMRI, dMRI, rfMRI, and derived data.
Depending on the input data, the processing pipelines and stages are then dynamically built and configured
  based on the parameters set in the different configuration files.
Empowered by the Nipype workflow engine, the re-execution of the workflow will resume the
  processing at the stage where a change of parameter occurred, thus not needing to recompute
  outputs unaffected by the change.

To ensure reproducibility and maximize re-usability of the tool, the implemented pipelines are encapsulated
  in Docker [@merkeldocker:2014] and Singularity [@Kurtzer2017Singularity:Compute] software image
  containers, in concordance with the BIDS App framework [@GorgolewskiBIDSMethods:2017].
This means that the BIDS App of CMP3 can be run on a large diversity of datasets, on Linux, MacOSX, and Windows computers,
  and on high performance computing systems (clusters) for large-scale analysis.

![\textbf{Overview of the Connectome Mapper 3 BIDS App's workflow.}
\label{fig:cmp3-diagram}](cmp3-diagram.png)

All these design considerations make CMP3 easy to install and use (as it provides the user with a computing
  environment in which the pipelines are guaranteed to run, and where all dependencies
  are already installed), and this on a diversity of multi-modal BIDS datasets.
They also make CMP3 efficient in managing and scaling the pipeline execution while recording provenance,
  and easy to customize and extend for specific needs.

## A revisited and extended multi-scale cortical parcellation scheme

CMP3 revisits the multiscale cortical parcellation proposed by [@Cammoun2012:MappingMRI].
The parcellation derived from the Desikan-Killiany atlas [@Desikan2006AnInterest] has been
  made symmetric by projecting the right hemisphere labels to the left hemisphere, matching the
  boundaries of the projected regions of the left hemisphere to the boundaries of the original regions
  of the left hemisphere, applying this transformation to the rest of the scales, and saving
  each parcellation scale of each hemisphere in a FreeSurfer annotation file.
It also extends the parcellations with new structures including a subdivision of the thalamus into
  7 nuclei per hemisphere, of the hippocampus into 12 subfields, and of the brainstem into 4 sub-structures.
An overview and brief description of the new scheme and its integration with all the implemented pipelines
  are provided in \autoref{fig:parc}.

![\textbf{Overview of the new multi-scale parcellation scheme.}
After performing Desikan-Killiany brain parcellation [@Desikan2006AnInterest] with FreeSurfer, CMP3 resamples
  the fsaverage cortical surface onto the individual cortical surface and maps the parcellation
  annotation files to the individual space, to generate the volumetric parcellation for each scale.
Then, one can now decide whether to perform brainstem parcellation [@Iglesias2015BayesianMRI], hippocampal
  subfields segmentation [@Iglesias2015AMRI], and/or probabilistic atlas-based segmentation of the thalamic
  nuclei [@Najdenovska2018In-vivoImaging].
All segmented structures are then combined to create the final parcellation NIfTI image at each scale
  along with the corresponding label index color mapping file in accordance with the BIDS Derivatives
  specifications.
The different segmentation and parcellation outputs of the anatomical pipeline are then taken as inputs of
  the diffusion, fMRI, and EEG pipelines that estimate the structural and functional connectomes from
  raw dMRI, raw rfMRI, and preprocessed EEG data and the pairs of sub-cortical and cortical areas previously segmented.
All connectome files employ a common naming convention, based on the current
  BIDS extension proposal (BEP) 17 for generic BIDS connectivity data schema, and can be saved in a
  diversity of formats (`tsv`, `gpickle`, `mat`, `graphml`) compatible with the most popular
  software packages used in this field to perform complex network analyses (See next section
  for more details).
\label{fig:parc}](Lausanne2018_parcellation_diagram.png)

## A focus on accessibility and versatility

CMP3 takes advantage of the Traits/TraitsUI framework
  (\href{http://docs.enthought.com/traits/}{http://docs.enthought.com/traits/}) for building an
  interactive GUI, to give to pipelines and stages a graphical representation
  which is easy to understand and extend.
This has enabled the design of a GUI, which we call the `cmpbidsappmanager`, that reflects
  the modular structure of the processing workflow.
It is designed to guide and support the user in all the steps required to
  perform an analysis (\autoref{fig:gui}).

![\textbf{Graphical User Interface of the Connectome Mapper 3.}
A typical procedure to perform an analysis would consists of
  (a)   the selection of the root directory of the BIDS dataset to be analyzed,
  (b)   the creation/edition of the different pipeline configuration files,
  (c)   the configuration of the BIDS App run and its execution, and
  (d)   the inspection of stage outputs with fsleyes, freeview, mrview, or TrackVis
        depending on the tool involved in the stage.
\label{fig:gui}](cmp3-gui-paper.png)

Each pipeline can be individually configured and executed with the aid of the user-friendly
  GUI and the output of each stage can be visually reviewed, enabling the user to keep
  an eye on the data being processed, change the parameters and re-execute the pipeline
  when it is found not to be satisfactory.
In this way, CMP3 simplifies the creation of connectomes and makes it a straightforward process
  even for users not familiar with Nipype and software container technology.
Nevertheless, it still fulfils the needs of advanced users in charge of analyzing large datasets.
It offers them the possibility to tune and save all the parameters in configuration files, which
  can then be employed for running the BIDS App either with the Docker or Singularity software container engine directly,
  or with the two [lightweight Docker and Singularity wrappers](https://connectome-mapper-3.readthedocs.io/en/latest/usage.html#with-the-wrappers).

## Outputs ready to be reused in the BIDS ecosystem

CMP3 outputs follow the BIDS Derivatives specifications wherever possible,
  which facilitates the sharing of the derivatives in the BIDS App ecosystem,
  and allows the user to easily retrieve any of the files generated by CMP3
  with tools of the BIDS ecosystem such as pybids [@Yarkoni:2019].
It introduces a new BIDS entity ``atlas-<atlas_label>`` (See [proposal](https://github.com/bids-standard/bids-specification/pull/997))
  that is used in combination with the ``res-<atlas_scale>`` entity to distinguish imaging and network data derived
  from different parcellation atlases and scales (\autoref{fig:parc}).
While the BIDS-Derivatives extension to organize network data
  (See [BEP017](https://docs.google.com/document/d/1ugBdUF6dhElXdj3u9vw0iWjE6f_Bibsro3ah7sRV0GA/edit#heading=h.mqkmyp254xh6))
  is being developed, in which we are actively participating, structural and functional connectome files
  derived from the different imaging modalities are saved in multiple formats following the convention shown in \autoref{fig:parc}.
All connectomes are saved by default as graph edge lists in ``.tsv`` files, that can
  be directly analyzed using \href{https://networkx.org/documentation/stable/tutorial.html}{NetworkX} [@Hagberg:2008],
  a Python library which offers many algorithms and tools to explore graphs and compute local and global network properties.
Connectivity matrices can be exported to MATLAB as MAT-files can be fed to the
  \href{www.brain-connectivity-toolbox.net}{Brain Connectivity Toolbox} [@Rubinov:2010], which is a powerful
  toolbox containing a large selection of network measures for the characterization of brain
  connectivity datasets.
Finally, connectomes can be saved in GraphML format to interface with a lot of general purpose
  software packages for graph analysis such as \href{https://www.cytoscape.org}{Cytoscape} [@Gustavsen:2019;@Shannon:2003]
  or \href{https://www.gephi.org}{Gephi} [@Bastian:2009].
Structuring outputs as BIDS Derivatives and saving them in a range of file formats
  thus has a lot of advantages.
Not only does it ensure that the connectome files can be opened by the most popular
  software packages used in this field to perform complex network analyses, but it
  also eases the reuse of all outputs in the BIDS ecosystem.

## Developed with open science in mind

CMP3 is published under the terms of the open source 3-Clause Berkeley Software
  Distribution (3-Clause BSD) license, which allows unlimited modification, redistribution
  and commercial use in source and binary forms, as long as the copyright notice is retained, and the
  license's disclaimers of warranty are maintained.
The source code for CMP3 is hosted at
  [https://github.com/connectomicslab/connectomemapper3](https://github.com/connectomicslab/connectomemapper3),
  where all bugs and contributions are transparently discussed and managed through issues, and each release is
  published to the [Python Package Index (PyPI)](https://pypi.org/project/connectomemapper/) and archived to Zenodo [@ZenodoCMP:2022].
In case of problems, CMP3 has a dedicated forum at
  [groups.google.com/group/cmtk-users](https://groups.google.com/group/cmtk-users) where a
  community of users is active to support each other and have scientific discussions.
To be robust to adverse code changes, versions are released through continuous integration building
  and testing.
Specifically, this involves testing the installation of the Python package, the build of
  the Docker and Singularity container images, the execution of the BIDS App via the different container
  images adopting multiple pipeline configurations, using a sample multi-modal MRI dataset [@Tourbier2020SampleDataset]
  that has been created for this purpose, the publication of the new version of the Python package to PyPI, and
  the deployment of the container images to [DockerHub](https://hub.docker.com/r/sebastientourbier/connectomemapper-bidsapp) and
  [Sylabs Cloud](https://cloud.sylabs.io/library/connectomicslab/default/connectomemapper-bidsapp).
Doing so, we can guarantee the full functionality of each newly released version of CMP3
  for a range of different use cases.
More details about CMP3, the different processing steps and generated outputs together with
  installation and usage instructions, different tutorials supporting the analysis,
  and the interpretation of the generated outputs with popular tools, can be found in
  the documentation ([connectome-mapper-3.readthedocs.io](https://connectome-mapper-3.readthedocs.io))
  that is kept up to date with the current release and can be retrieved for older versions.

# Community impact

CMP3 has been successfully employed in a number of methodological
  [@AkselrodHBM:2021;@GlombNet:2020;@GlombNeuro:2020;@PascucciNet:2021;@RueQueraltNeuro:2021;@Zheng2020GeometricConnectomeb], clinical [@Carboni:2019;@CarboniNeuro:2020;@Carboni:2022;@Vorderwulbecke2020High-densityPoint], and data [@Pascucci2022;@ds003505:1.1.1] research articles.
CMP3 is part of the [BIDS Apps](https://bids-apps.neuroimaging.io/apps/), and also part of [`ReproNim/containers`](https://github.com/ReproNim/containers),
  a DataLad dataset with a collection of 40 popular containerized neuroimaging research pipelines,
  which allows one to easily include it as a subdataset within DataLad-controlled BIDS datasets,
  and achieve fully reproducible analysis by running CMP3 directly with DataLad.

# Acknowledgements

This work was supported by Swiss National Science Foundation Sinergia
  [grant no. 170873](https://p3.snf.ch/project-170873).
  Katharina Glomb's involvement was also supported by DFG Priority Program "SPP DBS RI 2073/10-2". 
M. Anıl Tuncel's involvement was supported by funding to the Blue Brain Project, a research center
  of the École polytechnique fédérale de Lausanne (EPFL), from the Swiss government’s ETH Board of
  the Swiss Federal Institutes of Technology.
All the contributors listed in the project’s Zenodo and GitHub repository have contributed code and
  intellectual labor to further improve CMP3.

# References
