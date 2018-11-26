
Connectome Mapper 3
=======================================================

This neuroimage processing pipeline software is developed by the Hagmann's group at the University Hospital of Lausanne (CHUV) and the Signal Processing Laboratory (LTS5) of the Ecole Polytechnique Fédérale de Lausanne (EPFL) for use at the Center for BioMedical Imaging (CIBM) within the `FNSNF Sinergia Project 170873 <http://p3.snf.ch/project-170873>`_, as well as for open-source software distribution.

.. image:: http://bids.neuroimaging.io/openneuro_badge.svg
  :target: https://openneuro.org
  :alt: Available in OpenNeuro!

.. image:: https://circleci.com/gh/poldracklab/fmriprep/tree/master.svg?style=shield
  :target: https://circleci.com/gh/poldracklab/fmriprep/tree/master

.. image:: https://readthedocs.org/projects/fmriprep/badge/?version=latest
  :target: http://fmriprep.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/fmriprep.svg
  :target: https://pypi.python.org/pypi/fmriprep/
  :alt: Latest Version


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
Acknowledgement
*********

.. important::
	* If you use the Connectome Mapper 3 in your research, please acknowledge this work by mentioning explicitly the name of this software (connectomemapper3) and the version, along with a link to the BitBucket repository or the Zenodo reference.

	* If you use the Connectome Mapper 2 in your research, please cite:

		A. Daducci, S. Gerhard, A. Griffa, A. Lemkaddem, L. Cammoun, X. Gigandet, R. Meuli, P. Hagmann and J.-P. Thiran
		*The Connectome Mapper: An Open-Source Processing Pipeline to Map Connectomes with MRI*

		Plos One 7(12):e48121 (2012)

		`Link to manuscript <http://www.plosone.org/article/info%3Adoi%2F10.1371%2Fjournal.pone.0048121>`_

	* If you use the Connectome Mapper 3 in your research, please acknowledge this work by mentioning explicitly the name of this software (connectomemapper3) and the version, along with a link to the BitBucket repository or the Zenodo reference.

*********
Funding
*********

Work supported by the [Sinergia SNFNS-170873 Grant](http://p3.snf.ch/Project-170873).

*******************
License information
*******************

This software is distributed under the open-source license Modified BSD. See `license <LICENSE>`_ for more details.

All trademarks referenced herein are property of their respective holders.

Copyright (C) 2009-2018, Brain Communication Pathways Sinergia Consortium, Switzerland.


********
Contents
********

.. toctree::
   :maxdepth: 2

   cmp2/installation
   cmp2/download
   cmp2/conf
   cmp2/stages
   cmp2/exampleresults
