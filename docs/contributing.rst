.. _contributing:

=================================
Contributing to Connectome Mapper
=================================

:Authors: Sebastien Tourbier, Adrien Birbaumer
:Version: Revision: 2
:Copyright: Copyright (C) 2017-2019, Brain Communication Pathways Sinergia Consortium, Switzerland.
            This software is distributed under the open-source license Modified BSD.

.. contents::

Philosophy
----------

The development philosophy for this new version of the Connectome Mapper is to:

I. Keep the code of the processing as much as possible outside of the actual
main Connectome Mapper code, through the use and extension of existing Nipype interfaces and
an external library (dubbed cmtklib).

II. Separation between the code of the graphical interface and the actual main Connectomer Mapper code, achieved through inheritance of the actual main stages and pipelines.

III. Enhance portability by freezing the computing environment with all software dependencies installed, through the adoption of the BIDS App framework relying on light software container technologies.

IV. Enhance interoperability by working with datasets structured following the Brain Imaging Data Structure structured dataset.

Further development, typically additions of other tools and configuration options should go in this direction.

Enhancements
------------

Possible enhancements are probably to be included in the following list:

I. Adding of a configuration option to an existing stage
II. Adding a new interface to cmtklib
III. Adding of a new stage
IV. Adding of a new pipeline

The adding of newer configuration options to existing stages should be self-
understandable. If the addition is large enough to be considered a "sub-module"
of an existing stage, see the Diffusion stage example.

Adding a new stage implies the addition of the stage folder to the cmp/stages and cmp/bidsappmanager/stages
directory and according modification of the parent pipeline along with insertion
of a new image in cmp/bidsappmanager/stages. Copy-paste of existing stage (such as segmentation stage) is
recommended.

Adding a new pipeline implies the creation of a new pipeline script and folder
in the cmp/pipelines and cmp/bidsappmanager/pipelines directories Again copy-pasting an existing pipeline is the
better idea here. Modification of cmp/project.py and cmp/bidsappmanager/project.py file is also needed.
