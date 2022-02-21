# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for computing brain parcellation."""

# General imports
import os
from traits.api import *

# Nipype imports
import nipype.pipeline.engine as pe

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.eeg import EEGLoader


class EEGLoaderConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.eeg.loader.EEGLoaderStage` instance.

    Attributes
    ----------
    invsol_format : ['Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA']
        Specify the inverse solution algorithm
        (Default: Cartool-LAURA)

    See Also
    --------
    cmp.stages.eeg.loader.EEGLoaderStage
    """

    invsol_format = Enum(
        "Cartool-LAURA", "Cartool-LORETA", "mne-sLORETA",
        desc="Specify the inverse solution algorithm"
    )


class EEGLoaderStage(Stage):
    """Class that represents inverse solution input loader stage of a :class:`~cmp.pipelines.functional.eeg.EEGPipeline`.

    This stage consists of one processing interface:

        - :class:`~cmtklib.interfaces.eeg.EEGLoader`: Use `nipype.interfaces.io.BIDSDataGrabber`
          to query all the necessary files to be passed as inputs to the inverse solution stage of
          the EEG pipeline.

    Methods
    -------
    create_workflow()
        Create the workflow of the `EEGLoaderStage`

    See Also
    --------
    cmp.pipelines.functional.eeg.EEGPipeline
    cmp.stages.eeg.loader.EEGLoaderConfig
    """

    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.eeg.loader.EEGLoaderStage` instance."""
        self.name = "eeg_loader_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGLoaderConfig()
        self.inputs = ["subject", "base_directory", "output_query", "derivative_list"]
        self.outputs = ["EEG", "src", "invsol", "rois", "bem"]

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
        eegloader_node = pe.Node(interface=EEGLoader(), name="eegloader")

        # fmt: off
        flow.connect(
            [
                (inputnode, eegloader_node, [('subject', 'subject'),
                                             ('base_directory', 'base_directory'),
                                             ('output_query', 'output_query'),
                                             ('derivative_list', 'derivative_list')]),
                (eegloader_node, outputnode, [('EEG', 'EEG'),
                                              ('src', 'src'),
                                              ('invsol', 'invsol'),
                                              ('rois', 'rois'),
                                              ('bem', 'bem')])
            ]
        )
        # fmt: on

    def define_inspect_outputs(self):
        raise NotImplementedError

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        if self.config.eeg_format == ".set":
            if "Cartool" in self.config.inverse_solution:
                return os.path.exists(self.config.epochs_fif)
