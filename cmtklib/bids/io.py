# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module provides classes to handle custom BIDS derivatives file input."""
import csv
import os
import json
from traits.api import (HasTraits, Str)

from cmp.info import __version__
from nipype import __version__ as nipype_version


# Directories for derivatives compliant to BIDS `1.4.0` (e.g. <toolbox>-<version>)
# Need to be declared before import the pipeline modules
__cmp_directory__ = f'cmp-{__version__}'
__nipype_directory__ = f'nipype-{nipype_version}'
__freesurfer_directory__ = f'freesurfer-6.0.1'


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

    res : Str
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
    res = Str
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
            p_res="",
            p_label="",
            p_desc=""
    ):
        self.toolbox_derivatives_dir = p_toolbox_derivatives_dir
        self.suffix = p_suffix
        self.extension = p_extension
        self.acquisition = p_acquisition
        self.atlas = p_atlas
        self.res = p_res
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
        if self.res:
            msg += f', "res": "{self.res}"'
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

    def get_filename_path(self, base_dir, subject, session=None, debug=True):
        """Return the number of regions by reading its associated TSV side car file describing the nodes.

        Parameters
        ----------
        base_dir: str
            BIDS root directory or `derivatives/` directory in BIDS root directory

        subject: str
            Subject filename entity e.g. "sub-01"

        session: str
            Session filename entity e.g. "ses-01" if applicable
            (Default: None)

        debug: bool
            Debug mode (Extra outputed messages) if `True`

        """
        # Build path to BIDS TSV side car of the parcellation file
        filepath = os.path.join(
            base_dir,
            subject
        )
        fname = f'{subject}' if session is None else f'{subject}_{session}'
        filepath = os.path.join(filepath, session)
        if self.label is not None and self.label != "":
            fname += f'_label-{self.label}'
        if self.atlas is not None and self.atlas != "":
            fname += f'_atlas-{self.atlas}'
        if self.res is not None and self.res != "":
            fname += f'_res-{self.res}'
        if self.desc is not None and self.desc != "":
            fname += f'_desc-{self.desc}'
        fname += f'_{self.suffix}'
        filepath = os.path.join(filepath, "anat", fname)
        if debug:
            print(f" .. DEBUG : Generated parcellation file path (no extension) = {filepath}")
        return filepath


class CustomParcellationBIDSFile(CustomBIDSFile):
    """Represent a custom parcellation files in the form `sub-<label>_atlas-<label>[_res-<label>]_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_atlas="L2018", p_extension=".nii.gz")

    def get_nb_of_regions(self, bids_dir, subject, session=None, debug=True):
        """Return the number of regions by reading its associated TSV side car file describing the nodes.

        Parameters
        ----------
        bids_dir: str
            BIDS root directory

        subject: str
            Subject filename entity e.g. "sub-01"

        session: str
            Session filename entity e.g. "ses-01" if applicable
            (Default: None)

        debug: bool
            Debug mode (Extra outputed messages) if `True`
        """
        # Build path to BIDS TSV side car of the parcellation file
        parc_filepath = self.get_filename_path(
            base_dir=os.path.join( bids_dir, "derivatives", self.toolbox_derivatives_dir),
            subject=subject,
            session=session,
            debug=debug
        ) + '.tsv'

        if os.path.exists(parc_filepath):
            if debug:
                print(f" .. DEBUG : Open {parc_filepath} to get number of regions")
            with open(parc_filepath) as file:
                tsv_file = csv.reader(file, delimiter="\t")
                nb_of_regions = len(list(tsv_file)) - 1  # Remove 1 to account for the header (# of lines - 1 = # regions)
                if debug:
                    print(f" .. DEBUG : Number of regions = {nb_of_regions}")
            return nb_of_regions
        else:
            return None


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
