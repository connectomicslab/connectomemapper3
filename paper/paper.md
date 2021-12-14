---
title: "Connectome Mapper 3: A Flexible and Open-Source Pipeline Software for Multiscale Multimodal Human Connectome Mapping"
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
  - name: Joan Rue Queralt
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
 - name: Medical Image Processing Lab (MIP:Lab), Ecole Polytechnique Fédérale de Lausanne (EPFL), Switzerland
   index: 2
- name: Département des Neurosciences Cliniques, University of Geneva, Switzerland
   index: 3
date: 14 December 2021
bibliography: ./paper.bib
---

# Summary

The source code for ``Connectome Mapper 3`` has been
archived to Zenodo with the linked DOI: [@zenodo]

# Statement of Need

The field of Magnetic Resonance (MR) Connectomics has rapidly expanded since its advent 
  in the 2000s[@Sporns2005TheBrain,@Hagmann2005FromConnectomics,@Sporns2018Editorial:Connectomics].
It has revolutionized the way to investigate ``in-vivo``, ``non-invasively`` and 
  ``safely`` at different macroscopic scales the structural and functional systems of the 
  brain by modeling connections between brain areas as a graph or network, the so-called
  ``connectome``.

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
While reliability in human brain connectomics concerns the consistency and accuracy of connectome
  estimation for the discrimination of individuals, reproducibility concerns steps towards 1) increasing the
  transparency of data analysis, by sharing data, code, computing environment, pipeline configuration files,
  and recording data and workflow provenance, and 2) minimizing numerical variability when the
  pipeline is executed on different operating systems. 

The last ten years have witnessed a trend towards the adoption by the community of open research
  practices, which promotes ``open data`` and ``open method``, to address these challenges.
This has led to the elaboration of the principles of open and reproducible research for
  neuroimaging using Magnetic Resonance Imaging (MRI)[@Nichols2017] and to recommendation of
  standard practices for sharing code and programs[@Eglen2017TowardNeuroscience]. 
To ease and automate
  the practice of sharing raw and processed neuroimaging data and code with appropriate metadata
  and provenance records, multiple initiatives have developed new standards, tools, and educational
  resources.
Among others, this has contributed to the emergence of
  Nipype[@Gorgolewski2011Nipype:Python], a dataflow library that facilitates workflow
  execution/re-execution, provenance tracking and provides a uniform interface to existing
  neuroimaging softwares; the Brain Imaging Data Structure (BIDS)
  standard[@Gorgolewski2016TheExperiments], to standardize the organization and description
  of neuroimaging data; Datalad a data portal, versioning, and provenance tracking system
  supporting BIDS; and more recently, the BIDS-Apps framework[@Gorgolewski2017BIDSMethods],
  which employs modern software practices and encapsulates into a software container a processing
  pipeline that takes a BIDS dataset as input in order to improve the ease of use, accessibility,
  deliverability, portability, scalability and reproducibility of processing pipelines. 

Following these advances, a number of processing pipelines such as C-PAC~[@cpac2013],
  NIAK[@Bellec2016NeuroimagingNIAK], fMRIPrep[@Ghosh2018],
  dMRIPrep[@dmriprep2019], QSIPREP[@Cieslak2020QSIPrep:MRI], NDMG[@Kiar2018AVariability] and PyNets[@Pisner2020PyNets:Learning] have been
  developed to support the mapping of connectomes derived from MRI data organized following the BIDS standard.
They have demonstrated their capability in addressing all the challenges of data sharing,
  portability, computing scalability, reliability, reproducibility and transparency.
However, none of the existing solutions are designed (1) to generate  precise brain parcellation
  from cortical surfaces and map corresponding structural and / or functional connectomes at
  different macroscopic scales with hierarchical region grouping, (2) to build personalized
  processing pipeline combining among multiple neuroimaging (3) to work across both fMRI and dMRI
  (except NDMG), (4) to enable the end users to tune pipeline hyper-parameters to their dataset and
  (5) to provide a user-friendly graphical interface that enhances its accessibility.

In this article we present the third release of the Connectome Mapper (CMP3), whose original main
  goal was to simplify the organisation and the analysis of sMRI and dMRI from raw data to
  multi-scale structural weighted connectomes.
While CMP3 derives from the now deprecated CMP1 and CMP2 packages[@Daducci2012], it has
  evolved massively over the years in terms of the underlying codebase, the tools used and the
  scope of the functionality provided.
Designed following the specification established by the BIDS-Apps standard, CMP3 is a scalable,
  portable and a reproducible pipeline software with optionally a graphical user interface that
  guides and helps researchers through all the steps needed to compute in a common framework both
  structural and functional connectomes from raw sMRI, dMRI, and resting-state fMRI (rfMRI) data at
  five different macroscopic scales.
It handles datasets organized according to the BIDS standard and works transparently with the most
  used and promising diffusion acquisition schemes.
Its modular architecture, embedding most popular neuroimaging tools (such as including FSL,
  FreeSurfer, ANTs, MRtrix3, Dipy and AFNI) used in combination with the Nipype dataflow library
  makes it not only efficient in managing and scaling the pipeline execution while recording provenance,
  but also easy to customize it for specific needs.
CMP3 is open-source, developed in Python, and the processing pipelines and all dependencies
  are encapsulated in a software container to facilitate installation, enhance execution
  reproducibility, and to be fully portable, being compatible with all types of operating systems.  
It is worth noting the software is ready to accommodate other imaging modalities
  such as the current integration of a source EEG imaging pipeline, which makes it an ideal to be further developed into
  the next generation brain connectivity mapping tools.

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
