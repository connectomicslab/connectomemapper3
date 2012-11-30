# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Diffusion pipeline Class definition
""" 

import os
import datetime
from cmp.pipelines.common import *
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *
    
from traitsui.wx.themed_button_editor import ThemedButtonEditor
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
from nipype import config, logging
from nipype.caching import Memory
from pyface.api import ImageResource
import shutil

from cmp.stages.preprocessing.preprocessing import Preprocessing
from cmp.stages.segmentation.segmentation import Segmentation
from cmp.stages.parcellation.parcellation import Parcellation
from cmp.stages.diffusion.diffusion import Diffusion
from cmp.stages.registration.registration import Registration
from cmp.stages.connectome.connectome import Connectome

class Global_Configuration(HasTraits):
    process_type = Str('Diffusion')
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
                       buttons=['OK'])

class Pipeline(HasTraits):
    base_directory = Str('')
    input_folders = ['DSI','DTI','HARDI','T1','T2']
    stages = {'Preprocessing':Preprocessing(), 'Segmentation':Segmentation(), 
            'Parcellation':Parcellation(), 'Diffusion':Diffusion(),
            'Registration':Registration(), 'Connectome':Connectome()}
            
    ordered_stage_list = ['Preprocessing','Segmentation','Parcellation','Registration','Diffusion','Connectome']
    
    global_conf = Global_Configuration()
    
    preprocessing = Button('Preprocessing')
    segmentation = Button('Segmentation')
    parcellation = Button('Parcellation')
    diffusion = Button('Diffusion')
    registration = Button('Registration')
    connectome = Button('Connectome')
    
    config_file = Str
    
    traits_view = View(VGroup(
                        #HGroup(spring,Item('preprocessing',editor=ThemedButtonEditor(image=ImageResource('preprocessing'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('segmentation',editor=ThemedButtonEditor(image=ImageResource('segmentation'),theme='@G')),spring,show_labels=False),#Item('parcellation',editor=ThemedButtonEditor(image=ImageResource('parcellation'),theme='@G')),show_labels=False),
                        HGroup(spring,Item('parcellation',editor=ThemedButtonEditor(image=ImageResource('parcellation'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('registration',editor=ThemedButtonEditor(image=ImageResource('registration'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('diffusion',editor=ThemedButtonEditor(image=ImageResource('diffusion'),theme='@G')),spring,show_labels=False),
                        HGroup(spring,Item('connectome',editor=ThemedButtonEditor(image=ImageResource('connectome'),theme='@G')),spring,show_labels=False),
                        )
                        )
                        
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
        
    def define_custom_mapping(self, stage_stop):
        stage_stop_seen = False
        for stage in self.ordered_stage_list:
            if stage_stop_seen:
                self.stages[stage].enabled = False
            if stage == stage_stop:
                stage_stop_seen = True

    
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

        imaging_model = ''
        if len(diffusion_model) > 0:
            imaging_model = diffusion_model[0]
          
        if gui:  
            input_notification = Check_Input_Notification(message=input_message, imaging_model_options=diffusion_model,imaging_model=imaging_model)
            input_notification.configure_traits()    
            self.global_conf.imaging_model = input_notification.imaging_model
            self.stages['Registration'].config.imaging_model = input_notification.imaging_model
            self.stages['Diffusion'].config.imaging_model = input_notification.imaging_model
        else:
            print input_message
            self.global_conf.imaging_model = imaging_model
            self.stages['Registration'].config.imaging_model = imaging_model
            self.stages['Diffusion'].config.imaging_model = imaging_model
        
        return valid_inputs
        
    def prepare_outputs(self):
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        outdir = os.path.join(self.base_directory,"RESULTS",now)
        os.makedirs(outdir)
        
        # copy .ini and log file
        shutil.copy(self.config_file,outdir)
        shutil.copy(os.path.join(self.base_directory,'LOG','pypeline.log'),outdir)
        
        # copy connectivity matrices
        mat_folder = os.path.join(self.base_directory,"RESULTS","CMP",'fibers','connectivity_matrices')
        matrices = os.listdir(mat_folder)
        for mat in matrices:
            shutil.copy(os.path.join(mat_folder, mat),outdir)

    def process(self):
        # Prepare
        config.update_config({'logging': {'log_directory': os.path.join(self.base_directory,"LOG"),
                                  'log_to_file': True},
                              'exectution': {'use_relative_paths': True}
                              })
        logging.update_logging(config)
        print '**** Processing ****'
        flow = pe.Workflow(name='diffusion_pipeline', base_dir=os.path.join(self.base_directory,'NIPYPE'))

        # Data import
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['diffusion','T1','T2']), name='datasource')
        datasource.inputs.base_directory = os.path.join(self.base_directory,'NIFTI')
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = dict(diffusion=self.global_conf.imaging_model+'.nii.gz',T1='T1.nii.gz',T2='T2.nii.gz')
        
        # Prepare output directory
        sinker = pe.Node(nio.DataSink(), name="sinker")
        sinker.inputs.base_directory = os.path.join(self.base_directory, "RESULTS", "CMP")
        
        if self.stages['Segmentation'].enabled:
            if self.stages['Segmentation'].config.use_existing_freesurfer_data == False:
                self.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.base_directory,'FREESURFER')
            seg_flow = self.stages['Segmentation'].create_workflow()
            flow.connect([(datasource,seg_flow, [('T1','inputnode.T1')])])
        
        if self.stages['Parcellation'].enabled:
            parc_flow = self.stages['Parcellation'].create_workflow()
            flow.connect([(seg_flow,parc_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                ('outputnode.subject_id','inputnode.subject_id')]),
                          (parc_flow,sinker, [('outputnode.aseg_file','fs_output.HR.@aseg'),('outputnode.wm_mask_file','fs_output.HR.@wm'),
                                       ('outputnode.cc_unknown_file','fs_output.HR.@unknown'),('outputnode.ribbon_file','fs_output.HR.@ribbon'),
                                       ('outputnode.roi_files','fs_output.HR.scales.@files'),('outputnode.roi_volumes','fs_output.HR.scales.@volumes')])
                        ])
                                                
        if self.stages['Registration'].enabled:
            reg_flow = self.stages['Registration'].create_workflow()
            flow.connect([
                          (datasource,reg_flow, [('diffusion','inputnode.diffusion')]),
                          (seg_flow,reg_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                ('outputnode.subject_id','inputnode.subject_id')]),
                          (datasource,reg_flow, [('T1','inputnode.T1'),('T2','inputnode.T2')]),
                          (reg_flow,sinker, [('outputnode.diffusion_b0_resampled','diffusion')]),
                          ])
        
        if self.stages['Diffusion'].enabled:
            diff_flow = self.stages['Diffusion'].create_workflow()
            flow.connect([
                        (datasource,diff_flow, [('diffusion','inputnode.diffusion')]),
                        (parc_flow,diff_flow, [('outputnode.wm_mask_file','inputnode.wm_mask')]),
                        (reg_flow,diff_flow, [('outputnode.T1-TO-B0_mat','inputnode.T1-TO-B0_mat'),('outputnode.diffusion_b0_resampled','inputnode.diffusion_b0_resampled')]),
                        (diff_flow,sinker, [('outputnode.gFA','scalars.@gfa'),('outputnode.skewness','scalars.@skewness'),
                                       ('outputnode.kurtosis','scalars.@kurtosis'),('outputnode.P0','scalars.@P0')])
                        ])
                        
        if self.stages['Connectome'].enabled:
            con_flow = self.stages['Connectome'].create_workflow()
            flow.connect([
                        (parc_flow,con_flow, [('outputnode.roi_volumes','inputnode.roi_volumes'),('outputnode.parcellation_scheme','inputnode.parcellation_scheme')]),
                        (reg_flow,con_flow, [('outputnode.T1-TO-B0_mat','inputnode.T1-TO-B0_mat'),('outputnode.diffusion_b0_resampled','inputnode.diffusion_b0_resampled')]),
                        (diff_flow,con_flow, [('outputnode.track_file','inputnode.track_file'),('outputnode.gFA','inputnode.gFA'),
                                              ('outputnode.skewness','inputnode.skewness'),('outputnode.kurtosis','inputnode.kurtosis'),
                                              ('outputnode.P0','inputnode.P0')]),
                        (con_flow,sinker, [('outputnode.endpoints_file','fibers.@endpoints_file'),('outputnode.endpoints_mm_file','fibers.@endpoints_mm_file'),
                             ('outputnode.final_fiberslength_files','fibers.@final_fiberslength_files'),('outputnode.filtered_fiberslabel_files','fibers.@filtered_fiberslabel_files'),
                             ('outputnode.final_fiberlabels_files','fibers.@final_fiberlabels_files'),('outputnode.streamline_final_files','fibers.@streamline_final_files'),
                             ('outputnode.connectivity_matrices','fibers.connectivity_matrices')])
                        ])
        
        #flow.run(plugin='MultiProc', plugin_args={'n_procs' : 4}) // for multicore processing
        flow.run()
        
        self.prepare_outputs()
        
        return True,'Processing sucessful'

