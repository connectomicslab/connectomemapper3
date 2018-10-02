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

from bids.grabbids import BIDSLayout

# Own import
import cmp.configurator.pipelines.common as cmp_common
from cmp.configurator.stages.segmentation.segmentation import SegmentationStage
from cmp.configurator.stages.parcellation.parcellation import ParcellationStage

class Global_Configuration(HasTraits):
    process_type = Str('anatomical')
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str

class Check_Input_Notification(HasTraits):
    message = Str
    diffusion_imaging_model_options = List(['DSI','DTI','HARDI'])
    diffusion_imaging_model = Str
    diffusion_imaging_model_message = Str('\nMultiple diffusion inputs available. Please select desired diffusion modality.')

    traits_view = View(Item('message',style='readonly',show_label=False),
                       Item('diffusion_imaging_model_message',visible_when='len(diffusion_imaging_model_options)>1',style='readonly',show_label=False),
                       Item('diffusion_imaging_model',editor=EnumEditor(name='diffusion_imaging_model_options'),visible_when='len(diffusion_imaging_model_options)>1'),
                       kind='modal',
                       buttons=['OK'],
                       title="Check inputs")

class AnatomicalPipeline(cmp_common.Pipeline):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("anatomical_pipeline")
    input_folders = ['anat']
    process_type = Str
    diffusion_imaging_model = Str
    parcellation_scheme = Str('Lausanne2008')
    atlas_info = Dict()

    #subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ['Segmentation','Parcellation']# ,'MRTrixConnectome']
    custom_last_stage = Enum('Parcellation',['Segmentation','Parcellation'])

    global_conf = Global_Configuration()

    segmentation = Button()
    #segmentation.setIcon(QIcon(QPixmap("segmentation.png")))

    parcellation = Button()

    #parcellation.setIcon(QIcon(QPixmap("parcellation.png")))

    #custom_run = Button('Custom...')
    #run = Button('Run...')

    config_file = Str

    pipeline_group = VGroup(
                        HGroup(spring,UItem('segmentation',style='custom',width=450,height=170,resizable=True,editor_args={'image':ImageResource('segmentation'),'label':""}),spring,show_labels=False,label=""),#Item('parcellation',editor=CustomEditor(image=ImageResource('parcellation'))),show_labels=False),
                        HGroup(spring,UItem('parcellation',style='custom',width=450,height=200,resizable=True,editor_args={'image':ImageResource('parcellation'),'label':""}),spring,show_labels=False,label=""),
                        spring,
                        springy=True
                        )

    def __init__(self,project_info):
        self.stages = {'Segmentation':SegmentationStage(),
            'Parcellation':ParcellationStage(pipeline_mode = "Diffusion")}

        cmp_common.Pipeline.__init__(self, project_info)
        #super(Pipeline, self).__init__(project_info)

        self.subject = project_info.subject
        self.last_date_processed = project_info.anat_last_date_processed

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = self.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory =  os.path.join(self.base_directory,self.subject,self.global_conf.subject_session)
        else:
            self.global_conf.subject_session = ''
            self.subject_directory =  os.path.join(self.base_directory,self.subject)

        self.derivatives_directory =  os.path.join(self.base_directory,'derivatives')

        self.stages['Segmentation'].config.on_trait_change(self.update_parcellation,'seg_tool')
        self.stages['Parcellation'].config.on_trait_change(self.update_segmentation,'parcellation_scheme')

        self.stages['Parcellation'].config.on_trait_change(self.update_parcellation_scheme,'parcellation_scheme')

    def check_config(self):
        if self.stages['Segmentation'].config.seg_tool ==  'Custom segmentation':
            if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\nCustom segmentation selected but no WM mask provided.\nPlease provide an existing WM mask file in the Segmentation configuration window.\n')
            if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
                return('\n\tCustom segmentation selected but no atlas provided.\nPlease specify an existing atlas file in the Parcellation configuration window.\t\n')
            if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
                return('\n\tCustom segmentation selected but no graphml info provided.\nPlease specify an existing graphml file in the Parcellation configuration window.\t\n')
        return ''

    def update_parcellation_scheme(self):
        self.parcellation_scheme = self.stages['Parcellation'].config.parcellation_scheme
        self.atlas_info = self.stages['Parcellation'].config.atlas_info

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

    def _segmentation_fired(self, info):
        self.stages['Segmentation'].configure_traits()

    def _parcellation_fired(self, info):
        self.stages['Parcellation'].configure_traits()

    def check_input(self, layout, gui=True):
        print '**** Check Inputs  ****'
        t1_available = False
        valid_inputs = False

        types = layout.get_types()

        if self.global_conf.subject_session == '':
            T1_file = os.path.join(self.subject_directory,'anat',self.subject+'_T1w.nii.gz')
        else:
            subjid = self.subject.split("-")[1]
            sessid = self.global_conf.subject_session.split("-")[1]
            files = layout.get(subject=subjid,type='T1w',extensions='.nii.gz',session=sessid)
            if len(files) > 0:
                T1_file = files[0].filename
                print T1_file
            else:
                error(message="T1w image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
                return

        print "Looking in %s for...." % self.base_directory
        print "T1_file : %s" % T1_file

        for typ in types:
            if typ == 'T1w' and os.path.isfile(T1_file):
                print "%s available" % typ
                t1_available = True

        if t1_available:
            #Copy diffusion data to derivatives / cmp  / subject / dwi
            if self.global_conf.subject_session == '':
                out_T1_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'anat',self.subject+'_T1w.nii.gz')
            else:
                out_T1_file = os.path.join(self.derivatives_directory,'cmp',self.subject,self.global_conf.subject_session,'anat',self.subject+'_'+self.global_conf.subject_session+'_T1w.nii.gz')

            if not os.path.isfile(out_T1_file):
                shutil.copy(src=T1_file,dst=out_T1_file)

            valid_inputs = True
            input_message = 'Inputs check finished successfully. \nOnly anatomical data (T1) available.'
        else:
            input_message = 'Error during inputs check. No anatomical data available in folder '+os.path.join(self.base_directory,self.subject)+'/anat/!'

        #diffusion_imaging_model = diffusion_imaging_model[0]

        if gui:
            #input_notification = Check_Input_Notification(message=input_message, diffusion_imaging_model_options=diffusion_imaging_model,diffusion_imaging_model=diffusion_imaging_model)
            #input_notification.configure_traits()
            print input_message

        else:
            print input_message

        if(t1_available):
            valid_inputs = True
        else:
            print "Missing required inputs."
            error(message="Missing required inputs. Please see documentation for more details.", title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        for stage in self.stages.values():
            if stage.enabled:
                print stage.name
                print stage.stage_dir

        self.fill_stages_outputs()

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
            anat_deriv_subject_directory = os.path.join(self.base_directory,"derivatives","cmp",self.subject,'anat')
        else:
            if self.global_conf.subject_session not in subject:
                anat_deriv_subject_directory = os.path.join(self.base_directory,"derivatives","cmp",subject,self.global_conf.subject_session,'anat')
                subject = "_".join((subject,self.global_conf.subject_session))
            else:
                anat_deriv_subject_directory = os.path.join(self.base_directory,"derivatives","cmp",subject.split("_")[0],self.global_conf.subject_session,'anat')

        T1_file = os.path.join(anat_deriv_subject_directory,subject+'_T1w_head.nii.gz')
        brain_file = os.path.join(anat_deriv_subject_directory,subject+'_T1w_brain.nii.gz')
        brainmask_file = os.path.join(anat_deriv_subject_directory,subject+'_T1w_brainmask.nii.gz')
        wm_mask_file = os.path.join(anat_deriv_subject_directory,subject+'_T1w_class-WM.nii.gz')
        roiv_files = glob.glob(anat_deriv_subject_directory+"/"+subject+"_T1w_parc_scale*.nii.gz")

        error_message = ''

        if os.path.isfile(T1_file):
            t1_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % T1_file
            print error_message
            error(message=error_message, title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        if os.path.isfile(brain_file):
            brain_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % brain_file
            print error_message
            error(message=error_message, title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        if os.path.isfile(brainmask_file):
            brainmask_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % brainmask_file
            print error_message
            error(message=error_message, title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        if os.path.isfile(wm_mask_file):
            wm_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % wm_mask_file
            print error_message
            error(message=error_message, title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        cnt1=0
        cnt2=0
        for roiv_file in roiv_files:
            cnt1 = cnt1 + 1
            if os.path.isfile(roiv_file): cnt2 = cnt2 + 1
        if cnt1 == cnt2:
            roivs_available = True
        else:
            error_message = "Missing %g/%g anatomical parcellation output files. Please re-run the anatomical pipeline" % (cnt1-cnt2,cnt1)
            print error_message
            error(message=error_message, title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        if t1_available == True and brain_available == True and brainmask_available == True and wm_available == True and roivs_available == True:
            print "valid deriv/anat output"
            valid_output = True

        return valid_output,error_message
