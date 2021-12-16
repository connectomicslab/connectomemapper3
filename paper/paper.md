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
  functional brain connectomes are mapped usually from functional MRI (fMRI), which exploits
  the blood oxygen-level dependent (BOLD) signals of the different regions, typically at rest.
As MRI is being increasingly more accessible and used in both clinical and research settings,
  such multi-modal MR datasets are being gathered at an unprecedented rate.
The size and organization of these datasets as well as the increasing complexity of the processing
  pipelines to analyze them present important challenges for scalable computing, data sharing,
  reliability, reproducibility and transparency of the analysis.

The last ten years have indeed witnessed a trend towards the adoption by the community of open research
  practices, which promotes `open data` and `open method`, to address these challenges.
This has led to the elaboration of the principles of open and reproducible research for
  neuroimaging using Magnetic Resonance Imaging (MRI) [@Nichols:2017] and to recommendation of
  standard practices for sharing code and programs [@EglenTowardNeuroscience:2017]. 
To ease and automate
  the practice of sharing raw and processed neuroimaging data and code with appropriate metadata
  and provenance records, multiple initiatives have developed new standards, tools, and educational
  resources.
Among others, this has contributed to the emergence of
  nipype [@GorgolewskiNipype:2011], a dataflow library that facilitates workflow
  execution/re-execution, provenance tracking and provides a uniform interface to existing
  neuroimaging softwares; the Brain Imaging Data Structure (BIDS)
  standard [@GorgolewskiTheExperiments:2016], to standardize the organization and description
  of neuroimaging data; Datalad a data portal, versioning, and provenance tracking system
  supporting BIDS; and more recently, the BIDS-Apps framework [@GorgolewskiBIDSMethods:2017],
  which employs modern software practices and encapsulates a processing
  pipeline that takes a BIDS dataset as input into a software container in order to improve
  the ease of use, accessibility, deliverability, portability, scalability and reproducibility
  of processing pipelines. 

Following these advances, a number of processing pipelines such as C-PAC [@cpac:2013],
  NIAK [@BellecNeuroimagingNIAK:2016], fMRIPrep [@Ghosh:2018],
  dMRIPrep [@dmriprep:2019], QSIPREP [@CieslakQSIPrep:2020], NDMG [@KiarAVariability:2018] and PyNets
  [@PisnerPyNets:2020] have been developed to support the mapping of connectomes derived from
  MRI data organized following the BIDS standard.
They have demonstrated their capability in addressing all the challenges of data sharing,
  portability, computing scalability, reliability, reproducibility and transparency.
However, none of the existing solutions provides a user-friendly graphical interface
  that would enhance their accessibility and are designed to map from sMRI / dMRI / fMRI
  the structural and / or functional connectomes, for five macroscopic brain parcellation
  scales with hierarchical region grouping.

# Summary

Connectome Mapper 3 provides a unique open-source software pipeline solution with a Graphical User Interface
  (GUI) for researchers to easily, reliably and transparently create a hierarchical multi-scale
  connectome representation of the structural and functional brain systems, on any sMRI / dMRI /
  rfMRI dataset structured according to the BIDS standard, by interfacing with a number of popular
  neuroimaging tools (inclusing FSL [@Jenkinson2012FSL], FreeSurfer [@Fischl2012FreeSurfer],
  ANTs [@AVANTS2008SymmetricBrain], dipy [@Garyfallidis2014DipyData],
  mrtrix3 [@Tournier2019MRtrix3:Visualisation], and AFNI [@Cox2012]).
While CMP3 derives from the now deprecated CMP1 and CMP2 packages[@Daducci:2012], whose original main
  goals were to simplify the organisation and the analysis of sMRI and dMRI from raw data to
  multi-scale structural weighted connectomes, it has evolved massively over the years in terms
  of the underlying codebase, the tools used, and the scope of the functionality provided.
Design considerations with the implementation of modular, configurable, and containerized
  processing pipelines, empowered by nipype, handling datasets concordant to the BIDS standard,
  distributed as a BIDS App, makes it not only easy to install and use (as it provides the user with a computing
  environment in which the pipelines are guarantee to run, and where all dependencies
  are already installed), but also efficient in managing and scaling the pipeline execution
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

While CMP3 simplifies the creation of connectomes and makes it a straightforward process
  even for users not familiar with nipype and software container technology, it fulfils
  at the same time the needs of advanced users in charge of analyzing huge amount of data, offering them the
  possibility to tune and save all the parameters in configuration files and create a batch
  job to automatically process all data with the BIDS App.
CMP3 can be highly versatile as it offers a number of options at each processing steps to
  be completely data agnostic.
At the same time, it provides the user with a very efficient framework to compute
  connectomes in the way it guides them through all the steps and options involved in their
  creation, and it guarantees seamless processing, irrespective of the choices made.
In addition, the very flexible framework of CMP3 enables the addition of new steps, stages
  or pipelines with relatively little effort to account for additional imaging modalities
  and algorithms.
It is worth noting the software is ready to accommodate other imaging modalities
  such as the current integration of an EEG source imaging pipeline initiated at OHBM BrainHack 2020
  ([https://github.com/ohbm/hackathon2020/issues/214](https://github.com/ohbm/hackathon2020/issues/214)),
  which makes CMP3 an ideal to be further developed into the next generation brain connectivity mapping tools.

# Design considerations

CMP3 is written in Python and adopts an object-oriented programming style for the sake of modularity, extensibility,
  and re-usability.
It uses Miniconda (\href{https://docs.conda.io}{https://docs.conda.io}),
  a package and environment manager, to facilitate the installation of the Python environment with
  all package dependencies installed inside, that is particularly powerful at two levels.
It provides a way to ease the installation of python package dependencies at a fixed version for
  both the processing core inside the BIDS App and the GUI on the host system.
It also provides a way to isolate the installation of CMP3 with other python dependencies.
This prevents conflicts with other package versions that might exist already on the host system.

\textbf{A modular and flexible workflow in the BIDS ecosystem} The implemented participant-level analysis workflow is represented in
  nipype [@GorgolewskiNipype:2011] with a modular structure, composed of three different
  pipeline classes (anatomical, diffusion, and fMRI) dedicated to the processing of each
  modality (sMRI, dMRI, rfMRI), which takes as principal inputs the path of the BIDS dataset
  to be processed, and a pipeline configuration file.
Each pipeline class provides methods to create and execute a nipype workflow that runs a number of
  nipype sub-workflows, described by stage classes and implementing one or multiple tasks,
  where each task can interface with either a specific tool including in
  FSL [@Jenkinson2012FSL], FreeSurfer [@Fischl2012FreeSurfer],
  ANTs [@AVANTS2008SymmetricBrain], dipy [@Garyfallidis2014DipyData],
  mrtrix3 [@Tournier2019MRtrix3:Visualisation], AFNI [@Cox2012], or with an in-house tool
  (see Figure \autoref{fig:cmp3-diagram}); Pipeline and stage object attributes (parameters)
  can be set from configuration files in `.json` format.
Empowered by the nipype workflow engine, the re-execution of the workflow will resume the
  processing at any stages a change of parameter occurred.
To maximize software accessibility, interoperability, portability and reproducibility, the
  implemented pipelines are encapsulated in a Docker [@merkeldocker:2014]
  and a Singularity [@Kurtzer2017Singularity:Compute] software image containers in concordance to the BIDS
  App standard [@GorgolewskiBIDSMethods:2017]. This means that the BIDS App of CMP3 can be run on diversity
  of datasets Linux, MacOSX, Windows computers, and on high performance computing systems (clusters)
  for large-scale analysis.


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

\textbf{A Graphical User Interface that reflects the worklow structure} CMP3 takes advantage of Traits/TraitsUI framework
  (\href{http://docs.enthought.com/traits/}{http://docs.enthought.com/traits/}) for building an
  interactive Graphical User Interface (GUI), where pipeline and stage
  class attributes (parameters) are represented as Traits objects with TraitsUI graphical
  representations, which makes it easier to understand and extend.
This has enabled the design of a GUI aka `cmpbidsappmanager` (Figure \autoref{fig:gui}) that reflects
  the structure of the processing workflow and that facilitates the configuration of all pipeline stages
  and guarantees the formatting of the `.json` pipeline configuration files (Figure \autoref{fig:gui} b),
  supports their execution within the BIDS App (Figure \autoref{fig:gui} c), and the inspection of stage
  outputs with native visualization tools bundled with each software package
  involved in the processing stage as the end user might be already very familiar with these tools
  (Figure \autoref{fig:gui} d).
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

\textbf{Highly reusable connectome mapping outputs} CMP3 outputs follow as close as possible the BIDS Derivatives specifications,
  which allows the user to easily retrieve any of the files generated by CMP3
  with tools of the BIDS ecosystem such as pybids [@Yarkoni:2019].
The data derived from the processing of one subject are placed in a \texttt{sub-<participant\_id>/}
  folder.
Derivatives are also kept in separate folders to distinguish main CMP3 outputs (`cmp-<version>/`) from outputs
  produced by FreeSurfer (`freesurfer-<version>/`) and from all intermediate workflow outputs
  (`nipype-<version>/`), where `<version>` indicates the version of each tool as specified by the
  BIDS Derivatives specifications.
Main sMRI-, dMRI-, and rfMRI-derived data, which includes preprocessed data, brain parcellations,
  tractograms and connectivity matrices, are saved into their respective anat/, dwi/, and func/
  folder, and which contains sub-\textless subject\_label\textgreater\_log.txt. a log file that
  summarizes output execution.
All intermediate outputs generated by nipype interfaces can be found in their respective {\textless
  pipeline\_name\textgreater/ \textless stage\_name\textgreater/ \textless
  interface\_name\textgreater} folders, which contains among others execution report in the
  {\textless interface\_name\textgreater} folder and the pipeline execution graph in the {\textless
  pipeline\_name\textgreater/} folder.
While the BIDS-Derivatives extension to organize network data is being developed, in which we
  are actively participating, both structural and functional connectomes generated with CMP3 are
  saved by default as graph objects in Python pickle format that can be directly analysed using the
  \href{https://networkx.org/documentation/stable/tutorial.html}{NetworkX} Python library, which
  offers many general purpose algorithms to explore graphs as well as tools to compute local and
  global network properties.
Connectivity matrices can also be exported to Matlab as MAT-files and fed to the
  \href{www.brain-connectivity-toolbox.net}{Brain Connectivity Toolbox}, which is a powerful
  toolbox containing a large selection of network measures for the characterization of brain
  connectivity datasets.
Finally, connectome data can be saved in generic file formats such as GraphML, GML and DOT to
  interface with a lot of general purpose software packages for graph analysis such as
  \href{www.cytoscape.org}{Cytoscape} or \href{www.gephi.org}{Gephi}.
The full documentation of the outputs can be found on the
  \href{https://connectome-mapper-3.readthedocs.io/en/latest/outputs.html}{documentation website}.
}

\textbf{Open-source software development practices} CMP3 is developed with openness and transparency in mind.
The software is published under the terms of the open source 3-Clause Berkeley Software
  Distribution (3-Clause BSD) license, which allows unlimited modification, redistribution
  and commercial use in source and binary forms as long as its copyright notices, and the
  license's disclaimers of warranty are maintained.
The source code for `Connectome Mapper 3` is hosted at
  [https://github.com/sebastientourbier/connectomemapper3](https://github.com/sebastientourbier/connectomemapper3),
  and archived to Zenodo [@ZenodoCMP:2021].
To be robust to adverse code changes, versions are released through continuous integration building
  and testing using a sample multi-modal MRI dataset [@Tourbier2020SampleDataset] that we created
  for this purpose. Specifically, this involves testing the installation of the python package, the build of
  the Docker and Singularity container images, and the execution of the BIDS App via the container
  images with multiple configurations, to guarantee the full functionality of each new version release.
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

# Mention

Connectome Mapper 3 was successfully employed in

*   2021 - VEPCON: Source imaging of high-density visual evoked potentials with multi-scale brain parcellations and connectomes
    In press, Scientific Data Nature
    https://www.biorxiv.org/content/10.1101/2021.03.16.435599v1.abstract
    
*   2021 - The connectome spectrum as a canonical basis for a sparse representation of fast brain activity
    https://www.sciencedirect.com/science/article/pii/S1053811921008843
    
*   2021 - Relation between palm and finger cortical representations in primary somatosensory cortex: A 7T fMRI study
    https://onlinelibrary.wiley.com/doi/10.1002/hbm.25365

*   2020 - Using structural connectivity to augment community structure in EEG functional connectivity
    https://direct.mit.edu/netn/article/4/3/761/95852/Using-structural-connectivity-to-augment-community

*   2020 - Connectome spectral analysis to track EEG task dynamics on a subsecond scale
    https://www.sciencedirect.com/science/article/pii/S1053811920306236

*   2020 - Abnormal directed connectivity of resting state networks in focal epilepsy
    https://www.sciencedirect.com/science/article/pii/S221315822030173X#bi005
    
*   2020 - High-density Electric Source Imaging of interictal epileptic discharges: How many electrodes and which time point?
    https://www.sciencedirect.com/science/article/pii/S1388245720304934#bi005
    
*   2020 - Geometric renormalization unravels self-similarity of the multiscale human connectome
    https://www.pnas.org/content/117/33/20244
    
*   2019 - The network integration of epileptic activity in relation to surgical outcome
    https://www.sciencedirect.com/science/article/pii/S1388245719312258
    
# Acknowledgements

This work was supported by Swiss National Science Foundation Sinergia
  [grant no. 170873](https://p3.snf.ch/project-170873).

# References
