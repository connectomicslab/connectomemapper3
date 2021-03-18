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
from dev.cmtklib_dev.interfaces.eeglab2fif import EEGLAB2fif
from dev.cmtklib_dev.interfaces.createrois import CreateRois
from cmtklib.util import get_pipeline_dictionary_outputs

class EEGPreprocessingConfig(HasTraits):

    eeg_format = Enum('.set', '.fif',
                                   desc='<.set|.fif> (default is .set)')
    inverse_solution = List(
        ['Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA'])

    parcellation_scheme = Str('Lausanne2008')
    parcellation_scheme_editor = List(
        ['NativeFreesurfer', 'Lausanne2008', 'Lausanne2018'])

class EEGPreprocessingStage(Stage):
    def __init__(self, pipeline_mode, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.parcellation.parcellation.ParcellationStage` instance."""
        self.name = 'eeg_preprocessing_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGPreprocessingConfig()
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["eeg_ts_file", "behav_file", "epochs_fif_fname",
                       "subject_id","parcellation","cmp3_dir","cartool_dir"]
        self.outputs = ["fif_ts_file","rois_pickle"]

    def create_workflow(self, flow, inputnode, outputnode):
        

        if self.config.eeg_format == ".set":
            eeglab2fif_node = pe.Node(EEGLAB2fif(), name="eeglab2fif")

            flow.connect([(inputnode, eeglab2fif_node,
                 [('epochs','eeg_ts_file'),
                  ('behav_file','behav_file'),
                  ('epochs_fif_fname','epochs_fif_fname'),
                 ]
                    )])
            flow.connect([(eeglab2fif_node,outputnode,
                 [
                  ('epochs_fif_fname','epochs_fif_fname'),
                 ]
                    )])
            
        if self.config.invsol.split('-')[0] == "Cartool":
        	createrois_node = pe.Node(CreateRois(), name="createrois")
            flow.connect([(inputnode, createrois_node,
                 [('subject_id','subject_id'),
                  ('parcellation','parcellation'),
                  ('cartool_dir','cartool_dir'),
                  ('cmp3_dir','cmp3_dir'),
                 ]
                    )])
            flow.connect([(createrois_node, outputnode,
                 [
                  ('rois_pickle','rois_pickle'),
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