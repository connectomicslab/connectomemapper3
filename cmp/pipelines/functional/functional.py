# Copyright (C) 2009-2014, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Functional pipeline Class definition
"""

import os
import datetime
from cmp.pipelines.common import *
from traits.api import *
from traitsui.api import *

from traitsui.wx.themed_button_editor import ThemedButtonEditor
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
from nipype import config, logging
from nipype.caching import Memory
from pyface.api import ImageResource
import shutil

import nibabel as nib

from cmp.stages.preprocessing.fmri_preprocessing import PreprocessingStage
from cmp.stages.segmentation.segmentation import SegmentationStage
from cmp.stages.parcellation.parcellation import ParcellationStage
from cmp.stages.registration.registration import RegistrationStage
from cmp.stages.functional.functional import FunctionalStage
from cmp.stages.connectome.fmri_connectome import ConnectomeStage

class Global_Configuration(HasTraits):
    process_type = Str('fMRI')
    imaging_model = Str
   
class Check_Input_Notification(HasTraits):
    message = Str
    imaging_model_options = List(['fMRI'])
    imaging_model = Str

    traits_view = View(Item('message',style='readonly',show_label=False),
                       Item('imaging_model',editor=EnumEditor(name='imaging_model_options'),visible_when='len(imaging_model_options)>1'),
                       kind='modal',
                       buttons=['OK'],
                       title="Check inputs")

class fMRIPipeline(Pipeline):
    pipeline_name = Str("fMRI_pipeline")
    input_folders = ['fMRI','T1','T2']
           
    ordered_stage_list = ['Preprocessing','Segmentation','Parcellation','Registration','Functional','Connectome']
   
    global_conf = Global_Configuration()
   
    preprocessing = Button('Preprocessing')
    segmentation = Button('Segmentation')
    parcellation = Button('Parcellation')
    functional = Button('Functional')
    registration = Button('Registration')
    connectome = Button('Connectome')
   
    config_file = Str
   
    pipeline_group = VGroup(
                        HGroup(spring,Item('preprocessing',editor=ThemedButtonEditor(image=ImageResource('preprocessing'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('segmentation',editor=ThemedButtonEditor(image=ImageResource('segmentation'),theme='@G')),spring,show_labels=False),#Item('parcellation',editor=ThemedButtonEditor(image=ImageResource('parcellation'),theme='@G')),show_labels=False),
                        HGroup(spring,Item('parcellation',editor=ThemedButtonEditor(image=ImageResource('parcellation'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('registration',editor=ThemedButtonEditor(image=ImageResource('registration'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('functional',editor=ThemedButtonEditor(image=ImageResource('functional'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('connectome',editor=ThemedButtonEditor(image=ImageResource('connectome'),theme='@G')),spring,show_labels=False),
                        springy=True
                        )
    
    def __init__(self,project_info):
        self.stages = {'Preprocessing':PreprocessingStage(),
        'Segmentation':SegmentationStage(),
            'Parcellation':ParcellationStage(pipeline_mode = "fMRI"),
            'Registration':RegistrationStage(pipeline_mode = "fMRI"),
            'Functional':FunctionalStage(),
            'Connectome':ConnectomeStage()}
        Pipeline.__init__(self, project_info)
        self.stages['Segmentation'].config.on_trait_change(self.update_parcellation,'seg_tool')
        self.stages['Parcellation'].config.on_trait_change(self.update_segmentation,'parcellation_scheme')
        
    def update_parcellation(self):
        if self.stages['Segmentation'].config.seg_tool == "Custom segmentation" :
            self.stages['Parcellation'].config.parcellation_scheme = 'Custom'
        else:
            self.stages['Parcellation'].config.parcellation_scheme = self.stages['Parcellation'].config.pre_custom
    
    def update_segmentation(self):
        if self.stages['Parcellation'].config.parcellation_scheme == 'Custom':
            self.stages['Segmentation'].config.seg_tool = "Custom segmentation"
        else:
            self.stages['Segmentation'].config.seg_tool = 'Freesurfer'
                       
    def _preprocessing_fired(self, info):
        self.stages['Preprocessing'].configure_traits()
       
    def _segmentation_fired(self, info):
        self.stages['Segmentation'].configure_traits()
       
    def _parcellation_fired(self, info):
        self.stages['Parcellation'].configure_traits()
       
    def _functional_fired(self, info):
        self.stages['Functional'].configure_traits()
       
    def _registration_fired(self, info):
        self.stages['Registration'].configure_traits()

    def _connectome_fired(self, info):
        self.stages['Connectome'].configure_traits()
       
    def define_custom_mapping(self, custom_last_stage):
        # start by disabling all stages
        for stage in self.ordered_stage_list:
            self.stages[stage].enabled = False
        # enable until selected one
        for stage in self.ordered_stage_list:
            print 'Enable stage : %s' % stage
            self.stages[stage].enabled = True
            if stage == custom_last_stage:
                break

    def check_input(self, gui=True):
        print '**** Check Inputs ****'
        fMRI_available = False
        t1_available = False
        t2_available = False
        valid_inputs = False

        mem = Memory(base_dir=os.path.join(self.base_directory,'NIPYPE'))
        swap_and_reorient = mem.cache(SwapAndReorient)

        # Check for (and if existing, convert) functional data
        input_dir = os.path.join(self.base_directory,'RAWDATA','fMRI')
        if len(os.listdir(input_dir)) > 0:
            if convert_rawdata(self.base_directory, input_dir, 'fMRI'):
                fMRI_available = True

        # Check for (and if existing, convert)  T1
        input_dir = os.path.join(self.base_directory,'RAWDATA','T1')
        if len(os.listdir(input_dir)) > 0:
            if convert_rawdata(self.base_directory, input_dir, 'T1_orig'):
                t1_available = True

        # Check for (and if existing, convert)  T2
        input_dir = os.path.join(self.base_directory,'RAWDATA','T2')
        if len(os.listdir(input_dir)) > 0:
            if convert_rawdata(self.base_directory, input_dir, 'T2_orig'):
                t2_available = True   

        if fMRI_available:
            if t2_available:
                swap_and_reorient(src_file=os.path.join(self.base_directory,'NIFTI','T2_orig.nii.gz'),
                                  ref_file=os.path.join(self.base_directory,'NIFTI','fMRI.nii.gz'),
                                  out_file=os.path.join(self.base_directory,'NIFTI','T2.nii.gz'))
            if t1_available:
                swap_and_reorient(src_file=os.path.join(self.base_directory,'NIFTI','T1_orig.nii.gz'),
                                  ref_file=os.path.join(self.base_directory,'NIFTI','fMRI.nii.gz'),
                                  out_file=os.path.join(self.base_directory,'NIFTI','T1.nii.gz'))
                valid_inputs = True
                input_message = 'Inputs check finished successfully.\nfMRI and morphological data available.'
            else:
                input_message = 'Error during inputs check.\nMorphological data (T1) not available.'
        elif t1_available:
            input_message = 'Error during inputs check. \nfMRI data not available (fMRI).'
        else:
            input_message = 'Error during inputs check. No fMRI or morphological data available in folder '+os.path.join(self.base_directory,'RAWDATA')+'!'

        if gui: 
            input_notification = Check_Input_Notification(message=input_message, imaging_model='fMRI')
            input_notification.configure_traits()
            self.global_conf.imaging_model = input_notification.imaging_model
            self.stages['Registration'].config.imaging_model = input_notification.imaging_model
        else:
            print input_message
            self.global_conf.imaging_model = 'fMRI'
            self.stages['Registration'].config.imaging_model = 'fMRI'
       
        if t2_available:
            self.stages['Registration'].config.registration_mode_trait = ['Linear (FSL)','BBregister (FS)','Nonlinear (FSL)']
       
        self.fill_stages_outputs()
       
        return valid_inputs

    def process(self):
        # Process time
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
       
        # Initialization
        if os.path.exists(os.path.join(self.base_directory,"LOG","pypeline.log")):
            os.unlink(os.path.join(self.base_directory,"LOG","pypeline.log"))
        config.update_config({'logging': {'log_directory': os.path.join(self.base_directory,"LOG"),
                                  'log_to_file': True},
                              'execution': {'remove_unnecessary_outputs': False}
                              })
        logging.update_logging(config)
        flow = pe.Workflow(name='fMRI_pipeline', base_dir=os.path.join(self.base_directory,'NIPYPE'))
        iflogger = logging.getLogger('interface')
       
        # Data import
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['fMRI','T1','T2']), name='datasource')
        datasource.inputs.base_directory = os.path.join(self.base_directory,'NIFTI')
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = dict(fMRI=self.global_conf.imaging_model+'.nii.gz',T1='T1.nii.gz',T2='T2.nii.gz')
       
        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="sinker")
        sinker.inputs.base_directory = os.path.join(self.base_directory, "RESULTS")
        
        # Clear previous outputs
        self.clear_stages_outputs()

        if self.stages['Preprocessing'].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            flow.connect([
                (datasource,preproc_flow,[("fMRI","inputnode.functional")]),
                ])
       
        if self.stages['Segmentation'].enabled:
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                if self.stages['Segmentation'].config.use_existing_freesurfer_data == False:
                    self.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.base_directory)
                    self.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(self.base_directory,'FREESURFER')
                    if (os.path.exists(os.path.join(self.base_directory,'NIPYPE/diffusion_pipeline/segmentation_stage/reconall/result_reconall.pklz')) and (not os.path.exists(os.path.join(self.base_directory,'NIPYPE/fMRI_pipeline/segmentation_stage/')))):
                        shutil.copytree(os.path.join(self.base_directory,'NIPYPE/diffusion_pipeline/segmentation_stage'),os.path.join(self.base_directory,'NIPYPE/fMRI_pipeline/segmentation_stage'))
                    if (not os.path.exists(os.path.join(self.base_directory,'NIPYPE/fMRI_pipeline/segmentation_stage/reconall/result_reconall.pklz'))) and os.path.exists(os.path.join(self.base_directory,'FREESURFER')):
                        shutil.rmtree(os.path.join(self.base_directory,'FREESURFER'))
            seg_flow = self.create_stage_flow("Segmentation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                flow.connect([(datasource,seg_flow, [('T1','inputnode.T1')])])
       
        if self.stages['Parcellation'].enabled:
            parc_flow = self.create_stage_flow("Parcellation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                flow.connect([(seg_flow,parc_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                    ('outputnode.subject_id','inputnode.subject_id')]),
                            ])
            else:
                flow.connect([
                            (seg_flow,parc_flow,[("outputnode.custom_wm_mask","inputnode.custom_wm_mask")])
                            ])
                                               
        if self.stages['Registration'].enabled:
            reg_flow = self.create_stage_flow("Registration")
            flow.connect([
                          (datasource,reg_flow,[('T1','inputnode.T1')]),(datasource,reg_flow,[('T2','inputnode.T2')]),
                          (preproc_flow,reg_flow, [('outputnode.mean_vol','inputnode.target')]),
                          (parc_flow,reg_flow, [('outputnode.wm_mask_file','inputnode.wm_mask'),('outputnode.roi_volumes','inputnode.roi_volumes'),
                                                ('outputnode.wm_eroded','inputnode.eroded_wm'),('outputnode.csf_eroded','inputnode.eroded_csf'),
                        ('outputnode.brain_eroded','inputnode.eroded_brain')]),
                          ])
            if self.stages['Registration'].config.registration_mode == "BBregister (FS)":
                flow.connect([
                          (seg_flow,reg_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                ('outputnode.subject_id','inputnode.subject_id')]),
                          ])
       
        if self.stages['Functional'].enabled:
            func_flow = self.create_stage_flow("Functional")
            flow.connect([
                        (preproc_flow,func_flow, [('outputnode.functional_preproc','inputnode.preproc_file')]),
                        (reg_flow,func_flow, [('outputnode.wm_mask_registered','inputnode.registered_wm'),('outputnode.roi_volumes_registered','inputnode.registered_roi_volumes'),
                        ('outputnode.eroded_wm_registered','inputnode.eroded_wm'),('outputnode.eroded_csf_registered','inputnode.eroded_csf'),
                        ('outputnode.eroded_brain_registered','inputnode.eroded_brain')]),
                        (preproc_flow,func_flow,[("outputnode.par_file","inputnode.motion_par_file")])
                        ])
                       
        if self.stages['Connectome'].enabled:
            con_flow = self.create_stage_flow("Connectome")
            flow.connect([
		                (parc_flow,con_flow, [('outputnode.parcellation_scheme','inputnode.parcellation_scheme')]),
		                (func_flow,con_flow, [('outputnode.func_file','inputnode.func_file'),("outputnode.FD","inputnode.FD"),
                                              ("outputnode.DVARS","inputnode.DVARS")]),
                        (reg_flow,con_flow,[("outputnode.roi_volumes_registered","inputnode.roi_volumes_registered")]),
		                (con_flow,sinker, [('outputnode.connectivity_matrices',now+'.connectivity_matrices')])
		                ])
            
            if self.stages['Parcellation'].config.parcellation_scheme == "Custom":
                flow.connect([(parc_flow,con_flow, [('outputnode.atlas_info','inputnode.atlas_info')])])
        
        iflogger.info("**** Processing ****")
       
        if(self.number_of_cores != 1):
            flow.run(plugin='MultiProc', plugin_args={'n_procs' : self.number_of_cores})
        else:
            flow.run()
       
        self.fill_stages_outputs()
        
        # Clean undesired folders/files
        rm_file_list = ['rh.EC_average','lh.EC_average','fsaverage']
        for file_to_rm in rm_file_list:
            if os.path.exists(os.path.join(self.base_directory,file_to_rm)):
                os.remove(os.path.join(self.base_directory,file_to_rm))
       
        # copy .ini and log file
        outdir = os.path.join(self.base_directory,"RESULTS",now)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        shutil.copy(self.config_file,outdir)
        shutil.copy(os.path.join(self.base_directory,'LOG','pypeline.log'),outdir)
       
        iflogger.info("**** Processing finished ****")
       
        return True,'Processing sucessful'
