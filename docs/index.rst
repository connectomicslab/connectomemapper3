
Connectome Mapper 3 (UNDER DEVELOPMENT)
=======================================================

This neuroimage processing pipeline software is developed by the Hagmann's group at the University Hospital of Lausanne (CHUV) for use at the Center for BioMedical Imaging (CIBM) within the `SNF Sinergia Project 170873 <http://p3.snf.ch/project-170873>`_, as well as for open-source software distribution.

..

.. image:: http://bids.neuroimaging.io/openneuro_badge.svg
  :target: https://openneuro.org
  :alt: Available in OpenNeuro!


.. image:: https://circleci.com/gh/connectomicslab/connectomemapper3/tree/master.svg?style=svg
  :target: https://circleci.com/gh/connectomicslab/connectomemapper3/tree/master
  :alt: Continuous Integration Status

.. image:: https://readthedocs.org/projects/connectome-mapper-3/badge/?version=latest
  :target: https://connectome-mapper-3.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status


*********
About
*********

.. image:: images/flowchart.jpg
	:height: 300
	:align: center

``Connectome Mapper 3``, part of the Connectome Mapping Toolkit (CMTK), implements full anatomical, diffusion and resting-state MRI processing pipelines, from raw Diffusion / T1 / T2 / BOLD data to multi-resolution connection matrices.

The ``Connectome Mapper 3`` pipelines uses a combination of tools from well-known software
packages, including FSL_, FreeSurfer_, ANTs_, MRtrix3_, Dipy_ and AFNI_.
These pipelines were designed to provide the best software implementation for each
state of processing, and will be updated as newer and better neuroimaging
software become available.

This tool allows you to easily do the following:

- Take T1 / Diffusion / resting-state MRI data from raw to multi-resolution connection matrices.
- Implement tools from different software packages.
- Achieve optimal data processing quality by using the best tools available
- Automate and parallelize processing steps, which provides a significant
  speed-up from typical linear, manual processing.

Reproducibility and replicatibility is achieved through the distribution of a BIDSApp, a software container image which provide a frozen environment where versions of all external softwares and libraries are fixed.


*********
Funding
*********

Work supported by the SNF Sinergia Grant 170873 (http://p3.snf.ch/Project-170873).

*******************
License information
*******************

This software is distributed under the open-source license Modified BSD. See :ref:`license <LICENSE>` for more details.

All trademarks referenced herein are property of their respective holders.

Copyright (C) 2017-2019, Brain Communication Pathways Sinergia Consortium, Switzerland.


********
Contents
********

.. toctree::
   :maxdepth: 1

   index
   installation
   usage
   conf
   stages
   exampleresults
   outputs
   citing
   contributing
   datalad
