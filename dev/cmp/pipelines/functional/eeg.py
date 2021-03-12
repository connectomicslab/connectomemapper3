# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" EEG pipeline Class definition
"""

import datetime
import os
import glob
import shutil

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from nipype import config, logging

from traits.api import *

from cmp.pipelines.common import *
from cmp.stages.eeg.eeg_preprocessing import EEGPreprocessingStage
from cmp.stages.eeg.eeg_inverse_solution import EEGInverseSolutionStage


 
class Global_Configuration(HasTraits):

    process_type = Str('EEG')
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str


class EEGPipeline(Pipeline):
	now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("EEG_pipeline")
    input_folders = ['anat','eeg']    
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ['EEGPreprocessing',
                          'InverseSolution']
    
	global_conf = Global_Configuration()
    config_file = Str

    eeg_format = Str
    subjects_dir = Str
    subject_id = Str

    flow =  Instance(pe.Workflow)

    def __init__(self, project_info):
    	self.subjects_dir = project_info.freesurfer_subjects_dir
        self.subject_id = project_info.freesurfer_subject_id
        self.subject = project_info.subject

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = project_info.subject

		if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory = os.path.join(project_info.base_directory,
                                                  project_info.subject,
                                                  project_info.subject_session)
        else:
            self.global_conf.subject_session = ''
            self.subject_directory = os.path.join(project_info.base_directory,
                                                  project_info.subject)

		self.derivatives_directory = os.path.abspath(project_info.output_directory)

        if project_info.output_directory is not None:
            self.output_directory = os.path.abspath(project_info.output_directory)
        else:
            self.output_directory = os.path.join(self.base_directory, "derivatives")

        self.stages = {'EEGPreprocessing': EEGPreprocessing(bids_dir=project_info.base_directory,
                                                           output_dir=self.output_directory),
                       'EEGInverseSolution': EEGInverseSolution(bids_dir=project_info.base_directory,
                                                           output_dir=self.output_directory),
                       }
        cmp_common.Pipeline.__init__(self, project_info)

		self.stages['EEGPreprocessing'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
        self.stages['EEGInverseSolution'].config.on_trait_change(self.update_parcellation_scheme, 'parcellation_scheme')
       	
    def check_config(self):
    	raise NotImplementedError
    def check_inpuf(self):
    	raise NotImplementedError
    def check_output(self):
    	raise NotImplementedError

	def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):
		datasource = pe.Node(interface=nio.BIDSDataGrabber(index_derivatives=True), name='bids-grabber',anat_only=False)
		datasource.inputs.base_dir = self.base_directory
		datasource.inputs.subject = self.subject_id
		datasource.inputs.output_query = {
											'EEG': {
													'scope': 'EEGLAB',
													'suffix': 'prepd',
													'extensions': ['set']
													},
											'behav': {'scope': 'EEGLAB',
				                                	'suffix': 'behav',
				                                    'extensions': ['txt']},
											'rois_file': {
													'scope': 'Cartool',
									    			'suffix': 'scale3',
									        		'extensions': ['rois']
									        		},
									        'src_file': {
									        		'scope': 'Cartool',
									        		'extensions': ['spi']
									    			},
											'invsol_file': {
													'scope': 'Cartool',
									        		'extensions': ['LAURA.is']
									        		},
									        }
        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="eeg_sinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)

         # Clear previous outputs
        self.clear_stages_outputs()

        # Create common_flow
        eeg_flow = pe.Workflow(name='eeg_pipeline', base_dir=os.path.abspath(
            nipype_deriv_subject_directory))


        eeg_inputnode = pe.Node(interface=util.IdentityInterface(
        					fields=['epochs', 
                                    'behav', 
                                    'src_file', 
                                    'invsol_file', 
                                    'lamda', 
                                    'rois_file', 
                                    'svd_params'
                                    ], 
                            mandatory_inputs=True), name="inputnode")

        eeg_outputnode = pe.Node(interface=util.IdentityInterface(
            				fields=["roi_ts_file"]), name="outputnode")

        eeg_flow.add_nodes([eeg_inputnode, eeg_outputnode])

        eeg_flow.connect([
            (datasource, eeg_inputnode, 
            	[("EEG", "epochs"),
            	('behav','behav_file'),
            	('src_file','src_file')
            	('invsol_file','invsol_file'),            	
            	]),
        ])

        eeg_flow.connect([(eeg_inputnode, eeglab2fif_node,
        				 [('epochs','eeg_ts_file'),
                          ('behav','behav_file'),
                         ]
            )])

		eeg_flow.connect([(eeg_inputnode, is_node,
						 [('src_file','src_file'),
                          ('invsol_file','invsol_file'),
                          ('lamda','lamda'),
                          ('rois_file','rois_file'),
                          ('svd_params','svd_params'),
                         ]
            )])

		eeg_flow.connect([(eeglab2fif_node, is_node,
						 [('fif_ts_file','epochs_file'),
                          
                         ]
            )])

		eeg_flow.connect([(is_node, eeg_outputnode,
						 [('roi_ts_file','roi_ts_file'),
                         ]
            )])
