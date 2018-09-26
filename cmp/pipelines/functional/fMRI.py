# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Functional pipeline Class definition
"""

import os
import datetime

# try:
#     from traitsui.api import *
#     from traits.api import *
#     from traitsui.wx.themed_button_editor import ThemedButtonEditor
# except ImportError:
#     from enthought.traits.api import *
#     from enthought.traits.ui.api import *
#     from  enthought.traits.ui.wx.themed_button_editor import ThemedButtonEditor

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.ui.qt4.image_resource import ImageResource

import apptools.io.api as io

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Merge
from nipype import config, logging
from nipype.caching import Memory
from pyface.api import ImageResource
import shutil

import nibabel as nib

from bids.grabbids import BIDSLayout

from cmp.pipelines.common import *
from cmp.pipelines.anatomical.anatomical import AnatomicalPipeline
from cmp.stages.preprocessing.fmri_preprocessing import PreprocessingStage
from cmp.stages.segmentation.segmentation import SegmentationStage
from cmp.stages.parcellation.parcellation import ParcellationStage
from cmp.stages.registration.registration import RegistrationStage
from cmp.stages.functional.functionalMRI import FunctionalMRIStage
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
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("fMRI_pipeline")
    input_folders = ['anat','func']
    seg_tool = Str

    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory

    ordered_stage_list = ['Preprocessing','Registration','FunctionalMRI','Connectome']

    global_conf = Global_Configuration()

    preprocessing = Button('Preprocessing')
    functionalMRI = Button('FunctionalMRI')
    registration = Button('Registration')
    connectome = Button('Connectome')

    config_file = Str

    subjects_dir = Str
    subject_id = Str

    # pipeline_group = VGroup(
    #                     HGroup(spring,Item('preprocessing',editor=ToolkitEditorFactory(image=ImageResource('preprocessing'))),spring,show_labels=False),
    #                     HGroup(spring,Item('registration',editor=ToolkitEditorFactory(image=ImageResource('registration'))),spring,show_labels=False),
    #                     HGroup(spring,Item('functionalMRI',editor=ToolkitEditorFactory(image=ImageResource('functionalMRI'))),spring,show_labels=False),
    #                     HGroup(spring,Item('connectome',editor=ToolkitEditorFactory(image=ImageResource('connectome'))),spring,show_labels=False),
    #                     springy=True
    #                     )

    pipeline_group = VGroup(
                        HGroup(spring,UItem('preprocessing',style='custom',width=450,height=130,resizable=True,editor_args={'image':ImageResource('preprocessing'),'label':""}),spring,show_labels=False,label=""),
                        HGroup(spring,UItem('registration',style='custom',width=500,height=110,resizable=True,editor_args={'image':ImageResource('registration'),'label':""}),spring,show_labels=False,label=""),
                        HGroup(spring,UItem('functionalMRI',style='custom',width=450,height=240,resizable=True,editor_args={'image':ImageResource('functionalMRI'),'label':""}),spring,show_labels=False,label=""),
                        HGroup(spring,UItem('connectome',style='custom',width=450,height=130,resizable=True,editor_args={'image':ImageResource('connectome'),'label':""}),spring,show_labels=False,label=""),
                        spring,
                        springy=True
                    )

    def __init__(self,project_info):
        self.stages = {'Preprocessing':PreprocessingStage(),
            'Registration':RegistrationStage(pipeline_mode = "fMRI"),
            'FunctionalMRI':FunctionalMRIStage(),
            'Connectome':ConnectomeStage()}
        Pipeline.__init__(self, project_info)
        self.stages['FunctionalMRI'].config.on_trait_change(self.update_nuisance_requirements,'global_nuisance')
        self.stages['FunctionalMRI'].config.on_trait_change(self.update_nuisance_requirements,'csf')
        self.stages['FunctionalMRI'].config.on_trait_change(self.update_nuisance_requirements,'wm')
        self.stages['Connectome'].config.on_trait_change(self.update_scrubbing,'apply_scrubbing')

        self.subject = project_info.subject

        self.subjects_dir = project_info.freesurfer_subjects_dir
        self.subject_id = project_info.freesurfer_subject_id

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = self.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory =  os.path.join(self.base_directory,self.subject,project_info.subject_session)
        else:
            self.global_conf.subject_session = ''
            self.subject_directory =  os.path.join(self.base_directory,self.subject)

        self.derivatives_directory =  os.path.join(self.base_directory,'derivatives')

    def _subject_changed(self,new):
        self.stages['Connectome'].config.subject = new

    def update_registration(self):
        if self.seg_tool == "Custom segmentation" :
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
        self.stages['Registration'].config.apply_to_eroded_brain = self.stages['FunctionalMRI'].config.global_nuisance
        self.stages['Registration'].config.apply_to_eroded_csf = self.stages['FunctionalMRI'].config.csf
        self.stages['Registration'].config.apply_to_eroded_wm = self.stages['FunctionalMRI'].config.wm

    def update_scrubbing(self):
        self.stages['FunctionalMRI'].config.scrubbing = self.stages['Connectome'].config.apply_scrubbing

    def _preprocessing_fired(self, info):
        print "preproc fired"
        self.stages['Preprocessing'].configure_traits()

    def _functionalMRI_fired(self, info):
        print "func fired"
        self.stages['FunctionalMRI'].configure_traits()

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

    def check_input(self, layout, gui=True):
        print '**** Check Inputs ****'
        fMRI_available = False
        t1_available = False
        t2_available = False
        valid_inputs = False

        if self.global_conf.subject_session == '':
            subject = self.subject
        else:
            subject = "_".join((self.subject,self.global_conf.subject_session))

        fmri_file = os.path.join(self.subject_directory,'func',subject+'_task-rest_bold.nii.gz')
        t1_file = os.path.join(self.subject_directory,'anat',subject+'_T1w.nii.gz')
        t2_file = os.path.join(self.subject_directory,'anat',subject+'_T2w.nii.gz')

        print "Looking for...."
        print "fmri_file : %s" % fmri_file
        print "t1_file : %s" % t1_file
        print "t2_file : %s" % t2_file

        # mods = layout.get_modalities()
        types = layout.get_types()
        print "Available modalities :"
        for typ in types:
            print "-%s" % typ

        for typ in types:
            if typ == 'T1w' and os.path.isfile(t1_file):
                print "%s available" % typ
                t1_available = True
            if typ == 'T2w' and os.path.isfile(t2_file):
                print "%s available" % typ
                t2_available = True
            if typ == 'bold' and os.path.isfile(fmri_file):
                print "%s available" % typ
                fMRI_available = True

        print('fMRI :',fMRI_available)
        print('t1 :',t1_available)
        print('t2 :',t2_available)

        if fMRI_available:
            if self.global_conf.subject_session == '':
                out_dir = os.path.join(self.derivatives_directory,'cmp',self.subject)
            else:
                out_dir = os.path.join(self.derivatives_directory,'cmp',self.subject,self.global_conf.subject_session)

            out_fmri_file = os.path.join(out_dir,'func',subject+'_task-rest_bold.nii.gz')
            shutil.copy(src=fmri_file,dst=out_fmri_file)
            if t2_available:
                out_t2_file = os.path.join(out_dir,'anat',subject+'_T2w.nii.gz')
                shutil.copy(src=t2_file,dst=out_t2_file)
                # swap_and_reorient(src_file=os.path.join(self.base_directory,'NIFTI','T2_orig.nii.gz'),
                #                   ref_file=os.path.join(self.base_directory,'NIFTI','fMRI.nii.gz'),
                #                   out_file=os.path.join(self.base_directory,'NIFTI','T2.nii.gz'))
            if t1_available:
                # out_t1_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'anat',self.subject+'_T1w.nii.gz')
                # shutil.copy(src=t1_file,dst=out_t1_file)
                valid_inputs = True
                input_message = 'Inputs check finished successfully.\nfMRI and morphological data available.'
            else:
                input_message = 'Error during inputs check.\nMorphological data (T1) not available.'
        elif t1_available:
            input_message = 'Error during inputs check. \nfMRI data not available (fMRI).'
        else:
            input_message = 'Error during inputs check. No fMRI or morphological data available in folder '+os.path.join(self.base_directory,'RAWDATA')+'!'

        print input_message

        # if gui:
        #     # input_notification = Check_Input_Notification(message=input_message, imaging_model='fMRI')
        #     # input_notification.configure_traits()
        #     self.global_conf.imaging_model = input_notification.imaging_model
        #     self.stages['Registration'].config.imaging_model = input_notification.imaging_model
        # else:
        #     self.global_conf.imaging_model = 'fMRI'
        #     self.stages['Registration'].config.imaging_model = 'fMRI'

        self.global_conf.imaging_model = 'fMRI'
        self.stages['Registration'].config.imaging_model = 'fMRI'

        if t2_available:
            self.stages['Registration'].config.registration_mode_trait = ['FSL (Linear)','BBregister (FS)']
        else:
            self.stages['Registration'].config.registration_mode_trait = ['FSL (Linear)','BBregister (FS)']

        self.fill_stages_outputs()

        return valid_inputs

    def check_config(self):
        if self.stages['FunctionalMRI'].config.motion == True and self.stages['Preprocessing'].config.motion_correction == False:
            return('\n\tMotion signal regression selected but no motion correction set.\t\n\tPlease activate motion correction in the preprocessing configuration window,\n\tor disable the motion signal regression in the functional configuration window.\t\n')
        if self.stages['Connectome'].config.apply_scrubbing == True and self.stages['Preprocessing'].config.motion_correction == False:
            return('\n\tScrubbing applied but no motion correction set.\t\n\tPlease activate motion correction in the preprocessing configutation window,\n\tor disable scrubbing in the connectome configuration window.\t\n')
        return ''

    def process(self):
        # Process time
        self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        if '_' in self.subject:
            self.subject = self.subject.split('_')[0]

        old_subject = self.subject

        if self.global_conf.subject_session == '':
            deriv_subject_directory = os.path.join(self.base_directory,"derivatives","cmp",self.subject)
        else:
            deriv_subject_directory = os.path.join(self.base_directory,"derivatives","cmp",self.subject,self.global_conf.subject_session)

            self.subject = "_".join((self.subject,self.global_conf.subject_session))

        # Initialization
        if os.path.isfile(os.path.join(deriv_subject_directory,"func","pypeline.log")):
            os.unlink(os.path.join(deriv_subject_directory,"func","pypeline.log"))
        config.update_config({'logging': {'log_directory': os.path.join(deriv_subject_directory,"func"),
                                  'log_to_file': True},
                              'execution': {'remove_unnecessary_outputs': False,
                              'stop_on_first_crash': True,'stop_on_first_rerun': False,
                              'crashfile_format': "txt"}
                              })
        logging.update_logging(config)
        iflogger = logging.getLogger('nipype.interface')

        iflogger.info("**** Processing ****")
        print self.anat_flow

        flow = self.create_pipeline_flow(deriv_subject_directory=deriv_subject_directory)
        flow.write_graph(graph2use='colored', format='svg', simple_form=False)

        # try:

        if(self.number_of_cores != 1):
            flow.run(plugin='MultiProc', plugin_args={'n_procs' : self.number_of_cores})
        else:
            flow.run()

        self.fill_stages_outputs()

        iflogger.info("**** Processing finished ****")

        return True,'Processing sucessful'

        self.subject = old_subject

        # except:
        #
        #     self.subject = old_subject
        #     iflogger.info("**** Processing terminated :< ****")
        #
        #     return False,'Processing unsucessful'

        # # Clean undesired folders/files
        # rm_file_list = ['rh.EC_average','lh.EC_average','fsaverage']
        # for file_to_rm in rm_file_list:
        #     if os.path.exists(os.path.join(self.base_directory,file_to_rm)):
        #         os.remove(os.path.join(self.base_directory,file_to_rm))
        #
        # # copy .ini and log file
        # outdir = os.path.join(self.base_directory,"RESULTS",'fMRI',now)
        # if not os.path.exists(outdir):
        #     os.makedirs(outdir)
        # shutil.copy(self.config_file,outdir)
        # shutil.copy(os.path.join(self.base_directory,'LOG','pypeline.log'),outdir)

        # iflogger.info("**** Processing finished ****")
        #
        # return True,'Processing sucessful'

    def create_pipeline_flow(self,deriv_subject_directory):

        subject_directory = self.subject_directory

        #datasource.inputs.subject = self.subject

        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="diffusion_sinker")
        sinker.inputs.base_directory = os.path.join(deriv_subject_directory)

        sinker.inputs.substitutions = [
                                        ('wm_mask_registered.nii.gz', self.subject+'_T1w_space-bold_class-WM.nii.gz'),
                                        ('eroded_wm_registered.nii.gz', self.subject+'_T1w_space-bold_class-WM_eroded.nii.gz'),
                                        ('fMRI_despike_st_mcf.nii.gz_mean_reg.nii.gz', self.subject+'_task-rest_meanBOLD.nii.gz'),
                                        ('fMRI_despike_st_mcf.nii.gz.par', self.subject+'_task-rest_bold_motion.par'),
                                        ('FD.npy',self.subject+'_task-rest_bold_srubbing_FD.npy'),
                                        ('DVARS.npy', self.subject+'_task-rest_bold_scrubbing_DVARS.npy'),
                                        ('fMRI_bandpass.nii.gz',self.subject+'_task-rest_bold_bandpass.nii.gz'),

                                        (self.subject+'_T1w_parc_scale1_flirt.nii.gz',self.subject+'_T1w_space-meanBOLD_parc_scale1.nii.gz'),
                                        (self.subject+'_T1w_parc_scale2_flirt.nii.gz',self.subject+'_T1w_space-meanBOLD_parc_scale2.nii.gz'),
                                        (self.subject+'_T1w_parc_scale3_flirt.nii.gz',self.subject+'_T1w_space-meanBOLD_parc_scale3.nii.gz'),
                                        (self.subject+'_T1w_parc_scale4_flirt.nii.gz',self.subject+'_T1w_space-meanBOLD_parc_scale4.nii.gz'),
                                        (self.subject+'_T1w_parc_scale5_flirt.nii.gz',self.subject+'_T1w_space-meanBOLD_parc_scale5.nii.gz'),

                                        ('connectome_scale',self.subject+'_bold_connectome_scale'),
                                        ('averageTimeseries_scale',self.subject+'_bold_averageTimeseries_scale'),

                                      ]

        # Data import
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['fMRI','T1','T2','aseg','brain','brain_mask','wm_mask_file','wm_eroded','brain_eroded','csf_eroded','roi_volume_s1','roi_volume_s2','roi_volume_s3','roi_volume_s4','roi_volume_s5','roi_graphml_s1','roi_graphml_s2','roi_graphml_s3','roi_graphml_s4','roi_graphml_s5']), name='datasource')
        datasource.inputs.base_directory = deriv_subject_directory
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        #datasource.inputs.field_template = dict(fMRI='fMRI.nii.gz',T1='T1.nii.gz',T2='T2.nii.gz')
        datasource.inputs.field_template = dict(fMRI='func/'+self.subject+'_task-rest_bold.nii.gz',T1='anat/'+self.subject+'_T1w_head.nii.gz',T2='anat/'+self.subject+'_T2w.nii.gz',aseg='anat/'+self.subject+'_T1w_aseg.nii.gz',brain='anat/'+self.subject+'_T1w_brain.nii.gz',brain_mask='anat/'+self.subject+'_T1w_brainmask.nii.gz',
                                                wm_mask_file='anat/'+self.subject+'_T1w_class-WM.nii.gz',wm_eroded='anat/'+self.subject+'_T1w_class-WM.nii.gz',
                                                brain_eroded='anat/'+self.subject+'_T1w_brainmask.nii.gz',csf_eroded='anat/'+self.subject+'_T1w_class-CSF.nii.gz',
                                                roi_volume_s1='anat/'+self.subject+'_T1w_parc_scale1.nii.gz',roi_volume_s2='anat/'+self.subject+'_T1w_parc_scale2.nii.gz',roi_volume_s3='anat/'+self.subject+'_T1w_parc_scale3.nii.gz',
                                                roi_volume_s4='anat/'+self.subject+'_T1w_parc_scale4.nii.gz',roi_volume_s5='anat/'+self.subject+'_T1w_parc_scale5.nii.gz',roi_graphml_s1='anat/'+self.subject+'_T1w_parc_scale1.graphml',roi_graphml_s2='anat/'+self.subject+'_T1w_parc_scale2.graphml',roi_graphml_s3='anat/'+self.subject+'_T1w_parc_scale3.graphml',
                                                roi_graphml_s4='anat/'+self.subject+'_T1w_parc_scale4.graphml',roi_graphml_s5='anat/'+self.subject+'_T1w_parc_scale5.graphml')
        datasource.inputs.sort_filelist=False

        # Clear previous outputs
        self.clear_stages_outputs()

        # Create fMRI flow
        fMRI_flow = pe.Workflow(name='fMRI_pipeline',base_dir=os.path.join(deriv_subject_directory,'tmp'))
        fMRI_inputnode = pe.Node(interface=util.IdentityInterface(fields=["fMRI","T1","T2","subjects_dir","subject_id","wm_mask_file","roi_volumes","roi_graphMLs","wm_eroded","brain_eroded","csf_eroded"]),name="inputnode")
        fMRI_inputnode.inputs.parcellation_scheme = self.parcellation_scheme
        fMRI_inputnode.inputs.atlas_info = self.atlas_info
        fMRI_inputnode.subjects_dir = self.subjects_dir
        fMRI_inputnode.subject_id = self.subject_id

        fMRI_outputnode = pe.Node(interface=util.IdentityInterface(fields=["connectivity_matrices"]),name="outputnode")
        fMRI_flow.add_nodes([fMRI_inputnode,fMRI_outputnode])

        merge_roi_volumes = pe.Node(interface=Merge(5),name='merge_roi_volumes')
        merge_roi_graphmls = pe.Node(interface=Merge(5),name='merge_roi_graphmls')

        def remove_non_existing_scales(roi_volumes):
            out_roi_volumes = []
            for vol in roi_volumes:
                if vol != None: out_roi_volumes.append(vol)
            return out_roi_volumes

        fMRI_flow.connect([
                      (datasource,merge_roi_volumes,[("roi_volume_s1","in1"),("roi_volume_s2","in2"),("roi_volume_s3","in3"),("roi_volume_s4","in4"),("roi_volume_s5","in5")])
                      ])

        fMRI_flow.connect([
                      (datasource,merge_roi_graphmls,[("roi_graphml_s1","in1"),("roi_graphml_s2","in2"),("roi_graphml_s3","in3"),("roi_graphml_s4","in4"),("roi_graphml_s5","in5")])
                      ])

        fMRI_flow.connect([
                      (datasource,fMRI_inputnode,[("fMRI","fMRI"),("T1","T1"),("T2","T2"),("aseg","aseg"),("wm_mask_file","wm_mask_file"),("brain_eroded","brain_eroded"),("wm_eroded","wm_eroded"),("csf_eroded","csf_eroded")]), #,( "roi_volumes","roi_volumes")])
                      (merge_roi_volumes,fMRI_inputnode,[( ("out",remove_non_existing_scales),"roi_volumes")]),
                      (merge_roi_graphmls,fMRI_inputnode,[( ("out",remove_non_existing_scales),"roi_graphMLs")]),
                      ])


        if self.stages['Preprocessing'].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            fMRI_flow.connect([
                (fMRI_inputnode,preproc_flow,[("fMRI","inputnode.functional")]),
                (preproc_flow,sinker,[("outputnode.mean_vol","func.@mean_vol")]),
                ])

        if self.stages['Registration'].enabled:
            reg_flow = self.create_stage_flow("Registration")
            fMRI_flow.connect([
                          (fMRI_inputnode,reg_flow,[('T1','inputnode.T1')]),(fMRI_inputnode,reg_flow,[('T2','inputnode.T2')]),
                          (preproc_flow,reg_flow, [('outputnode.mean_vol','inputnode.target')]),
                          (fMRI_inputnode,reg_flow, [('wm_mask_file','inputnode.wm_mask'),('roi_volumes','inputnode.roi_volumes'),
                                                ('wm_eroded','inputnode.eroded_wm')]),
                          (reg_flow,sinker, [('outputnode.wm_mask_registered_crop','func.@registered_wm'),('outputnode.roi_volumes_registered_crop','func.@registered_roi_volumes'),
                                                 ('outputnode.eroded_wm_registered_crop','func.@eroded_wm'),('outputnode.eroded_csf_registered_crop','func.@eroded_csf'),
                                                 ('outputnode.eroded_brain_registered_crop','func.@eroded_brain')]),
                          ])
            if self.stages['FunctionalMRI'].config.global_nuisance:
                fMRI_flow.connect([
                              (fMRI_inputnode,reg_flow,[('brain_eroded','inputnode.eroded_brain')])
                            ])
            if self.stages['FunctionalMRI'].config.csf:
                fMRI_flow.connect([
                              (fMRI_inputnode,reg_flow,[('csf_eroded','inputnode.eroded_csf')])
                            ])
            if self.stages['Registration'].config.registration_mode == "BBregister (FS)":
                fMRI_flow.connect([
                          (fMRI_inputnode,reg_flow, [('subjects_dir','inputnode.subjects_dir'),
                                                ('subject_id','inputnode.subject_id')]),
                          ])

        if self.stages['FunctionalMRI'].enabled:
            func_flow = self.create_stage_flow("FunctionalMRI")
            fMRI_flow.connect([
                        (preproc_flow,func_flow, [('outputnode.functional_preproc','inputnode.preproc_file')]),
                        (reg_flow,func_flow, [('outputnode.wm_mask_registered_crop','inputnode.registered_wm'),('outputnode.roi_volumes_registered_crop','inputnode.registered_roi_volumes'),
                                              ('outputnode.eroded_wm_registered_crop','inputnode.eroded_wm'),('outputnode.eroded_csf_registered_crop','inputnode.eroded_csf'),
                                              ('outputnode.eroded_brain_registered_crop','inputnode.eroded_brain')]),
                        (func_flow,sinker,[('outputnode.func_file','func.@func_file'),("outputnode.FD","func.@FD"),
                                              ("outputnode.DVARS","func.@DVARS")]),
                        ])
            if self.stages['FunctionalMRI'].config.scrubbing or self.stages['FunctionalMRI'].config.motion:
                fMRI_flow.connect([
                                   (preproc_flow,func_flow,[("outputnode.par_file","inputnode.motion_par_file")]),
                                   (preproc_flow,sinker,[("outputnode.par_file","func.@motion_par_file")])
                                ])

        if self.stages['Connectome'].enabled:
            self.stages['Connectome'].config.subject = self.global_conf.subject
            con_flow = self.create_stage_flow("Connectome")
            fMRI_flow.connect([
		                (fMRI_inputnode,con_flow, [('parcellation_scheme','inputnode.parcellation_scheme'),('roi_graphMLs','inputnode.roi_graphMLs')]),
		                (func_flow,con_flow, [('outputnode.func_file','inputnode.func_file'),("outputnode.FD","inputnode.FD"),
                                              ("outputnode.DVARS","inputnode.DVARS")]),
                        (reg_flow,con_flow,[("outputnode.roi_volumes_registered_crop","inputnode.roi_volumes_registered")]),
                        (con_flow,fMRI_outputnode,[("outputnode.connectivity_matrices","connectivity_matrices")]),
                        (con_flow,sinker,[("outputnode.connectivity_matrices","func.@connectivity_matrices")]),
                        (con_flow,sinker,[("outputnode.avg_timeseries","func.@avg_timeseries")])
		                ])

            if self.parcellation_scheme == "Custom":
                fMRI_flow.connect([(fMRI_inputnode,con_flow, [('atlas_info','inputnode.atlas_info')])])

        return fMRI_flow


    def old_check_input(self, gui=True):
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

    def old_check_config(self):
        common_check = Pipeline.check_config(self)
        if common_check == '':
            if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation' and self.stages['FunctionalMRI'].config.global_nuisance and not os.path.exists(self.stages['Parcellation'].config.brain_file):
                return('\n\tGlobal signal regression selected but no existing brain mask provided.\t\n\tPlease provide a brain mask in the parcellation configuration window,\n\tor disable the global signal regression in the functional configuration window.\t\n')
            if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation' and self.stages['FunctionalMRI'].config.csf and not os.path.exists(self.stages['Parcellation'].config.csf_file):
                return('\n\tCSF signal regression selected but no existing csf mask provided.\t\n\tPlease provide a csf mask in the parcellation configuration window,\n\tor disable the csf signal regression in the functional configuration window.\t\n')
            if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation' and self.stages['FunctionalMRI'].config.wm and not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\n\tWM signal regression selected but no existing wm mask provided.\t\n\tPlease provide a wm mask in the segmentation configuration window,\n\tor disable the wm signal regression in the functional configuration window.\t\n')
            if self.stages['FunctionalMRI'].config.motion == True and self.stages['Preprocessing'].config.motion_correction == False:
                return('\n\tMotion signal regression selected but no motion correction set.\t\n\tPlease activate motion correction in the preprocessing configuration window,\n\tor disable the motion signal regression in the functional configuration window.\t\n')
            if self.stages['Connectome'].config.apply_scrubbing == True and self.stages['Preprocessing'].config.motion_correction == False:
                return('\n\tScrubbing applied but no motion correction set.\t\n\tPlease activate motion correction in the preprocessing configutation window,\n\tor disable scrubbing in the connectome configuration window.\t\n')
            return ''
        return common_check

    def old_process(self):
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
        iflogger = logging.getLogger('nipype.interface')

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
            if self.stages['FunctionalMRI'].config.global_nuisance:
                fMRI_flow.connect([
                              (fMRI_inputnode,reg_flow,[('brain_eroded','inputnode.eroded_brain')])
                            ])
            if self.stages['FunctionalMRI'].config.csf:
                fMRI_flow.connect([
                              (fMRI_inputnode,reg_flow,[('csf_eroded','inputnode.eroded_csf')])
                            ])
            if self.stages['Registration'].config.registration_mode == "BBregister (FS)":
                fMRI_flow.connect([
                          (fMRI_inputnode,reg_flow, [('subjects_dir','inputnode.subjects_dir'),
                                                ('subject_id','inputnode.subject_id')]),
                          ])

        if self.stages['FunctionalMRI'].enabled:
            func_flow = self.create_stage_flow("FunctionalMRI")
            fMRI_flow.connect([
                        (preproc_flow,func_flow, [('outputnode.functional_preproc','inputnode.preproc_file')]),
                        (reg_flow,func_flow, [('outputnode.wm_mask_registered','inputnode.registered_wm'),('outputnode.roi_volumes_registered','inputnode.registered_roi_volumes'),
                                              ('outputnode.eroded_wm_registered','inputnode.eroded_wm'),('outputnode.eroded_csf_registered','inputnode.eroded_csf'),
                                              ('outputnode.eroded_brain_registered','inputnode.eroded_brain')])
                        ])
            if self.stages['FunctionalMRI'].config.scrubbing or self.stages['FunctionalMRI'].config.motion:
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

            if self.parcellation_scheme == "Custom":
                fMRI_flow.connect([(fMRI_inputnode,con_flow, [('atlas_info','inputnode.atlas_info')])])

        # Create NIPYPE flow

        flow = pe.Workflow(name='nipype', base_dir=os.path.join(self.base_directory))

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
        print('out of run')
        self.fill_stages_outputs()
        print('after filling stages outputs')
        # Clean undesired folders/files
        #rm_file_list = ['rh.EC_average','lh.EC_average','fsaverage']
        #for file_to_rm in rm_file_list:
        #    if os.path.exists(os.path.join(self.base_directory,file_to_rm)):
        #        os.remove(os.path.join(self.base_directory,file_to_rm))

        # copy .ini and log file
        outdir = os.path.join(self.base_directory,"RESULTS",'fMRI',now)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        shutil.copy(self.config_file,outdir)
        shutil.copy(os.path.join(self.base_directory,'LOG','pypeline.log'),outdir)

        iflogger.info("**** Processing finished ****")

        return True,'Processing sucessful'
