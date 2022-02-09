# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions for plotting Lausanne parcellation files."""

import nibabel as ni
from nilearn import plotting, datasets

from cmtklib.data.parcellation.util import (
    get_lausanne2018_parcellation_annot
)
