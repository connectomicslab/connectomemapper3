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

import cmp.pipelines.common as cmp_common
from cmp.pipelines.common import *
from cmp.stages.eeg.eeg_loader import EEGLoaderStage
from cmp.stages.eeg.eeg_preparer import EEGPreparerStage
from cmp.stages.eeg.eeg_inverse_solution import EEGInverseSolutionStage

class Global_Configuration(HasTraits):

	process_type = Str('EEG')
	subjects = List(trait=Str)
	subject = Str
	subject_session = Str

class Check_Input_Notification(HasTraits):
	message = Str
	eeg_format_options = List(['set', 'fif'])
	eeg_format = Str
	eeg_format_message = Str(
		'\nMultiple EEG formats available. Please select desired EEG format.')

class EEGPipeline(Pipeline):
	now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
	pipeline_name = Str("EEG_pipeline")
	input_folders = ['anat','eeg']    
	subject = Str
	subject_directory = Directory
	derivatives_directory = Directory
	ordered_stage_list = ['EEGPreparer',
						  'EEGLoader',
						  'InverseSolution']

	global_conf = Global_Configuration()
	config_file = Str
	parcellation_scheme = Str
	atlas_info = Dict()
	eeg_format = Str
	subjects_dir = Str	

	flow =  Instance(pe.Workflow)

	def __init__(self, project_info):

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

		self.stages = {'EEGPreparer': EEGPreparerStage(bids_dir=project_info.base_directory,
														   output_dir=self.output_directory),
					   'EEGLoader': EEGLoaderStage(bids_dir=project_info.base_directory,
														   output_dir=self.output_directory),
					   'EEGInverseSolution': EEGInverseSolutionStage(bids_dir=project_info.base_directory,
														   output_dir=self.output_directory), #, invsol_format=self.
					   }
		
		cmp_common.Pipeline.__init__(self, project_info)

		self.stages['EEGPreparer'].config.cmp3_dir = os.path.join(self.derivatives_directory,'cmp')
		self.stages['EEGPreparer'].config.cartool_dir = os.path.join(self.derivatives_directory,'cartool')

		self.stages['EEGLoader'].config.eeg_format = self.stages['EEGPreparer'].config.eeg_format
		self.stages['EEGLoader'].config.invsol_format = self.stages['EEGPreparer'].config.invsol_format 
        
		#self.stages['EEGPreparer'].config.on_trait_change(self.update_eeg_format, 'eeg_format')

		#self.stages['EEGLoader'].config.on_trait_change(self.update_eeg_format, 'eeg_format')	
		#self.stages['EEGInverseSolution'].config.on_trait_change(self.update_parcellation_scheme, 'parcellation_scheme')
		
	def check_config(self):
		raise NotImplementedError
	def check_input(self,layout, gui=True):
		"""Check if input of the eeg pipeline are available.

        Parameters
        ----------
        layout : bids.BIDSLayout
            Instance of BIDSLayout

        gui : traits.Bool
            Boolean used to display different messages
            but not really meaningful anymore since the GUI
            components have been migrated to `cmp.bidsappmanager`

        Returns
        -------

        valid_inputs : traits.Bool
            True if inputs are available
        """
		print('**** Check Inputs is not still implemented ****')
		eeg_available = False
		epochs_available = False
		#valid_inputs = False
		valid_inputs = True
		return valid_inputs

	def check_output(self):
		raise NotImplementedError

	def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):    		
		datasource = pe.Node(interface=util.IdentityInterface(
					fields=['base_directory',
							'subject',
							'cmp_deriv_subject_directory',
							'nipype_deriv_subject_directory',							
							], 
					mandatory_inputs=True), name="datasource")

		datasource.inputs.base_directory = self.base_directory
		datasource.inputs.subject = self.subject
		datasource.inputs.cmp_deriv_subject_directory = cmp_deriv_subject_directory
		datasource.inputs.nipype_deriv_subject_directory = nipype_deriv_subject_directory

		if self.stages['EEGPreparer'].config.eeg_format == '.set':
			datasource.inputs.epochs = [os.path.join(self.base_directory,'derivatives','eeglab',self.subject,'eeg',self.subject+'_task-FACES_desc-preproc_eeg.set')]
			datasource.inputs.behav_file = [os.path.join(self.base_directory,'derivatives','eeglab',self.subject,'eeg',self.subject+'_task-FACES_events.txt')]
			datasource.inputs.epochs_fif_fname = os.path.join(self.base_directory,'derivatives','cmp',self.subject,'eeg',self.subject+'_epo.fif')
	
		datasource.inputs.roi_ts_file = os.path.join(self.base_directory,'derivatives','cmp',self.subject,'eeg',self.subject+'_rtc_epo.npy')
		if self.stages['EEGPreparer'].config.parcellation == 'Lausanne2008':
			datasource.inputs.parcellation = [os.path.join(self.base_directory,'derivatives','cmp',self.subject,'anat',self.subject+'_label-L2008_desc-scale2_atlas.nii.gz')]

		datasource.inputs.output_query = dict()

		# Data sinker for output
		sinker = pe.Node(nio.DataSink(), name="eeg_sinker")
		sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)        

		 # Clear previous outputs
		self.clear_stages_outputs()

		# Create common_flow
		eeg_flow = pe.Workflow(name='eeg_pipeline', 
							   base_dir= os.path.abspath(nipype_deriv_subject_directory))

		
		preparer_flow = self.create_stage_flow("EEGPreparer")        
		loader_flow = self.create_stage_flow("EEGLoader")    
		invsol_flow = self.create_stage_flow("EEGInverseSolution")    
	

		eeg_flow.connect([
						  (datasource, preparer_flow, 
						   [
							('epochs','inputnode.epochs'),
							('subject','inputnode.subject'),
							('behav_file','inputnode.behav_file'),
							('parcellation','inputnode.parcellation'),
							('epochs_fif_fname','inputnode.epochs_fif_fname'),
							('output_query','inputnode.output_query'),
							]),
						 ])

		eeg_flow.connect([
						  (datasource, loader_flow, 
						   [('base_directory','inputnode.base_directory'),
						    ('subject','inputnode.subject'),
							]),
						 ])

		eeg_flow.connect([
						  (preparer_flow, loader_flow, 
						   [('outputnode.output_query','inputnode.output_query'),
						    ('outputnode.derivative_list','inputnode.derivative_list'),
							]),
						 ])

		
		eeg_flow.connect([
						  (loader_flow, invsol_flow, 
						   [
							('outputnode.EEG','inputnode.eeg_ts_file'),                            
							('outputnode.rois','inputnode.rois_file'),
							('outputnode.src','inputnode.src_file'),
							('outputnode.invsol','inputnode.invsol_file'),
							]),
						 ])

		eeg_flow.connect([
						  (datasource, invsol_flow, 
						   [
							('roi_ts_file','inputnode.roi_ts_file'),
							]),
						 ])

		eeg_flow.connect([
						  (preparer_flow, invsol_flow, 
						   [
							('outputnode.invsol_params','inputnode.invsol_params'),
							]),
						 ])


		eeg_flow.connect([			
			(invsol_flow, sinker, [("outputnode.roi_ts_file", "eeg.@roi_ts_file")]),
		])

		self.flow = eeg_flow
		return eeg_flow

	def process(self):
		"""Executes the anatomical pipeline workflow and returns True if successful."""
		# Enable the use of the W3C PROV data model to capture and represent provenance in Nipype
		# config.enable_provenance()

		# Process time
		self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

		if '_' in self.subject:
			self.subject = self.subject.split('_')[0]

		if self.global_conf.subject_session == '':
			cmp_deriv_subject_directory = os.path.join(
				self.output_directory, "cmp", self.subject)
			nipype_deriv_subject_directory = os.path.join(
				self.output_directory, "nipype", self.subject)
		else:
			cmp_deriv_subject_directory = os.path.join(self.output_directory, "cmp", self.subject,
													   self.global_conf.subject_session)
			nipype_deriv_subject_directory = os.path.join(self.output_directory, "nipype", self.subject,
														  self.global_conf.subject_session)

			self.subject = "_".join(
				(self.subject, self.global_conf.subject_session))

		if not os.path.exists(os.path.join(nipype_deriv_subject_directory, "eeg_pipeline")):
			try:
				os.makedirs(os.path.join(
					nipype_deriv_subject_directory, "eeg_pipeline"))
			except os.error:
				print("%s was already existing" % os.path.join(
					nipype_deriv_subject_directory, "eeg_pipeline"))

		# Initialization
		if os.path.isfile(os.path.join(nipype_deriv_subject_directory, "eeg_pipeline", "pypeline.log")):
			os.unlink(os.path.join(nipype_deriv_subject_directory,
								   "eeg_pipeline", "pypeline.log"))
		config.update_config(
			{'logging': {'log_directory': os.path.join(nipype_deriv_subject_directory, "eeg_pipeline"),
						 'log_to_file': True},
			 'execution': {'remove_unnecessary_outputs': False,
						   'stop_on_first_crash': True,
						   'stop_on_first_rerun': False,
						   'use_relative_paths': True,
						   'crashfile_format': "txt"}
			 })
		logging.update_logging(config)

		iflogger = logging.getLogger('nipype.interface')
		iflogger.info("**** Processing ****")

		eeg_flow = self.create_pipeline_flow(cmp_deriv_subject_directory=cmp_deriv_subject_directory,
											  nipype_deriv_subject_directory=nipype_deriv_subject_directory)
		eeg_flow.write_graph(graph2use='colored',
							  format='svg', simple_form=True)

		if self.number_of_cores != 1:
			eeg_flow.run(plugin='MultiProc',
						  plugin_args={'n_procs': self.number_of_cores})
		else:
			eeg_flow.run()

		iflogger.info("**** Processing finished ****")

		return True

