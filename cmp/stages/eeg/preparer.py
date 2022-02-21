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
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.eeg import CreateRois
from cmtklib.interfaces.mne import CreateBEM, CreateSrc, EEGLAB2fif


class EEGPreparerConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.eeg.preparer.EEGPreparerStage` instance.

    Attributes
    ----------
    eeg_format : Enum(['.set', '.fif'])
        Specify the format in which EGG data is stored
        (Default: `.set`)

    epochs : File
        Name of file containing EEG epochs

    invsol_format : Enum(['Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA'])
        Specify the inverse solution algorithm
        (Default: Cartool-LAURA)

    parcellation = Dict({'label':'aparc', 'desc':'', 'suffix':''})
        Dictionary used to differentiate parcellation files

    cartool_dir = Str
        Name of cartool derivatives directory
        (Default: `'cartool-v3.80'`)

    cmp3_dir = Str
        Name of cartool derivatives directory
        (Default: `'cmp'`)

    EEG_params = Dict()
        Dictionary storing extra EEG parameters

    See Also
    --------
    cmp.stages.eeg.preparer.EEGPreparerStage
    """
    eeg_format = Enum('.set', '.fif',
                      desc='<.set|.fif> (default is .set)')
    epochs = File(desc='name of file containing EEG epochs')
    invsol_format = Enum('Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA',
                         desc='Cartool vs mne')

    parcellation = Dict({'label': 'aparc', 'desc': '', 'suffix': ''})
    cartool_dir = Str('cartool-v3.80')
    cmp3_dir = Str('cmp')
    EEG_params = Dict()


class EEGPreparerStage(Stage):
    """Class that represents the preparing stage of a :class:`~cmp.pipelines.functional.eeg.EEGPipeline`.

    This stage consists of three processing interfaces:

        - :class:`~cmtklib.interfaces.mne.EEGLAB2fif`: Reads eeglab data and converts them to MNE format (`.fif` file extension).
        - :class:`~cmtklib.interfaces.mne.CreateSrc`: Creates the dipole locations along the surface of the brain.
        - :class:`~cmtklib.interfaces.mne.CreateBEM`: Creates the boundary element method.


    Methods
    -------
    create_workflow()
        Create the workflow of the `EEGPreparerStage`

    See Also
    --------
    cmp.pipelines.functional.eeg.EEGPipeline
    cmp.stages.eeg.preparer.EEGPreparerConfig
    """
    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.eeg.preparer.EEGPreparer` instance."""
        self.name = 'eeg_preparer_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGPreparerConfig()
        self.inputs = [
            "eeg_format",
            "epochs",
            "behav_file",
            "parcellation",
            "cartool_dir",
            "cmp3_dir",
            "output_query",
            "epochs_fif_fname",
            "electrode_positions_file",
            "subject",
            "EEG_params",
            "derivative_list",
            "bids_dir"
        ]
        self.outputs = [
            "output_query",
            "invsol_params",
            "epochs_fif_fname",
            "derivative_list"
        ]

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
        inputnode.inputs.derivative_list = []
        inputnode.inputs.output_query = {}

        if "Cartool" in self.config.invsol_format:

            createrois_node = pe.Node(CreateRois(), name="createrois")
            inputnode.inputs.parcellation = self.config.parcellation
            inputnode.inputs.cartool_dir = self.config.cartool_dir
            inputnode.inputs.cmp3_dir = self.config.cmp3_dir

            if self.config.eeg_format == ".set":

                eeglab2fif_node = pe.Node(EEGLAB2fif(), name="eeglab2fif")
                # fmt: off
                flow.connect(
                    [
                        (inputnode, eeglab2fif_node, [('epochs', 'eeg_ts_file'),
                                                      ('behav_file', 'behav_file'),
                                                      ('epochs_fif_fname', 'epochs_fif_fname'),
                                                      ('EEG_params', 'EEG_params'),
                                                      ('output_query', 'output_query'),
                                                      ('derivative_list', 'derivative_list')]),
                        (eeglab2fif_node, createrois_node, [('output_query', 'output_query'),
                                                            ('derivative_list', 'derivative_list')])
                    ]
                )
                # fmt: on

            else:
                # fmt: off
                flow.connect(
                    [
                        (inputnode, createrois_node, [('output_query', 'output_query'),
                                                      ('derivative_list', 'derivative_list')])
                    ]
                )
                # fmt: on

            # fmt: off
            flow.connect(
                [
                    (inputnode, createrois_node, [('subject', 'subject'),
                                                  ('bids_dir', 'bids_dir'),
                                                  ('parcellation', 'parcellation'),
                                                  ('cartool_dir', 'cartool_dir'),
                                                  ('cmp3_dir', 'cmp3_dir')]),
                    (createrois_node, outputnode, [('output_query', 'output_query'),
                                                   ('derivative_list', 'derivative_list')])
                ]
            )
            # fmt: on

            ii = pe.Node(interface=util.IdentityInterface(
                fields=['invsol_params', 'roi_ts_file'],
                mandatory_inputs=True), name="identityinterface")

            ii.inputs.roi_ts_file = ''
            ii.inputs.invsol_params = {
                'lamda': 6,
                'svd_params': {
                    'toi_begin': 120,
                    'toi_end': 500
                }
            }
            # fmt: off
            flow.connect(
                [
                    (ii, outputnode,[('invsol_params', 'invsol_params')])
                ]
            )
            # fmt: on

        elif "mne" in self.config.invsol_format:

            createsrc_node = pe.Node(CreateSrc(), name="createsrc")
            createbem_node = pe.Node(CreateBEM(), name="createbem")
            inputnode.inputs.base_dir = self.bids_dir

            # Create source space
            if self.config.eeg_format == ".set":

                eeglab2fif_node = pe.Node(EEGLAB2fif(), name="eeglab2fif")

                # fmt: off
                flow.connect(
                    [
                        (inputnode, eeglab2fif_node, [('epochs', 'eeg_ts_file'),
                                                      ('behav_file', 'behav_file'),
                                                      ('epochs_fif_fname', 'epochs_fif_fname'),
                                                      ('electrode_positions_file','electrode_positions_file'),
                                                      ('EEG_params','EEG_params'),
                                                      ('output_query', 'output_query'),
                                                      ('derivative_list', 'derivative_list')]),
                        (eeglab2fif_node, createsrc_node, [('output_query', 'output_query'),
                                                           ('derivative_list', 'derivative_list')]),
                        (inputnode, createsrc_node, [('subject', 'subject'), ('bids_dir', 'bids_dir')])
                    ]
                )
                # fmt: on

            else:
                # fmt: off
                flow.connect(
                    [
                        (inputnode, createsrc_node, [('output_query', 'output_query'),
                                                     ('derivative_list', 'derivative_list'),
                                                     ('subject', 'subject'),
                                                     ('bids_dir', 'bids_dir')])
                    ]
                )
                # fmt: on

            # create boundary element model (BEM) and link the output node
            # fmt: off
            flow.connect(
                [
                    (inputnode, createbem_node, [('subject', 'subject'),
                                                 ('bids_dir', 'bids_dir')]),
                    (createsrc_node, createbem_node, [('output_query', 'output_query'),
                                                      ('derivative_list', 'derivative_list')]),
                    (createbem_node, outputnode,  [('output_query', 'output_query'),
                                                   ('derivative_list', 'derivative_list')]),
                    (eeglab2fif_node, outputnode, [('epochs_fif_fname', 'epochs_fif_fname')])
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
            if self.config.inverse_solution.split('-')[0] == "Cartool":
                return os.path.exists(self.config.epochs_fif)
