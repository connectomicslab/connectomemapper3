#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 15:01:03 2021

@author: katha

Create a fake pipeline to test the new MNE inverse solution interface. 
Code pieces gathered from cmp/pipelines/functional/eeg.py

"""

import pdb

import nipype.pipeline.engine as pe
from nipype.interfaces.utility import IdentityInterface

from traits.api import *

# cmp imports
import cmp.pipelines.common as cmp_common
from cmp.pipelines.common import * # contains class Pipeline
from cmp.stages.common import Stage
import cmp.project
from cmp.stages.eeg.eeg_inverse_solution import EEGInverseSolutionStage


class FakeEEGPipeline(Pipeline):
    pipeline_name = Str("Fake_EEG_pipeline")
    
    def __init__(self, project_info):
        self.stages = {#'EEGFakeInput' : EEGFakeInputStage(bids_dir=project_info.base_directory,
						#								   output_dir=self.output_directory), 
					   'EEGInverseSolution': EEGInverseSolutionStage(bids_dir=project_info.base_directory,
														   output_dir=self.output_directory),
					   }
        self.output_directory = os.path.join(project_info.base_directory, "derivatives")
        self.subject = project_info.subject
        
        cmp_common.Pipeline.__init__(self, project_info)	
        
    def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):    		
        datasource = pe.Node(interface=util.IdentityInterface(
					fields=['base_directory',
							'subject_id',
							'cmp_deriv_subject_directory',
							'nipype_deriv_subject_directory',							
							], 
					mandatory_inputs=True), name="datasource")


        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="eeg_sinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)     
        
        eeg_flow = pe.Workflow(name='eeg_pipeline', 
							   base_dir= os.path.abspath(nipype_deriv_subject_directory))

        invsol_flow = self.create_stage_flow("EEGInverseSolution")    
	
    def process(self):
        cmp_deriv_subject_directory = os.path.join(
				self.output_directory, "cmp", self.subject)
        nipype_deriv_subject_directory = os.path.join(
				self.output_directory, "nipype", self.subject)
        
        self.create_pipeline_flow(cmp_deriv_subject_directory, nipype_deriv_subject_directory)

        
class EEGFakeInputStage(Stage): 
    def __init__(self, bids_dir, output_dir):
        self.name = 'eeg_fake_input_stage'
        self.inputs = ["eeg_format","invsol_format","epochs","behav_file","parcellation","cartool_dir","cmp3_dir","output_query","epochs_fif_fname","subject_id","derivative_list"]
        self.outputs = ["output_query","invsol_params","derivative_list"]
        

# create project with project info 
bids_dir = '/home/katha/data/DS001_BIDS'

project = cmp.project.CMP_Project_Info()
project.base_directory = bids_dir
#pdb.set_trace()
project.subject = "sub-01"
project.subject_sessions = ['']
project.subject_session = ''

project.number_of_cores = 1

eeg_test_pipeline = FakeEEGPipeline(project)

eeg_test_pipeline.process()

pdb.set_trace()

#self.stages[stage].stage_dir = os.path.join(self.base_directory, "derivatives", 'nipype', self.subject,
#                                                            project_info.subject_session, self.pipeline_name,
 #                                                           self.stages[stage].name)


