# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Diffusion pipeline Class definition
"""

import os
import shutil
import datetime
from cmp.pipelines.common import *


from traits.api import *

import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Merge
from nipype import config, logging
from nipype.caching import Memory
from pyface.api import ImageResource

import nibabel as nib

from cmp.pipelines.common import *
from cmp.pipelines.anatomical.anatomical import AnatomicalPipeline

from cmp.stages.preprocessing.preprocessing import PreprocessingStage
from cmp.stages.diffusion.diffusion import DiffusionStage
from cmp.stages.registration.registration import RegistrationStage
from cmp.stages.connectome.connectome import ConnectomeStage

from bids.grabbids import BIDSLayout

class Global_Configuration(HasTraits):
    process_type = Str('diffusion')
    diffusion_imaging_model = Str
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str
    modalities = List(trait=Str)
    dmri_bids_acq = Str


class Check_Input_Notification(HasTraits):
    message = Str
    diffusion_imaging_model_options = List(['DSI','DTI','HARDI'])
    diffusion_imaging_model = Str
    diffusion_imaging_model_message = Str('\nMultiple diffusion inputs available. Please select desired diffusion modality.')

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

    config_file = Str

    # anat_flow = Instance(pe.Workflow)

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

        self.derivatives_directory =  os.path.abspath(project_info.output_directory)
        self.output_directory =  os.path.abspath(project_info.output_directory)

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
        # if self.stages['MRTrixConnectome'].config.output_types == []:
        #     return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        if self.stages['Connectome'].config.output_types == []:
            return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        return ''

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

    def _atlas_info_changed(self, new):
        print "Atlas info changed : "
        print new

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

        subjid = self.subject.split("-")[1]

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

            if self.global_conf.subject_session == '':

                files = layout.get(subject=subjid,type='dwi',extensions='.nii.gz')
                if len(files) > 0:
                    if self.global_conf.dmri_bids_acq != '':
                        for file in files:
                            if self.global_conf.dmri_bids_acq in file:
                                dwi_file = file
                                break
                    else:#TODO: Better parsing of multiple runs
                        dwi_file = files[0].filename
                        print(dwi_file)
                else:
                    print("ERROR: Diffusion image not found for subject %s."%(subjid))
                    return

                files = layout.get(subject=subjid,type='dwi',extensions='.bval')
                if len(files) > 0:
                    if self.global_conf.dmri_bids_acq != '':
                        for file in files:
                            if self.global_conf.dmri_bids_acq in file:
                                bval_file = file
                                break
                    else:#TODO: Better parsing of multiple runs
                        bval_file = files[0].filename
                        print(bval_file)
                else:
                    print("Diffusion bval image not found for subject %s."%(subjid))
                    return

                files = layout.get(subject=subjid,type='dwi',extensions='.bvec')
                if len(files) > 0:
                    if self.global_conf.dmri_bids_acq != '':
                        for file in files:
                            if self.global_conf.dmri_bids_acq in file:
                                bvec_file = file
                                break
                    else:#TODO: Better parsing of multiple runs
                        bvec_file = files[0].filename
                        print(bvec_file)
                else:
                    print("Diffusion bvec image not found for subject %s."%(subjid))
                    return
            else:
                sessid = self.global_conf.subject_session.split("-")[1]

                files = layout.get(subject=subjid,type='dwi',extensions='.nii.gz',session=sessid)
                if len(files) > 0:
                    if self.global_conf.dmri_bids_acq != '':
                        for file in files:
                            if self.global_conf.dmri_bids_acq in file:
                                dwi_file = file
                                break
                    else:#TODO: Better parsing of multiple runs
                        dwi_file = files[0].filename
                        print(dwi_file)
                else:
                    print("Diffusion image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session))
                    return

                files = layout.get(subject=subjid,type='dwi',extensions='.bval',session=sessid)
                if len(files) > 0:
                    if self.global_conf.dmri_bids_acq != '':
                        for file in files:
                            if self.global_conf.dmri_bids_acq in file:
                                bval_file = file
                                break
                    else:#TODO: Better parsing of multiple runs
                        bval_file = files[0].filename
                        print bval_file
                else:
                    print("Diffusion bval image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session))
                    return

                files = layout.get(subject=subjid,type='dwi',extensions='.bvec',session=sessid)
                if len(files) > 0:
                    if self.global_conf.dmri_bids_acq != '':
                        for file in files:
                            if self.global_conf.dmri_bids_acq in file:
                                bvec_file = file
                                break
                    else:#TODO: Better parsing of multiple runs
                        bvec_file = files[0].filename
                        print bvec_file
                else:
                    print("Diffusion bvec image not found for subject %s, session %s."%(subjid,self.global_conf.subject_session))
                    return

            print("Looking for....")
            print("dwi_file : %s" % dwi_file)
            print("bvecs_file : %s" % bvec_file)
            print("bvals_file : %s" % bval_file)

            for typ in types:
                if typ == 'dwi' and os.path.isfile(dwi_file):
                    print("%s available" % typ)
                    diffusion_available = True

        except:
            print("Invalid BIDS dataset. Please see documentation for more details.")
            return


        if os.path.isfile(bval_file): bvals_available = True

        if os.path.isfile(bvec_file): bvecs_available = True

        if diffusion_available:
            if bvals_available and bvecs_available:
                self.stages['Diffusion'].config.diffusion_imaging_model_choices = self.diffusion_imaging_model

                #Copy diffusion data to derivatives / cmp  / subject / dwi
                if self.global_conf.subject_session == '':
                    out_dwi_file = os.path.join(self.output_directory,'cmp',self.subject,'dwi',subject+'_dwi.nii.gz')
                    out_bval_file = os.path.join(self.output_directory,'cmp',self.subject,'dwi',subject+'_dwi.bval')
                    out_bvec_file = os.path.join(self.output_directory,'cmp',self.subject,'dwi',subject+'_dwi.bvec')
                else:
                    out_dwi_file = os.path.join(self.output_directory,'cmp',self.subject,self.global_conf.subject_session,'dwi',subject+'_dwi.nii.gz')
                    out_bval_file = os.path.join(self.output_directory,'cmp',self.subject,self.global_conf.subject_session,'dwi',subject+'_dwi.bval')
                    out_bvec_file = os.path.join(self.output_directory,'cmp',self.subject,self.global_conf.subject_session,'dwi',subject+'_dwi.bvec')

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

            # if diffusion_available:
            #     n_vol = nib.load(dwi_file).shape[3]
            #     if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
            #         self.stages['Preprocessing'].config.end_vol = n_vol-1
            #     self.stages['Preprocessing'].config.max_vol = n_vol-1

            self.stages['Registration'].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages['Diffusion'].config.diffusion_imaging_model = self.diffusion_imaging_model
        else:
            print input_message
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model

            # if diffusion_available:
            #     n_vol = nib.load(dwi_file).shape[3]
            #     if self.stages['Preprocessing'].config.end_vol == 0 or self.stages['Preprocessing'].config.end_vol == self.stages['Preprocessing'].config.max_vol or self.stages['Preprocessing'].config.end_vol >= n_vol-1:
            #         self.stages['Preprocessing'].config.end_vol = n_vol-1
            #     self.stages['Preprocessing'].config.max_vol = n_vol-1

            self.stages['Registration'].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages['Diffusion'].config.diffusion_imaging_model = self.diffusion_imaging_model


        if(diffusion_available):
            valid_inputs = True
        else:
            print("Missing required inputs.Please see documentation for more details.")

        for stage in self.stages.values():
            if stage.enabled:
                print stage.name
                print stage.stage_dir

        self.fill_stages_outputs()

        return valid_inputs

    def create_pipeline_flow(self,cmp_deriv_subject_directory,nipype_deriv_subject_directory):

        subject_directory = self.subject_directory

        acquisition_model = self.stages['Diffusion'].config.diffusion_imaging_model
        recon_tool = self.stages['Diffusion'].config.recon_processing_tool

        if acquisition_model == 'DSI':
            recon_model = 'SHORE'
        else:
            if recon_tool == 'Dipy':
                if self.stages['Diffusion'].config.dipy_recon_config.local_model:
                    recon_model = 'CSD'
                else:
                    recon_model = 'DTI'
                    recon_model_desc = 'WLS'
            elif recon_tool == 'MRtrix':
                if self.stages['Diffusion'].config.mrtrix_recon_config.local_model:
                    recon_model = 'CSD'
                else:
                    recon_model = 'DTI'
                    recon_model_desc = 'WLS'

        tracking_model = self.stages['Diffusion'].config.diffusion_model

        if tracking_model == 'Deterministic':
            tracking_model = 'DET'
        elif tracking_model == 'Probabilistic':
            tracking_model = 'PROB'

        # Data import
        #datasource = pe.Node(interface=nio.DataGrabber(outfields = ['T1','T2','diffusion','bvecs','bvals']), name='datasource')
        datasource = pe.Node(interface=nio.DataGrabber(outfields = ['diffusion','bvecs','bvals','T1','aparc_aseg','aseg','brain','brain_mask','wm_mask_file','wm_eroded','brain_eroded','csf_eroded','roi_volume_s1','roi_volume_s2','roi_volume_s3','roi_volume_s4','roi_volume_s5','roi_graphml_s1','roi_graphml_s2','roi_graphml_s3','roi_graphml_s4','roi_graphml_s5']), name='datasource')
        datasource.inputs.base_directory = cmp_deriv_subject_directory
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        #datasource.inputs.field_template = dict(T1='anat/T1.nii.gz', T2='anat/T2.nii.gz', diffusion='dwi/dwi.nii.gz', bvecs='dwi/dwi.bvec', bvals='dwi/dwi.bval')
        datasource.inputs.field_template = dict(diffusion='dwi/'+self.subject+'_dwi.nii.gz', bvecs='dwi/'+self.subject+'_dwi.bvec', bvals='dwi/'+self.subject+'_dwi.bval',
                                                T1='anat/'+self.subject+'_desc-head_T1w.nii.gz',aseg='anat/'+self.subject+'_desc-aseg_dseg.nii.gz',
                                                aparc_aseg='anat/'+self.subject+'_desc-aparcaseg_dseg.nii.gz',brain='anat/'+self.subject+'_desc-brain_T1w.nii.gz',
                                                brain_mask='anat/'+self.subject+'_desc-brain_mask.nii.gz',
                                                wm_mask_file='anat/'+self.subject+'_label-WM_dseg.nii.gz',wm_eroded='anat/'+self.subject+'_label-WM_dseg.nii.gz',
                                                brain_eroded='anat/'+self.subject+'_desc-brain_mask.nii.gz',csf_eroded='anat/'+self.subject+'_label-CSF_dseg.nii.gz',
                                                roi_volume_s1='anat/'+self.subject+'_label-L2018_desc-scale1_atlas.nii.gz',roi_volume_s2='anat/'+self.subject+'_label-L2018_desc-scale2_atlas.nii.gz',
                                                roi_volume_s3='anat/'+self.subject+'_label-L2018_desc-scale3_atlas.nii.gz',
                                                roi_volume_s4='anat/'+self.subject+'_label-L2018_desc-scale4_atlas.nii.gz',roi_volume_s5='anat/'+self.subject+'_label-L2018_desc-scale5_atlas.nii.gz',
                                                roi_graphml_s1='anat/'+self.subject+'_label-L2018_desc-scale1_atlas.graphml',roi_graphml_s2='anat/'+self.subject+'_label-L2018_desc-scale2_atlas.graphml',
                                                roi_graphml_s3='anat/'+self.subject+'_label-L2018_desc-scale3_atlas.graphml',
                                                roi_graphml_s4='anat/'+self.subject+'_label-L2018_desc-scale4_atlas.graphml',roi_graphml_s5='anat/'+self.subject+'_label-L2018_desc-scale5_atlas.graphml')
        # datasource.inputs.field_template_args = dict(diffusion=[], bvecs=[], bvals=[],T1=[],brain=[],brain_mask=[],
        #                                         wm_mask_file=[],wm_eroded=[],brain_eroded=[],csf_eroded=[],
        #                                         roi_volumes=[['%s'%self.subject],[1,2,3,4,5]])
        #datasource.inputs.field_template_args = dict(T1=[['subject']], T2=[['subject']], diffusion=[['subject', ['subject']]], bvecs=[['subject', ['subject']]], bvals=[['subject', ['subject']]])
        datasource.inputs.sort_filelist=True

        #datasource.inputs.subject = self.subject

        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="diffusion_sinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)

        #Dataname substitutions in order to comply with BIDS derivatives specifications
        if self.stages['Diffusion'].config.tracking_processing_tool == 'Custom':
            sinker.inputs.substitutions = [ #('T1', self.subject+'_T1w_head'),
                                            ('brain_mask.nii.gz', self.subject+'_desc-brain_mask.nii.gz'),
                                            ('brain.nii.gz', self.subject+'_desc-brain_T1w.nii.gz'),
                                            #('wm_mask',self.subject+'_T1w_class-WM'),('brain_mask_resampled_warped',self.subject+'_space-DWI_desc-brain_mask'),
                                            #('gm_mask',self.subject+'_T1w_class-GM'),
                                            #('roivs', self.subject+'_T1w_parc'),#TODO substitute for list of files
                                            # ('ROIv_HR_th_scale33.nii.gz',self.subject+'_T1w_parc_scale33.nii.gz'),
                                            # ('ROIv_HR_th_scale60.nii.gz',self.subject+'_T1w_parc_scale60.nii.gz'),
                                            # ('ROIv_HR_th_scale125.nii.gz',self.subject+'_T1w_parc_scale125.nii.gz'),
                                            # ('ROIv_HR_th_scale250.nii.gz',self.subject+'_T1w_parc_scale250.nii.gz'),
                                            # ('ROIv_HR_th_scale500.nii.gz',self.subject+'_T1w_parc_scale500.nii.gz'),

                                            #('*/_ROIs_resample*/fast__pve_0_out.nii.gz',self.subject+'_dwi_connectome'),

                                            ('T1_warped', self.subject+'_space-DWI_desc-head_T1w'),
                                            ('anat_resampled_warped', self.subject+'_space-DWI_desc-head_T1w'),
                                            ('brain_warped',self.subject+'_space-DWI_desc-brain_T1w'),
                                            ('anat_masked_resampled_warped', self.subject+'_space-DWI_desc-brain_T1w'),
                                            ('brain_mask_registered_temp_crop',self.subject+'_space-DWI_desc-brain_mask'),
                                            ('brain_mask_resampled_warped.nii.gz',self.subject+'_space-DWI_desc-brain_mask'),
                                            ('wm_mask_warped',self.subject+'_space-DWI_label-WM_dseg'),
                                            ('wm_mask_resampled_warped',self.subject+'_space-DWI_label-WM_dseg'),
                                            ('ROIv_HR_th_scale1_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale1_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale2_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale2_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale3_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale3_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale4_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale4_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale5_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale5_atlas.nii.gz'),
                                            ('fast__pve_0_out_warped.nii.gz',self.subject+'_space-DWI_label-CSF_probseg.nii.gz'),
                                            ('fast__pve_1_out_warped.nii.gz',self.subject+'_space-DWI_label-GM_probseg.nii.gz'),
                                            ('fast__pve_2_out_warped.nii.gz',self.subject+'_space-DWI_label-WM_probseg.nii.gz'),
                                            ('pve_0_out_warped.nii.gz',self.subject+'_space-DWI_label-CSF_probseg.nii.gz'),
                                            ('pve_1_out_warped.nii.gz',self.subject+'_space-DWI_label-GM_probseg.nii.gz'),
                                            ('pve_2_out_warped.nii.gz',self.subject+'_space-DWI_label-WM_probseg.nii.gz'),
                                            ('act_5tt_resampled_warped.nii.gz',self.subject+'_space-DWI_label-5TT_probseg.nii.gz'),
                                            ('gmwmi_resampled_warped.nii.gz',self.subject+'_space-DWI_label-GMWMI_probseg.nii.gz'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale1',self.subject+'_label-L2018_desc-scale1_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale2',self.subject+'_label-L2018_desc-scale2_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale3',self.subject+'_label-L2018_desc-scale3_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale4',self.subject+'_label-L2018_desc-scale4_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale5',self.subject+'_label-L2018_desc-scale5_connectome'),
                                            ('connectome_scale1',self.subject+'_label-L2018_desc-scale1_connectome'),
                                            ('connectome_scale2',self.subject+'_label-L2018_desc-scale2_connectome'),
                                            ('connectome_scale3',self.subject+'_label-L2018_desc-scale3_connectome'),
                                            ('connectome_scale4',self.subject+'_label-L2018_desc-scale4_connectome'),
                                            ('connectome_scale5',self.subject+'_label-L2018_desc-scale5_connectome'),
                                            ('dwi.nii.gz',self.subject+'_dwi.nii.gz'),
                                            ('dwi.bval',self.subject+'_dwi.bval'),
                                            # ('dwi.bvec',self.subject+'_dwi.bvec'),
                                            #('diffusion_resampled_CSD_det_tracked',self.subject+'_desc-DET_tractogram'),
                                            #('diffusion_resampled_CSD_prob_tracked',self.subject+'_desc-PROB_tractogram'),
                                            ('eddy_corrected.nii.gz.eddy_rotated_bvecs',self.subject+'_desc-eddyrotated.bvec'),
                                            ('eddy_corrected.nii.gz',self.subject+'_desc-eddycorrected_dwi.nii.gz'),
                                            ('dwi_brain_mask_resampled.nii.gz',self.subject+'_desc-brain_mask.nii.gz'),
                                            ('ADC',self.subject+'_model-DTI_MD'),
                                            ('FA',self.subject+'_model-DTI_FA'),
                                            ('diffusion_preproc_resampled_fa',self.subject+'_model-DTI_FA'),
                                            ('shore_gfa.nii.gz','{}_model-SHORE_GFA.nii.gz'.format(self.subject)),
                                            ('shore_msd.nii.gz','{}_model-SHORE_MSD.nii.gz'.format(self.subject)),
                                            ('shore_rtop_signal.nii.gz','{}_model-SHORE_RTOP.nii.gz'.format(self.subject)),
                                            ('shore_fodf.nii.gz','{}_model-SHORE_FOD.nii.gz'.format(self.subject)),
                                            ('diffusion_resampled_CSD.mif',self.subject+'_model-CSD_diffmodel.mif'),
                                            ('diffusion_shm_coeff.nii.gz','{}_model-CSD_SHM.nii.gz'.format(self.subject)),#Dipy
                                            ('shm_coeff.nii.gz','{}_model-CSD_SHM.nii.gz'.format(self.subject)),#MRtrix
                                            ('dwi_tensor.nii.gz','{}_desc-WLS_model-DTI_diffmodel.nii.gz'.format(self.subject)),#MRtrix
                                            ('grad.txt',self.subject+'_desc-grad_dwi.txt'),
                                            ('target_epicorrected',self.subject+'_desc-preproc_dwi'),
                                            ('diffusion_preproc_resampled.nii.gz',self.subject+'_desc-preproc_dwi.nii.gz'),
                                            #('endpoints',self.subject+'_tract_endpoints'),
                                            # ('filtered_fiberslabel',self.subject+'_desc-fiberslabel_filt'),
                                            #('final_fiberlabels_'+self.subject+'_T1w_parc',self.subject+'_desc-filtered_fiberlabels'),
                                            #('final_fiberslength_'+self.subject+'_T1w_parc',self.subject+'_desc-filtered_fiberslength'),
                                            ('streamline_final','{}_model-{}_desc-{}_tractogram'.format(self.subject,recon_model,tracking_model)),
                                            ##('_trackvis0/converted',self.subject+'_dwi_tract'),#MRtrix tracts
                                            ##('diffusion_preproc_resampled_tracked',self.subject+'_dwi_tract') #Dipy tracts
                                            ##TODO: Add fODF CSD / SHORE model /
                                          ]

        else:
            sinker.inputs.substitutions = [ #('T1', self.subject+'_T1w_head'),
                                            ('brain_mask.nii.gz', self.subject+'_desc-brain_mask.nii.gz'),
                                            ('brain.nii.gz', self.subject+'_desc-brain_T1w.nii.gz'),
                                            #('wm_mask',self.subject+'_T1w_class-WM'),
                                            #('gm_mask',self.subject+'_T1w_class-GM'),
                                            #('roivs', self.subject+'_T1w_parc'),#TODO substitute for list of files
                                            # ('ROIv_HR_th_scale33.nii.gz',self.subject+'_T1w_parc_scale33.nii.gz'),
                                            # ('ROIv_HR_th_scale60.nii.gz',self.subject+'_T1w_parc_scale60.nii.gz'),
                                            # ('ROIv_HR_th_scale125.nii.gz',self.subject+'_T1w_parc_scale125.nii.gz'),
                                            # ('ROIv_HR_th_scale250.nii.gz',self.subject+'_T1w_parc_scale250.nii.gz'),
                                            # ('ROIv_HR_th_scale500.nii.gz',self.subject+'_T1w_parc_scale500.nii.gz'),

                                            #('*/_ROIs_resample*/fast__pve_0_out.nii.gz',self.subject+'_dwi_connectome'),

                                            ('T1_warped', self.subject+'_space-DWI_desc-head_T1w'),
                                            ('anat_resampled_warped', self.subject+'_space-DWI_desc-head_T1w'),
                                            ('brain_warped',self.subject+'_space-DWI_desc-brain_T1w'),
                                            ('anat_masked_resampled_warped', self.subject+'_space-DWI_desc-brain_T1w'),
                                            ('brain_mask_resampled_warped',self.subject+'_space-DWI_desc-brain_mask'),
                                            ('brain_mask_registered_temp_crop',self.subject+'_space-DWI_desc-brain_mask'),
                                            ('wm_mask_warped',self.subject+'_space-DWI_label-WM_dseg'),
                                            ('wm_mask_resampled_warped',self.subject+'_space-DWI_label-WM_dseg'),
                                            ('ROIv_HR_th_scale1_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale1_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale2_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale2_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale3_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale3_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale4_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale4_atlas.nii.gz'),
                                            ('ROIv_HR_th_scale5_out_warped.nii.gz',self.subject+'_space-DWI_label-L2018_desc-scale5_atlas.nii.gz'),
                                            ('fast__pve_0_out_warped.nii.gz',self.subject+'_space-DWI_label-CSF_probseg.nii.gz'),
                                            ('fast__pve_1_out_warped.nii.gz',self.subject+'_space-DWI_label-GM_probseg.nii.gz'),
                                            ('fast__pve_2_out_warped.nii.gz',self.subject+'_space-DWI_label-WM_probseg.nii.gz'),
                                            ('pve_0_out_warped.nii.gz',self.subject+'_space-DWI_label-CSF_probseg.nii.gz'),
                                            ('pve_1_out_warped.nii.gz',self.subject+'_space-DWI_label-GM_probseg.nii.gz'),
                                            ('pve_2_out_warped.nii.gz',self.subject+'_space-DWI_label-WM_probseg.nii.gz'),
                                            ('act_5tt_resampled_warped.nii.gz',self.subject+'_space-DWI_label-5TT_probseg.nii.gz'),
                                            ('gmwmi_resampled_warped.nii.gz',self.subject+'_space-DWI_label-GMWMI_probseg.nii.gz'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale1',self.subject+'_label-L2018_desc-scale1_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale2',self.subject+'_label-L2018_desc-scale2_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale3',self.subject+'_label-L2018_desc-scale3_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale4',self.subject+'_label-L2018_desc-scale4_connectome'),
                                            # ('connectome_'+self.subject+'_T1w_parc_scale5',self.subject+'_label-L2018_desc-scale5_connectome'),
                                            ('connectome_scale1',self.subject+'_label-L2018_desc-scale1_connectome'),
                                            ('connectome_scale2',self.subject+'_label-L2018_desc-scale2_connectome'),
                                            ('connectome_scale3',self.subject+'_label-L2018_desc-scale3_connectome'),
                                            ('connectome_scale4',self.subject+'_label-L2018_desc-scale4_connectome'),
                                            ('connectome_scale5',self.subject+'_label-L2018_desc-scale5_connectome'),
                                            ('dwi.nii.gz',self.subject+'_dwi.nii.gz'),
                                            ('dwi.bval',self.subject+'_dwi.bval'),
                                            # ('dwi.bvec',self.subject+'_dwi.bvec'),
                                            #('diffusion_resampled_CSD_det_tracked',self.subject+'_desc-DET_tractogram'),
                                            #('diffusion_resampled_CSD_prob_tracked',self.subject+'_desc-PROB_tractogram'),
                                            ('eddy_corrected.nii.gz.eddy_rotated_bvecs',self.subject+'_desc-eddyrotated.bvec'),
                                            ('eddy_corrected.nii.gz',self.subject+'_desc-eddycorrected_dwi.nii.gz'),
                                            ('dwi_brain_mask_resampled.nii.gz',self.subject+'_desc-brain_mask_resampled.nii.gz'),
                                            ('ADC',self.subject+'_model-DTI_MD'),
                                            ('FA',self.subject+'_model-DTI_FA'),
                                            ('diffusion_preproc_resampled_fa',self.subject+'_model-DTI_FA'),
                                            ('shore_gfa.nii.gz','{}_model-SHORE_GFA.nii.gz'.format(self.subject)),
                                            ('shore_msd.nii.gz','{}_model-SHORE_MSD.nii.gz'.format(self.subject)),
                                            ('shore_rtop_signal.nii.gz','{}_model-SHORE_RTOP.nii.gz'.format(self.subject)),
                                            ('shore_fodf.nii.gz','{}_model-SHORE_FOD.nii.gz'.format(self.subject)),
                                            ('diffusion_resampled_CSD.mif',self.subject+'_model-CSD_diffmodel.mif'),
                                            ('diffusion_shm_coeff.nii.gz','{}_model-CSD_SHM.nii.gz'.format(self.subject)),#Dipy
                                            ('shm_coeff.nii.gz','{}_model-CSD_SHM.nii.gz'.format(self.subject)),#MRtrix
                                            ('dwi_tensor.nii.gz','{}_desc-WLS_model-DTI_diffmodel.nii.gz'.format(self.subject)),#MRtrix
                                            ('grad.txt',self.subject+'_desc-grad_dwi.txt'),
                                            ('target_epicorrected',self.subject+'_desc-preproc_dwi'),
                                            ('diffusion_preproc_resampled.nii.gz',self.subject+'_desc-preproc_dwi.nii.gz'),
                                            #('endpoints',self.subject+'_tract_endpoints'),
                                            # ('filtered_fiberslabel',self.subject+'_desc-fiberslabel_filt'),
                                            #('final_fiberlabels_'+self.subject+'_T1w_parc',self.subject+'_desc-filtered_fiberlabels'),
                                            #('final_fiberslength_'+self.subject+'_T1w_parc',self.subject+'_desc-filtered_fiberslength'),
                                            ('streamline_final','{}_model-{}_desc-{}_tractogram'.format(self.subject,recon_model,tracking_model)),
                                            ##('_trackvis0/converted',self.subject+'_dwi_tract'),#MRtrix tracts
                                            ##('diffusion_preproc_resampled_tracked',self.subject+'_dwi_tract') #Dipy tracts
                                            ##TODO: Add fODF CSD / SHORE model /
                                        ]
        # Clear previous outputs
        self.clear_stages_outputs()

        # Create diffusion flow

        diffusion_flow = pe.Workflow(name='diffusion_pipeline', base_dir=os.path.abspath(nipype_deriv_subject_directory))
        diffusion_inputnode = pe.Node(interface=util.IdentityInterface(fields=['diffusion','bvecs','bvals','T1','aseg','aparc_aseg','brain','T2','brain_mask','wm_mask_file','roi_volumes','roi_graphMLs','subjects_dir','subject_id','parcellation_scheme']),name='inputnode')# ,'atlas_info'
        diffusion_inputnode.inputs.parcellation_scheme = self.parcellation_scheme
        diffusion_inputnode.inputs.atlas_info = self.atlas_info

        diffusion_outputnode = pe.Node(interface=util.IdentityInterface(fields=['connectivity_matrices']),name='outputnode')
        diffusion_flow.add_nodes([diffusion_inputnode,diffusion_outputnode])

        # diffusion_flow.connect([
        #               (datasource,diffusion_inputnode,[("diffusion","diffusion"),("bvecs","bvecs"),("bvals","bvals")]),
        #               (self.anat_flow,diffusion_inputnode,[("outputnode.subjects_dir","subjects_dir"),("outputnode.subject_id","subject_id"),
        #                                            ("outputnode.T1","T1"),
        #                                            ("outputnode.brain","brain"),
        #                                            ("outputnode.brain_mask","brain_mask"),
        #                                            ("outputnode.wm_mask_file","wm_mask_file"),
        #                                            ( "outputnode.roi_volumes","roi_volumes"),
        #                                            ("outputnode.parcellation_scheme","parcellation_scheme"),
        #                                            ("outputnode.atlas_info","atlas_info")]),
        #               ])

        merge_roi_volumes = pe.Node(interface=Merge(5),name='merge_roi_volumes')
        merge_roi_graphmls = pe.Node(interface=Merge(5),name='merge_roi_graphmls')

        def remove_non_existing_scales(roi_volumes):
            out_roi_volumes = []
            for vol in roi_volumes:
                if vol != None: out_roi_volumes.append(vol)
            return out_roi_volumes

        diffusion_flow.connect([
                      (datasource,merge_roi_volumes,[("roi_volume_s1","in1"),
                                                     ("roi_volume_s2","in2"),
                                                     ("roi_volume_s3","in3"),
                                                     ("roi_volume_s4","in4"),
                                                     ("roi_volume_s5","in5")])
                      ])

        diffusion_flow.connect([
                      (datasource,merge_roi_graphmls,[("roi_graphml_s1","in1"),
                                                      ("roi_graphml_s2","in2"),
                                                      ("roi_graphml_s3","in3"),
                                                      ("roi_graphml_s4","in4"),
                                                      ("roi_graphml_s5","in5")])
                      ])

        diffusion_flow.connect([
                      (datasource,diffusion_inputnode,[("diffusion","diffusion"),
                                                       ("bvecs","bvecs"),
                                                       ("bvals","bvals")]),
                      (datasource,diffusion_inputnode,[("T1","T1"),
                                                       ("aseg","aseg"),
                                                       ("aparc_aseg","aparc_aseg"),
                                                       ("brain","brain"),
                                                       ("brain_mask","brain_mask"),
                                                       ("wm_mask_file","wm_mask_file")]), #,( "roi_volumes","roi_volumes")])
                      (merge_roi_volumes,diffusion_inputnode,[( ("out",remove_non_existing_scales),"roi_volumes")]),
                      (merge_roi_graphmls,diffusion_inputnode,[( ("out",remove_non_existing_scales),"roi_graphMLs")])
                                                #    ("parcellation_scheme","parcellation_scheme"),
                                                #    ("atlas_info","atlas_info")]),
                      ])

        print diffusion_inputnode.outputs

        if self.stages['Preprocessing'].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            diffusion_flow.connect([
                                    (diffusion_inputnode,preproc_flow,[('diffusion','inputnode.diffusion'),
                                                                       ('brain','inputnode.brain'),
                                                                       ('aseg','inputnode.aseg'),
                                                                       ('aparc_aseg','inputnode.aparc_aseg'),
                                                                       ('brain_mask','inputnode.brain_mask'),
                                                                       ('wm_mask_file','inputnode.wm_mask_file'),
                                                                       ('roi_volumes','inputnode.roi_volumes'),
                                                                       ('bvecs','inputnode.bvecs'),('bvals','inputnode.bvals'),('T1','inputnode.T1')]),
                                    ])

        if self.stages['Registration'].enabled:
            reg_flow = self.create_stage_flow("Registration")
            diffusion_flow.connect([
                                    #(diffusion_inputnode,reg_flow,[('T2','inputnode.T2')]),
                                    #(diffusion_inputnode,reg_flow,[("bvals","inputnode.bvals")]),
                                    (preproc_flow,reg_flow, [('outputnode.T1','inputnode.T1'),
                                                             ('outputnode.act_5TT','inputnode.act_5TT'),
                                                             ('outputnode.gmwmi','inputnode.gmwmi'),
                                                             ('outputnode.bvecs_rot','inputnode.bvecs'),
                                                             ('outputnode.bvals','inputnode.bvals'),
                                                             ('outputnode.wm_mask_file','inputnode.wm_mask'),
                                                            ('outputnode.partial_volume_files','inputnode.partial_volume_files'),
                                                            ('outputnode.roi_volumes','inputnode.roi_volumes'),
                                                            ("outputnode.brain","inputnode.brain"),
                                                            ("outputnode.brain_mask","inputnode.brain_mask"),
                                                            ("outputnode.brain_mask_full","inputnode.brain_mask_full"),
                                                            ('outputnode.diffusion_preproc','inputnode.target'),
                                                            ('outputnode.dwi_brain_mask','inputnode.target_mask')]),
                                    (preproc_flow,sinker,[("outputnode.bvecs_rot","dwi.@bvecs_rot")]),
                                    (preproc_flow,sinker,[("outputnode.diffusion_preproc","dwi.@diffusion_preproc")]),
                                    (preproc_flow,sinker,[("outputnode.dwi_brain_mask","dwi.@diffusion_brainmask")]),
                                    #(preproc_flow,sinker,[("outputnode.roi_volumes","anat.@roi_volumes")]),
                                    #(preproc_flow,sinker,[("outputnode.partial_volume_files","anat.@partial_volume_files")])
                                    ])
            if self.stages['Registration'].config.registration_mode == "BBregister (FS)":
                diffusion_flow.connect([
                                        (diffusion_inputnode,reg_flow, [('subjects_dir','inputnode.subjects_dir'),
                                                                        ('subject_id','inputnode.subject_id')]),
                                        ])

        if self.stages['Diffusion'].enabled:
            diff_flow = self.create_stage_flow("Diffusion")
            diffusion_flow.connect([
                                    (reg_flow,diff_flow, [('outputnode.target_epicorrected','inputnode.diffusion')]),
                                    # (reg_flow,diff_flow, [('outputnode.T1_registered_crop','inputnode.T1')]),
                                    (reg_flow,diff_flow, [('outputnode.wm_mask_registered_crop','inputnode.wm_mask_registered')]),
                                    (reg_flow,diff_flow, [('outputnode.brain_mask_registered_crop','inputnode.brain_mask_registered')]),
                                    (reg_flow,diff_flow,[('outputnode.partial_volumes_registered_crop','inputnode.partial_volumes')]),
                                    (reg_flow,diff_flow,[('outputnode.roi_volumes_registered_crop','inputnode.roi_volumes')]),
                                    (reg_flow,diff_flow,[('outputnode.act_5tt_registered_crop','inputnode.act_5tt_registered')]),
                                    (reg_flow,diff_flow,[('outputnode.gmwmi_registered_crop','inputnode.gmwmi_registered')]),
                                    (reg_flow,diff_flow,[('outputnode.grad','inputnode.grad')]),
                                    (reg_flow,diff_flow,[('outputnode.bvals','inputnode.bvals')]),
                                    (reg_flow,diff_flow,[('outputnode.bvecs','inputnode.bvecs')]),
                                    (reg_flow,sinker,[("outputnode.target_epicorrected","dwi.@bdiffusion_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.grad","dwi.@diffusion_grad")]),
                                    (reg_flow,sinker,[("outputnode.T1_registered_crop","anat.@T1_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.act_5tt_registered_crop","anat.@act_5tt_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.gmwmi_registered_crop","anat.@gmwmi_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.brain_registered_crop","anat.@brain_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.brain_mask_registered_crop","anat.@brain_mask_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.wm_mask_registered_crop","anat.@wm_mask_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.roi_volumes_registered_crop","anat.@roivs_reg_crop")]),
                                    (reg_flow,sinker,[("outputnode.partial_volumes_registered_crop","anat.@pves_reg_crop")])
                                    ])

        # if self.stages['MRTrixConnectome'].enabled:
        #     if self.stages['Diffusion'].config.processing_tool == 'FSL':
        #         self.stages['MRTrixConnectome'].config.probtrackx = True
        #     else:
        #         self.stages['MRTrixConnectome'].config.probtrackx = False
        #     con_flow = self.create_stage_flow("MRTrixConnectome")
        #     diffusion_flow.connect([
		      #           (diffusion_inputnode,con_flow, [('parcellation_scheme','inputnode.parcellation_scheme')]),
		      #           (diff_flow,con_flow, [('outputnode.diffusion_model','inputnode.diffusion_model'),('outputnode.track_file','inputnode.track_file'),('outputnode.fod_file','inputnode.fod_file'),('outputnode.gFA','inputnode.gFA'),
        #                                       ('outputnode.roi_volumes','inputnode.roi_volumes_registered'),
		      #                                 ('outputnode.skewness','inputnode.skewness'),('outputnode.kurtosis','inputnode.kurtosis'),
		      #                                 ('outputnode.P0','inputnode.P0')]),
		      #           (con_flow,diffusion_outputnode, [('outputnode.connectivity_matrices','connectivity_matrices')]),
        #                 (diff_flow,sinker,[('outputnode.track_file','dwi.@track_file'),('outputnode.fod_file','dwi.@fod_file'),('outputnode.gFA','dwi.@gFA'),
        #                                       ('outputnode.skewness','dwi.@skewness'),('outputnode.kurtosis','dwi.@kurtosis'),
        #                                       ('outputnode.P0','dwi.@P0')])
		      #           ])

        #     if self.stages['Parcellation'].config.parcellation_scheme == "Custom":
        #         diffusion_flow.connect([(diffusion_inputnode,con_flow, [('atlas_info','inputnode.atlas_info')])])

        if self.stages['Connectome'].enabled:
            # if self.stages['Diffusion'].config.processing_tool == 'FSL':
            #     self.stages['Connectome'].config.probtrackx = True
            # else:
            self.stages['Connectome'].config.probtrackx = False
            self.stages['Connectome'].config.subject = self.global_conf.subject
            con_flow = self.create_stage_flow("Connectome")
            diffusion_flow.connect([
                        (diffusion_inputnode,con_flow, [('parcellation_scheme','inputnode.parcellation_scheme'),
                                                        ('atlas_info','inputnode.atlas_info'),
                                                        ('roi_graphMLs','inputnode.roi_graphMLs')]),
                        (diff_flow,con_flow, [('outputnode.track_file','inputnode.track_file'),
                                              ('outputnode.FA','inputnode.FA'),
                                              ('outputnode.ADC','inputnode.ADC'),
                                              ('outputnode.AD','inputnode.AD'),
                                              ('outputnode.RD','inputnode.RD'),
                                              ('outputnode.roi_volumes','inputnode.roi_volumes_registered'),
                                              ('outputnode.skewness','inputnode.skewness'),
                                              ('outputnode.kurtosis','inputnode.kurtosis'),
                                              ('outputnode.P0','inputnode.P0'),
                                              ('outputnode.mapmri_maps','inputnode.mapmri_maps'),
                                              ('outputnode.shore_maps','inputnode.shore_maps')]),
                        (con_flow,diffusion_outputnode, [('outputnode.connectivity_matrices','connectivity_matrices')]),
                        (diff_flow,sinker,[
                        #                   ('outputnode.track_file','dwi.@track_file'),
                                           ('outputnode.fod_file','dwi.@fod_file'),
                                           ('outputnode.FA','dwi.@FA'),
                                           ('outputnode.ADC','dwi.@ADC'),
                                           ('outputnode.AD','dwi.@AD'),
                                           ('outputnode.RD','dwi.@RD'),
                                           ('outputnode.skewness','dwi.@skewness'),
                                           ('outputnode.kurtosis','dwi.@kurtosis'),
                                           ('outputnode.P0','dwi.@P0'),
                                           ('outputnode.mapmri_maps','dwi.@mapmri_maps'),
                                           ('outputnode.shore_maps','dwi.@shore_maps'),]),
                         (con_flow,sinker,[
                        #                 ('outputnode.endpoints_file','dwi.@endpoints_file'),
                        #                 ('outputnode.endpoints_mm_file','dwi.@endpoints_mm_file'),
                        #                 ('outputnode.final_fiberslength_files','dwi.@sfinal_fiberslength_files'),
                        #                 ('outputnode.filtered_fiberslabel_files','dwi.@filtered_fiberslabel_files'),
                        #                 ('outputnode.final_fiberlabels_files','dwi.@final_fiberlabels_files'),
                                         ('outputnode.streamline_final_file','dwi.@streamline_final_file'),
                                         ("outputnode.connectivity_matrices","dwi.@connectivity_matrices")
                                        ])
                        ])

            # if self.stages['Parcellation'].config.parcellation_scheme == "Custom":
            #     diffusion_flow.connect([(diffusion_inputnode,con_flow, [('atlas_info','inputnode.atlas_info')])])

        return diffusion_flow


    def process(self):
        # Process time
        self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        if '_' in self.subject:
            self.subject = self.subject.split('_')[0]

        old_subject = self.subject

        if self.global_conf.subject_session == '':
            cmp_deriv_subject_directory = os.path.join(self.output_directory,"cmp",self.subject)
            nipype_deriv_subject_directory = os.path.join(self.output_directory,"nipype",self.subject)
        else:
            cmp_deriv_subject_directory = os.path.join(self.output_directory,"cmp",self.subject,self.global_conf.subject_session)
            nipype_deriv_subject_directory = os.path.join(self.output_directory,"nipype",self.subject,self.global_conf.subject_session)

            self.subject = "_".join((self.subject,self.global_conf.subject_session))

        # Initialization
        if os.path.isfile(os.path.join(cmp_deriv_subject_directory,"dwi","pypeline.log")):
            os.unlink(os.path.join(cmp_deriv_subject_directory,"dwi","pypeline.log"))
        config.update_config({'logging': {'log_directory': os.path.join(cmp_deriv_subject_directory,"dwi"),
                                  'log_to_file': True},
                              'execution': {'remove_unnecessary_outputs': False,
                              'stop_on_first_crash': True,'stop_on_first_rerun': False,
                              'crashfile_format': "txt"}
                              })
        logging.update_logging(config)
        iflogger = logging.getLogger('nipype.interface')

        iflogger.info("**** Processing ****")
        print self.anat_flow

        flow = self.create_pipeline_flow(cmp_deriv_subject_directory=cmp_deriv_subject_directory, nipype_deriv_subject_directory=nipype_deriv_subject_directory)
        flow.write_graph(graph2use='colored', format='svg', simple_form=True)
        if(self.number_of_cores != 1):
            flow.run(plugin='MultiProc', plugin_args={'n_procs' : self.number_of_cores})
        else:
            flow.run()

        self.fill_stages_outputs()

        # Clean undesired folders/files
        # rm_file_list = ['rh.EC_average','lh.EC_average','fsaverage']
        # for file_to_rm in rm_file_list:
        #     if os.path.exists(os.path.join(self.base_directory,file_to_rm)):
        #         os.remove(os.path.join(self.base_directory,file_to_rm))

        # copy .ini and log file
        # outdir = os.path.join(cmp_deriv_subject_directory,'config')
        # if not os.path.exists(outdir):
        #     os.makedirs(outdir)
        #
        # try:
        #     shutil.copy(self.config_file,outdir)
        # except shutil.Error:
        #     print("Skipped copy of config file")
        # #shutil.copy(os.path.join(self.base_directory,"derivatives","cmp",self.subject,'pypeline.log'),outdir)

        iflogger.info("**** Processing finished ****")

        return True,'Processing successful'
