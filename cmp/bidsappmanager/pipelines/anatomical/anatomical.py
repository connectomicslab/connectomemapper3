# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Anatomical pipeline Class definition
"""

import datetime
import os
import glob

import shutil

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.ui.qt4.image_resource import ImageResource

from pyface.qt.QtCore import *
from pyface.qt.QtGui import *

from bids import BIDSLayout

# Own import
# import cmp.bidsappmanager.pipelines.common as cmp_common

from cmp.bidsappmanager.stages.segmentation.segmentation import SegmentationStageUI
from cmp.bidsappmanager.stages.parcellation.parcellation import ParcellationStageUI

from cmp.pipelines.common import Pipeline
from cmp.pipelines.anatomical.anatomical import Global_Configuration, Check_Input_Notification, AnatomicalPipeline


class Check_Input_NotificationUI(Check_Input_Notification):
    traits_view = View(Item('message', style='readonly', show_label=False),
                       Item('diffusion_imaging_model_message', visible_when='len(diffusion_imaging_model_options)>1',
                            style='readonly', show_label=False),
                       Item('diffusion_imaging_model', editor=EnumEditor(name='diffusion_imaging_model_options'),
                            visible_when='len(diffusion_imaging_model_options)>1'),
                       kind='modal',
                       buttons=['OK'],
                       title="Check inputs")


class AnatomicalPipelineUI(AnatomicalPipeline):
    segmentation = Button()
    # segmentation.setIcon(QIcon(QPixmap("segmentation.png")))
    
    parcellation = Button()
    
    view_mode = Enum('config_view', ['config_view', 'inspect_outputs_view'])
    
    # parcellation.setIcon(QIcon(QPixmap("parcellation.png")))
    
    # custom_run = Button('Custom...')
    # run = Button('Run...')
    
    pipeline_group = VGroup(
        HGroup(spring, UItem('segmentation', style='custom', width=450, height=170, resizable=True,
                             editor_args={'image': ImageResource('segmentation'), 'label': ""}), spring,
               show_labels=False, label=""),
        # Item('parcellation',editor=CustomEditor(image=ImageResource('parcellation'))),show_labels=False),
        HGroup(spring, UItem('parcellation', style='custom', width=450, height=200, resizable=True,
                             editor_args={'image': ImageResource('parcellation'), 'label': ""}), spring,
               show_labels=False, label=""),
        spring,
        springy=True
    )
    
    traits_view = QtView(Include('pipeline_group'))
    
    def __init__(self, project_info):
        
        AnatomicalPipeline.__init__(self, project_info)
        
        self.stages = {
            'Segmentation': SegmentationStageUI(),
            'Parcellation': ParcellationStageUI(pipeline_mode="Diffusion")}
        
        for stage in self.stages.keys():
            if project_info.subject_session != '':
                self.stages[stage].stage_dir = os.path.join(self.base_directory, "derivatives", 'nipype', self.subject,
                                                            project_info.subject_session, self.pipeline_name,
                                                            self.stages[stage].name)
            else:
                self.stages[stage].stage_dir = os.path.join(self.base_directory, "derivatives", 'nipype', self.subject,
                                                            self.pipeline_name, self.stages[stage].name)
    
    def _segmentation_fired(self, info):
        self.stages['Segmentation'].configure_traits(view=self.view_mode)
    
    def _parcellation_fired(self, info):
        self.stages['Parcellation'].configure_traits(view=self.view_mode)
    
    def check_input(self, layout, gui=True):
        print '**** Check Inputs  ****'
        t1_available = False
        valid_inputs = False
        
        types = layout.get_modalities()
        
        if self.global_conf.subject_session == '':
            T1_file = os.path.join(self.subject_directory, 'anat', self.subject + '_T1w.nii.gz')
        else:
            subjid = self.subject.split("-")[1]
            sessid = self.global_conf.subject_session.split("-")[1]
            files = layout.get(subject=subjid, suffix='T1w', extensions='.nii.gz', session=sessid)
            if len(files) > 0:
                T1_file = files[0].filename
                print T1_file
            else:
                error(message="T1w image not found for subject %s, session %s." % (
                subjid, self.global_conf.subject_session), title="Error", buttons=['OK', 'Cancel'], parent=None)
                return
        
        print "Looking in %s for...." % self.base_directory
        print "T1_file : %s" % T1_file
        
        for typ in types:
            if typ == 'T1w' and os.path.isfile(T1_file):
                print "%s available" % typ
                t1_available = True
        
        if t1_available:
            # Copy diffusion data to derivatives / cmp  / subject / dwi
            if self.global_conf.subject_session == '':
                out_T1_file = os.path.join(self.derivatives_directory, 'cmp', self.subject, 'anat',
                                           self.subject + '_T1w.nii.gz')
            else:
                out_T1_file = os.path.join(self.derivatives_directory, 'cmp', self.subject,
                                           self.global_conf.subject_session, 'anat',
                                           self.subject + '_' + self.global_conf.subject_session + '_T1w.nii.gz')
            
            if not os.path.isfile(out_T1_file):
                shutil.copy(src=T1_file, dst=out_T1_file)
            
            valid_inputs = True
            input_message = 'Inputs check finished successfully. \nOnly anatomical data (T1) available.'
        else:
            input_message = 'Error during inputs check. No anatomical data available in folder ' + os.path.join(
                self.base_directory, self.subject) + '/anat/!'
        
        # diffusion_imaging_model = diffusion_imaging_model[0]
        
        if gui:
            # input_notification = Check_Input_Notification(message=input_message, diffusion_imaging_model_options=diffusion_imaging_model,diffusion_imaging_model=diffusion_imaging_model)
            # input_notification.configure_traits()
            print input_message
        
        else:
            print input_message
        
        if (t1_available):
            valid_inputs = True
        else:
            print "Missing required inputs."
            error(message="Missing required inputs. Please see documentation for more details.", title="Error",
                  buttons=['OK', 'Cancel'], parent=None)
        
        for stage in self.stages.values():
            if stage.enabled:
                print stage.name
                print stage.stage_dir
        
        # self.fill_stages_outputs()
        
        return valid_inputs
    
    def check_output(self):
        t1_available = False
        brain_available = False
        brainmask_available = False
        wm_available = False
        roivs_available = False
        valid_output = False
        
        subject = self.subject
        
        if self.global_conf.subject_session == '':
            anat_deriv_subject_directory = os.path.join(self.base_directory, "derivatives", "cmp", self.subject, 'anat')
        else:
            if self.global_conf.subject_session not in subject:
                anat_deriv_subject_directory = os.path.join(self.base_directory, "derivatives", "cmp", subject,
                                                            self.global_conf.subject_session, 'anat')
                subject = "_".join((subject, self.global_conf.subject_session))
            else:
                anat_deriv_subject_directory = os.path.join(self.base_directory, "derivatives", "cmp",
                                                            subject.split("_")[0], self.global_conf.subject_session,
                                                            'anat')
        
        T1_file = os.path.join(anat_deriv_subject_directory, subject + '_T1w_head.nii.gz')
        brain_file = os.path.join(anat_deriv_subject_directory, subject + '_T1w_brain.nii.gz')
        brainmask_file = os.path.join(anat_deriv_subject_directory, subject + '_T1w_brainmask.nii.gz')
        wm_mask_file = os.path.join(anat_deriv_subject_directory, subject + '_T1w_class-WM.nii.gz')
        roiv_files = glob.glob(anat_deriv_subject_directory + "/" + subject + "_T1w_parc_scale*.nii.gz")
        
        error_message = ''
        
        if os.path.isfile(T1_file):
            t1_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % T1_file
            print error_message
            error(message=error_message, title="Error", buttons=['OK', 'Cancel'], parent=None)
        
        if os.path.isfile(brain_file):
            brain_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % brain_file
            print error_message
            error(message=error_message, title="Error", buttons=['OK', 'Cancel'], parent=None)
        
        if os.path.isfile(brainmask_file):
            brainmask_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % brainmask_file
            print error_message
            error(message=error_message, title="Error", buttons=['OK', 'Cancel'], parent=None)
        
        if os.path.isfile(wm_mask_file):
            wm_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % wm_mask_file
            print error_message
            error(message=error_message, title="Error", buttons=['OK', 'Cancel'], parent=None)
        
        cnt1 = 0
        cnt2 = 0
        for roiv_file in roiv_files:
            cnt1 = cnt1 + 1
            if os.path.isfile(roiv_file): cnt2 = cnt2 + 1
        if cnt1 == cnt2:
            roivs_available = True
        else:
            error_message = "Missing %g/%g anatomical parcellation output files. Please re-run the anatomical pipeline" % (
            cnt1 - cnt2, cnt1)
            print error_message
            error(message=error_message, title="Error", buttons=['OK', 'Cancel'], parent=None)
        
        if t1_available == True and brain_available == True and brainmask_available == True and wm_available == True and roivs_available == True:
            print "valid deriv/anat output"
            valid_output = True
        
        return valid_output, error_message
