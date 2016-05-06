# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Diffusion pipeline Class definition
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

from cmp.stages.preprocessing.preprocessing import PreprocessingStage
from cmp.stages.segmentation.segmentation import SegmentationStage
from cmp.stages.parcellation.parcellation import ParcellationStage
from cmp.stages.diffusion.diffusion import DiffusionStage
from cmp.stages.registration.registration import RegistrationStage
from cmp.stages.connectome.connectome import ConnectomeStage

class Global_Configuration(HasTraits):
    process_type = Str('diffusion')
    imaging_model = Str
   
class Check_Input_Notification(HasTraits):
    message = Str
    imaging_model_options = List(['DSI','DTI','HARDI'])
    imaging_model = Str
    imaging_model_message = Str('\nMultiple diffusion inputs available. Please select desired diffusion modality.')
   
    traits_view = View(Item('message',style='readonly',show_label=False),
                       Item('imaging_model_message',visible_when='len(imaging_model_options)>1',style='readonly',show_label=False),
                       Item('imaging_model',editor=EnumEditor(name='imaging_model_options'),visible_when='len(imaging_model_options)>1'),
                       kind='modal',
                       buttons=['OK'],
                       title="Check inputs")

class DiffusionPipeline(Pipeline):
    pipeline_name = Str("diffusion_pipeline")
    input_folders = ['DSI','DTI','HARDI','T1','T2']
           
    ordered_stage_list = ['Preprocessing','Segmentation','Parcellation','Registration','Diffusion','Connectome']
   
    global_conf = Global_Configuration()
   
    preprocessing = Button('Preprocessing')
    segmentation = Button('Segmentation')
    parcellation = Button('Parcellation')
    diffusion = Button('Diffusion')
    registration = Button('Registration')
    connectome = Button('Connectome')
   
    config_file = Str
   
    pipeline_group = VGroup(
                        HGroup(spring,Item('preprocessing',editor=ThemedButtonEditor(image=ImageResource('preprocessing'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('segmentation',editor=ThemedButtonEditor(image=ImageResource('segmentation'),theme='@G')),spring,show_labels=False),#Item('parcellation',editor=ThemedButtonEditor(image=ImageResource('parcellation'),theme='@G')),show_labels=False),
                        HGroup(spring,Item('parcellation',editor=ThemedButtonEditor(image=ImageResource('parcellation'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('registration',editor=ThemedButtonEditor(image=ImageResource('registration'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('diffusion',editor=ThemedButtonEditor(image=ImageResource('diffusion'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('connectome',editor=ThemedButtonEditor(image=ImageResource('connectome'),theme='@G')),spring,show_labels=False),
                        springy=True
                        )
    
    def __init__(self,project_info):
        self.stages = {'Preprocessing':PreprocessingStage(),
        'Segmentation':SegmentationStage(),
            'Parcellation':ParcellationStage(pipeline_mode = "Diffusion"),
            'Registration':RegistrationStage(pipeline_mode = "Diffusion"),
            'Diffusion':DiffusionStage(),
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
       
    def _diffusion_fired(self, info):
        self.stages['Diffusion'].configure_traits()
       
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
        diffusion_available = False
        t1_available = False
        t2_available = False
        valid_inputs = False

        mem = Memory(base_dir=os.path.join(self.base_directory,'NIPYPE'))
        swap_and_reorient = mem.cache(SwapAndReorient)

        # Check for (and if existing, convert) diffusion data
        diffusion_model = []
        for model in ['DSI','DTI','HARDI']:
            input_dir = os.path.join(self.base_directory,'RAWDATA',model)
            if len(os.listdir(input_dir)) > 0:
                if convert_rawdata(self.base_directory, input_dir, model):
                    diffusion_available = True
                    diffusion_model.append(model)

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

        if diffusion_available:
            #project.stages['Diffusion'].config.imaging_model_choices = diffusion_model
            if t2_available:
                swap_and_reorient(src_file=os.path.join(self.base_directory,'NIFTI','T2_orig.nii.gz'),
                                  ref_file=os.path.join(self.base_directory,'NIFTI',diffusion_model[0]+'.nii.gz'),
                                  out_file=os.path.join(self.base_directory,'NIFTI','T2.nii.gz'))
            if t1_available:
                swap_and_reorient(src_file=os.path.join(self.base_directory,'NIFTI','T1_orig.nii.gz'),
                                  ref_file=os.path.join(self.base_directory,'NIFTI',diffusion_model[0]+'.nii.gz'),
                                  out_file=os.path.join(self.base_directory,'NIFTI','T1.nii.gz'))
                valid_inputs = True
                input_message = 'Inputs check finished successfully.\nDiffusion and morphological data available.'
            else:
                input_message = 'Error during inputs check.\nMorphological data (T1) not available.'
        elif t1_available:
            input_message = 'Error during inputs check. \nDiffusion data not available (DSI/DTI/HARDI).'
        else:
            input_message = 'Error during inputs check. No diffusion or morphological data available in folder '+os.path.join(self.base_directory,'RAWDATA')+'!'

        imaging_model = diffusion_model[0]
         
        if gui: 
            input_notification = Check_Input_Notification(message=input_message, imaging_model_options=diffusion_model,imaging_model=imaging_model)
            input_notification.configure_traits()
            self.global_conf.imaging_model = input_notification.imaging_model
            diffusion_file = os.path.join(self.base_directory,'NIFTI',input_notification.imaging_model+'.nii.gz')
            n_vol = nib.load(diffusion_file).shape[3]
            if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
                self.stages['Preprocessing'].config.end_vol = n_vol-1
            self.stages['Preprocessing'].config.max_vol = n_vol-1
            self.stages['Registration'].config.imaging_model = input_notification.imaging_model
            self.stages['Diffusion'].config.imaging_model = input_notification.imaging_model
        else:
            print input_message
            self.global_conf.imaging_model = imaging_model
            diffusion_file = os.path.join(self.base_directory,'NIFTI',imaging_model+'.nii.gz')
            n_vol = nib.load(diffusion_file).shape[3]
            if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
                self.stages['Preprocessing'].config.end_vol = n_vol-1
            self.stages['Preprocessing'].config.max_vol = n_vol-1
            self.stages['Registration'].config.imaging_model = imaging_model
            self.stages['Diffusion'].config.imaging_model = imaging_model
       
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
        iflogger = logging.getLogger('interface')
       
        # Data import
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['diffusion','T1','T2']), name='datasource')
        datasource.inputs.base_directory = os.path.join(self.base_directory,'NIFTI')
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = dict(diffusion=self.global_conf.imaging_model+'.nii.gz',T1='T1.nii.gz',T2='T2.nii.gz')
        datasource.inputs.sort_filelist=False
       
        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="diffusion_sinker")
        sinker.inputs.base_directory = os.path.join(self.base_directory, "RESULTS")
        
        # Clear previous outputs
        self.clear_stages_outputs()
        
        # Create common_flow
        common_flow = self.create_common_flow()
        
        # Create diffusion flow
        
        diffusion_flow = pe.Workflow(name='diffusion_pipeline')
        diffusion_inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion","T1","T2","wm_mask_file","roi_volumes","subjects_dir","subject_id",
                                                                               "atlas_info","parcellation_scheme"]),name="inputnode")
        diffusion_outputnode = pe.Node(interface=util.IdentityInterface(fields=["connectivity_matrices"]),name="outputnode")
        diffusion_flow.add_nodes([diffusion_inputnode,diffusion_outputnode])
        
        if self.stages['Preprocessing'].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            diffusion_flow.connect([
                                    (diffusion_inputnode,preproc_flow,[("diffusion","inputnode.diffusion")]),
                                    ])
                                               
        if self.stages['Registration'].enabled:
            reg_flow = self.create_stage_flow("Registration")
            diffusion_flow.connect([
                                    (diffusion_inputnode,reg_flow,[('T1','inputnode.T1'),('T2','inputnode.T2'),('wm_mask_file','inputnode.wm_mask'),
                                                                   ('roi_volumes','inputnode.roi_volumes')]),
                                    (preproc_flow,reg_flow, [('outputnode.diffusion_preproc','inputnode.target')])
                                    ])
            if self.stages['Registration'].config.registration_mode == "BBregister (FS)":
                diffusion_flow.connect([
                                        (diffusion_inputnode,reg_flow, [('subjects_dir','inputnode.subjects_dir'),
                                                                        ('subject_id','inputnode.subject_id')]),
                                        ])
       
        if self.stages['Diffusion'].enabled:
            diff_flow = self.create_stage_flow("Diffusion")
            diffusion_flow.connect([
                                    (preproc_flow,diff_flow, [('outputnode.diffusion_preproc','inputnode.diffusion')]),
                                    (reg_flow,diff_flow, [('outputnode.wm_mask_registered','inputnode.wm_mask_registered')]),
                                    (reg_flow,diff_flow,[('outputnode.roi_volumes_registered','inputnode.roi_volumes')])
                                    ])
                       
        if self.stages['Connectome'].enabled:
            if self.stages['Diffusion'].config.processing_tool == 'FSL':
                self.stages['Connectome'].config.probtrackx = True
            else:
                self.stages['Connectome'].config.probtrackx = False
            con_flow = self.create_stage_flow("Connectome")
            diffusion_flow.connect([
		                (diffusion_inputnode,con_flow, [('parcellation_scheme','inputnode.parcellation_scheme')]),
		                (diff_flow,con_flow, [('outputnode.track_file','inputnode.track_file'),('outputnode.gFA','inputnode.gFA'),
                                              ('outputnode.roi_volumes','inputnode.roi_volumes_registered'),
		                                      ('outputnode.skewness','inputnode.skewness'),('outputnode.kurtosis','inputnode.kurtosis'),
		                                      ('outputnode.P0','inputnode.P0')]),
		                (con_flow,diffusion_outputnode, [('outputnode.connectivity_matrices','connectivity_matrices')])
		                ])
            
            if self.stages['Parcellation'].config.parcellation_scheme == "Custom":
                diffusion_flow.connect([(diffusion_inputnode,con_flow, [('atlas_info','inputnode.atlas_info')])])
                
        # Create NIPYPE flow
        
        flow = pe.Workflow(name='NIPYPE', base_dir=os.path.join(self.base_directory))
        
        flow.connect([
                      (datasource,common_flow,[("T1","inputnode.T1")]),
                      (datasource,diffusion_flow,[("diffusion","inputnode.diffusion"),("T1","inputnode.T1"),("T2","inputnode.T2")]),
                      (common_flow,diffusion_flow,[("outputnode.subjects_dir","inputnode.subjects_dir"),("outputnode.subject_id","inputnode.subject_id"),
                                                   ("outputnode.wm_mask_file","inputnode.wm_mask_file"),
                                                   ( "outputnode.roi_volumes","inputnode.roi_volumes"),
                                                   ("outputnode.parcellation_scheme","inputnode.parcellation_scheme"),
                                                   ("outputnode.atlas_info","inputnode.atlas_info")]),
                      (diffusion_flow,sinker,[("outputnode.connectivity_matrices","%s.%s.connectivity_matrices"%(self.global_conf.imaging_model,now))])
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
        outdir = os.path.join(self.base_directory,"RESULTS",self.global_conf.imaging_model,now)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        shutil.copy(self.config_file,outdir)
        shutil.copy(os.path.join(self.base_directory,'LOG','pypeline.log'),outdir)
       
        iflogger.info("**** Processing finished ****")
       
        return True,'Processing sucessful'
