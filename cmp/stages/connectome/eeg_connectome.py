# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for building functional connectivity matrices from preprocessed EEG."""

# Global imports
from traits.api import (
    HasTraits, List
)

# Nipype imports
import nipype.pipeline.engine as pe

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.mne import MNESpectralConnectivity


class EEGConnectomeConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.connectome.eeg_connectome.EEGConnectomeStage` instance.

    Attributes
    ----------
    connectivity_metrics : ['coh', 'cohy', 'imcoh', 'plv', 'ciplv', 'ppc', 'pli', 'wpli', 'wpli2_debiased']
        Set of frequency- and time-frequency-domain connectivity metrics to compute

    output_types: ['tsv', 'gpickle', 'mat', 'graphml']
        Output connectome file format

    See Also
    --------
    cmp.stages.connectome.eeg_connectome.EEGConnectomeStage
    """
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

    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.connectome.eeg_connectome.EEGConnectomeStage` instance."""
        self.name = "eeg_connectome_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = EEGConnectomeConfig()
        self.inputs = ["roi_ts_file", "epochs_file"]
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
                                       ("roi_ts_file", "roi_ts_file")]),
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
