
Changes
========

*************************
Version 3.0.0-beta-240120
*************************

Date: January 24, 2020

* Updated multi-scale parcellation with a new symmetric version:

	1. The right hemisphere labels were projected in the left hemisphere to create a symmetric version of the multiscale cortical parcellation proposed by Cammoun2012_.
	2. For scale 1, the boundaries of the projected regions over the left hemisphere were matched to the boundaries of the original parcellation for the left hemisphere.
	3. This transformation was applied for the rest of the scales.

	.. _Cammoun2012: https://doi.org/10.1016/j.jneumeth.2011.09.031

* Updated documentation with list of changes