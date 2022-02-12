#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 15:01:03 2021

@author: katha

Create a fake pipeline to test the new MNE inverse solution interface. 
Code pieces gathered from cmp/pipelines/functional/eeg.py

"""
# basic python modules import
import pdb 
import getpass
import os

# specific python modules import
import pandas as pd
import mne

# nipype imports 
import nipype.pipeline.engine as pe
from nipype.interfaces.utility import IdentityInterface
import nipype.interfaces.io as nio

from traits.api import *

# cmp imports
import cmp.pipelines.common as cmp_common
from cmp.pipelines.common import * # contains class Pipeline
from cmp.stages.common import Stage
import cmp.project
from cmp.stages.eeg.eeg_inverse_solution import EEGInverseSolutionStage
from cmtklib.config import eeg_load_config_json

class Global_Configuration(HasTraits): # copied from eeg.py

	process_type = Str('EEG')
	subjects = List(trait=Str)
	subject = Str
	subject_session = Str
    
class FakeEEGPipeline(Pipeline):
    # bits and pieces of project.py init_eeg_project and eeg.py 
    pipeline_name = Str("Fake_EEG_pipeline")
    global_conf = Global_Configuration()
    flow =  Instance(pe.Workflow)
    
    def __init__(self, project_info):
        self.stages = {'EEGInverseSolution': EEGInverseSolutionStage(bids_dir=project_info.base_directory, 														   output_dir=self.output_directory),
					   }
        self.output_directory = os.path.join(project_info.base_directory, "derivatives")
        self.subject = project_info.subject
        self.subject_id = project_info.subject_id
        
        cmp_common.Pipeline.__init__(self, project_info)	

    def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):    		
        datasource = pe.Node(interface=util.IdentityInterface(
					fields=['base_directory',
							'subject_id',
							'cmp_deriv_subject_directory',
							'nipype_deriv_subject_directory',							
							], 
					mandatory_inputs=True), name="datasource")

        datasource.inputs.base_directory = self.base_directory
        datasource.inputs.subject_id = self.subject_id
        datasource.inputs.cmp_deriv_subject_directory = cmp_deriv_subject_directory
        datasource.inputs.nipype_deriv_subject_directory = nipype_deriv_subject_directory

        datasource.inputs.epochs = [os.path.join(self.base_directory,'derivatives','eeglab','sub-'+self.subject_id,self.subject_id+'_FACES_250HZ_prepd.set')]
                
        datasource.inputs.behav_file = [os.path.join(self.base_directory,'derivatives','eeglab','sub-'+self.subject_id,'sub-'+self.subject_id+'_FACES_250HZ_behav.txt')]
        
        datasource.inputs.epochs_fif_fname = os.path.join(self.base_directory,'derivatives','cmp','sub-'+self.subject_id,'eeg','sub-'+self.subject_id+'_epo.fif')
        
        datasource.inputs.roi_ts_file = os.path.join(self.base_directory,'derivatives','cmp','sub-'+self.subject_id,'eeg','sub-'+self.subject_id+'_rtc_epo.npy')
        
        datasource.inputs.parcellation = [os.path.join(self.base_directory,'derivatives','cmp','sub-'+self.subject_id,'anat','sub-'+self.subject_id+'_label-L2008_desc-scale1_atlas.nii.gz')]
        
        datasource.inputs.eeg_ts_file = datasource.inputs.epochs
    
        datasource.inputs.output_query = dict()

        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="eeg_sinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)     
        
        eeg_flow = pe.Workflow(name='eeg_pipeline', 
							   base_dir= os.path.abspath(nipype_deriv_subject_directory))
        invsol_flow = self.create_stage_flow("EEGInverseSolution")
        
        eeg_flow.connect([
						  (datasource, invsol_flow, 
						   [
							('eeg_ts_file','inputnode.eeg_ts_file'),
                            ('subject','inputnode.subject'),
                            ('base_directory','inputnode.base_directory')
							]),
						 ])
        
        eeg_flow.connect([			
			(invsol_flow, sinker, [("outputnode.roi_ts_file", "eeg.@roi_ts_file")]),
		])
        
        self.flow = eeg_flow
        return eeg_flow
	
    def process(self):
        cmp_deriv_subject_directory = os.path.join(
				self.output_directory, "cmp", self.subject)
        nipype_deriv_subject_directory = os.path.join(
				self.output_directory, "nipype", self.subject)
        
        eeg_flow = self.create_pipeline_flow(cmp_deriv_subject_directory, nipype_deriv_subject_directory)
        
        eeg_flow.write_graph(graph2use='colored',
							  format='svg', simple_form=True)
        eeg_flow.run()

        
class EEGFakeInputStage(Stage): 
    def __init__(self, bids_dir, output_dir):
        self.name = 'eeg_fake_input_stage'
        self.inputs = ["eeg_format","invsol_format","epochs","behav_file","parcellation","cartool_dir","cmp3_dir","output_query","epochs_fif_fname","subject_id","derivative_list"]
        self.outputs = ["output_query","invsol_params","derivative_list"]
        

# create project with project info 
username = getpass.getuser()
if username=='katha':
    bids_dir = '/home/katha/data/DS001_BIDS'
elif username=='katharina':
    bids_dir = '/mnt/data/Lausanne/DS001_BIDS'

project = cmp.project.CMP_Project_Info()
project.base_directory = bids_dir
participant_label = '01'
project.subjects = ['{}'.format(participant_label)]
project.subject = '{}'.format(participant_label)
project.subject_id = '{}'.format(participant_label)
project.subject_sessions = ['']
project.subject_session = ''

project.number_of_cores = 1

# MNE: 
eeg_pipeline_config = '/mnt/data/Lausanne/DS001_BIDS/code/ref_mne_eeg_config.json'
# Cartool (default): 
# eeg_pipeline_config = '/mnt/data/Lausanne/DS001_BIDS/code/ref_eeg_config.json'
project.eeg_config_file = os.path.abspath(eeg_pipeline_config)

# create the pipeline 
eeg_test_pipeline = FakeEEGPipeline(project)
eeg_conf_loaded = eeg_load_config_json(eeg_test_pipeline, project.eeg_config_file)

# eeg_test_pipeline.config_file = project.eeg_config_file
eeg_test_pipeline.process()


# create mne epochs file 
# taken from eeglab2fif interface 
behav_file = eeg_test_pipeline.flow.inputs.datasource.behav_file
epochs_file = eeg_test_pipeline.flow.inputs.datasource.epochs
epochs_fif_fname = eeg_test_pipeline.flow.inputs.datasource.epochs_fif_fname
behav = pd.read_csv(behav_file[0], sep=",")
behav = behav[behav.bad_trials == 0]
epochs = mne.read_epochs_eeglab(epochs_file[0], events=None, event_id=None, eog=(), verbose=None, uint16_codec=None)
epochs.events[:,2] = list(behav.COND)
epochs.event_id = {"Scrambled":0, "Faces":1}
if not os.path.exists(os.path.join(bids_dir,'derivatives','cmp','eeg','sub-'+participant_label)):
    os.makedirs(os.path.join(bids_dir,'derivatives','cmp','eeg','sub-'+participant_label))
epochs.save(epochs_fif_fname,overwrite=True)

# info about parcellation 
#eeg_pipeline.parcellation_scheme = anat_pipeline.parcellation_scheme
#eeg_pipeline.atlas_info = anat_pipeline.atlas_info



pdb.set_trace()
