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
    orcid: 0000-0002-4521-9837 
    affiliation: 1
  - name: Jonathan Wirsich
    orcid: 0000-0003-0588-9710
    affiliation: 3
  - name: Anil Tuncel
    orcid: 0000-0003-0317-2556
    affiliation: 4
  - name: Jakub Jancovic
    orcid: 0000-0002-3312-3918
    affiliation: 5
  - name: Meritxell Bach Cuadra
    affiliation: 3,6
    orcid: 0000-0003-2730-4285
  - name: Patric Hagmann
    orcid: 0000-0002-2854-6561
    affiliation: 1
affiliations:
 - name: Radiology Department, Centre Hospitalier Universitaire Vaudois and University of Lausanne (CHUV-UNIL), Switzerland
   index: 1
 - name: Medical Image Processing Lab (MIP:Lab), Ecole Polytechnique Federale de Lausanne (EPFL), Switzerland
   index: 2
 - name: Departement des Neurosciences Cliniques, University of Geneva, Switzerland
   index: 3
 - name: Blue Brain Project, BBP-CORE, Ecole Polytechnique Federale de Lausanne (EPFL), Switzerland
   index: 4
 - name: Foxight, Geneva, Switzerland
   index: 5
 - name: CIBM Center for Biomedical Imaging, Geneva, Switzerland
   index: 6
date: 02 February 2021
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
# aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
# aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Statement of Need

The field of Magnetic Resonance Imaging (MRI) Connectomics has rapidly expanded since its advent 
  in the 2000s [@SpornsTheBrain:2005], [@HagmannFromConnectomics:2005], [@SpornsEditorialConnectomics:2018].
It has revolutionized the way to investigate `in-vivo`, `non-invasively` and 
  `safely` at different macroscopic scales the structural and functional systems of the 
  brain by modeling connections between brain areas as a graph or network, the so-called
  `connectome`, and has become a widely used method in Neuroscience [@Bassett2017]. 
While brain areas are usually derived from high resolution structural T1 weighted MRI (sMRI),
  structural brain connectomes are mapped from diffusion MR imaging (dMRI) tractography, and
  functional brain connectomes are usually mapped from resting-state functional MRI (rfMRI).
As MRI is being increasingly more accessible and used in both clinical and research settings,
  such multi-modal MRI datasets are being gathered at an unprecedented rate.
The size and organization of these datasets as well as the increasing complexity of the processing
  pipelines to analyze them present important challenges for scalable computing, data sharing,
  reproducibility and transparency of the analysis.

The last ten years have indeed witnessed a number of technical advances and a trend towards the adoption
  by the community of open research practices, which promotes `open data` and `open method`,
  to address these challenges [@Nichols:2017] [@EglenTowardNeuroscience:2017] [@Kennedy2019].
This has led in particular to the creation of a community standard, known as the Brain Imaging Data Structure (BIDS),
  initially designed to ease the practice of sharing raw MRI data [@GorgolewskiTheExperiments:2016]. 
[@GorgolewskiBIDSMethods:2017].
Combined with advances in software virtualization, BIDS has enabled the creation of the BIDS Apps
  framework which uses software container technology to encapsulate neuroimaging processing pipelines
  and ensure portability and reproducibility.
A large ecosystem of processing pipelines supporting the mapping of connectomes has evolved around this framework,
  including C-PAC [@cpac:2013], NIAK [@BellecNeuroimagingNIAK:2016], fMRIPrep [@Ghosh:2018], dMRIPrep [@dmriprep:2019],
  QSIPREP [@CieslakQSIPrep:2020], MRtrix3_connectome [@Smith2019:BIDSApp], NDMG [@KiarAVariability:2018]
  and PyNets [@PisnerPyNets:2020], which have all demonstrated their capability in addressing all the previously-mentioned
  challenges.
However, none of the existing solutions provide a direct alternative to Connectome Mapper.

Connectome Mapper (CMP) is an open-source pipeline software with a graphical user interface, designed
  to simplify the organisation and the analysis of sMRI, dMRI, and rfMRI from raw data to multi-scale
  structural weighted and functional connectomes [@Daducci:2012], using in a common framework
  a multi-scale extension of the Desikan-Killiany parcellation [@Desikan2006AnInterest],
  the so-called Lausanne brain parcellation [@Cammoun2012:MappingMRI], before the emergence of BIDS.
While CMP3 derives from the two preceding versions and keeps the same philosophy, it has made CMP massively
  evolve over the years in terms of the underlying codebase, the tools used, and the scope of the functionality
  provided, including the migration to Python 3, a brand-new Lausanne parcellation scheme, the adoption
  of the BIDS standard for data organization, the encapsulation of the processing pipelines in software
  container images, continuously tested in concordance to the BIDS Apps standard, major upgrades of the diffusion and
  fMRI pipelines, and the current extension to Electro-EncephaloGraphy (EEG), initiated during OHBM BrainHack 2020
  ([https://github.com/ohbm/hackathon2020/issues/214](https://github.com/ohbm/hackathon2020/issues/214)).
CMP3 has been designed around different characteristics and principles along which it is summarized
  in this manuscript.

# Summary

\textbf{A flexible and interoperable workflow for multi-modal human connectome mapping.}
Connectome Mapper 3 (CMP3) implements a workflow that creates a hierarchical multi-scale
  connectome representation of the structural and functional brain systems, from any
  sMRI / dMRI / rfMRI dataset structured according to the BIDS standard.
It relies on Nipype [@GorgolewskiNipype:2011] and adopts a modular architecture.
As illustrated by \autoref{fig:cmp3-diagram}, the workflow is composed of three different
  pipelines (anatomical, diffusion, and fMRI) dedicated to the processing of each modality (sMRI, dMRI, rfMRI).

![\textbf{Overview of the Connectome Mapper 3 BIDS App's workflow.}
\label{fig:cmp3-diagram}](cmp3-diagram.png)

Each pipeline is represented by a Nipype workflow that takes a BIDS formatted dataset as input, and
  runs a number of sub-workflows (stages).
Each stage implements one or multiple tasks, where each task can interface with either
  a specific tool including in FSL [@Jenkinson2012FSL], FreeSurfer [@Fischl2012FreeSurfer],
  ANTs [@AVANTS2008SymmetricBrain], dipy [@Garyfallidis2014DipyData],
  mrtrix3 [@Tournier2019MRtrix3:Visualisation], AFNI [@Cox2012], or with an in-house tool
  (\autoref{fig:cmp3-diagram}).

To guarantee consistent processing in large neuroimaging cohorts,
  pipeline and stage parameters can be set by loading pipeline
  configuration files in `.json` format.
Adopting BIDS allows CMP3 to automatically identify the structure of the input data, and to check the
  availability of sMRI, dMRI, rfMRI, and derived data.
Depending on the input data, the processing pipelines and stages are then dynamically built and configured
  based on the parameters set in the different configuration files.
Empowered by the Nipype workflow engine, the re-execution of the workflow will resume the
  processing at any stages a change of parameter occurred.

To ensure reproducibility and maximize re-usability of the tool, the implemented pipelines are encapsulated
  in a Docker [@merkeldocker:2014] and a Singularity [@Kurtzer2017Singularity:Compute] software image
  containers, in concordance to the BIDS App framework [@GorgolewskiBIDSMethods:2017].
This means that the BIDS App of CMP3 can be run on a large diversity of datasets on Linux, MacOSX, Windows computers,
  and on high performance computing systems (clusters) for large-scale analysis.

Design considerations make CMP3 not only easy to install and use (as it provides the user with a computing
  environment in which the pipelines are guaranteed to run, and where all dependencies
  are already installed) on a diversity of multi-modal BIDS datasets, but also efficient in managing and
  scaling the pipeline execution while recording provenance, and easy to customize and extend it for specific needs.
At the time EEG is being integrated, CMP3 already provides a collection of interfaces dedicated
  for this modality that would allow anyone to map the connectivity derived from EEG in
  the CMP3 framework, as demonstrated in a tutorial notebook.

\textbf{A revisited and extended multi-scale cortical parcellation scheme.}
CMP3 revisits the multiscale cortical parcellation proposed by [@Cammoun2012:MappingMRI]
  and its implementation, and extends with new structures including a subdivision for each
  brain hemisphere of the thalamus into 7 nuclei, the hippocampus into 12 subfields and the brainstem into
  4 sub-structures (\autoref{fig:parc}).

![\textbf{Creation of the new Lausanne2018 Connectome Parcellation.}
\label{fig:parc}](Lausanne2018_parcellation_diagram.png)

The parcellation derived from the Desikan-Killiany atlas [@Desikan2006AnInterest] has been
  made symmetric by projecting the right hemisphere labels to the left hemisphere, matching the
  boundaries of the projected regions of the left hemisphere to the boundaries of the original regions
  of the left hemisphere, applying this transformation to the rest of the scales, and saving
  each parcellation scale in a Freesurfer annotation file.
After generating the volumetric parcellations from the annotation files, one can now decide or not
  to perform brainstem parcellation [@Iglesias2015BayesianMRI], hippocampal subfields segmentation [@Iglesias2015AMRI],
  and / or probabilistic atlas-based segmentation of the thalamic nuclei [@Najdenovska2018In-vivoImaging].
All segmented structures are combined at the end of process to create the final parcellation nifti image
  at each scale along with the corresponding label index color mapping file in accordance with the BIDS Derivatives
  specifications.

\textbf{A graphical user interface reflecting the workflow structure.}
CMP3 takes advantage of Traits/TraitsUI framework
  (\href{http://docs.enthought.com/traits/}{http://docs.enthought.com/traits/}) for building an
  interactive Graphical User Interface (GUI), to give to pipelines and stages a graphical representation,
  which is easy to understand and extend.
This has enabled the design of a GUI aka `cmpbidsappmanager` (\autoref{fig:gui}) that reflects
  the modular structure of the processing workflow.
It has been designed to guide and support the user in all the steps required to
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
  an eye on the data being processed and easily understand the cause of the problems, change the
  parameters and re-execute when results at a given stage are found not to be satisfactory.
In this way, CMP3 simplifies the creation of connectomes and makes it a straightforward process
  even for users not familiar with Nipype and software container technology.
Nevertheless, it still fulfils the needs of advanced users in charge of analyzing a huge amount of data,
  offering them the possibility to tune and save all the parameters in configuration files and create a batch
  job to automatically process all data with the BIDS App.

\textbf{Outputs ready to be consumed in the BIDS ecosystem.}
CMP3 outputs follow as close as possible the BIDS Derivatives specifications,
  which facilitates the sharing of the derivatives in the BIDS App ecosystem,
  and allows the user to easily retrieve any of the files generated by CMP3
  with tools of the BIDS ecosystem such as pybids [@Yarkoni:2019].
However, it introduces a new BIDS entity ``atlas-<atlas_label>`` that is used in combination
  with the ``res-<atlas_scale>`` entity to distinguish imaging and network data derived
  from different parcellation atlases and scales.
While the BIDS-Derivatives extension to organize network data is being developed, in which we
  are actively participating, both structural and functional connectomes generated with CMP3 are
  saved by default as graph edge lists in ``.tsv`` files, that can be directly analyzed using
  the \href{https://networkx.org/documentation/stable/tutorial.html}{NetworkX}, a Python library which
  offers many algorithms and tools to explore graphs and compute local and global network properties.
Connectivity matrices exported to Matlab as MAT-files and fed to the
  \href{www.brain-connectivity-toolbox.net}{Brain Connectivity Toolbox}, which is a powerful
  toolbox containing a large selection of network measures for the characterization of brain
  connectivity datasets.
Finally, connectomes can be saved in GraphML format to interface with a lot of general purpose
  software packages for graph analysis such as \href{www.cytoscape.org}{Cytoscape} or \href{www.gephi.org}{Gephi}.
Not only this ensures that the connectome files can be opened by
  the most popular software packages used in this field to perform complex network
  analyzes, but also this eases the reuse of all outputs in the BIDS ecosystem.

\textbf{Developed with openness, transparency, and good practices in mind.}
CMP3 is published under the terms of the open source 3-Clause Berkeley Software
  Distribution (3-Clause BSD) license, which allows unlimited modification, redistribution
  and commercial use in source and binary forms as long as its copyright notices, and the
  license's disclaimers of warranty are maintained.
The source code for CMP3 is hosted at
  [https://github.com/sebastientourbier/connectomemapper3](https://github.com/sebastientourbier/connectomemapper3),
  where all bugs and contributions are transparently discussed and managed through issues, and each release is
  archived to Zenodo [@ZenodoCMP:2021].
In case of problems, CMP3 has a dedicated forum at
  [groups.google.com/group/cmtk-users](groups.google.com/group/cmtk-users) where a
  community of users is active to support and have scientific discussions.
To be robust to adverse code changes, versions are released through continuous integration building
  and testing.
Specifically, this involves testing the installation of the python package, the build of
  the Docker and Singularity container images, and the execution of the BIDS App via the different container
  images adopting multiple pipeline configurations, using a sample multi-modal MRI dataset [@Tourbier2020SampleDataset]
  that has been created for this purpose.
Doing so, we can guarantee the full functionality of each newly released version of CMP3.
More details about CMP3, the different processing steps and generated outputs together with
  installation and usage instructions, and different tutorials supporting the analysis,
  and the interpretation of the generated outputs with popular tools, can be found in
  the documentation ([connectome-mapper-3.readthedocs.io](connectome-mapper-3.readthedocs.io))
  that is kept up to date with the current release and can be retrieved for older versions.

# Mention

CMP3 has been successfully employed in a number of methodological
  [@Zheng2020GeometricConnectomeb] [@GlombNeuro:2020] [@GlombNet:2020] [@AkselrodHBM:2021]
  [@RueQueraltNeuro:2021] [@PascucciNet:2021], clinical [@Carboni2019TheOutcome] 
  [@Vorderwulbecke2020High-densityPoint] [@CarboniNeuro:2020], and data [@Pascucci2022]
  research articles.
CMP3 is also part of [`ReproNim/containers`](https://github.com/ReproNim/containers),
  a Datalad dataset with a collection of containerized 40 popular neuroimaging research pipelines,
  which allows one to easily include it as a subdataset within Datalad-controlled BIDS datasets,
  and achieve fully reproducible analysis by running CMP3 directly with Datalad.

# Acknowledgements

This work was supported by Swiss National Science Foundation Sinergia
  [grant no. 170873](https://p3.snf.ch/project-170873).
All the contributors listed in the project’s Zenodo and GitHub repository have contributed code and
  intellectual labor to further improve CMP3.

# References
