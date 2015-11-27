# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
        self.stages['Functional'].config.on_trait_change(self.update_nuisance_requirements,'global_nuisance')
        self.stages['Functional'].config.on_trait_change(self.update_nuisance_requirements,'csf')
        self.stages['Functional'].config.on_trait_change(self.update_nuisance_requirements,'wm')
        self.stages['Connectome'].config.on_trait_change(self.update_scrubbing,'apply_scrubbing')
        
    def update_parcellation(self):
        if self.stages['Segmentation'].config.seg_tool == "Custom segmentation" :
            self.stages['Parcellation'].config.parcellation_scheme = 'Custom'
        else:
            self.stages['Parcellation'].config.parcellation_scheme = self.stages['Parcellation'].config.pre_custom
        self.update_registration()
    
    def update_segmentation(self):
        if self.stages['Parcellation'].config.parcellation_scheme == 'Custom':
            self.stages['Segmentation'].config.seg_tool = "Custom segmentation"
        else:
            self.stages['Segmentation'].config.seg_tool = 'Freesurfer'
        self.update_registration()
            
    def update_registration(self):
        if self.stages['Segmentation'].config.seg_tool == "Custom segmentation" :
            if self.stages['Registration'].config.registration_mode == 'BBregister (FS)':
                self.stages['Registration'].config.registration_mode = 'Linear (FSL)'
            if 'Nonlinear (FSL)' in self.stages['Registration'].config.registration_mode_trait:
                self.stages['Registration'].config.registration_mode_trait = ['Linear (FSL)','Nonlinear (FSL)']
            else:
                self.stages['Registration'].config.registration_mode_trait = ['Linear (FSL)']
        else:
            if 'Nonlinear (FSL)' in self.stages['Registration'].config.registration_mode_trait:
                self.stages['Registration'].config.registration_mode_trait = ['Linear (FSL)','BBregister (FS)','Nonlinear (FSL)']
            else:
                self.stages['Registration'].config.registration_mode_trait = ['Linear (FSL)','BBregister (FS)']
                
    def update_nuisance_requirements(self):
        self.stages['Registration'].config.apply_to_eroded_brain = self.stages['Functional'].config.global_nuisance
        self.stages['Registration'].config.apply_to_eroded_csf = self.stages['Functional'].config.csf
        self.stages['Registration'].config.apply_to_eroded_wm = self.stages['Functional'].config.wm
            
    def update_scrubbing(self):
        self.stages['Functional'].config.scrubbing = self.stages['Connectome'].config.apply_scrubbing
                       
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
    
    def check_config(self):
        common_check = Pipeline.check_config(self)
        if common_check == '':
            if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation' and self.stages['Functional'].config.global_nuisance and not os.path.exists(self.stages['Parcellation'].config.brain_file):
                return('\n\tGlobal signal regression selected but no existing brain mask provided.\t\n\tPlease provide a brain mask in the parcellation configuration window,\n\tor disable the global signal regression in the functional configuration window.\t\n')
            if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation' and self.stages['Functional'].config.csf and not os.path.exists(self.stages['Parcellation'].config.csf_file):
                return('\n\tCSF signal regression selected but no existing csf mask provided.\t\n\tPlease provide a csf mask in the parcellation configuration window,\n\tor disable the csf signal regression in the functional configuration window.\t\n')
            if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation' and self.stages['Functional'].config.wm and not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\n\tWM signal regression selected but no existing wm mask provided.\t\n\tPlease provide a wm mask in the segmentation configuration window,\n\tor disable the wm signal regression in the functional configuration window.\t\n')
            if self.stages['Functional'].config.motion == True and self.stages['Preprocessing'].config.motion_correction == False:
                return('\n\tMotion signal regression selected but no motion correction set.\t\n\tPlease activate motion correction in the preprocessing configuration window,\n\tor disable the motion signal regression in the functional configuration window.\t\n')
            if self.stages['Connectome'].config.apply_scrubbing == True and self.stages['Preprocessing'].config.motion_correction == False:
                return('\n\tScrubbing applied but no motion correction set.\t\n\tPlease activate motion correction in the preprocessing configutation window,\n\tor disable scrubbing in the connectome configuration window.\t\n')
            return ''
        return common_check

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
        iflogger = logging.getLogger('interface')
       
        # Data import
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['fMRI','T1','T2']), name='datasource')
        datasource.inputs.base_directory = os.path.join(self.base_directory,'NIFTI')
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = dict(fMRI='fMRI.nii.gz',T1='T1.nii.gz',T2='T2.nii.gz')
        datasource.inputs.sort_filelist=False
       
        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="fMRI_sinker")
        sinker.inputs.base_directory = os.path.join(self.base_directory, "RESULTS")
        
        # Clear previous outputs
        self.clear_stages_outputs()
        
        # Create common_flow
        common_flow = self.create_common_flow()
        
        # Create fMRI flow
        
        fMRI_flow = pe.Workflow(name='fMRI_pipeline')
        fMRI_inputnode = pe.Node(interface=util.IdentityInterface(fields=["fMRI","T1","T2","subjects_dir","subject_id","wm_mask_file","roi_volumes","wm_eroded","brain_eroded","csf_eroded","parcellation_scheme","atlas_info"]),name="inputnode")
        fMRI_outputnode = pe.Node(interface=util.IdentityInterface(fields=["connectivity_matrices"]),name="outputnode")
        fMRI_flow.add_nodes([fMRI_inputnode,fMRI_outputnode])

        if self.stages['Preprocessing'].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            fMRI_flow.connect([
                (fMRI_inputnode,preproc_flow,[("fMRI","inputnode.functional")]),
                ])
                                               
        if self.stages['Registration'].enabled:
            reg_flow = self.create_stage_flow("Registration")
            fMRI_flow.connect([
                          (fMRI_inputnode,reg_flow,[('T1','inputnode.T1')]),(fMRI_inputnode,reg_flow,[('T2','inputnode.T2')]),
                          (preproc_flow,reg_flow, [('outputnode.mean_vol','inputnode.target')]),
                          (fMRI_inputnode,reg_flow, [('wm_mask_file','inputnode.wm_mask'),('roi_volumes','inputnode.roi_volumes'),
                                                ('wm_eroded','inputnode.eroded_wm')])
                          ])
            if self.stages['Functional'].config.global_nuisance:
                fMRI_flow.connect([
                              (fMRI_inputnode,reg_flow,[('brain_eroded','inputnode.eroded_brain')])
                            ])
            if self.stages['Functional'].config.csf:
                fMRI_flow.connect([
                              (fMRI_inputnode,reg_flow,[('csf_eroded','inputnode.eroded_csf')])
                            ])
            if self.stages['Registration'].config.registration_mode == "BBregister (FS)":
                fMRI_flow.connect([
                          (fMRI_inputnode,reg_flow, [('subjects_dir','inputnode.subjects_dir'),
                                                ('subject_id','inputnode.subject_id')]),
                          ])
       
        if self.stages['Functional'].enabled:
            func_flow = self.create_stage_flow("Functional")
            fMRI_flow.connect([
                        (preproc_flow,func_flow, [('outputnode.functional_preproc','inputnode.preproc_file')]),
                        (reg_flow,func_flow, [('outputnode.wm_mask_registered','inputnode.registered_wm'),('outputnode.roi_volumes_registered','inputnode.registered_roi_volumes'),
                                              ('outputnode.eroded_wm_registered','inputnode.eroded_wm'),('outputnode.eroded_csf_registered','inputnode.eroded_csf'),
                                              ('outputnode.eroded_brain_registered','inputnode.eroded_brain')])
                        ])
            if self.stages['Functional'].config.scrubbing or self.stages['Functional'].config.motion:
                fMRI_flow.connect([
                                   (preproc_flow,func_flow,[("outputnode.par_file","inputnode.motion_par_file")])
                                ])
                       
        if self.stages['Connectome'].enabled:
            con_flow = self.create_stage_flow("Connectome")
            fMRI_flow.connect([
		                (fMRI_inputnode,con_flow, [('parcellation_scheme','inputnode.parcellation_scheme')]),
		                (func_flow,con_flow, [('outputnode.func_file','inputnode.func_file'),("outputnode.FD","inputnode.FD"),
                                              ("outputnode.DVARS","inputnode.DVARS")]),
                        (reg_flow,con_flow,[("outputnode.roi_volumes_registered","inputnode.roi_volumes_registered")]),
                        (con_flow,fMRI_outputnode,[("outputnode.connectivity_matrices","connectivity_matrices")])
		                ])
            
            if self.stages['Parcellation'].config.parcellation_scheme == "Custom":
                fMRI_flow.connect([(fMRI_inputnode,con_flow, [('atlas_info','inputnode.atlas_info')])])
                
        # Create NIPYPE flow
        
        flow = pe.Workflow(name='NIPYPE', base_dir=os.path.join(self.base_directory))
        
        flow.connect([
                      (datasource,common_flow,[("T1","inputnode.T1")]),
                      (datasource,fMRI_flow,[("fMRI","inputnode.fMRI"),("T1","inputnode.T1"),("T2","inputnode.T2")]),
                      (common_flow,fMRI_flow,[("outputnode.subjects_dir","inputnode.subjects_dir"),
                                              ("outputnode.subject_id","inputnode.subject_id"),
                                              ("outputnode.wm_mask_file","inputnode.wm_mask_file"),
                                              ("outputnode.roi_volumes","inputnode.roi_volumes"),
                                              ("outputnode.wm_eroded","inputnode.wm_eroded"),
                                              ("outputnode.brain_eroded","inputnode.brain_eroded"),
                                              ("outputnode.csf_eroded","inputnode.csf_eroded"),
                                              ("outputnode.parcellation_scheme","inputnode.parcellation_scheme"),
                                              ("outputnode.atlas_info","inputnode.atlas_info")]),
                      (fMRI_flow,sinker,[("outputnode.connectivity_matrices","fMRI.%s.connectivity_matrices"%now)])
                    ])
        
        # Process pipeline
        
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
        outdir = os.path.join(self.base_directory,"RESULTS",'fMRI',now)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        shutil.copy(self.config_file,outdir)
        shutil.copy(os.path.join(self.base_directory,'LOG','pypeline.log'),outdir)
       
        iflogger.info("**** Processing finished ****")
       
        return True,'Processing sucessful'
