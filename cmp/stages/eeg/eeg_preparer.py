# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
from cmtklib.interfaces.eeglab2fif import EEGLAB2fif
from cmtklib.interfaces.createrois import CreateRois
from cmtklib.interfaces.createsrc import CreateSrc
from cmtklib.interfaces.createbem import CreateBEM


class EEGPreparerConfig(HasTraits):
    eeg_format = Enum('.set', '.fif',
                      desc='<.set|.fif> (default is .set)')
    invsol_format = Enum('Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA',
                         desc='Cartool vs mne')

    parcellation = Str('Lausanne2008')
    cartool_dir = Str()
    cmp3_dir = Str()


class EEGPreparerStage(Stage):
    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.parcellation.parcellation.ParcellationStage` instance."""
        self.name = 'eeg_preparing_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGPreparerConfig()
        self.inputs = [
            "eeg_format",
            "invsol_format",
            "epochs",
            "behav_file",
            "parcellation",
            "cartool_dir",
            "cmp3_dir",
            "output_query",
            "epochs_fif_fname",
            "subject",
            "derivative_list",
            "bids_dir",
        ]
        self.outputs = [
            "output_query",
            "invsol_params",
            "derivative_list"
        ]

    def create_workflow(self, flow, inputnode, outputnode):
        inputnode.inputs.derivative_list = []
        inputnode.inputs.output_query = {}
        if self.config.eeg_format == ".set":

            eeglab2fif_node = pe.Node(EEGLAB2fif(), name="eeglab2fif")
            flow.connect([(inputnode, eeglab2fif_node,
                           [('epochs', 'eeg_ts_file'),
                            ('behav_file', 'behav_file'),
                            ('epochs_fif_fname', 'epochs_fif_fname'),
                            ('output_query', 'output_query'),
                            ('derivative_list', 'derivative_list'),
                            ]
                           )])

            if (not self.config.invsol_format.split('-')[0] == "Cartool") & (not self.config.invsol_format.split('-')[0] == "mne"):
                flow.connect([(eeglab2fif_node, outputnode,
                               [('output_query', 'output_query'),
                                ('derivative_list', 'derivative_list')]
                               )])

        if self.config.invsol_format.split('-')[0] == "Cartool":

            createrois_node = pe.Node(CreateRois(), name="createrois")
            inputnode.inputs.parcellation = self.config.parcellation
            inputnode.inputs.cartool_dir = self.config.cartool_dir
            inputnode.inputs.cmp3_dir = self.config.cmp3_dir

            if self.config.eeg_format == ".set":

                flow.connect([(eeglab2fif_node, createrois_node,
                               [('output_query', 'output_query'),
                                ('derivative_list', 'derivative_list')]
                               )])

            else:
                flow.connect([(inputnode, createrois_node,
                               [('output_query', 'output_query'),
                                ('derivative_list', 'derivative_list')]
                               )])

            flow.connect([(inputnode, createrois_node,
                           [('subject', 'subject'),
                            ('parcellation', 'parcellation'),
                            ('cartool_dir', 'cartool_dir'),
                            ('cmp3_dir', 'cmp3_dir'),
                            ]
                           )])
            flow.connect([(createrois_node, outputnode,
                           [('output_query', 'output_query'),
                            ('derivative_list', 'derivative_list')]
                           )])

            ii = pe.Node(interface=util.IdentityInterface(
                fields=['invsol_params', 'roi_ts_file'],
                mandatory_inputs=True), name="identityinterface")

            ii.inputs.roi_ts_file = ''
            ii.inputs.invsol_params = {'lamda': 6,
                                       'svd_params': {'toi_begin': 120,
                                                      'toi_end': 500}
                                       }
            flow.connect([(ii, outputnode,
                           [('invsol_params', 'invsol_params')]
                           )])
            
        elif self.config.invsol_format.split('-')[0] == "mne":
            
            createsrc_node = pe.Node(CreateSrc(), name="createsrc")
            createbem_node = pe.Node(CreateBEM(), name="createbem")
            inputnode.inputs.base_dir = self.bids_dir
            # inputnode.inputs.subject = self.subject
            
            # create source space 
            flow.connect([(eeglab2fif_node, createsrc_node,
                           [('output_query', 'output_query'),
                            ('derivative_list', 'derivative_list')]                           
                           )])            
            flow.connect([(inputnode, createsrc_node,
                           [('subject', 'subject'),
                            ('bids_dir', 'bids_dir'),
                            ]
                           )])
            
            # create boundary element model (BEM) 
            flow.connect([(inputnode, createbem_node,
                           [('subject', 'subject'),
                            ('bids_dir', 'bids_dir'),
                            ]
                           )])
            
            flow.connect([(createsrc_node, createbem_node,
                           [('output_query', 'output_query'),
                            ('derivative_list', 'derivative_list')]
                           )])
            
            # outputnode  
            flow.connect([(createbem_node, outputnode,
                           [('output_query', 'output_query'),
                            ('derivative_list', 'derivative_list')]
                           )])

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
