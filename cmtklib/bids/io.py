# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module provides classes to handle custom BIDS derivatives file input."""
import csv
import os
import json
from traits.api import (HasTraits, Str, Enum)

from cmp.info import __version__
from nipype import __version__ as nipype_version


# Directories for derivatives compliant to BIDS `1.4.0` (e.g. <toolbox>-<version>)
# Need to be declared before import the pipeline modules
__cmp_directory__ = f'cmp-{__version__}'
__nipype_directory__ = f'nipype-{nipype_version}'
__freesurfer_directory__ = f'freesurfer-7.1.1'
__cartool_directory__ = f'cartool-v3.80'
__eeglab_directory__ = f'eeglab-v14.1.1'


class CustomBIDSFile(HasTraits):
    """Base class used to represent a BIDS-formatted file inside a custom BIDS derivatives directory.

    Attributes
    ----------
    toolbox_derivatives_dir : Str
        Toolbox folder name in the `derivatives/` of the BIDS dataset

    datatype: Enum(["anat", "dwi", "func", "eeg"])
        BIDS data type

    suffix : Str
        Filename suffix e.g. `sub-01_T1w.nii.gz` has suffix `T1w`

    acquisition : Str
        Label used in `_acq-<label>_`

    task : Str
        Label used in `_task-<label>_`

    rec : Str
        Label used in `_rec-<label>_`

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
    toolbox_derivatives_dir = Str(desc="Toolbox folder name in the derivatives/ directory of the BIDS dataset")
    datatype = Enum(["anat", "dwi", "func", "eeg"], desc="")
    suffix = Str(desc="")
    acquisition = Str(desc="")
    rec = Str(desc="")
    extension = Str(desc="")
    atlas = Str(desc="")
    res = Str(desc="")
    label = Str(desc="")
    desc = Str(desc="Label used in _desc-<label>_")
    task = Str(desc="")

    def __init__(
            self,
            p_toolbox_derivatives_dir="",
            p_datatype="",
            p_suffix="",
            p_extension="",
            p_acquisition="",
            p_rec="",
            p_atlas="",
            p_res="",
            p_label="",
            p_desc="",
            p_task=""
    ):
        self.toolbox_derivatives_dir = p_toolbox_derivatives_dir
        self.datatype = p_datatype
        self.suffix = p_suffix
        self.extension = p_extension
        self.acquisition = p_acquisition
        self.rec = p_rec
        self.atlas = p_atlas
        self.res = p_res
        self.label = p_label
        self.desc = p_desc
        self.task = p_task

    def __str__(self):
        msg = "{"
        msg += f' "custom_derivatives_dir": "{self.toolbox_derivatives_dir}"'
        if self.datatype:
            msg += f', "datatype": "{self.datatype}"'
        if self.task:
            msg += f', "task": "{self.task}"'
        if self.acquisition:
            msg += f', "acquisition": "{self.acquisition}"'
        if self.rec:
            msg += f', "reconstruction": "{self.rec}"'
        if self.atlas:
            msg += f', "atlas": "{self.atlas}"'
        if self.res:
            msg += f', "res": "{self.res}"'
        if self.label:
            msg += f', "label": "{self.label}"'
        if self.desc:
            msg += f', "desc": "{self.desc}"'
        if self.suffix:
            msg += f', "suffix": "{self.suffix}"'
        if self.extension:
            msg += f', "extension": "{self.extension}"'
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

    def get_filename_path(self, base_dir, subject, session=None, debug=False):
        """Return the filename path without extension of the represented BIDS file.

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
            Debug mode (Extra output messages) if `True`

        """
        # Build path to custom parcellation file, dropping the extension
        filepath = os.path.join(
            base_dir,
            subject
        )
        fname = f'{subject}'
        if session is not None and session != "":
            # Handle the subject/session filename and structure
            fname += f'_{session}'
            filepath = os.path.join(filepath, session)
        if self.task is not None and self.task != "":
            fname += f'_task-{self.task}'
        if self.label is not None and self.label != "":
            fname += f'_label-{self.label}'
        if self.atlas is not None and self.atlas != "":
            fname += f'_atlas-{self.atlas}'
        if self.res is not None and self.res != "":
            fname += f'_res-{self.res}'
        if self.rec is not None and self.rec != "":
            fname += f'_rec-{self.rec}'
        if self.desc is not None and self.desc != "":
            fname += f'_desc-{self.desc}'
        fname += f'_{self.suffix}'
        filepath = os.path.join(filepath, self.datatype, fname)
        if debug:  # pragma: no cover
            print(f" .. DEBUG : Generated file path (no extension) = {filepath}")
        return filepath

    def get_filename(self, subject, session=None, debug=False):
        """Return the filename path with extension of the represented BIDS file.

        Parameters
        ----------
        subject: str
            Subject filename entity e.g. "sub-01"

        session: str
            Session filename entity e.g. "ses-01" if applicable
            (Default: None)

        debug: bool
            Debug mode (Extra output messages) if `True`

        """
        # Build filename

        fname = f'{subject}'
        if session is not None and session != "":
            # Handle the subject/session filename and structure
            fname += f'_{session}'
        if self.task is not None and self.task != "":
            fname += f'_task-{self.task}'
        if self.label is not None and self.label != "":
            fname += f'_label-{self.label}'
        if self.atlas is not None and self.atlas != "":
            fname += f'_atlas-{self.atlas}'
        if self.res is not None and self.res != "":
            fname += f'_res-{self.res}'
        if self.rec is not None and self.rec != "":
            fname += f'_rec-{self.rec}'
        if self.desc is not None and self.desc != "":
            fname += f'_desc-{self.desc}'
        fname += f'_{self.suffix}.{self.extension}'
        if debug:  # pragma: no cover
            print(f" .. DEBUG : Generated file name = {fname}")
        return fname


class CustomParcellationBIDSFile(CustomBIDSFile):
    """Represent a custom parcellation files in the form `sub-<label>_atlas-<label>[_res-<label>]_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_datatype="anat", p_suffix="dseg", p_atlas="L2018", p_extension="nii.gz")

    def get_nb_of_regions(self, bids_dir, subject, session=None, debug=False):
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
            Debug mode (Extra output messages) if `True`
        """
        # Build path to BIDS TSV side car of the parcellation file
        parc_filepath = self.get_filename_path(
            base_dir=os.path.join( bids_dir, "derivatives", self.toolbox_derivatives_dir),
            subject=subject,
            session=session,
            debug=debug
        ) + '.tsv'

        if os.path.exists(parc_filepath):
            if debug:  # pragma: no cover
                print(f" .. DEBUG : Open {parc_filepath} to get number of regions")
            with open(parc_filepath) as file:
                tsv_file = csv.reader(file, delimiter="\t")
                nb_of_regions = len(list(tsv_file)) - 1  # Remove 1 to account for the header (# of lines - 1 = # regions)
                if debug:  # pragma: no cover
                    print(f" .. DEBUG : Number of regions = {nb_of_regions}")
            return nb_of_regions
        else:
            return None


class CustomBrainMaskBIDSFile(CustomBIDSFile):
    """Represent a custom brain mask in the form `sub-<label>_desc-brain_mask.nii.gz`."""

    def __init__(self):
        super().__init__(p_datatype="anat", p_suffix="mask", p_desc="brain", p_extension="nii.gz")


class CustomWMMaskBIDSFile(CustomBIDSFile):
    """Represent a custom white-matter mask in the form `sub-<label>_label-WM_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_datatype="anat", p_suffix="dseg", p_label="WM", p_extension="nii.gz")


class CustomGMMaskBIDSFile(CustomBIDSFile):
    """Represent a custom gray-matter mask in the form `sub-<label>_label-GM_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_datatype="anat", p_suffix="dseg", p_label="GM", p_extension="nii.gz")


class CustomCSFMaskBIDSFile(CustomBIDSFile):
    """Represent a custom CSF mask in the form `sub-<label>_label-CSF_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_datatype="anat", p_suffix="dseg", p_label="CSF", p_extension="nii.gz")


class CustomAparcAsegBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted Freesurfer aparc+aseg file in the form `sub-<label>_desc-aparcaseg_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_datatype="anat", p_suffix="dseg", p_desc="aparcaseg", p_extension="nii.gz")


class CustomEEGPreprocBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted preprocessed EEG file in the form `sub-<label>_task-<label>_desc-preproc_eeg.[set|fif]`."""
    extension = Enum(['set', 'fif'])

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="eeg", p_desc="preproc", p_extension=self.extension)


class CustomEEGEpochsBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted EEG Epochs file in .set or .fif format."""
    extension = Enum(['set', 'fif'])

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="epo", p_desc="preproc", p_extension=self.extension)


class CustomEEGEventsBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted EEG task events file in the form `sub-<label>_task-<label>_events.tsv`."""

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="events", p_extension="tsv")

    def extract_event_ids_from_json_sidecar(self, base_dir, subject, session=None, debug=False):
        events_json_file = self.get_filename_path(base_dir, subject, session, debug) + ".json"
        with open(events_json_file, "r") as f:
            json_content = json.load(f)
            # Reformat the information about tasks and integer encoding
            # to the format MNE expects
            trial_name = json_content["trial_type"]["Levels"].keys()
            trial_id = json_content["trial_type_id"]["Levels"].keys()
            event_ids = {f"{t_name}": f"{t_id}" for t_name, t_id in zip(trial_name, trial_id)}
            if debug:
                print(f"  .. DEBUG: Event_ids for Epochs extraction: {event_ids}")
        return event_ids


class CustomEEGElectrodesBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted EEG electrodes file in the form `sub-<label>_task-<label>_electrodes.tsv`."""

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="electrodes", p_extension="tsv")


class CustomEEGCartoolElectrodesBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted electrode file produced by Cartool, in the form `sub-<label>_eeg.xyz`."""

    def __init__(self):
        super().__init__(p_datatype="eeg", p_task="", p_suffix="eeg", p_extension="xyz")


class CustomEEGCartoolSpiBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted Source Point Irregularly spaced file produced by Cartool, in the form `sub-<label>_eeg.spi`."""

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="eeg", p_extension="spi")


class CustomEEGCartoolMapSpiRoisBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted spi / rois mapping file in the form `sub-<label>_eeg.pickle.rois`."""

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="eeg", p_extension="pickle.rois")


class CustomEEGMNETransformBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted electrode transform file in the form `sub-<label>_trans.fif`."""

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="trans", p_extension="fif")


class CustomEEGCartoolInvSolBIDSFile(CustomBIDSFile):
    """Represent a custom BIDS-formatted inverse solution file produced by Cartool in the form `sub-<label>_eeg.[LAURA|LORETA].is`."""
    esi_method = Enum(['LAURA', 'LORETA'], desc="EEG Source Imaging method")

    def __init__(self):
        super().__init__(p_datatype="eeg", p_suffix="eeg", p_extension=f"{self.esi_method}.is")

    def _esi_method_changed(self, new):
        """Update extension when esi method is modified."""
        self.extension = f"{new}.is"

