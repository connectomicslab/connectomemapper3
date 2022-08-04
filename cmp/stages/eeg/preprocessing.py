# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for computing brain parcellation."""

# General imports
import os
from traits.api import (
    HasTraits, Enum, Instance, Float, Str
)

# Nipype imports
import nipype.pipeline.engine as pe

# Own imports
from cmp.stages.common import Stage
from cmtklib.bids.io import (
    CustomEEGPreprocBIDSFile, CustomEEGEventsBIDSFile,
    CustomEEGElectrodesBIDSFile, CustomEEGCartoolElectrodesBIDSFile,
    __cmp_directory__
)
from cmtklib.interfaces.mne import EEGLAB2fif


class EEGPreprocessingConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.eeg.preparer.EEGPreprocessingStage` instance.

    Attributes
    ----------

    task_label : Str
        Task label (e.g. `_task-<label>_`)

    eeg_ts_file : CustomEEGPreprocBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGPreprocBIDSFile`
        that describes the input BIDS-formatted preprocessed EEG file

    events_file : CustomEEGEventsBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGEventsBIDSFile`
        that describes the input BIDS-formatted EEG events file

    electrodes_file_fmt : Enum(["BIDS", "Cartool"])
        Select the type of tabular file describing electrode positions

    bids_electrodes_file : CustomEEGElectrodesBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGElectrodesBIDSFile`
        that describes the input BIDS-compliant EEG electrode file

    cartool_electrodes_file : CustomEEGCartoolElectrodesBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolElectrodesBIDSFile`
        that describes the input BIDS-formatted EEG electrode file created by Cartool

    t_min : Float
        Start time of the epochs in seconds, relative to the time-locked event
        (Default: -0.2)

    t_max : Float
        End time of the epochs in seconds, relative to the time-locked event
        (Default: 0.5)

    See Also
    --------
    cmp.stages.eeg.preparer.EEGPreprocessingStage
    """

    task_label = Str("Undefined", desc="Task label (e.g. _task-<label>_)")

    eeg_ts_file = Instance(
        CustomEEGPreprocBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGPreprocBIDSFile`"
             "that describes the input BIDS-formatted preprocessed EEG file"
    )

    events_file = Instance(
        CustomEEGEventsBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGEventsBIDSFile`"
             "that describes the input BIDS-formatted EEG events file"
    )

    electrodes_file_fmt = Enum(
        "BIDS", "Cartool",
        desc="Select the type of tabular file describing electrode positions"
    )

    bids_electrodes_file = Instance(
        CustomEEGElectrodesBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGElectrodesBIDSFile`"
             "that describes the input BIDS-compliant EEG electrode file"
    )

    cartool_electrodes_file = Instance(
        CustomEEGCartoolElectrodesBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolElectrodesBIDSFile`"
             "that describes the input BIDS-formatted EEG electrode file created by Cartool"
    )

    t_min = Float(-0.2, desc="Start time of the epochs in seconds, relative to the time-locked event.")
    t_max = Float(0.5, desc="End time of the epochs in seconds, relative to the time-locked event.")

    def _task_label_changed(self, new):
        self.eeg_ts_file.task = new
        self.events_file.task = new
        self.bids_electrodes_file.task = new

    def __str__(self):
        str_repr = '\tEEGPreprocessingConfig:\n'
        str_repr += f'\t\t* task_label: {self.task_label}\n'
        str_repr += f'\t\t* eeg_ts_file: {self.eeg_ts_file}\n'
        str_repr += f'\t\t* events_file: {self.events_file}\n'
        str_repr += f'\t\t* electrodes_file_fmt: {self.electrodes_file_fmt}\n'
        str_repr += f'\t\t* cartool_electrodes_file: {self.cartool_electrodes_file}\n'
        str_repr += f'\t\t* bids_electrodes_file: {self.bids_electrodes_file}\n'
        str_repr += f'\t\t* t_min: {self.t_min}\n'
        str_repr += f'\t\t* t_max: {self.t_max}\n'
        return str_repr


class EEGPreprocessingStage(Stage):
    """Class that represents the preprocessing stage of a :class:`~cmp.pipelines.functional.eeg.EEGPipeline`.

    This stage consists of converting EEGLab `.set` EEG files to MNE Epochs in `.fif` format, the format used in the rest of the pipeline
    by calling, if necessary the following interface:

        - :class:`~cmtklib.interfaces.mne.EEGLAB2fif`: Reads eeglab data and converts them to MNE format (`.fif` file extension).

    See Also
    --------
    cmp.pipelines.functional.eeg.EEGPipeline
    cmp.stages.eeg.preparer.EEGPreprocessingConfig
    """
    def __init__(self, subject, session, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.eeg.prerocessing.EEGPreprocessingStage` instance."""
        self.name = 'eeg_preprocessing_stage'
        self.bids_subject_label = subject
        self.bids_session_label = session
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGPreprocessingConfig()
        self.inputs = [
            "eeg_ts_file",
            "events_file",
            "electrodes_file",
        ]
        self.outputs = [
            "epochs_file",
        ]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the EEG pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """
        if self.config.eeg_ts_file.extension == "set":
            events_derivatives_dir = self.config.events_file.get_toolbox_derivatives_dir()
            eeglab2fif_node = pe.Node(
                interface=EEGLAB2fif(
                    out_epochs_fif_fname='epo.fif',
                    event_ids=self.config.events_file.extract_event_ids_from_json_sidecar(
                        base_dir=(self.bids_dir
                                  if events_derivatives_dir == ""
                                  else os.path.join(self.bids_dir, 'derivatives', events_derivatives_dir)),
                        subject=self.bids_subject_label,
                        session=self.bids_session_label
                    ),
                    t_min=self.config.t_min,
                    t_max=self.config.t_max
                ),
                name="eeglab2fif"
            )
            # fmt: off
            flow.connect(
                [
                    (inputnode, eeglab2fif_node, [('eeg_ts_file', 'eeg_ts_file'),
                                                  ('events_file', 'events_file'),
                                                  ('electrodes_file', 'electrodes_file')]),
                    (eeglab2fif_node, outputnode, [('epochs_file', 'epochs_file')])
                ]
            )
            # fmt: on
        else:  # Already in fif format
            # fmt: off
            flow.connect(
                [
                    (inputnode, outputnode, [('eeg_ts_file', 'epochs_file')])
                ]
            )
            # fmt: on

    def define_inspect_outputs(self):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        self.inspect_outputs_dict = {}

        subject_derivatives_dir = os.path.join(
            self.output_dir, __cmp_directory__, self.bids_subject_label
        )
        if self.bids_session_label and self.bids_session_label != "":
            subject_derivatives_dir = os.path.join(
                subject_derivatives_dir, self.bids_session_label
            )

        subject_part = (f'{self.bids_subject_label}_{self.bids_session_label}'
                        if self.bids_session_label and self.bids_session_label != ""
                        else f'{self.bids_subject_label}')

        epo_fname = f'{subject_part}_task-{self.config.task_label}_epo.fif'
        epo_file = os.path.join(subject_derivatives_dir, "eeg", epo_fname)

        if os.path.exists(epo_file):
            self.inspect_outputs_dict[f"Epochs * Electrodes time series (Task:{self.config.task_label})"] = [
                "visualize_eeg_pipeline_outputs",
                "--epo_file", epo_file
            ]

        if not self.inspect_outputs_dict:
            self.inspect_outputs = ["Outputs not available"]
        else:
            self.inspect_outputs = sorted(
                [key for key in list(self.inspect_outputs_dict.keys())], key=str.lower
            )
