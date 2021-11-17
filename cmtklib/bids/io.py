# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module provides classes to handle custom BIDS derivatives file input."""

import os
import json
from traits.api import (HasTraits, Directory, Str)
from bids import BIDSLayout


class CustomBIDSFile(HasTraits):
    """Base class used to represent a BIDS-formatted file inside a custom BIDS derivatives directory.

    Attributes
    ----------
    toolbox_derivatives_dir : Str
        Toolbox folder name in the `derivatives/` of the BIDS dataset

    suffix : Str
        Filename suffix e.g. `sub-01_T1w.nii.gz` has suffix `T1w`

    acquisition : Str
        Label used in `_acq-<label>_`

    resolution : Str
        Label used in `_res-<label>_`

    extension : Str
        File extension

    atlas : Str
        Label used in `_atlas-<label>_`

    label : Str
        Label used in `_label-<label>_`

    desc : Str
        Label used in `_desc-<label>_`

    """
    toolbox_derivatives_dir = Str
    suffix = Str
    acquisition = Str
    resolution = Str
    extension = Str
    atlas = Str
    label = Str
    desc = Str

    def __init__(
            self,
            p_toolbox_derivatives_dir="",
            p_suffix="",
            p_extension="",
            p_acquisition="",
            p_atlas="",
            p_resolution="",
            p_label="",
            p_desc=""
    ):
        self.toolbox_derivatives_dir = p_toolbox_derivatives_dir
        self.suffix = p_suffix
        self.extension = p_extension
        self.acquisition = p_acquisition
        self.atlas = p_atlas
        self.resolution = p_resolution
        self.label = p_label
        self.desc = p_desc

    def __str__(self):
        msg = "{"
        msg += f' "custom_derivatives_dir": "{self.toolbox_derivatives_dir}"'
        if self.suffix:
            msg += f', "suffix": "{self.suffix}"'
        if self.extension:
            msg += f', "extension": "{self.extension}"'
        if self.acquisition:
            msg += f', "acquisition": "{self.acquisition}"'
        if self.atlas:
            msg += f', "atlas": "{self.atlas}"'
        if self.resolution:
            msg += f', "resolution": "{self.resolution}"'
        if self.label:
            msg += f', "label": "{self.label}"'
        if self.desc:
            msg += f', "desc": "{self.desc}"'
        msg += "}"
        return msg

    def _string2dict(self):
        return json.loads(self.__str__())

    def get_query_dict(self):
        """Return the dictionary to be passed to `BIDSDataGrabber` to query a list of files."""
        query_dict = self._string2dict()
        del query_dict["custom_derivatives_dir"]
        return query_dict

    def get_toolbox_derivatives_dir(self):
        """Return the value of `custom_derivatives_dir` attribute."""
        return self.toolbox_derivatives_dir


class CustomParcellationBIDSFile(CustomBIDSFile):
    """Represent a custom parcellation files in the form `sub-<label>_atlas-<label>[_res-<label>]_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_atlas="L2018", p_extension=".nii.gz")


class CustomBrainMaskBIDSFile(CustomBIDSFile):
    """Represent a custom brain mask in the form `sub-<label>_desc-brain_mask.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="mask", p_desc="brain", p_extension=".nii.gz")


class CustomWMMaskBIDSFile(CustomBIDSFile):
    """Represent a custom white-matter mask in the form `sub-<label>_label-WM_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_label="WM", p_extension=".nii.gz")


class CustomGMMaskBIDSFile(CustomBIDSFile):
    """Represent a custom gray-matter mask in the form `sub-<label>_label-GM_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_label="GM", p_extension=".nii.gz")


class CustomCSFMaskBIDSFile(CustomBIDSFile):
    """Represent a custom CSF mask in the form `sub-<label>_label-CSF_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_label="CSF", p_extension=".nii.gz")


class CustomAparcAsegBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted Freesurfer aparc+aseg file in the form `sub-<label>_desc-aparcaseg_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_desc="aparcaseg", p_extension=".nii.gz")
