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
import fnmatch
import shutil
import threading
import multiprocessing
import time

from nipype.utils.filemanip import copyfile
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.dcm2nii import Dcm2niix
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs


# from pyface.api import ImageResource
import nipype.interfaces.io as nio
from nipype import config, logging

from nipype.caching import Memory
from nipype.interfaces.base import CommandLineInputSpec, CommandLine, traits, BaseInterface, \
    BaseInterfaceInputSpec, File, TraitedSpec, isdefined, Directory, InputMultiPath
from nipype.utils.filemanip import split_filename

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.ui.qt4.image_resource import ImageResource

import apptools.io.api as io

from pyface.qt.QtCore import *
from pyface.qt.QtGui import *

from bids.grabbids import BIDSLayout

# Own import
import cmp.interfaces.fsl as cmp_fsl

import cmp.pipelines.common as cmp_common
from cmp.stages.segmentation.segmentation import SegmentationStage
from cmp.stages.parcellation.parcellation import ParcellationStage

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
    #input_folders = ['DSI','DTI','HARDI','T1','T2']
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

    flow = Instance(pe.Workflow)

    pipeline_group = VGroup(
                        HGroup(spring,UItem('segmentation',style='custom',width=450,height=170,resizable=True,editor_args={'image':ImageResource('segmentation'),'label':""}),spring,show_labels=False,label=""),#Item('parcellation',editor=CustomEditor(image=ImageResource('parcellation'))),show_labels=False),
                        HGroup(spring,UItem('parcellation',style='custom',width=450,height=200,resizable=True,editor_args={'image':ImageResource('parcellation'),'label':""}),spring,show_labels=False,label=""),
                        # HGroup(spring,Item('segmentation',style='custom',width=550,height=170,editor_args={'image':ImageResource('segmentation',search_path=['./']),'label':""}),spring,show_labels=False),#Item('parcellation',editor=CustomEditor(image=ImageResource('parcellation'))),show_labels=False),
                        # HGroup(spring,Item('parcellation',style='custom',width=550,height=200,editor_args={'image':ImageResource('parcellation',search_path=['./']),'label':""}),spring,show_labels=False),
                        # HGroup(spring,Item('segmentation',style='custom',editor_args={'image':ImageResource('segmentation',search_path=['./']),'label':""}),spring,show_labels=False),#Item('parcellation',editor=CustomEditor(image=ImageResource('parcellation'))),show_labels=False),
                        # HGroup(spring,Item('parcellation',style='custom',editor_args={'image':ImageResource('parcellation',search_path=['./']),'label':""}),spring,show_labels=False),
                        spring,
    #                    HGroup(spring,Item('run',width=50,show_label=False),spring,Item('custom_run',width=50,show_label=False),spring),
                        springy=True
                        )

    def __init__(self,project_info):
        self.stages = {'Segmentation':SegmentationStage(),
            'Parcellation':ParcellationStage(pipeline_mode = "Diffusion")}
        #import inspect
        #print inspect.getmro(self)
        # print isinstance(self, AnatomicalPipeline)
        # print isinstance(self, Pipeline)
        # print issubclass(AnatomicalPipeline,Pipeline)

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

    # def _custom_run_fired(self, ui_info):
    #     if self.custom_last_stage == '':
    #         ui_info.ui.context["object"].project_info.anat_custom_last_stage = self.ordered_stage_list[0]
    #     ui_info.ui.context["object"].project_info.anat_stage_names = self.ordered_stage_list
    #     cus_res = ui_info.ui.context["object"].project_info.configure_traits(view='anat_custom_map_view')
    #     if cus_res:
    #         self.define_custom_mapping(ui_info.ui.context["object"].project_info.anat_custom_last_stage)
    #
    # def _run_fired(self, ui_info):
    #     ui_info.ui.context["object"].project_info.config_error_msg = self.check_config()
    #     if ui_info.ui.context["object"].project_info.config_error_msg != '':
    #         ui_info.ui.context["object"].project_info.configure_traits(view='config_error_view')
    #     else:
    #         # save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)
    #         self.launch_process()
    #         self.launch_progress_window()
    #         # update_last_processed(ui_info.ui.context["object"].project_info, self.pipeline)

    def check_input(self, layout, gui=True):
        print '**** Check Inputs  ****'
        t1_available = False
        valid_inputs = False

        types = layout.get_types()

        subjid = self.subject.split("-")[1]

        if self.global_conf.subject_session == '':
            T1_file = os.path.join(self.subject_directory,'anat',self.subject+'_T1w.nii.gz')
            files = layout.get(subject=subjid,type='T1w',extensions='.nii.gz')
            if len(files) > 0:
                T1_file = files[0].filename
                print T1_file
            else:
                error(message="T1w image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session), title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
                return
        else:
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

    def create_pipeline_flow(self,deriv_subject_directory):
        subject_directory = self.subject_directory

        # Data import
        #datasource = pe.Node(interface=nio.DataGrabber(outfields = ['T1','T2','diffusion','bvecs','bvals']), name='datasource')
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['T1']), name='datasource')
        datasource.inputs.base_directory = deriv_subject_directory
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        #datasource.inputs.field_template = dict(T1='anat/T1.nii.gz', T2='anat/T2.nii.gz', diffusion='dwi/dwi.nii.gz', bvecs='dwi/dwi.bvec', bvals='dwi/dwi.bval')
        datasource.inputs.field_template = dict(T1='anat/'+self.subject+'_T1w.nii.gz')
        #datasource.inputs.field_template_args = dict(T1=[['subject']], T2=[['subject']], diffusion=[['subject', ['subject']]], bvecs=[['subject', ['subject']]], bvals=[['subject', ['subject']]])
        datasource.inputs.sort_filelist=False
        #datasource.inputs.subject = self.subject


        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="anatomical_sinker")
        sinker.inputs.base_directory = os.path.join(deriv_subject_directory)

        #Dataname substitutions in order to comply with BIDS derivatives specifications
        if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
            sinker.inputs.substitutions = [ ('T1.nii.gz', self.subject+'_T1w_head.nii.gz'),
                                            ('aseg.nii.gz', self.subject+'_T1w_aseg.nii.gz'),
                                            ('brain_mask.nii.gz', self.subject+'_T1w_brainmask.nii.gz'),
                                            ('brainmask_eroded.nii.gz', self.subject+'_T1w_brainmask_eroded.nii.gz'),
                                            ('brain.nii.gz', self.subject+'_T1w_brain.nii.gz'),
                                            ('fsmask_1mm.nii.gz',self.subject+'_T1w_class-WM.nii.gz'),
                                            ('gmmask.nii.gz',self.subject+'_T1w_class-GM.nii.gz'),
                                            ('fsmask_1mm_eroded.nii.gz',self.subject+'_T1w_class-WM_eroded.nii.gz'),
                                            ('csf_mask_eroded.nii.gz',self.subject+'_T1w_class-CSF_eroded.nii.gz'),
                                            #('gm_mask',self.subject+'_T1w_class-GM'),
                                            #('roivs', self.subject+'_T1w_parc'),#TODO substitute for list of files
                                            ('aparc+aseg.native.nii.gz',self.subject+'_T1w_aparc+aseg.nii.gz'),
                                            ('T1w_class-GM.nii.gz',self.subject+'_T1w_class-GM.nii.gz'),
                                            ('ROIv_HR_th_scale1.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
                                            ('ROIv_HR_th_scale2.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
                                            ('ROIv_HR_th_scale3.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
                                            ('ROIv_HR_th_scale4.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
                                            ('ROIv_HR_th_scale5.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
                                            ('ROIv_HR_th_scale1_final.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
                                            ('ROIv_HR_th_scale2_final.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
                                            ('ROIv_HR_th_scale3_final.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
                                            ('ROIv_HR_th_scale4_final.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
                                            ('ROIv_HR_th_scale5_final.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
                                            ('ROIv_HR_th_scale1.graphml',self.subject+'_T1w_parc_scale1.graphml'),
                                            ('ROIv_HR_th_scale2.graphml',self.subject+'_T1w_parc_scale2.graphml'),
                                            ('ROIv_HR_th_scale3.graphml',self.subject+'_T1w_parc_scale3.graphml'),
                                            ('ROIv_HR_th_scale4.graphml',self.subject+'_T1w_parc_scale4.graphml'),
                                            ('ROIv_HR_th_scale5.graphml',self.subject+'_T1w_parc_scale5.graphml'),
                                            ('ROIv_HR_th_scale1_FreeSurferColorLUT.txt',self.subject+'_T1w_parc_scale1_FreeSurferColorLUT.txt'),
                                            ('ROIv_HR_th_scale2_FreeSurferColorLUT.txt',self.subject+'_T1w_parc_scale2_FreeSurferColorLUT.txt'),
                                            ('ROIv_HR_th_scale3_FreeSurferColorLUT.txt',self.subject+'_T1w_parc_scale3_FreeSurferColorLUT.txt'),
                                            ('ROIv_HR_th_scale4_FreeSurferColorLUT.txt',self.subject+'_T1w_parc_scale4_FreeSurferColorLUT.txt'),
                                            ('ROIv_HR_th_scale5_FreeSurferColorLUT.txt',self.subject+'_T1w_parc_scale5_FreeSurferColorLUT.txt'),
                                            ('ROIv_HR_th_scale33.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
                                            ('ROIv_HR_th_scale60.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
                                            ('ROIv_HR_th_scale125.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
                                            ('ROIv_HR_th_scale250.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
                                            ('ROIv_HR_th_scale500.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
                                          ]
        else:
            sinker.inputs.substitutions = [ (self.subject+'_T1w.nii.gz', self.subject+'_T1w_head.nii.gz'),
                                            ('brain_mask.nii.gz', self.subject+'_T1w_brainmask.nii.gz'),
                                            ('brainmask_eroded.nii.gz', self.subject+'_T1w_brainmask_eroded.nii.gz'),
                                            ('brain.nii.gz', self.subject+'_T1w_brain.nii.gz'),
                                            ('fsmask_1mm.nii.gz',self.subject+'_T1w_class-WM.nii.gz'),
                                            ('fsmask_1mm_eroded.nii.gz',self.subject+'_T1w_class-WM_eroded.nii.gz'),
                                            ('csf_mask_eroded.nii.gz',self.subject+'_T1w_class-CSF_eroded.nii.gz'),
                                            #('gm_mask',self.subject+'_T1w_class-GM'),
                                            #('roivs', self.subject+'_T1w_parc'),#TODO substitute for list of files
                                            ('T1w_class-GM.nii.gz',self.subject+'_T1w_class-GM.nii.gz'),
                                            ('ROIv_HR_th_scale1.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
                                            ('ROIv_HR_th_scale2.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
                                            ('ROIv_HR_th_scale3.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
                                            ('ROIv_HR_th_scale4.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
                                            ('ROIv_HR_th_scale5.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
                                            ('ROIv_HR_th_scale33.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
                                            ('ROIv_HR_th_scale60.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
                                            ('ROIv_HR_th_scale125.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
                                            ('ROIv_HR_th_scale250.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
                                            ('ROIv_HR_th_scale500.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
                                          ]

        # Clear previous outputs
        self.clear_stages_outputs()

        # Create common_flow

        anat_flow = pe.Workflow(name='anatomical_pipeline', base_dir=os.path.join(deriv_subject_directory,'tmp'))
        anat_inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1"]),name="inputnode")
        anat_outputnode = pe.Node(interface=util.IdentityInterface(fields=["subjects_dir","subject_id","T1","aseg","aparc_aseg","brain","brain_mask","wm_mask_file", "gm_mask_file", "wm_eroded","brain_eroded","csf_eroded",
            "roi_volumes","parcellation_scheme","atlas_info","roi_colorLUTs", "roi_graphMLs"]),name="outputnode")
        anat_flow.add_nodes([anat_inputnode,anat_outputnode])

        anat_flow.connect([
                        (datasource,anat_inputnode,[("T1","T1")]),
                        ])


        if self.stages['Segmentation'].enabled:
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":

                if self.stages['Segmentation'].config.use_existing_freesurfer_data == False:
                    self.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.base_directory,"derivatives",'freesurfer')
                    print "Freesurfer_subjects_dir: %s" % self.stages['Segmentation'].config.freesurfer_subjects_dir
                    self.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(self.base_directory,"derivatives",'freesurfer',self.subject)
                    print "Freesurfer_subject_id: %s" % self.stages['Segmentation'].config.freesurfer_subject_id

            seg_flow = self.create_stage_flow("Segmentation")

            anat_flow.connect([(anat_inputnode,seg_flow, [('T1','inputnode.T1')])])

            if self.stages['Segmentation'].config.seg_tool == "Custom segmentation":
                anat_flow.connect([
                            (seg_flow,anat_outputnode,[("outputnode.brain_mask","brain_mask"),
                                                         ("outputnode.brain","brain")]),
                            (anat_inputnode,anat_outputnode,[("T1","T1")])
                            ])

            anat_flow.connect([
                        (seg_flow,anat_outputnode,[("outputnode.subjects_dir","subjects_dir"),
                                                     ("outputnode.subject_id","subject_id")])
                        ])

        if self.stages['Parcellation'].enabled:
            parc_flow = self.create_stage_flow("Parcellation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                anat_flow.connect([(seg_flow,parc_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                           ('outputnode.subject_id','inputnode.subject_id')]),
                                     ])
            else:
                anat_flow.connect([
                                     (seg_flow,parc_flow,[("outputnode.custom_wm_mask","inputnode.custom_wm_mask")])
                                     ])
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                anat_flow.connect([
                                    (parc_flow,anat_outputnode,[("outputnode.wm_mask_file","wm_mask_file"),
                                                               ("outputnode.parcellation_scheme","parcellation_scheme"),
                                                               ("outputnode.atlas_info","atlas_info"),
                                                               ("outputnode.roi_volumes","roi_volumes"),
                                                               ("outputnode.roi_colorLUTs","roi_colorLUTs"),
                                                               ("outputnode.roi_graphMLs","roi_graphMLs"),
                                                               ("outputnode.wm_eroded","wm_eroded"),
                                                               ("outputnode.gm_mask_file","gm_mask_file"),
                                                               ("outputnode.csf_eroded","csf_eroded"),
                                                               ("outputnode.brain_eroded","brain_eroded"),
                                                               ("outputnode.T1","T1"),
                                                               ("outputnode.aseg","aseg"),
                                                               ("outputnode.aparc_aseg","aparc_aseg"),
                                                               ("outputnode.brain_mask","brain_mask"),
                                                               ("outputnode.brain","brain"),
                                                               ])
                                ])
            else:
                anat_flow.connect([
                                    (parc_flow,anat_outputnode,[("outputnode.wm_mask_file","wm_mask_file"),
                                                               ("outputnode.parcellation_scheme","parcellation_scheme"),
                                                               ("outputnode.atlas_info","atlas_info"),
                                                               ("outputnode.roi_volumes","roi_volumes"),
                                                               ("outputnode.wm_eroded","wm_eroded"),
                                                               ("outputnode.gm_mask_file","gm_mask_file"),
                                                               ("outputnode.csf_eroded","csf_eroded"),
                                                               ("outputnode.brain_eroded","brain_eroded"),

                                                               ]),
                                ])

                if not self.stages['Segmentation'].enabled:
                    anat_flow.connect([
                                        (anat_inputnode,anat_outputnode,[("T1","T1")])
                                    ])

        anat_flow.connect([
                        (anat_outputnode,sinker,[("T1","anat.@T1")]),
                        (anat_outputnode,sinker,[("aseg","anat.@aseg")]),
                        (anat_outputnode,sinker,[("aparc_aseg","anat.@aparc_aseg")]),
                        (anat_outputnode,sinker,[("brain","anat.@brain")]),
                        (anat_outputnode,sinker,[("brain_mask","anat.@brain_mask")]),
                        (anat_outputnode,sinker,[("wm_mask_file","anat.@wm_mask")]),
                        (anat_outputnode,sinker,[("gm_mask_file","anat.@gm_mask")]),
                        (anat_outputnode,sinker,[("roi_volumes","anat.@roivs")]),
                        (anat_outputnode,sinker,[("roi_colorLUTs","anat.@luts")]),
                        (anat_outputnode,sinker,[("roi_graphMLs","anat.@graphmls")])
                        ])

        self.flow = anat_flow
        return anat_flow



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
        if os.path.isfile(os.path.join(deriv_subject_directory,"anat","pypeline.log")):
            os.unlink(os.path.join(deriv_subject_directory,"anat","pypeline.log"))
        config.update_config({'logging': {'log_directory': os.path.join(deriv_subject_directory,"anat"),
                                  'log_to_file': True},
                              'execution': {'remove_unnecessary_outputs': False,
                              'stop_on_first_crash': True,'stop_on_first_rerun': False,
                              'crashfile_format': "txt"}
                              })
        logging.update_logging(config)
        iflogger = logging.getLogger('nipype.interface')

        iflogger.info("**** Processing ****")
        anat_flow = self.create_pipeline_flow(deriv_subject_directory=deriv_subject_directory)
        anat_flow.write_graph(graph2use='colored', format='svg', simple_form=True)

        if(self.number_of_cores != 1):
            anat_flow.run(plugin='MultiProc', plugin_args={'n_procs' : self.number_of_cores})
        else:
            anat_flow.run()

        self.fill_stages_outputs()

        # Clean undesired folders/files
        # rm_file_list = ['rh.EC_average','lh.EC_average','fsaverage']
        # for file_to_rm in rm_file_list:
        #     if os.path.exists(os.path.join(self.base_directory,file_to_rm)):
        #         os.remove(os.path.join(self.base_directory,file_to_rm))

        # copy .ini and log file
        outdir = deriv_subject_directory
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        try:
            shutil.copy(self.config_file,outdir)
        except shutil.Error:
            print("Skipped copy of config file")

        #shutil.copy(os.path.join(self.base_directory,"derivatives","cmp",self.subject,'pypeline.log'),outdir)

        iflogger.info("**** Processing finished ****")

        return True,'Processing sucessful'


class Pipeline(HasTraits):
    # informations common to project_info
    base_directory = Directory
    root = Property
    subject = 'sub-01'
    last_date_processed = Str
    last_stage_processed = Str

    # num core settings
    number_of_cores = Enum(1,range(1,multiprocessing.cpu_count()+1))

    traits_view = View(
                        Group(
                            VGroup(
                                VGroup(
                                    HGroup(
                                        # '20',Item('base_directory',width=-0.3,height=-0.2, style='custom',show_label=False,resizable=True),
                                        '20',Item('base_directory',width=-0.3,style='readonly',show_label=False,resizable=True),
                                        ),
                                    # HGroup(
                                    #     '20',Item('root',editor=TreeEditor(editable=False, auto_open=1),show_label=False,resizable=True)
                                    #     ),
                                label='BIDS base directory',
                                ),
                                spring,
                                Group(
                                    Item('subject',style='readonly',show_label=False,resizable=True),
                                    label='Subject',
                                ),
                                spring,
                                Group(
                                    Item('pipeline_name',style='readonly',resizable=True),
                                    Item('last_date_processed',style='readonly',resizable=True),
                                    Item('last_stage_processed',style='readonly',resizable=True),
                                    label='Last processing'
                                ),
                                spring,
                                Group(
                                    Item('number_of_cores',resizable=True),
                                    label='Processing configuration'
                                ),
                                '700',
                                spring,
                            label='Data',
                            springy=True),
                            HGroup(
                                Include('pipeline_group'),
                                label='Diffusion pipeline',
                                springy=True
                            ),
                        orientation='horizontal', layout='tabbed', springy=True)
                    ,kind = 'livemodal')
     #-- Traits Default Value Methods -----------------------------------------

    # def _base_directory_default(self):
    #     return getcwd()

    #-- Property Implementations ---------------------------------------------

    @property_depends_on('base_directory')
    def _get_root(self):
        return File(path=self.base_directory)

    def __init__(self, project_info):
        self.base_directory = project_info.base_directory
        self.subject = project_info.subject
        self.last_date_processed = project_info.last_date_processed
        for stage in self.stages.keys():
            if len(project_info.subject_sessions) > 0:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject, project_info.subject_session, 'tmp',self.pipeline_name,self.stages[stage].name)
            else:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp',self.pipeline_name,self.stages[stage].name)

    def check_config(self):
        if self.stages['Segmentation'].config.seg_tool ==  'Custom segmentation':
            if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\nCustom segmentation selected but no WM mask provided.\nPlease provide an existing WM mask file in the Segmentation configuration window.\n')
            if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
                return('\n\tCustom segmentation selected but no atlas provided.\nPlease specify an existing atlas file in the Parcellation configuration window.\t\n')
            if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
                return('\n\tCustom segmentation selected but no graphml info provided.\nPlease specify an existing graphml file in the Parcellation configuration window.\t\n')
        # if self.stages['MRTrixConnectome'].config.output_types == []:
        #     return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        if self.stages['Connectome'].config.output_types == []:
            return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        return ''

    def create_stage_flow(self, stage_name):
        stage = self.stages[stage_name]
        flow = pe.Workflow(name=stage.name)
        inputnode = pe.Node(interface=util.IdentityInterface(fields=stage.inputs),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=stage.outputs),name="outputnode")
        flow.add_nodes([inputnode,outputnode])
        stage.create_workflow(flow,inputnode,outputnode)
        return flow

    def create_common_flow(self):
        common_flow = pe.Workflow(name='common_stages')
        common_inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1"]),name="inputnode")
        common_outputnode = pe.Node(interface=util.IdentityInterface(fields=["subjects_dir","subject_id","T1","brain","brain_mask","wm_mask_file", "wm_eroded","brain_eroded","csf_eroded",
            "roi_volumes","parcellation_scheme","atlas_info"]),name="outputnode")
        common_flow.add_nodes([common_inputnode,common_outputnode])

        if self.stages['Segmentation'].enabled:
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":

                if self.stages['Segmentation'].config.use_existing_freesurfer_data == False:
                    self.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.base_directory,"derivatives",'freesurfer')
                    print "Freesurfer_subjects_dir: %s" % self.stages['Segmentation'].config.freesurfer_subjects_dir
                    self.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(self.base_directory,"derivatives",'freesurfer',self.subject)
                    print "Freesurfer_subject_id: %s" % self.stages['Segmentation'].config.freesurfer_subject_id

            seg_flow = self.create_stage_flow("Segmentation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                common_flow.connect([(common_inputnode,seg_flow, [('T1','inputnode.T1')])])

            common_flow.connect([
                                 (seg_flow,common_outputnode,[("outputnode.subjects_dir","subjects_dir"),
                                                              ("outputnode.subject_id","subject_id")])
                                ])

        if self.stages['Parcellation'].enabled:
            parc_flow = self.create_stage_flow("Parcellation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                common_flow.connect([(seg_flow,parc_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                           ('outputnode.subject_id','inputnode.subject_id')]),
                                     ])
            else:
                common_flow.connect([
                                     (seg_flow,parc_flow,[("outputnode.custom_wm_mask","inputnode.custom_wm_mask")])
                                     ])
            common_flow.connect([
                                 (parc_flow,common_outputnode,[("outputnode.wm_mask_file","wm_mask_file"),
                                                               ("outputnode.parcellation_scheme","parcellation_scheme"),
                                                               ("outputnode.atlas_info","atlas_info"),
                                                               ("outputnode.roi_volumes","roi_volumes"),
                                                               ("outputnode.wm_eroded","wm_eroded"),
                                                               ("outputnode.csf_eroded","csf_eroded"),
                                                               ("outputnode.brain_eroded","brain_eroded"),
                                                               ("outputnode.T1","T1"),
                                                               ("outputnode.brain_mask","brain_mask"),
                                                               ("outputnode.brain","brain"),
                                                               ])
                                 ])

        return common_flow

    def fill_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.define_inspect_outputs()

    def clear_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.inspect_outputs_dict = {}
                stage.inspect_outputs = ['Outputs not available']
                # Remove result_*.pklz files to clear them from visualisation drop down list
                #stage_results = [os.path.join(dirpath, f)
                #                 for dirpath, dirnames, files in os.walk(stage.stage_dir)
                #                 for f in fnmatch.filter(files, 'result_*.pklz')]
                #for stage_res in stage_results:
                #    os.remove(stage_res)

    def launch_progress_window(self):
        pw = ProgressWindow()
        pt = ProgressThread()
        pt.pw = pw
        pt.stages = self.stages
        pt.stage_names = self.ordered_stage_list
        pt.start()
        pw.configure_traits()

    def launch_process(self):
        pt = ProcessThread()
        pt.pipeline = self
        pt.start()


def convert_rawdata(base_directory, input_dir, out_prefix):
    os.environ['UNPACK_MGH_DTI'] = '0'
    file_list = os.listdir(input_dir)

    # If RAWDATA folder contains one (and only one) gunzipped nifti file -> copy it
    first_file = os.path.join(input_dir, file_list[0])
    if len(file_list) == 1 and first_file.endswith('nii.gz'):
        copyfile(first_file, os.path.join(base_directory, 'NIFTI', out_prefix+'.nii.gz'), False, False, 'content') # intelligent copy looking at input's content
    else:
        mem = Memory(base_dir=os.path.join(base_directory,'NIPYPE'))
        mri_convert = mem.cache(fs.MRIConvert)
        #mri_convert = mem.cache(fs.MRIConvert)
        #res = mri_convert(in_file=first_file, out_file=os.path.join(base_directory, 'NIFTI', out_prefix + '.nii.gz'))
        #mr_convert = mem.cache(mrt.MRConvert)
        #res = mr_convert(in_dir=str(input_dir), out_filename=os.path.join(base_directory, 'NIFTI', out_prefix + '.nii.gz'))
        dcm2niix = mem.cache(Dcm2niix)
        res = dcm2niix(source_dir=str(input_dir), output_dir=os.path.join(base_directory, 'NIFTI'), out_filename=out_prefix)
        if len(res.outputs.get()) == 0:
            return False
        if len(res.outputs.get()) == 0:
            return False

    return True

class SwapAndReorientInputSpec(BaseInterfaceInputSpec):
    src_file = File(desc='Source file to be reoriented.',exists=True,mandatory=True)
    ref_file = File(desc='Reference file, which orientation will be applied to src_file.',exists=True,mandatory=True)
    out_file = File(genfile=True, desc='Name of the reoriented file.')

class SwapAndReorientOutputSpec(TraitedSpec):
    out_file = File(desc='Reoriented file.')

class SwapAndReorient(BaseInterface):
    input_spec = SwapAndReorientInputSpec
    output_spec = SwapAndReorientOutputSpec

    def _gen_outfilename(self):
        out_file = self.inputs.out_file
        path,base,ext = split_filename(self.inputs.src_file)
        if not isdefined(self.inputs.out_file):
            out_file = os.path.join(path,base+'_reo'+ext)

        json_file = os.path.join(path,base+'.json')
        if os.path.isfile(json_file):
            path,base,ext = split_filename(self.inputs.out_file)
            out_json_file = os.path.join(path,base+'.json')
            shutil.copy(json_file,out_json_file)

        return os.path.abspath(out_file)

    def _run_interface(self, runtime):
        out_file = self._gen_outfilename()
        src_file = self.inputs.src_file
        ref_file = self.inputs.ref_file

        # Collect orientation infos

        # "orientation" => 3 letter acronym defining orientation
        src_orient = fs.utils.ImageInfo(in_file=src_file).run().outputs.orientation
        ref_orient = fs.utils.ImageInfo(in_file=ref_file).run().outputs.orientation
        # "convention" => RADIOLOGICAL/NEUROLOGICAL
        src_conv = cmp_fsl.Orient(in_file=src_file, get_orient=True).run().outputs.orient
        ref_conv = cmp_fsl.Orient(in_file=ref_file, get_orient=True).run().outputs.orient

        if src_orient == ref_orient:
            # no reorientation needed
            print "No reorientation needed for anatomical image; Copy only!"
            copyfile(src_file,out_file,False, False, 'content')
            return runtime
        else:
            if src_conv != ref_conv:
                # if needed, match convention (radiological/neurological) to reference
                tmpsrc = os.path.join(os.path.dirname(src_file), 'tmp_' + os.path.basename(src_file))

                fsl.SwapDimensions(in_file=src_file, new_dims=('-x','y','z'), out_file=tmpsrc).run()

                cmp_fsl.Orient(in_file=tmpsrc, swap_orient=True).run()
            else:
                # If conventions match, just use the original source
                tmpsrc = src_file

        tmp2 = os.path.join(os.path.dirname(src_file), 'tmp.nii.gz')
        map_orient = {'L':'RL','R':'LR','A':'PA','P':'AP','S':'IS','I':'SI'}
        fsl.SwapDimensions(in_file=tmpsrc, new_dims=(map_orient[ref_orient[0]],map_orient[ref_orient[1]],map_orient[ref_orient[2]]), out_file=tmp2).run()

        shutil.move(tmp2, out_file)

        # Only remove the temporary file if the conventions did not match.  Otherwise,
        # we end up removing the output.
        if tmpsrc != src_file:
            os.remove(tmpsrc)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename()
        return outputs
