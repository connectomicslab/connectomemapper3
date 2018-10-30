# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Functional pipeline Class definition
"""

import os
import datetime

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView

from pyface.ui.qt4.image_resource import ImageResource
from pyface.qt.QtCore import *
from pyface.qt.QtGui import *

import nipype.pipeline.engine as pe
from pyface.api import ImageResource

import shutil

from bids.grabbids import BIDSLayout

from cmp.configurator.pipelines.common import *
from cmp.configurator.pipelines.anatomical.anatomical import AnatomicalPipeline
from cmp.configurator.stages.preprocessing.fmri_preprocessing import PreprocessingStage
from cmp.configurator.stages.segmentation.segmentation import SegmentationStage
from cmp.configurator.stages.parcellation.parcellation import ParcellationStage
from cmp.configurator.stages.registration.registration import RegistrationStage
from cmp.configurator.stages.functional.functionalMRI import FunctionalMRIStage
from cmp.configurator.stages.connectome.fmri_connectome import ConnectomeStage

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

        subjid = self.subject.split("-")[1]

        if self.global_conf.subject_session == '':

            files = layout.get(subject=subjid,type='bold',extensions='.nii.gz')
            if len(files) > 0:
                fmri_file = files[0].filename
                print fmri_file
            else:
                error(message="BOLD image not found for subject %s."%(subjid), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
                return

            files = layout.get(subject=subjid,type='T1w',extensions='.nii.gz')
            if len(files) > 0:
                t1_file = files[0].filename
                print t1_file
            else:
                error(message="T1w image not found for subject %s."%(subjid), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
                return

            files = layout.get(subject=subjid,type='T2w',extensions='.nii.gz')
            if len(files) > 0:
                t2_file = files[0].filename
                print t2_file
            else:
                error(message="T2w image not found for subject %s."%(subjid), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        else:
            sessid = self.global_conf.subject_session.split("-")[1]

            files = layout.get(subject=subjid,type='bold',extensions='.nii.gz',session=sessid)
            if len(files) > 0:
                fmri_file = files[0].filename
                print fmri_file
            else:
                error(message="BOLD image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
                return

            files = layout.get(subject=subjid,type='T1w',extensions='.nii.gz',session=sessid)
            if len(files) > 0:
                t1_file = files[0].filename
                print t1_file
            else:
                error(message="T1w image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
                return

            files = layout.get(subject=subjid,type='T2w',extensions='.nii.gz',session=sessid)
            if len(files) > 0:
                t2_file = files[0].filename
                print t2_file
            else:
                error(message="T2w image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)


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
