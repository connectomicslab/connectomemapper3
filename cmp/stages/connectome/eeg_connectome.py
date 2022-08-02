# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for building functional connectivity matrices from preprocessed EEG."""

# Global imports
import os
from traits.api import (
    HasTraits, List, Enum
)

# Nipype imports
import nipype.pipeline.engine as pe

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.mne import MNESpectralConnectivity
from cmtklib.bids.io import __freesurfer_directory__


class EEGConnectomeConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.connectome.eeg_connectome.EEGConnectomeStage` instance.

    Attributes
    ----------
    parcellation_scheme : Enum(["NativeFreesurfer", "Lausanne2018"])
        Parcellation used to create the ROI source time-series

    lausanne2018_parcellation_res : Enum(["scale1", "scale2", "scale3", "scale4", "scale5"])
        Resolution of the parcellation if Lausanne2018 parcellation scheme is used

    connectivity_metrics : ['coh', 'cohy', 'imcoh', 'plv', 'ciplv', 'ppc', 'pli', 'wpli', 'wpli2_debiased']
        Set of frequency- and time-frequency-domain connectivity metrics to compute

    output_types: ['tsv', 'gpickle', 'mat', 'graphml']
        Output connectome file format

    See Also
    --------
    cmp.stages.connectome.eeg_connectome.EEGConnectomeStage
    """
    parcellation_scheme = Enum(
        "NativeFreesurfer", "Lausanne2018",
        desc="Parcellation used to create the ROI source time-series"
    )

    lausanne2018_parcellation_res = Enum(
        "scale1", "scale2", "scale3", "scale4", "scale5",
        desc="Resolution of the parcellation if Lausanne2018 "
             "parcellation scheme is used "
    )
    connectivity_metrics = List(
        ['coh', 'cohy', 'imcoh',
         'plv', 'ciplv', 'ppc',
         'pli', 'wpli', 'wpli2_debiased']
    )

    output_types = List(['tsv', 'gpickle', 'mat', 'graphml'])

    def __str__(self):
        str_repr = '\tEEGSourceImagingConfig:\n'
        str_repr += f'\t\t* connectivity_metrics: {self.connectivity_metrics}\n'
        str_repr += f'\t\t* output_types: {self.output_types}\n'
        return str_repr


class EEGConnectomeStage(Stage):
    """Class that represents the connectome building stage of a :class:`~cmp.pipelines.functional.eeg.EEGPipeline`.

    Methods
    -------
    create_workflow()
        Create the workflow of the EEG `EEGConnectomeStage`

    See Also
    --------
    cmp.pipelines.functional.eeg.EEGPipeline
    cmp.stages.connectome.eeg_connectome.EEGConnectomeConfig
    """

    def __init__(self, bids_dir, output_dir, subject, session=""):
        """Constructor of a :class:`~cmp.stages.connectome.eeg_connectome.EEGConnectomeStage` instance."""
        self.name = "eeg_connectome_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.fs_subjects_dir = os.path.join(
            bids_dir, 'derivatives', f'{__freesurfer_directory__}'
        )
        self.fs_subject = (subject
                           if session == "" or session is None
                           else '_'.join([subject, session]))

        self.config = EEGConnectomeConfig()
        self.inputs = ["roi_ts_file", "epochs_file", "roi_volume_tsv_file"]
        self.outputs = ["connectivity_matrices"]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the Diffusion pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """

        eeg_cmat = pe.Node(
            interface=MNESpectralConnectivity(
                fs_subject=self.fs_subject,
                fs_subjects_dir=self.fs_subjects_dir,
                atlas_annot=(f'lausanne2018.{self.config.lausanne2018_parcellation_res}'
                            if self.config.parcellation_scheme == "Lausanne2018"
                            else 'aparc'),
                connectivity_metrics=self.config.connectivity_metrics,
                output_types=self.config.output_types,
                out_cmat_fname="conndata-network_connectivity"
            ),
            name="eeg_compute_matrice"
        )

        # fmt: off
        flow.connect(
            [
                (inputnode, eeg_cmat, [("epochs_file", "epochs_file"),
                                       ("roi_ts_file", "roi_ts_file"),
                                       ("roi_volume_tsv_file", "roi_volume_tsv_file")]),
                (eeg_cmat, outputnode, [("connectivity_matrices", "connectivity_matrices")])
            ]
        )
        # fmt: on

    def define_inspect_outputs(self):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        self.inspect_outputs_dict = {}
        self.inspect_outputs = ["Outputs not available"]
