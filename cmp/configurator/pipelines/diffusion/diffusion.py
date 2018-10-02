# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Diffusion pipeline Class definition
"""

import os
import datetime

from pyface.qt.QtCore import *
from pyface.qt.QtGui import *

from traitsui.api import *
from traits.api import *

from traitsui.qt4.button_editor import ToolkitEditorFactory, CustomEditor

from pyface.api import ImageResource
import shutil

import nibabel as nib

from cmp.configurator.pipelines.common import *
from cmp.configurator.pipelines.anatomical.anatomical import AnatomicalPipeline

from cmp.configurator.stages.preprocessing.preprocessing import PreprocessingStage
from cmp.configurator.stages.diffusion.diffusion import DiffusionStage
from cmp.configurator.stages.registration.registration import RegistrationStage
from cmp.configurator.stages.connectome.connectome import ConnectomeStage, MRTrixConnectomeStage

from bids.grabbids import BIDSLayout

class Global_Configuration(HasTraits):
    process_type = Str('diffusion')
    diffusion_imaging_model = Str
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str
    modalities = []


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

class DiffusionPipeline(Pipeline):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("diffusion_pipeline")
    #input_folders = ['DSI','DTI','HARDI','T1','T2']
    input_folders = ['anat','dwi']
    process_type = Str
    diffusion_imaging_model = Str
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ['Preprocessing','Registration','Diffusion','Connectome']# ,'MRTrixConnectome']

    parcellation_scheme = Str
    atlas_info = Dict()

    global_conf = Global_Configuration()

    preprocessing = Button('Preprocessing')
    #preprocessing.setIcon(QIcon(QPixmap("preprocessing.png")))

    diffusion = Button('Diffusion')
    #diffusion.setIcon(QIcon(QPixmap("diffusion.png")))

    registration = Button('Registration')
    #registration.setIcon(QIcon(QPixmap("registration.png")))

    connectome = Button('Connectome')
    #connectome.setIcon(QIcon(QPixmap("connectome.png")))

    config_file = Str

    pipeline_group = VGroup(
                        HGroup(spring,UItem('preprocessing',style='custom',width=450,height=130,resizable=True,editor_args={'image':ImageResource('preprocessing'),'label':""}),spring,show_labels=False,label=""),
                        HGroup(spring,UItem('registration',style='custom',width=500,height=110,resizable=True,editor_args={'image':ImageResource('registration'),'label':""}),spring,show_labels=False,label=""),
                        HGroup(spring,UItem('diffusion',style='custom',width=450,height=240,resizable=True,editor_args={'image':ImageResource('diffusion'),'label':""}),spring,show_labels=False,label=""),
                        HGroup(spring,UItem('connectome',style='custom',width=450,height=130,resizable=True,editor_args={'image':ImageResource('connectome'),'label':""}),spring,show_labels=False,label=""),
                        spring,
                        springy=True
                    )

    def __init__(self,project_info):
        self.stages = {
            'Preprocessing':PreprocessingStage(),
            'Registration':RegistrationStage(pipeline_mode = "Diffusion"),
            'Diffusion':DiffusionStage(),
            'Connectome':ConnectomeStage()}
        Pipeline.__init__(self, project_info)

        self.diffusion_imaging_model = project_info.diffusion_imaging_model
        self.subject = project_info.subject

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = self.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory =  os.path.join(self.base_directory,self.subject,project_info.subject_session)
        else:
            self.global_conf.subject_session = ''
            self.subject_directory =  os.path.join(self.base_directory,self.subject)

        self.derivatives_directory =  os.path.join(self.base_directory,'derivatives')

        self.stages['Connectome'].config.subject = self.subject
        self.stages['Connectome'].config.on_trait_change(self.update_vizualization_layout,'circular_layout')
        self.stages['Connectome'].config.on_trait_change(self.update_vizualization_logscale,'log_visualization')
        self.stages['Diffusion'].config.on_trait_change(self.update_outputs_recon,'recon_processing_tool')
        self.stages['Diffusion'].config.on_trait_change(self.update_outputs_tracking,'tracking_processing_tool')
        # self.anat_flow = anat_flow

    def update_outputs_recon(self,new):
        self.stages['Diffusion'].define_inspect_outputs()

    def update_outputs_tracking(self,new):
        self.stages['Diffusion'].define_inspect_outputs()

    def update_vizualization_layout(self,new):
        self.stages['Connectome'].define_inspect_outputs()
        self.stages['Connectome'].config.subject = self.subject

    def update_vizualization_logscale(self,new):
        self.stages['Connectome'].define_inspect_outputs()
        self.stages['Connectome'].config.subject = self.subject

    def _subject_changed(self,new):
        self.stages['Connectome'].config.subject = new

    def _diffusion_imaging_model_changed(self,new):
        print "diffusion model changed"
        self.stages['Diffusion'].config.diffusion_imaging_model = new

    def check_config(self):
        if self.stages['Connectome'].config.output_types == []:
            return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        return ''

    def _preprocessing_fired(self, info):
        self.stages['Preprocessing'].configure_traits()

    def _diffusion_fired(self, info):
        self.stages['Diffusion'].configure_traits()

    def _registration_fired(self, info):
        self.stages['Registration'].configure_traits()

    def _connectome_fired(self, info):
        # self.stages['MRTrixConnectome'].configure_traits()
        self.stages['Connectome'].configure_traits()

    def _atlas_info_changed(self, new):
        print "Atlas info changed : "
        print new


    def check_input1(self, gui=True):
        print '**** Check Inputs  ****'
        diffusion_available = False
        bvecs_available = False
        bvals_available = False
        t1_available = False
        t2_available = False
        valid_inputs = False

        dwi_file = os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.nii.gz')
        bval_file = os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.bval')
        bvec_file = os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.bvec')
        T1_file = os.path.join(self.subject_directory,'anat',self.subject+'_T1w.nii.gz')
        T2_file = os.path.join(self.subject_directory,'anat',self.subject+'_T2w.nii.gz')

        print "Looking for...."
        print "dwi_file : %s" % dwi_file
        print "bvecs_file : %s" % bvec_file
        print "bvals_file : %s" % bval_file
        print "T1_file : %s" % T1_file
        print "T2_file : %s" % T2_file

        try:
            layout = BIDSLayout(self.base_directory)
            print "Valid BIDS dataset with %s subjects" % len(layout.get_subjects())
            for subj in layout.get_subjects():
                self.global_conf.subjects.append('sub-'+str(subj))
            # self.global_conf.subjects = ['sub-'+str(subj) for subj in layout.get_subjects()]
            self.global_conf.modalities = [str(mod) for mod in layout.get_modalities()]
            # mods = layout.get_modalities()
            types = layout.get_types()
            # print "Available modalities :"
            # for mod in mods:
            #     print "-%s" % mod

            for typ in types:
                if typ == 'dwi' and os.path.isfile(dwi_file):
                    print "%s available" % typ
                    diffusion_available = True

                if typ == 'T1w' and os.path.isfile(T1_file):
                    print "%s available" % typ
                    t1_available = True

                if typ == 'T2w' and os.path.isfile(T2_file):
                    print "%s available" % typ
                    t2_available = True
        except:
            error(message="Invalid BIDS dataset. Please see documentation for more details.", title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
            return


        if os.path.isfile(bval_file): bvals_available = True

        if os.path.isfile(bvec_file): bvecs_available = True

        mem = Memory(base_dir=os.path.join(self.derivatives_directory,'cmp',self.subject,'tmp','nipype'))
        swap_and_reorient = mem.cache(SwapAndReorient)

        if diffusion_available:
            if bvals_available and bvecs_available:
                self.stages['Diffusion'].config.diffusion_imaging_model_choices = self.diffusion_imaging_model

                #Copy diffusion data to derivatives / cmp  / subject / dwi
                out_dwi_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'dwi',self.subject+'_dwi.nii.gz')
                out_bval_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'dwi',self.subject+'_dwi.bval')
                out_bvec_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'dwi',self.subject+'_dwi.bvec')

                shutil.copy(src=dwi_file,dst=out_dwi_file)
                shutil.copy(src=bvec_file,dst=out_bvec_file)
                shutil.copy(src=bval_file,dst=out_bval_file)

                if t2_available:
                    print "Swap and reorient T2"
                    swap_and_reorient(src_file=os.path.join(self.subject_directory,'anat',self.subject+'_T2w.nii.gz'),
                                      ref_file=os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.nii.gz'),
                                      out_file=os.path.join(self.derivatives_directory,'cmp',self.subject,'anat',self.subject+'_T2w.nii.gz'))
                if t1_available:
                    swap_and_reorient(src_file=os.path.join(self.subject_directory,'anat',self.subject+'_T1w.nii.gz'),
                                      ref_file=os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.nii.gz'),
                                      out_file=os.path.join(self.derivatives_directory,'cmp',self.subject,'anat',self.subject+'_T1w.nii.gz'))
                    valid_inputs = True
                    input_message = 'Inputs check finished successfully.\nDiffusion and morphological data available.'
                else:
                    input_message = 'Error during inputs check.\nMorphological data (T1) not available.'
            else:
                input_message = 'Error during inputs check.\nDiffusion bvec or bval files not available.'
        elif t1_available:
            input_message = 'Error during inputs check. \nDiffusion data not available (DSI/DTI/HARDI).'
        else:
            input_message = 'Error during inputs check. No diffusion or morphological data available in folder '+os.path.join(self.base_directory,'RAWDATA')+'!'

        #diffusion_imaging_model = diffusion_imaging_model[0]

        if gui:
            #input_notification = Check_Input_Notification(message=input_message, diffusion_imaging_model_options=diffusion_imaging_model,diffusion_imaging_model=diffusion_imaging_model)
            #input_notification.configure_traits()
            print input_message
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model
            diffusion_file = os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.nii.gz')
            n_vol = nib.load(diffusion_file).shape[3]
            if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
                self.stages['Preprocessing'].config.end_vol = n_vol-1
            self.stages['Preprocessing'].config.max_vol = n_vol-1
            self.stages['Registration'].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages['Diffusion'].config.diffusion_imaging_model = self.diffusion_imaging_model
        else:
            print input_message
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model
            diffusion_file = os.path.join(self.subject_directory,'dwi',self.subject+'_dwi.nii.gz')
            n_vol = nib.load(diffusion_file).shape[3]
            if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
                self.stages['Preprocessing'].config.end_vol = n_vol-1
            self.stages['Preprocessing'].config.max_vol = n_vol-1
            self.stages['Registration'].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages['Diffusion'].config.diffusion_imaging_model = self.diffusion_imaging_model

        if t2_available:
            self.stages['Registration'].config.registration_mode_trait = ['Linear + Non-linear (FSL)']#,'BBregister (FS)','Nonlinear (FSL)']

        if(t1_available and diffusion_available):
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

    def check_input(self, layout, gui=True):
        print '**** Check Inputs  ****'
        diffusion_available = False
        bvecs_available = False
        bvals_available = False
        valid_inputs = False

        if self.global_conf.subject_session == '':
            subject = self.subject
        else:
            subject = "_".join((self.subject,self.global_conf.subject_session))

        dwi_file = os.path.join(self.subject_directory,'dwi',subject+'_dwi.nii.gz')
        bval_file = os.path.join(self.subject_directory,'dwi',subject+'_dwi.bval')
        bvec_file = os.path.join(self.subject_directory,'dwi',subject+'_dwi.bvec')

        print "Looking for...."
        print "dwi_file : %s" % dwi_file
        print "bvecs_file : %s" % bvec_file
        print "bvals_file : %s" % bval_file

        try:
            layout = BIDSLayout(self.base_directory)
            print "Valid BIDS dataset with %s subjects" % len(layout.get_subjects())
            for subj in layout.get_subjects():
                self.global_conf.subjects.append('sub-'+str(subj))
            # self.global_conf.subjects = ['sub-'+str(subj) for subj in layout.get_subjects()]
            self.global_conf.modalities = [str(mod) for mod in layout.get_modalities()]
            # mods = layout.get_modalities()
            types = layout.get_types()
            # print "Available modalities :"
            # for mod in mods:
            #     print "-%s" % mod

            for typ in types:
                if typ == 'dwi' and os.path.isfile(dwi_file):
                    print "%s available" % typ
                    diffusion_available = True

        except:
            error(message="Invalid BIDS dataset. Please see documentation for more details.", title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)
            return


        if os.path.isfile(bval_file): bvals_available = True

        if os.path.isfile(bvec_file): bvecs_available = True

        if diffusion_available:
            if bvals_available and bvecs_available:
                self.stages['Diffusion'].config.diffusion_imaging_model_choices = self.diffusion_imaging_model

                #Copy diffusion data to derivatives / cmp  / subject / dwi
                if self.global_conf.subject_session == '':
                    out_dwi_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'dwi',subject+'_dwi.nii.gz')
                    out_bval_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'dwi',subject+'_dwi.bval')
                    out_bvec_file = os.path.join(self.derivatives_directory,'cmp',self.subject,'dwi',subject+'_dwi.bvec')
                else:
                    out_dwi_file = os.path.join(self.derivatives_directory,'cmp',self.subject,self.global_conf.subject_session,'dwi',subject+'_dwi.nii.gz')
                    out_bval_file = os.path.join(self.derivatives_directory,'cmp',self.subject,self.global_conf.subject_session,'dwi',subject+'_dwi.bval')
                    out_bvec_file = os.path.join(self.derivatives_directory,'cmp',self.subject,self.global_conf.subject_session,'dwi',subject+'_dwi.bvec')

                if not os.path.isfile(out_dwi_file):
                    shutil.copy(src=dwi_file,dst=out_dwi_file)
                if not os.path.isfile(out_bvec_file):
                    shutil.copy(src=bvec_file,dst=out_bvec_file)
                if not os.path.isfile(out_bval_file):
                    shutil.copy(src=bval_file,dst=out_bval_file)

                valid_inputs = True
                input_message = 'Inputs check finished successfully.\nDiffusion and morphological data available.'
            else:
                input_message = 'Error during inputs check.\nDiffusion bvec or bval files not available.'
        else:
            if self.global_conf.subject_session == '':
                input_message = 'Error during inputs check. No diffusion data available in folder '+os.path.join(self.base_directory,self.subject,'dwi')+'!'
            else:
                input_message = 'Error during inputs check. No diffusion data available in folder '+os.path.join(self.base_directory,self.subject,self.global_conf.subject_session,'dwi')+'!'
        #diffusion_imaging_model = diffusion_imaging_model[0]

        if gui:
            #input_notification = Check_Input_Notification(message=input_message, diffusion_imaging_model_options=diffusion_imaging_model,diffusion_imaging_model=diffusion_imaging_model)
            #input_notification.configure_traits()
            print input_message
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model

            if diffusion_available:
                n_vol = nib.load(dwi_file).shape[3]
                if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
                    self.stages['Preprocessing'].config.end_vol = n_vol-1
                self.stages['Preprocessing'].config.max_vol = n_vol-1

            self.stages['Registration'].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages['Diffusion'].config.diffusion_imaging_model = self.diffusion_imaging_model
        else:
            print input_message
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model

            if diffusion_available:
                n_vol = nib.load(dwi_file).shape[3]
                if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
                    self.stages['Preprocessing'].config.end_vol = n_vol-1
                self.stages['Preprocessing'].config.max_vol = n_vol-1

            self.stages['Registration'].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages['Diffusion'].config.diffusion_imaging_model = self.diffusion_imaging_model


        if(diffusion_available):
            valid_inputs = True
        else:
            print "Missing required inputs."
            error(message="Missing diffusion inputs. Please see documentation for more details.", title="Error",buttons = [ 'OK', 'Cancel' ], parent = None)

        for stage in self.stages.values():
            if stage.enabled:
                print stage.name
                print stage.stage_dir

        self.fill_stages_outputs()

        return valid_inputs
