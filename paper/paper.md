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

While brain areas are usually derived from high resolution T1 weighted  MR imaging, so called
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
  Nipype [@GorgolewskiNipype:2011], a dataflow library that facilitates workflow
  execution/re-execution, provenance tracking and provides a uniform interface to existing
  neuroimaging softwares; the Brain Imaging Data Structure (BIDS)
  standard [@GorgolewskiTheExperiments:2016], to standardize the organization and description
  of neuroimaging data; Datalad a data portal, versioning, and provenance tracking system
  supporting BIDS; and more recently, the BIDS-Apps framework [@GorgolewskiBIDSMethods:2017],
  which employs modern software practices and encapsulates into a software container a processing
  pipeline that takes a BIDS dataset as input in order to improve the ease of use, accessibility,
  deliverability, portability, scalability and reproducibility of processing pipelines. 

Following these advances, a number of processing pipelines such as C-PAC [@cpac:2013],
  NIAK [@BellecNeuroimagingNIAK:2016], fMRIPrep [@Ghosh:2018],
  dMRIPrep [@dmriprep:2019], QSIPREP [@CieslakQSIPrep:2020], NDMG [@KiarAVariability:2018] and PyNets [@PisnerPyNets:2020] have been
  developed to support the mapping of connectomes derived from MRI data organized following the BIDS standard.
They have demonstrated their capability in addressing all the challenges of data sharing,
  portability, computing scalability, reliability, reproducibility and transparency.
However, none of the existing solutions are designed to map the structural and / or functional
  connectomes for five macroscopic brain parcellation scales with hierarchical region grouping,
  and to provide a user-friendly graphical interface that enhances its accessibility.

# Summary

Connectome Mapper 3 provides a unique software pipeline solution for researchers to easily,
  reliably and transparently create a hierarchical multi-scale connectome representation of
  the structural and functional brain systems, on any dataset structured according to the
  BIDS standard.
While CMP3 derives from the now deprecated CMP1 and CMP2 packages[@Daducci:2012], whose original main
  goals were to simplify the organisation and the analysis of sMRI and dMRI from raw data to
  multi-scale structural weighted connectomes, it has
  evolved massively over the years in terms of the underlying codebase, the tools used, and the
  scope of the functionality provided.
Design considerations with the implementation of modular, configurable, and containerized
  processing pipelines (\autoref{fig:cmp3.diagram}) handling datasets organized following the BIDS standard, distributed
  as a BIDS App, embedding most popular neuroimaging tools (such as including FSL,
  FreeSurfer, ANTs, MRtrix3, Dipy and AFNI) used in combination with the Nipype dataflow library
  makes it not only efficient in managing and scaling the pipeline execution while recording provenance,
  but also easy to customize it for specific needs.

![\textbf{Participant-level analysis workflow of the Connectome Mapper 3.}
It has a modular architecture composed of three different pipelines (anatomical, diffusion and
  fMRI) dedicated to each modality (sMRI, dMRI and rfMRI).
Each pipeline handles datasets organized following the Brain Imaging Data Structure standard and
  consists of a number of processing stages implementing one or multiple specific tasks of the
  workflow, where each task interfaces with a specific tool, empowered by the Nipype dataflow
  library, to computes, from raw MRI data, brain parcellation and corresponding structural and/or
  functional connectivity maps at 5 different scales using the Lausanne2018 hierarchical scheme.
\label{fig:cmp3-diagram}](cmp3-diagram.png)

Each pipeline can be individually executed with the aid of the user-friendly GUI and the
  output of each stage can be visually reviewed, enabling the user to keep an eye on the
  data being processed and easily understand the cause of the problems, change the
  parameters and re-execute when results are unsatisfactory.
The adoption of pipeline containerization not only eases the installation process as all
  dependencies are already installed, but it also provides the user with a computing
  environment in which the pipelines are guarantee to run.
# It however also presents some limitations.
# For instance, MP2RAGE needs to be masked ``a-priori`` to make FreeSurfer recon-all
#   succeeding.
# Moreover, CMP does not work with brains displaying abnormal anatomy (e.g., brain lesions)
#   because FreeSurfer may not run successfully and/or tractography potentially will fail in
#   lesion areas with excessively low Fractional Anisotropy (FA).

While CMP3 simplifies the creation of connectomes and makes it a straightforward process
  even for users not familiar with dataflow languages, it fulfils at the same time the
  needs of advanced users in charge of analyzing huge amount of data, offering them the
  possibility to tune and save all the parameters in configuration files and create a batch
  job to automatically process all data with the BIDS App.
Outputs are organized following a BIDS derivatives-like structure where connectome files
  can be exported to a number of formats, such that not only connectomes can be opened by
  the most popular software packages used in this field to perform complex network
  analyses, but also to facilitate the sharing of the derivatives in the BIDS App
  ecosystem.
To this end, we are actively participating in the development of BIDS-Derivatives for connectivity data.

CMP3 can be highly versatile as it offers a number of options at each processing steps to
  be completely data agnostic.
At the same time, it provides the user with a very efficient framework to compute
  connectomes in the way it guides them through all the steps and options involved in their
  creation and it guarantees seamless processing, irrespective of the choices made.
In addition, the very flexible framework of CMP3 enables the addition of new steps, stages
  or pipelines with relatively little effort to account for additional imaging modalities
  and algorithms.
At the time of writing, some new modules such as the SIFT2
  algorithm [@SmithSIFT2:2015] to guarantee more biologically accurate
  measures of fibre connectivity, or surface-based co-registration of the mean BOLD image
  with the anatomical MRI using FreeSurfer BBRegister are under development.
It is worth noting the software is ready to accommodate other imaging modalities
  such as the current integration of an EEG source imaging pipeline initiated at OHBM BrainHack 2020
  ([https://github.com/ohbm/hackathon2020/issues/214](https://github.com/ohbm/hackathon2020/issues/214)),
  which makes it an ideal to be further developed into the next generation brain connectivity mapping tools.

CMP3 is developed with openness and transparency in mind.
The source code for ``Connectome Mapper 3`` is hosted at
  [https://github.com/sebastientourbier/connectomemapper3](https://github.com/sebastientourbier/connectomemapper3),
  and archived to Zenodo [@ZenodoCMP:2021].
A detailed documentation is available
  at [connectome-mapper-3.readthedocs.io](connectome-mapper-3.readthedocs.io) that is
  kept up to date with the current release and can be retrieved for older versions.
It includes in particular step-by-step guides for installation and usage together with the
  description of all generated outputs and each processing step.
In case of problems, the Connectome Mapper has a dedicated forum at
  [groups.google.com/group/cmtk-users](groups.google.com/group/cmtk-users) where a
  community of users is active to support and have scientific discussions.
Furthermore, bugs as well as both internal and external developer contributions are
  discussed and managed through issues directly on GitHub for transparent software
  development.

# Mention

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

This work was supported by Swiss National Science Foundation Sinergia grant no. 170873.

# References
