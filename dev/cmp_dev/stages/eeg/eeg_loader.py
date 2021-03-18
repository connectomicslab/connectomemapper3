# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for computing brain parcellation."""

# General imports
import os
from traits.api import *
import pkg_resources

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage
from dev.cmtklib_dev.interfaces.eegloader import EEGLoader
from cmtklib.util import get_pipeline_dictionary_outputs

class EEGLoaderConfig(HasTraits):

    eeg_format = Enum('.set', '.fif',
                                   desc='<.set|.fif> (default is .set)')
    inverse_solution = List(
        ['Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA'])

    parcellation_scheme = Str('Lausanne2008')
    parcellation_scheme_editor = List(
        ['NativeFreesurfer', 'Lausanne2008', 'Lausanne2018'])

class EEGLoaderStage(Stage):
    def __init__(self, pipeline_mode, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.parcellation.parcellation.ParcellationStage` instance."""
        self.name = 'eeg_loader_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGLoaderConfig()
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["subject_id", "base_directory"]
        self.outputs = ["EEG","events","src_file","invsol_file","parcellation"]


    def create_workflow(self, flow, inputnode, outputnode):
        
        
        eegloader_node = pe.Node(interface = EEGLoader(), name="eegloader")

        flow.connect([(inputnode, eegloader_node,
             [('subject_id','subject_id'),
              ('base_directory','base_directory')
             ]
                )])
        flow.connect([(eegloader_node,outputnode,
             [
              ('EEG','EEG'),
              ('events','events'),
              ('src_file','src_file'),
              ('invsol_file','invsol_file'),
              ('parcellation','parcellation'),              
             ]
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
