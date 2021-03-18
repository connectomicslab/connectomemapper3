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
from cmp.stages.eeg.eeg_preprocessing import EEGPreprocessingStage
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
    ordered_stage_list = ['EEGLoading',
                          'EEGPreprocessing',
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

        self.stages = {'EEGLoader': EEGLoader(bids_dir=project_info.base_directory,
                                                           output_dir=self.output_directory),
                       'EEGPreprocessing': EEGPreprocessing(bids_dir=project_info.base_directory,
                                                           output_dir=self.output_directory),
                       'EEGInverseSolution': EEGInverseSolution(bids_dir=project_info.base_directory,
                                                           output_dir=self.output_directory),
                       }
        
        cmp_common.Pipeline.__init__(self, project_info)

        self.stages['EEGLoader'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
		self.stages['EEGPreprocessing'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
        self.stages['EEGInverseSolution'].config.on_trait_change(self.update_parcellation_scheme, 'parcellation_scheme')
       	
    def check_config(self):
    	raise NotImplementedError
    def check_input(self):
    	raise NotImplementedError
    def check_output(self):
    	raise NotImplementedError

	def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):    

        datasource = pe.Node(eegloader.EEGLoader(), name = "eegloader")
        datasource.inputs.base_directory = self.base_directory
        datasource.inputs.subject_id = self.subject_id



        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="eeg_sinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)        

         # Clear previous outputs
        self.clear_stages_outputs()

        # Create common_flow
        eeg_flow = pe.Workflow(name='eeg_pipeline', 
                               base_dir= os.path.abspath(nipype_deriv_subject_directory))

        eeg_inputnode = pe.Node(interface=util.IdentityInterface(
                    fields=['epochs', 
                            'src_file', 
                            'invsol_file', 
                            'lamda', 
                            'svd_params',
                            'cartool_dir',
                            'cmp3_dir',
                            'subject_id',
                            'parcellation',
                            'behav_file',
                            'epochs_fif_fname',
                            'roi_ts_file',
                            'base_dir',
                            ], 
                    mandatory_inputs=True), name="inputnode")
        
        ################################################
        # This needs to go somewhere else
        #
        eeg_inputnode.inputs.base_dir = self.base_directory
        eeg_inputnode.inputs.lamda = 6
        eeg_inputnode.inputs.svd_params =  {'toi_begin' : 120,
                                            'toi_end' : 500}                                            
        eeg_inputnode.inputs.cartool_dir = os.path.join(self.base_directory,'derivatives','cartool')
        eeg_inputnode.inputs.cmp3_dir = os.path.join(self.base_directory,'derivatives','cmp-v3.0.0-beta-RC1')
        eeg_inputnode.inputs.subject_id = self.subject_id
        eeg_inputnode.inputs.epochs_fif_fname = os.path.join(self.base_directory,'derivatives','cmp-v3.0.0-beta-RC1','sub-'+self.subject_id,'eeg','sub-'+self.subject_id+'_epo.fif')
        eeg_inputnode.inputs.roi_ts_file = os.path.join(self.base_directory,'derivatives','cmp-v3.0.0-beta-RC1','sub-'+self.subject_id,'eeg','sub-'+self.subject_id+'_rtc_epo.npy')
        #
        # 
        ################################################

        eeg_outputnode = pe.Node(interface=util.IdentityInterface(
                                 fields=["roi_ts_file"]), name="outputnode")

        eeg_flow.add_nodes([eeg_inputnode, eeg_outputnode])


        # Connect datasource to eeg_inputnode
        eeg_flow.connect([
                          (datasource, eeg_inputnode, 
                           [
                            ("EEG", "epochs"),
                            ('events','behav_file'),
                            ('src_file','src_file'),
                            ('invsol_file','invsol_file'),
                            ('parcellation','parcellation'),
                            ]),
                         ])

        # Create preproc. flow
        preproc_flow = self.create_stage_flow("EEGPreprocessing")

        eeg_flow.connect([
                          (eeg_inputnode, preproc_flow,
                           [
                            ('epochs','inputnode.eeg_ts_file'),
                            ('behav_file','inputnode.behav_file'),
                            ('epochs_fif_fname','inputnode.epochs_fif_fname'),
                            ('subject_id','inputnode.subject_id'),
                            ('parcellation','inputnode.parcellation'),
                            ('cartool_dir','inputnode.cartool_dir'),
                            ('cmp3_dir','inputnode.cmp3_dir'),
                           ]
                          )
                         ])


        eeg_flow.connect([
                          (preproc_flow, eeg_outputnode,
                           [
                            ('outputnode.fif_ts_file','epochs_fif_fname'),
                           ]
                          )
                         ])

        # Create invsol. flow
        invsol_flow = self.create_stage_flow("EEGInverseSolution")


        eeg_flow.connect([
                          (preproc_flow, invsol_flow,
                           [
                            ('outputnode.fif_ts_file','inputnode.eeg_ts_file'),
                            ('outputnode.rois_pickle','inputnode.rois_file'),
                           ]
                          )
                         ])

        eeg_flow.connect([
                          (eeg_inputnode, invsol_flow,
                           [('src_file','inputnode.src_file'),
                            ('invsol_file','inputnode.invsol_file'),
                            ('lamda','inputnode.lamda'),
                            ('svd_params','inputnode.svd_params'),
                            ('roi_ts_file','inputnode.roi_ts_file'),
                           ]
                          )
                         ])

        eeg_flow.connect([
                          (invsol_flow, eeg_outputnode
                           [('outputnode.roi_ts_file', 'roi_ts_file'),
                           ]
                          )
                         ])

        eeg_flow.connect([
            (eeg_outputnode, sinker, [("epochs_fif_fname", "eeg.@epochs_fif_fname")]),
            (eeg_outputnode, sinker, [("roi_ts_file", "eeg.@roi_ts_file")]),
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

        iflogge
        r.info("**** Processing finished ****")

        return True

