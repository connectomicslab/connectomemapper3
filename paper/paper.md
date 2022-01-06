---
title: 'Connectome Mapper 3: A Flexible and Open-Source Pipeline Software for Multiscale Multimodal Human Connectome Mapping'
tags:
  - Python
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
    orcid: 0000-0001-5680-4540
    affiliation: 1
  - name: Katharina Glomb
    orcid: 0000-0002-4596-4386
    affiliation: 1
  - name: Yasser Aleman-Gomez
    orcid: 0000-0001-6067-8639
    affiliation: 1
  - name: Emeline Mullier
    orcid: 0000-0001-6209-0791
    affiliation: 1
  - name: Alessandra Griffa
    orcid: 0000-0003-1923-1653
    affiliation: 2
  - name: Mikkel Schöttner
    affiliation: 1
  - name: Jonathan Wirsich
    orcid: 0000-0003-0588-9710
    affiliation: 3
  - name: Patric Hagmann
    orcid: 0000-0002-4441-899X
    affiliation: 1
affiliations:
 - name: Radiology Department, Centre Hospitalier Universitaire Vaudois and University of Lausanne (CHUV-UNIL), Switzerland
   index: 1
 - name: Medical Image Processing Lab (MIP:Lab), Ecole Polytechnique Federale de Lausanne (EPFL), Switzerland
   index: 2
 - name: Departement des Neurosciences Cliniques, University of Geneva, Switzerland
   index: 3
date: 14 December 2021
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
# aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
# aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Statement of Need

The field of Magnetic Resonance (MR) Connectomics has rapidly expanded since its advent 
  in the 2000s [@SpornsTheBrain:2005], [@HagmannFromConnectomics:2005], [@SpornsEditorialConnectomics:2018].
It has revolutionized the way to investigate `in-vivo`, `non-invasively` and 
  `safely` at different macroscopic scales the structural and functional systems of the 
  brain by modeling connections between brain areas as a graph or network, the so-called
  `connectome`.

While brain areas are usually derived from high resolution T1 weighted  MR imaging, so-called
  structural MRI (sMRI), structural brain connectomes are mapped from diffusion MR imaging (dMRI)
  tractography, which exploits the diffusion of water molecules in biological tissues, and
  functional brain connectomes are usually mapped from resting-state functional MRI (rfMRI), which exploits
  the blood oxygen-level dependent (BOLD) signals of the different regions at rest.
As MRI is being increasingly more accessible and used in both clinical and research settings,
  such multi-modal MR datasets are being gathered at an unprecedented rate.
The size and organization of these datasets as well as the increasing complexity of the processing
  pipelines to analyze them present important challenges for scalable computing, data sharing,
  reproducibility and transparency of the analysis.

The last ten years have indeed witnessed a trend towards the adoption by the community of open research
  practices, which promotes `open data` and `open method`, to not only address these challenges, but also
  due to the evolution of research incentives.
This has led for instance to the elaboration of the principles of open and reproducible research for
  neuroimaging using Magnetic Resonance Imaging (MRI) [@Nichols:2017] and to the recommendation of
  standard practices for sharing code and programs [@EglenTowardNeuroscience:2017]. 
To ease and automate the practice of sharing raw and processed neuroimaging data and code with
  appropriate metadata and provenance records, multiple initiatives have developed new standards,
  tools, and educational resources [@GorgolewskiNipype:2011] [@GorgolewskiTheExperiments:2016]
  [@GorgolewskiBIDSMethods:2017].

Following these advances, a number of processing pipelines, supporting the mapping of connectomes
  derived from MRI data organized following the BIDS standard, such as C-PAC [@cpac:2013],
  NIAK [@BellecNeuroimagingNIAK:2016], fMRIPrep [@Ghosh:2018],
  dMRIPrep [@dmriprep:2019], QSIPREP [@CieslakQSIPrep:2020], MRtrix3_connectome [@Smith2019:BIDSApp],
  NDMG [@KiarAVariability:2018] and PyNets [@PisnerPyNets:2020] have been developed .
They have demonstrated their capability in addressing all the challenges of data sharing,
  portability, computing scalability, reliability, reproducibility and transparency.
However, none of the existing solutions provide a direct alternative to Connectome Mapper (CMP)
  whose has been created before the emergence of the BIDS standards and the containerization technologies
  to simplify the organisation and the analysis of sMRI and dMRI from raw data to multi-scale
  structural weighted connectomes [@Daducci:2012] using the in-house multi-scale Lausanne brain parcellation
  scheme [@Cammoun2012:MappingMRI], extended in a second version release with a preliminary pipeline
  for resting-state fMRI for integrative multimodal analyses.
While CMP3 derives from the preceding two versions, it has made CMP massively evolve over the years
  in terms of the underlying codebase, the tools used, and the scope of the functionality provided, including
  the migration to Python 3, a brand-new Lausanne parcellation scheme, the adoption of the BIDS standard for
  data organization, the encapsulation of the processing pipelines have been encapsulated in software container images, continuously tested in concordance to the
  BIDS Apps standard, the refinement of the fMRI pipeline, and the current extension to
  Electroencephalography (EEG). 

# Summary

Connectome Mapper 3 provides a unique open-source software pipeline solution with a Graphical User Interface
  (GUI) for researchers to easily, reliably and transparently create a hierarchical multi-scale
  connectome representation of the structural and functional brain systems, on any sMRI / dMRI /
  rfMRI / EEG dataset structured according to the BIDS standard, by interfacing with a number
  of widely adopted neuroimaging tools (inclusing FSL [@Jenkinson2012FSL], FreeSurfer [@Fischl2012FreeSurfer],
  ANTs [@AVANTS2008SymmetricBrain], dipy [@Garyfallidis2014DipyData], mrtrix3 [@Tournier2019MRtrix3:Visualisation],
  AFNI [@Cox2012]), pycartool [@pycartool], and MNE [@GramfortEtAl2013a].
It has been developed around different principles and characteristics that are presented right after.

Design considerations with the implementation of modular, configurable, and containerized
  processing pipelines, empowered by nipype, handling datasets concordant to the BIDS standard,
  distributed as a BIDS App, makes it not only easy to install and use (as it provides the user with a computing
  environment in which the pipelines are guarantee to run, and where all dependencies
  are already installed) on a diversity of multi-modal BIDS datasets, but also efficient in managing and scaling the pipeline execution
  while recording provenance, and easy to customize it for specific needs.
Each pipeline can be individually configured and executed with the aid of the user-friendly
  GUI and the output of each stage can be visually reviewed, enabling the user to keep
  an eye on the data being processed and easily understand the cause of the problems, change the
  parameters and re-execute when results are unsatisfactory.
Outputs are organized following a BIDS derivatives-like structure where connectome files
  can be exported to a number of formats, such that not only connectomes can be opened by
  the most popular software packages used in this field to perform complex network
  analyzes, but also to facilitate the sharing of the derivatives in the BIDS App
  ecosystem.

# Highlights

\textbf{A unique parcellation scheme in the BIDS ecosystem.}

\textbf{A flexible workflow for multi-modal human connectome mapping in the BIDS ecosystem.} CMP3 is
  written in Python 3 and implements pipelines that maps the structural and
  / or functional connectomes from sMRI / dMRI and / or fMRI, for five macroscopic brain parcellation scales with hierarchical
  region grouping.
\autoref{fig:cmp3-diagram} illustrates the participant-level analysis workflow.

![\textbf{Overview of participant-level analysis workflow of the Connectome Mapper 3 BIDS App.}
It has a modular architecture composed of three different pipelines (anatomical, diffusion and
  fMRI) dedicated to each modality (sMRI, dMRI and rfMRI).
Each pipeline handles datasets organized following the Brain Imaging Data Structure standard and
  consists of a number of processing stages implementing one or multiple specific tasks of the
  workflow, where each task interfaces with a specific tool, empowered by the nipype dataflow
  library, to computes, from raw MRI data, brain parcellation and corresponding structural and/or
  functional connectivity maps at 5 different scales using the Lausanne2018 hierarchical scheme.
BIDS allows CMP3 to automatically identify the structure of the input data, to check the
  availability of sMRI, dMRI, rfMRI, and derived data, and to collect all the available acquisition
  metadata.
The processing pipelines and stages are dynamically built and configured depending on the input
  data (sMRI, dMRI, rfMRI) and parameters set in the configuration files.
This enables CMP3 to self-adapt to the type of dMRI acquisition scheme (DTI, DSI, multi-shell) and
  to appropriately set up the set of available pipeline configuration parameters for its processing.
\label{fig:cmp3-diagram}](cmp3-diagram.png)

The workflow  is implemented with nipype [@GorgolewskiNipype:2011] adopting an object-oriented programming style
  with a modular architecture, composed of three different pipeline classes (anatomical, diffusion, and fMRI) dedicated to the processing of
  each modality (sMRI, dMRI, rfMRI).
Each pipeline class provides methods to create and execute a nipype workflow that runs a number of
  nipype sub-workflows, described by stage classes and implementing one or multiple tasks,
  where each task can interface with either a specific tool including in
  FSL [@Jenkinson2012FSL], FreeSurfer [@Fischl2012FreeSurfer],
  ANTs [@AVANTS2008SymmetricBrain], dipy [@Garyfallidis2014DipyData],
  mrtrix3 [@Tournier2019MRtrix3:Visualisation], AFNI [@Cox2012], or with an in-house tool
  (\autoref{fig:cmp3-diagram}); Pipeline and stage object attributes (parameters)
  can be set by loading pipeline configuration files in `.json` format.
Empowered by the nipype workflow engine, the re-execution of the workflow will resume the
  processing at any stages a change of parameter occurred.
To ensure reproducibility and maximize re-usability of the tool, the implemented pipelines are encapsulated
  in a Docker [@merkeldocker:2014] and a Singularity [@Kurtzer2017Singularity:Compute] software image
  containers, in concordance to the BIDS App standard [@GorgolewskiBIDSMethods:2017].
This means that the BIDS App of CMP3 can be run on diversity of datasets Linux, MacOSX, Windows computers,
  and on high performance computing systems (clusters) for large-scale analysis.

\textbf{A Graphical User Interface that reflects the workflow structure.} CMP3 takes advantage of Traits/TraitsUI
  framework (\href{http://docs.enthought.com/traits/}{http://docs.enthought.com/traits/}) for building an
  interactive Graphical User Interface (GUI), where pipeline and stage class attributes (parameters) are
  represented as Traits objects with TraitsUI graphical representations, which makes it easier to understand
  and extend.
This has enabled the design of a GUI aka `cmpbidsappmanager` (Figure \autoref{fig:gui}) that reflects
  the modular structure of the processing workflow. It has been designed to facilitate the configuration of all pipeline stages,
  to guarantee the formatting of the `.json` pipeline configuration files (Figure \autoref{fig:gui} b),
  to support their execution within the BIDS App (Figure \autoref{fig:gui} c), and to allow seamless
  inspection of stage outputs with native visualization tools bundled with each software package
  involved in the processing stage (Figure \autoref{fig:gui} d).
In particular, all sMRI are inspected with the fsleyes viewer shipped with fsl, brain tissue
  segmentation and parcellation are inspected with freeview, mrview is used to visualize the fiber
  orientation distribution functions estimated by the diffusion signal model, and TrackVis is used
  to visualize the fiber bundles estimated with tractography.
If the outputs at a given stage are found not to be satisfactory, the GUI offers the possibility to
  easily tune any parameter specific to this stage, regenerate the configuration file and repeat
  the BIDS App execution.

![\textbf{Graphical User Interface of the Connectome Mapper 3.}
It is designed to bring the best experience to the final user by facilitating all the steps
 required to perform an analysis.
A typical procedure would consists of
  (a) the selection of the root directory of the BIDS dataset to be analyzed,
  (b) the creation/edition of the different pipeline configuration files,
  (c) the configuration of the BIDS App run and its execution, and
  (d) the inspection of stage outputs using either fslview or freeview or mrview or trackvis
  depending on the software involved in the stage.
Connectivity matrices are visualized using the matplotlib library. \label{fig:gui}](cmp3-gui-paper.png)

\textbf{Connectome mapping outputs ready to be consumed in the BIDS ecosystem.}
  CMP3 outputs follow as close as possible the BIDS
  Derivatives specifications, which allows the user to easily retrieve any of the files generated by CMP3
  with tools of the BIDS ecosystem such as pybids [@Yarkoni:2019].
While the BIDS-Derivatives extension to organize network data is being developed, in which we
  are actively participating, both structural and functional connectomes generated with CMP3 are
  saved by default in `.tsv` files and as graph objects with Python pickle format,
  that can be directly analyzed using the
  \href{https://networkx.org/documentation/stable/tutorial.html}{NetworkX} Python library, which
  offers many general purpose algorithms to explore graphs as well as tools to compute local and
  global network properties.
Connectivity matrices can also be exported to Matlab as MAT-files and fed to the
  \href{www.brain-connectivity-toolbox.net}{Brain Connectivity Toolbox}, which is a powerful
  toolbox containing a large selection of network measures for the characterization of brain
  connectivity datasets.
Finally, connectomes can be saved in generic file formats such as GraphML, GML and DOT to
  interface with a lot of general purpose software packages for graph analysis such as
  \href{www.cytoscape.org}{Cytoscape} or \href{www.gephi.org}{Gephi}.
The full documentation of the outputs can be found on the
  \href{https://connectome-mapper-3.readthedocs.io/en/latest/outputs.html}{documentation website}.

\textbf{Developed with openness, transparency, and good practices in mind.}
  CMP3 is published under the terms of the open source 3-Clause Berkeley Software
  Distribution (3-Clause BSD) license, which allows unlimited modification, redistribution
  and commercial use in source and binary forms as long as its copyright notices, and the
  license's disclaimers of warranty are maintained.
The source code for CMP3 is hosted at
  [https://github.com/sebastientourbier/connectomemapper3](https://github.com/sebastientourbier/connectomemapper3),
  and each release is archived to Zenodo [@ZenodoCMP:2021].
To be robust to adverse code changes, versions are released through continuous integration building
  and testing.
Specifically, this involves testing the installation of the python package, the build of
  the Docker and Singularity container images, and the execution of the BIDS App via the different container
  images adopting multiple pipeline configurations, using a sample multi-modal MRI dataset [@Tourbier2020SampleDataset]
  that has been created for this purpose.
Doing so, we can guarantee the full functionality of each new released version of CMP3.
A detailed documentation is available
  at [connectome-mapper-3.readthedocs.io](connectome-mapper-3.readthedocs.io) that is
  kept up to date with the current release and can be retrieved for older versions.
It includes in particular step-by-step guides for installation and usage together with the
  description of all processing steps and
  \href{https://connectome-mapper-3.readthedocs.io/en/latest/outputs.html}{generated outputs}.
In case of problems, CMP3 has a dedicated forum at
  [groups.google.com/group/cmtk-users](groups.google.com/group/cmtk-users) where a
  community of users is active to support and have scientific discussions.
Furthermore, bugs as well as both internal and external developer contributions are
  discussed and managed through issues directly on GitHub for transparent software
  development.

\textbf{A unique new generation connectome mapping tool highly flexible and extendable.}
  While CMP3 simplifies the creation of connectomes and makes it a straightforward process
  even for users not familiar with nipype and software container technology, it fulfils
  at the same time the needs of advanced users in charge of analyzing huge amount of data,
  offering them the possibility to tune and save all the parameters in configuration files and create a batch
  job to automatically process all data with the BIDS App.
CMP3 can be highly versatile as it offers a number of options at each processing steps to
  be completely data agnostic.
At the same time, it provides the user with a very efficient framework to compute
  connectomes in the way it guides them through all the steps and options involved in their
  creation, and it guarantees seamless processing, irrespective of the choices made.
In addition, the very flexible framework of CMP3 enables the addition of new steps, stages
  or pipelines with relatively little effort to account for additional imaging modalities
  and algorithms.
It is worth noting the software is ready to accommodate other imaging modalities.
At the time of writing, an EEG source imaging pipeline is being integrated, initiated during OHBM BrainHack 2020
  ([https://github.com/ohbm/hackathon2020/issues/214](https://github.com/ohbm/hackathon2020/issues/214)),
  which will make CMP3 even more unique in the new generation of connectome mapping tools.


# Mention

Connectome Mapper 3 has already been employed with success in a number of methodological
  and clinical research articles [@Carboni2019TheOutcome] [@Zheng2020GeometricConnectomeb]
  [@Vorderwulbecke2020High-densityPoint] [@CarboniNeuro:2020] [@GlombNeuro:2020] [@GlombNet:2020]
  [@AkselrodHBM:2021] [@RueQueraltNeuro:2021] [@PascucciNet:2021] [@ds003505:1.0.1].

# Acknowledgements

This work was supported by Swiss National Science Foundation Sinergia
  [grant no. 170873](https://p3.snf.ch/project-170873).
All the contributors listed in the project’s Zenodo and GitHub repository have contributed code and
  intellectual labor to further improve CMP3.
The same holds true for users that reported issues and continue to do so.

# References
