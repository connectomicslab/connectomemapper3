# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
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

# from nipype.utils.filemanip import copyfile
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util


# from pyface.api import ImageResource
import nipype.interfaces.io as nio
from nipype import config, logging

from nipype.interfaces.base import Directory

from traits.api import *

# from bids import BIDSLayout

# Own import
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
    diffusion_imaging_model_options = List(['DSI', 'DTI', 'HARDI'])
    diffusion_imaging_model = Str
    diffusion_imaging_model_message = Str(
        '\nMultiple diffusion inputs available. Please select desired diffusion modality.')


class AnatomicalPipeline(cmp_common.Pipeline):
    """

    """
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("anatomical_pipeline")
    # input_folders = ['DSI','DTI','HARDI','T1','T2']
    input_folders = ['anat']
    process_type = Str
    diffusion_imaging_model = Str
    parcellation_scheme = Str('Lausanne2008')
    atlas_info = Dict()

    # subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    # ,'MRTrixConnectome']
    ordered_stage_list = ['Segmentation', 'Parcellation']
    custom_last_stage = Enum('Parcellation', ['Segmentation', 'Parcellation'])

    global_conf = Global_Configuration()

    config_file = Str

    flow = Instance(pe.Workflow)

    def __init__(self, project_info):
        # super(Pipeline, self).__init__(project_info)

        self.subject = project_info.subject
        self.last_date_processed = project_info.anat_last_date_processed

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = self.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory = os.path.join(
                self.base_directory, self.subject, self.global_conf.subject_session)
        else:
            self.global_conf.subject_session = ''
            self.subject_directory = os.path.join(
                self.base_directory, self.subject)

        self.derivatives_directory = os.path.abspath(
            project_info.output_directory)
        self.output_directory = os.path.abspath(project_info.output_directory)

        self.stages = {'Segmentation': SegmentationStage(bids_dir=project_info.base_directory,
                                                         output_dir=self.output_directory),
                       'Parcellation': ParcellationStage(pipeline_mode="Diffusion",
                                                         bids_dir=project_info.base_directory,
                                                         output_dir=self.output_directory)}
        cmp_common.Pipeline.__init__(self, project_info)

        self.stages['Segmentation'].config.on_trait_change(
            self.update_parcellation, 'seg_tool')
        self.stages['Parcellation'].config.on_trait_change(
            self.update_segmentation, 'parcellation_scheme')

        self.stages['Parcellation'].config.on_trait_change(
            self.update_parcellation_scheme, 'parcellation_scheme')

    def check_config(self):
        """

        Returns
        -------

        """
        if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation':
            if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return (
                    '\nCustom segmentation selected but no WM mask provided.\n'
                    'Please provide an existing WM mask file in the Segmentation configuration '
                    'window.\n')
            if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
                return (
                    '\n\tCustom segmentation selected but no atlas provided.\n'
                    'Please specify an existing atlas file in the '
                    'Parcellation configuration window.\t\n')
            if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
                return (
                    '\n\tCustom segmentation selected but no graphml info provided.\n'
                    'Please specify an existing graphml file in the '
                    'Parcellation configuration window.\t\n')
        return ''

    def update_parcellation_scheme(self):
        """

        """
        self.parcellation_scheme = self.stages['Parcellation'].config.parcellation_scheme
        self.atlas_info = self.stages['Parcellation'].config.atlas_info

    def update_parcellation(self):
        """

        """
        if self.stages['Segmentation'].config.seg_tool == "Custom segmentation":
            self.stages['Parcellation'].config.parcellation_scheme = 'Custom'
        else:
            self.stages['Parcellation'].config.parcellation_scheme = self.stages['Parcellation'].config.pre_custom

    def update_segmentation(self):
        """

        """
        if self.stages['Parcellation'].config.parcellation_scheme == 'Custom':
            self.stages['Segmentation'].config.seg_tool = "Custom segmentation"
        else:
            self.stages['Segmentation'].config.seg_tool = 'Freesurfer'

    def define_custom_mapping(self, custom_last_stage):
        """

        Parameters
        ----------
        custom_last_stage
        """
        # start by disabling all stages
        for stage in self.ordered_stage_list:
            self.stages[stage].enabled = False
        # enable until selected one
        for stage in self.ordered_stage_list:
            print('Enable stage : %s' % stage)
            self.stages[stage].enabled = True
            if stage == custom_last_stage:
                break

    def check_input(self, layout, gui=True):
        """

        Parameters
        ----------
        layout
        gui

        Returns
        -------

        """
        print('**** Check Inputs  ****')
        t1_available = False
        t1_json_available = False
        valid_inputs = False

        print("> Looking in %s for...." % self.base_directory)

        # types = layout.get_modalities()

        subjid = self.subject.split("-")[1]

        if self.global_conf.subject_session == '':
            T1_file = os.path.join(
                self.subject_directory, 'anat', self.subject + '_T1w.nii.gz')
            files = layout.get(subject=subjid, suffix='T1w',
                               extensions='.nii.gz')
            if len(files) > 0:
                T1_file = os.path.join(files[0].dirname, files[0].filename)
                print(T1_file)
            else:
                return
        else:
            sessid = self.global_conf.subject_session.split("-")[1]
            files = layout.get(subject=subjid, suffix='T1w',
                               extensions='.nii.gz', session=sessid)
            if len(files) > 0:
                T1_file = os.path.join(files[0].dirname, files[0].filename)
                print(T1_file)
            else:
                return

        print("... t1_file : %s" % T1_file)

        if self.global_conf.subject_session == '':
            T1_json_file = os.path.join(
                self.subject_directory, 'anat', self.subject + '_T1w.json')
            files = layout.get(subject=subjid, suffix='T1w',
                               extensions='.json')
            if len(files) > 0:
                T1_json_file = os.path.join(
                    files[0].dirname, files[0].filename)
                print(T1_json_file)
            else:
                T1_json_file = 'NotFound'
        else:
            sessid = self.global_conf.subject_session.split("-")[1]
            files = layout.get(subject=subjid, suffix='T1w',
                               extensions='.json', session=sessid)
            if len(files) > 0:
                T1_json_file = os.path.join(
                    files[0].dirname, files[0].filename)
                print(T1_json_file)
            else:
                T1_json_file = 'NotFound'

        print("... t1_json_file : %s" % T1_json_file)

        if os.path.isfile(T1_file):
            # print("%s available" % typ)
            t1_available = True

        if os.path.isfile(T1_json_file):
            # print("%s available" % typ)
            t1_json_available = True

        if t1_available:
            # Copy T1w data to derivatives / cmp  / subject / anat
            if self.global_conf.subject_session == '':
                out_T1_file = os.path.join(self.output_directory, 'cmp', self.subject, 'anat',
                                           self.subject + '_desc-cmp_T1w.nii.gz')
            else:
                out_T1_file = os.path.join(self.output_directory, 'cmp', self.subject, self.global_conf.subject_session,
                                           'anat',
                                           self.subject + '_' + self.global_conf.subject_session + '_desc-cmp_T1w.nii.gz')

            if not os.path.isfile(out_T1_file):
                shutil.copy(src=T1_file, dst=out_T1_file)

            valid_inputs = True
            input_message = 'Inputs check finished successfully. \nOnly anatomical data (T1) available.'

            if t1_json_available:
                if self.global_conf.subject_session == '':
                    out_T1_json_file = os.path.join(self.output_directory, 'cmp', self.subject, 'anat',
                                                    self.subject + '_desc-cmp_T1w.json')
                else:
                    out_T1_json_file = os.path.join(self.output_directory, 'cmp', self.subject,
                                                    self.global_conf.subject_session, 'anat',
                                                    self.subject + '_' + self.global_conf.subject_session + '_desc-cmp_T1w.json')

                if not os.path.isfile(out_T1_json_file):
                    shutil.copy(src=T1_json_file, dst=out_T1_json_file)

        else:
            if self.global_conf.subject_session == '':
                input_message = 'Error during inputs check. No anatomical data available in folder ' + os.path.join(
                    self.base_directory, self.subject) + '/anat/!'
            else:
                input_message = 'Error during inputs check. No anatomical data available in folder ' + os.path.join(
                    self.base_directory, self.subject, self.global_conf.subject_session) + '/anat/!'

        # diffusion_imaging_model = diffusion_imaging_model[0]

        if gui:
            print(input_message)

        else:
            print(input_message)

        if (t1_available):
            valid_inputs = True
        else:
            print(
                "ERROR : Missing required inputs. Please see documentation for more details.")

        if not t1_json_available:
            print(
                "Warning : Missing BIDS json sidecar. Please see documentation for more details.")

        # for stage in self.stages.values():
        #     if stage.enabled:
        #         print stage.name
        #         print stage.stage_dir

        # self.fill_stages_outputs()

        return valid_inputs

    def check_output(self):
        """

        Returns
        -------

        """
        t1_available = False
        brain_available = False
        brainmask_available = False
        wm_available = False
        roivs_available = False
        valid_output = False

        subject = self.subject

        if self.global_conf.subject_session == '':
            anat_deriv_subject_directory = os.path.join(
                self.output_directory, "cmp", self.subject, 'anat')
        else:
            if self.global_conf.subject_session not in subject:
                anat_deriv_subject_directory = os.path.join(self.output_directory, "cmp", subject,
                                                            self.global_conf.subject_session, 'anat')
                subject = "_".join((subject, self.global_conf.subject_session))
            else:
                anat_deriv_subject_directory = os.path.join(self.output_directory, "cmp", subject.split("_")[0],
                                                            self.global_conf.subject_session, 'anat')

        T1_file = os.path.join(anat_deriv_subject_directory,
                               subject + '_desc-head_T1w.nii.gz')
        brain_file = os.path.join(
            anat_deriv_subject_directory, subject + '_desc-brain_T1w.nii.gz')
        brainmask_file = os.path.join(
            anat_deriv_subject_directory, subject + '_desc-brain_mask.nii.gz')
        wm_mask_file = os.path.join(
            anat_deriv_subject_directory, subject + '_label-WM_dseg.nii.gz')
        roiv_files = glob.glob(anat_deriv_subject_directory +
                               "/" + subject + "_label-L2018_desc-scale*_atlas.nii.gz")

        error_message = ''

        if os.path.isfile(T1_file):
            t1_available = True
        else:
            error_message = "ERROR : Missing anatomical output file %s . Please re-run the anatomical pipeline" % T1_file
            print(error_message)

        if os.path.isfile(brain_file):
            brain_available = True
        else:
            error_message = "ERROR : Missing anatomical output file %s . Please re-run the anatomical pipeline" % brain_file
            print(error_message)

        if os.path.isfile(brainmask_file):
            brainmask_available = True
        else:
            error_message = "ERROR : Missing anatomical output file %s . Please re-run the anatomical pipeline" % brainmask_file
            print(error_message)

        if os.path.isfile(wm_mask_file):
            wm_available = True
        else:
            error_message = "Missing anatomical output file %s . Please re-run the anatomical pipeline" % wm_mask_file
            print(error_message)

        cnt1 = 0
        cnt2 = 0
        for roiv_file in roiv_files:
            cnt1 = cnt1 + 1
            if os.path.isfile(roiv_file):
                cnt2 = cnt2 + 1
        if cnt1 == cnt2:
            roivs_available = True
        else:
            error_message = "ERROR : Missing %g/%g anatomical parcellation output files. Please re-run the anatomical pipeline" % (
                cnt1 - cnt2, cnt1)
            print(error_message)

        if t1_available is True and brain_available is True and brainmask_available is True and wm_available is True and roivs_available is True:
            print("INFO : Valid derivatives for anatomical pipeline")
            valid_output = True

        return valid_output, error_message

    def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):
        """

        Parameters
        ----------
        cmp_deriv_subject_directory
        nipype_deriv_subject_directory

        Returns
        -------

        """
        # subject_directory = self.subject_directory

        # Data import
        datasource = pe.Node(interface=nio.DataGrabber(
            outfields=['T1']), name='datasource')
        datasource.inputs.base_directory = cmp_deriv_subject_directory
        datasource.inputs.template = '*'
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = dict(
            T1='anat/' + self.subject + '_desc-cmp_T1w.nii.gz')
        datasource.inputs.sort_filelist = False

        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="anatomical_sinker")
        sinker.inputs.base_directory = os.path.abspath(
            cmp_deriv_subject_directory)

        # if self.parcellation_scheme == 'Lausanne2008':
        #     bids_atlas_label = 'L2008'
        # elif self.parcellation_scheme == 'Lausanne2018':
        #     bids_atlas_label = 'L2018'
        # elif self.parcellation_scheme == 'NativeFreesurfer':
        #     bids_atlas_label = 'Desikan'

        # Dataname substitutions in order to comply with BIDS derivatives specifications
        if self.parcellation_scheme == 'Lausanne2008':
            sinker.inputs.substitutions = [('T1.nii.gz', self.subject + '_desc-head_T1w.nii.gz'),
                                           ('brain.nii.gz', self.subject +
                                            '_desc-brain_T1w.nii.gz'),
                                           ('brain_mask.nii.gz', self.subject +
                                            '_desc-brain_mask.nii.gz'),
                                           ('aseg.nii.gz', self.subject +
                                            '_desc-aseg_dseg.nii.gz'),
                                           ('csf_mask.nii.gz', self.subject +
                                            '_label-CSF_dseg.nii.gz'),
                                           ('fsmask_1mm.nii.gz', self.subject +
                                            '_label-WM_dseg.nii.gz'),
                                           ('gmmask.nii.gz', self.subject +
                                            '_label-GM_dseg.nii.gz'),
                                           ('T1w_class-GM.nii.gz', self.subject +
                                            '_label-GM_dseg.nii.gz'),
                                           ('wm_eroded.nii.gz', self.subject +
                                            '_label-WM_desc-eroded_dseg.nii.gz'),
                                           ('csf_eroded.nii.gz', self.subject +
                                            '_label-CSF_desc-eroded_dseg.nii.gz'),
                                           ('brain_eroded.nii.gz',
                                            self.subject + '_label-brain_desc-eroded_dseg.nii.gz'),
                                           ('aparc+aseg.native.nii.gz', self.subject +
                                            '_desc-aparcaseg_dseg.nii.gz'),
                                           ('aparc+aseg.Lausanne2018.native.nii.gz',
                                            self.subject + '_desc-aparcaseg_dseg.nii.gz'),
                                           ('ROIv_Lausanne2008_scale1.nii.gz',
                                            self.subject + '_label-L2008_desc-scale1_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale2.nii.gz',
                                            self.subject + '_label-L2008_desc-scale2_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale3.nii.gz',
                                            self.subject + '_label-L2008_desc-scale3_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale4.nii.gz',
                                            self.subject + '_label-L2008_desc-scale4_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale5.nii.gz',
                                            self.subject + '_label-L2008_desc-scale5_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale1_final.nii.gz',
                                            self.subject + '_label-L2008_desc-scale1_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale2_final.nii.gz',
                                            self.subject + '_label-L2008_desc-scale2_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale3_final.nii.gz',
                                            self.subject + '_label-L2008_desc-scale3_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale4_final.nii.gz',
                                            self.subject + '_label-L2008_desc-scale4_atlas.nii.gz'),
                                           ('ROIv_Lausanne2008_scale5_final.nii.gz',
                                            self.subject + '_label-L2008_desc-scale5_atlas.nii.gz'),
                                           ('resolution83.graphml',
                                            self.subject + '_label-L2008_desc-scale1_atlas.graphml'),
                                           ('resolution150.graphml',
                                            self.subject + '_label-L2008_desc-scale2_atlas.graphml'),
                                           ('resolution258.graphml',
                                            self.subject + '_label-L2008_desc-scale3_atlas.graphml'),
                                           ('resolution500.graphml',
                                            self.subject + '_label-L2008_desc-scale4_atlas.graphml'),
                                           ('resolution1015.graphml',
                                            self.subject + '_label-L2008_desc-scale5_atlas.graphml'),
                                           ('resolution83_LUT.txt',
                                            self.subject + '_label-L2008_desc-scale1_atlas_FreeSurferColorLUT.txt'),
                                           ('resolution150_LUT.txt',
                                            self.subject + '_label-L2008_desc-scale2_atlas_FreeSurferColorLUT.txt'),
                                           ('resolution258_LUT.txt',
                                            self.subject + '_label-L2008_desc-scale3_atlas_FreeSurferColorLUT.txt'),
                                           ('resolution500_LUT.txt',
                                            self.subject + '_label-L2008_desc-scale4_atlas_FreeSurferColorLUT.txt'),
                                           ('resolution1015_LUT.txt',
                                            self.subject + '_label-L2008_desc-scale5_atlas_FreeSurferColorLUT.txt'),
                                           (
                                           'roi_stats_scale1.tsv', self.subject + '_label-L2008_desc-scale1_stats.tsv'),
                                           (
                                           'roi_stats_scale2.tsv', self.subject + '_label-L2008_desc-scale2_stats.tsv'),
                                           (
                                           'roi_stats_scale3.tsv', self.subject + '_label-L2008_desc-scale3_stats.tsv'),
                                           (
                                           'roi_stats_scale4.tsv', self.subject + '_label-L2008_desc-scale4_stats.tsv'),
                                           (
                                           'roi_stats_scale5.tsv', self.subject + '_label-L2008_desc-scale5_stats.tsv'),
                                           ]
        elif self.parcellation_scheme == 'Lausanne2018':
            sinker.inputs.substitutions = [('T1.nii.gz', self.subject + '_desc-head_T1w.nii.gz'),
                                           ('brain.nii.gz', self.subject +
                                            '_desc-brain_T1w.nii.gz'),
                                           ('brain_mask.nii.gz', self.subject +
                                            '_desc-brain_mask.nii.gz'),
                                           ('aseg.nii.gz', self.subject +
                                            '_desc-aseg_dseg.nii.gz'),
                                           ('csf_mask.nii.gz', self.subject +
                                            '_label-CSF_dseg.nii.gz'),
                                           ('fsmask_1mm.nii.gz', self.subject +
                                            '_label-WM_dseg.nii.gz'),
                                           ('gmmask.nii.gz', self.subject +
                                            '_label-GM_dseg.nii.gz'),
                                           ('T1w_class-GM.nii.gz', self.subject +
                                            '_label-GM_dseg.nii.gz'),
                                           ('wm_eroded.nii.gz', self.subject +
                                            '_label-WM_desc-eroded_dseg.nii.gz'),
                                           ('csf_eroded.nii.gz', self.subject +
                                            '_label-CSF_desc-eroded_dseg.nii.gz'),
                                           ('brain_eroded.nii.gz',
                                            self.subject + '_label-brain_desc-eroded_dseg.nii.gz'),
                                           ('aparc+aseg.native.nii.gz', self.subject +
                                            '_desc-aparcaseg_dseg.nii.gz'),
                                           ('aparc+aseg.Lausanne2018.native.nii.gz',
                                            self.subject + '_desc-aparcaseg_dseg.nii.gz'),
                                           ('ROIv_Lausanne2018_scale1.nii.gz',
                                            self.subject + '_label-L2018_desc-scale1_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale2.nii.gz',
                                            self.subject + '_label-L2018_desc-scale2_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale3.nii.gz',
                                            self.subject + '_label-L2018_desc-scale3_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale4.nii.gz',
                                            self.subject + '_label-L2018_desc-scale4_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale5.nii.gz',
                                            self.subject + '_label-L2018_desc-scale5_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale1_final.nii.gz',
                                            self.subject + '_label-L2018_desc-scale1_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale2_final.nii.gz',
                                            self.subject + '_label-L2018_desc-scale2_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale3_final.nii.gz',
                                            self.subject + '_label-L2018_desc-scale3_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale4_final.nii.gz',
                                            self.subject + '_label-L2018_desc-scale4_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale5_final.nii.gz',
                                            self.subject + '_label-L2018_desc-scale5_atlas.nii.gz'),
                                           ('ROIv_Lausanne2018_scale1.graphml',
                                            self.subject + '_label-L2018_desc-scale1_atlas.graphml'),
                                           ('ROIv_Lausanne2018_scale2.graphml',
                                            self.subject + '_label-L2018_desc-scale2_atlas.graphml'),
                                           ('ROIv_Lausanne2018_scale3.graphml',
                                            self.subject + '_label-L2018_desc-scale3_atlas.graphml'),
                                           ('ROIv_Lausanne2018_scale4.graphml',
                                            self.subject + '_label-L2018_desc-scale4_atlas.graphml'),
                                           ('ROIv_Lausanne2018_scale5.graphml',
                                            self.subject + '_label-L2018_desc-scale5_atlas.graphml'),
                                           ('ROIv_Lausanne2018_scale1_FreeSurferColorLUT.txt',
                                            self.subject + '_label-L2018_desc-scale1_atlas_FreeSurferColorLUT.txt'),
                                           ('ROIv_Lausanne2018_scale2_FreeSurferColorLUT.txt',
                                            self.subject + '_label-L2018_desc-scale2_atlas_FreeSurferColorLUT.txt'),
                                           ('ROIv_Lausanne2018_scale3_FreeSurferColorLUT.txt',
                                            self.subject + '_label-L2018_desc-scale3_atlas_FreeSurferColorLUT.txt'),
                                           ('ROIv_Lausanne2018_scale4_FreeSurferColorLUT.txt',
                                            self.subject + '_label-L2018_desc-scale4_atlas_FreeSurferColorLUT.txt'),
                                           ('ROIv_Lausanne2018_scale5_FreeSurferColorLUT.txt',
                                            self.subject + '_label-L2018_desc-scale5_atlas_FreeSurferColorLUT.txt'),
                                           ('ROIv_HR_th_scale33.nii.gz',
                                            self.subject + '_label-L2018_desc-scale1_atlas.nii.gz'),
                                           ('ROIv_HR_th_scale60.nii.gz',
                                            self.subject + '_label-L2018_desc-scale2_atlas.nii.gz'),
                                           ('ROIv_HR_th_scale125.nii.gz',
                                            self.subject + '_label-L2018_desc-scale3_atlas.nii.gz'),
                                           ('ROIv_HR_th_scale250.nii.gz',
                                            self.subject + '_label-L2018_desc-scale4_atlas.nii.gz'),
                                           ('ROIv_HR_th_scale500.nii.gz',
                                            self.subject + '_label-L2018_desc-scale5_atlas.nii.gz'),
                                           (
                                           'roi_stats_scale1.tsv', self.subject + '_label-L2018_desc-scale1_stats.tsv'),
                                           (
                                           'roi_stats_scale2.tsv', self.subject + '_label-L2018_desc-scale2_stats.tsv'),
                                           (
                                           'roi_stats_scale3.tsv', self.subject + '_label-L2018_desc-scale3_stats.tsv'),
                                           (
                                           'roi_stats_scale4.tsv', self.subject + '_label-L2018_desc-scale4_stats.tsv'),
                                           (
                                           'roi_stats_scale5.tsv', self.subject + '_label-L2018_desc-scale5_stats.tsv'),
                                           ]
        elif self.parcellation_scheme == 'NativeFreesurfer':
            sinker.inputs.substitutions = [('T1.nii.gz', self.subject + '_desc-head_T1w.nii.gz'),
                                           ('brain.nii.gz', self.subject +
                                            '_desc-brain_T1w.nii.gz'),
                                           ('brain_mask.nii.gz', self.subject +
                                            '_desc-brain_mask.nii.gz'),
                                           ('aseg.nii.gz', self.subject +
                                            '_desc-aseg_dseg.nii.gz'),
                                           ('csf_mask.nii.gz', self.subject +
                                            '_label-CSF_dseg.nii.gz'),
                                           ('fsmask_1mm.nii.gz', self.subject +
                                            '_label-WM_dseg.nii.gz'),
                                           ('gmmask.nii.gz', self.subject +
                                            '_label-GM_dseg.nii.gz'),
                                           ('T1w_class-GM.nii.gz', self.subject +
                                            '_label-GM_dseg.nii.gz'),
                                           ('wm_eroded.nii.gz', self.subject +
                                            '_label-WM_desc-eroded_dseg.nii.gz'),
                                           ('csf_eroded.nii.gz', self.subject +
                                            '_label-CSF_desc-eroded_dseg.nii.gz'),
                                           ('brain_eroded.nii.gz',
                                            self.subject + '_label-brain_desc-eroded_dseg.nii.gz'),
                                           ('aparc+aseg.native.nii.gz', self.subject +
                                            '_desc-aparcaseg_dseg.nii.gz'),
                                           ('aparc+aseg.Lausanne2018.native.nii.gz',
                                            self.subject + '_desc-aparcaseg_dseg.nii.gz'),
                                           ('ROIv_HR_th_freesurferaparc.nii.gz',
                                            self.subject + '_label-Desikan_atlas.nii.gz'),
                                           ('freesurferaparc.graphml', self.subject +
                                            '_label-Desikan_atlas.graphml'),
                                           ('FreeSurferColorLUT_adapted.txt',
                                            self.subject + '_label-Desikan_FreeSurferColorLUT.txt'),
                                           (
                                           'roi_stats_freesurferaparc.tsv', self.subject + '_label-Desikan_stats.tsv'),
                                           ]
        # else:
        #     sinker.inputs.substitutions = [ (self.subject+'_T1w.nii.gz', self.subject+'_T1w_head.nii.gz'),
        #                                     ('brain_mask.nii.gz', self.subject+'_T1w_brainmask.nii.gz'),
        #                                     ('brainmask_eroded.nii.gz', self.subject+'_T1w_brainmask_eroded.nii.gz'),
        #                                     ('brain.nii.gz', self.subject+'_T1w_brain.nii.gz'),
        #                                     ('fsmask_1mm.nii.gz',self.subject+'_T1w_class-WM.nii.gz'),
        #                                     ('fsmask_1mm_eroded.nii.gz',self.subject+'_T1w_class-WM_eroded.nii.gz'),
        #                                     ('csf_mask_eroded.nii.gz',self.subject+'_T1w_class-CSF_eroded.nii.gz'),
        #                                     #('gm_mask',self.subject+'_T1w_class-GM'),
        #                                     #('roivs', self.subject+'_T1w_parc'),#TODO substitute for list of files
        #                                     ('T1w_class-GM.nii.gz',self.subject+'_T1w_class-GM.nii.gz'),
        #                                     ('ROIv_HR_th_scale1.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
        #                                     ('ROIv_HR_th_scale2.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
        #                                     ('ROIv_HR_th_scale3.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
        #                                     ('ROIv_HR_th_scale4.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
        #                                     ('ROIv_HR_th_scale5.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
        #                                     ('ROIv_HR_th_scale33.nii.gz',self.subject+'_T1w_parc_scale1.nii.gz'),
        #                                     ('ROIv_HR_th_scale60.nii.gz',self.subject+'_T1w_parc_scale2.nii.gz'),
        #                                     ('ROIv_HR_th_scale125.nii.gz',self.subject+'_T1w_parc_scale3.nii.gz'),
        #                                     ('ROIv_HR_th_scale250.nii.gz',self.subject+'_T1w_parc_scale4.nii.gz'),
        #                                     ('ROIv_HR_th_scale500.nii.gz',self.subject+'_T1w_parc_scale5.nii.gz'),
        #                                   ]

        # Clear previous outputs
        self.clear_stages_outputs()

        # Create common_flow

        anat_flow = pe.Workflow(name='anatomical_pipeline', base_dir=os.path.abspath(
            nipype_deriv_subject_directory))
        anat_inputnode = pe.Node(interface=util.IdentityInterface(
            fields=["T1"]), name="inputnode")
        anat_outputnode = pe.Node(interface=util.IdentityInterface(
            fields=["subjects_dir", "subject_id", "T1", "aseg", "aparc_aseg", "brain", "brain_mask", "csf_mask_file",
                    "wm_mask_file", "gm_mask_file", "wm_eroded", "brain_eroded", "csf_eroded",
                    "roi_volumes", "parcellation_scheme", "atlas_info", "roi_colorLUTs", "roi_graphMLs",
                    "roi_volumes_stats"]), name="outputnode")
        anat_flow.add_nodes([anat_inputnode, anat_outputnode])

        anat_flow.connect([
            (datasource, anat_inputnode, [("T1", "T1")]),
        ])

        if self.stages['Segmentation'].enabled:
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":

                if self.stages['Segmentation'].config.use_existing_freesurfer_data is False:
                    self.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.output_directory,
                                                                                              'freesurfer')
                    print("Freesurfer_subjects_dir: %s" %
                          self.stages['Segmentation'].config.freesurfer_subjects_dir)
                    self.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(self.output_directory,
                                                                                            'freesurfer', self.subject)
                    print("Freesurfer_subject_id: %s" %
                          self.stages['Segmentation'].config.freesurfer_subject_id)

            seg_flow = self.create_stage_flow("Segmentation")

            anat_flow.connect(
                [(anat_inputnode, seg_flow, [('T1', 'inputnode.T1')])])

            if self.stages['Segmentation'].config.seg_tool == "Custom segmentation":
                anat_flow.connect([
                    (seg_flow, anat_outputnode, [("outputnode.brain_mask", "brain_mask"),
                                                 ("outputnode.brain", "brain")]),
                    (anat_inputnode, anat_outputnode, [("T1", "T1")])
                ])

            anat_flow.connect([
                (seg_flow, anat_outputnode, [("outputnode.subjects_dir", "subjects_dir"),
                                             ("outputnode.subject_id", "subject_id")])
            ])

        if self.stages['Parcellation'].enabled:
            parc_flow = self.create_stage_flow("Parcellation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                anat_flow.connect([(seg_flow, parc_flow, [('outputnode.subjects_dir', 'inputnode.subjects_dir'),
                                                          ('outputnode.subject_id', 'inputnode.subject_id')]),
                                   ])
            else:
                anat_flow.connect([
                    (seg_flow, parc_flow, [
                     ("outputnode.custom_wm_mask", "inputnode.custom_wm_mask")])
                ])
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                anat_flow.connect([
                    (parc_flow, anat_outputnode, [("outputnode.wm_mask_file", "wm_mask_file"),
                                                  ("outputnode.parcellation_scheme",
                                                   "parcellation_scheme"),
                                                  ("outputnode.atlas_info",
                                                   "atlas_info"),
                                                  ("outputnode.roi_volumes",
                                                   "roi_volumes"),
                                                  ("outputnode.roi_colorLUTs",
                                                   "roi_colorLUTs"),
                                                  ("outputnode.roi_graphMLs",
                                                   "roi_graphMLs"),
                                                  ("outputnode.roi_volumes_stats",
                                                   "roi_volumes_stats"),
                                                  ("outputnode.wm_eroded",
                                                   "wm_eroded"),
                                                  ("outputnode.gm_mask_file",
                                                   "gm_mask_file"),
                                                  ("outputnode.csf_mask_file",
                                                   "csf_mask_file"),
                                                  ("outputnode.csf_eroded",
                                                   "csf_eroded"),
                                                  ("outputnode.brain_eroded",
                                                   "brain_eroded"),
                                                  ("outputnode.T1", "T1"),
                                                  ("outputnode.aseg", "aseg"),
                                                  ("outputnode.aparc_aseg",
                                                   "aparc_aseg"),
                                                  ("outputnode.brain_mask",
                                                   "brain_mask"),
                                                  ("outputnode.brain", "brain"),
                                                  ])
                ])
            else:
                anat_flow.connect([
                    (parc_flow, anat_outputnode, [("outputnode.wm_mask_file", "wm_mask_file"),
                                                  ("outputnode.parcellation_scheme",
                                                   "parcellation_scheme"),
                                                  ("outputnode.atlas_info",
                                                   "atlas_info"),
                                                  ("outputnode.roi_volumes",
                                                   "roi_volumes"),
                                                  ("outputnode.wm_eroded",
                                                   "wm_eroded"),
                                                  ("outputnode.gm_mask_file",
                                                   "gm_mask_file"),
                                                  ("outputnode.csf_eroded",
                                                   "csf_eroded"),
                                                  ("outputnode.brain_eroded",
                                                   "brain_eroded"),

                                                  ]),
                ])

                if not self.stages['Segmentation'].enabled:
                    anat_flow.connect([
                        (anat_inputnode, anat_outputnode, [("T1", "T1")])
                    ])

        anat_flow.connect([
            (anat_outputnode, sinker, [("T1", "anat.@T1")]),
            (anat_outputnode, sinker, [("aseg", "anat.@aseg")]),
            (anat_outputnode, sinker, [("aparc_aseg", "anat.@aparc_aseg")]),
            (anat_outputnode, sinker, [("brain", "anat.@brain")]),
            (anat_outputnode, sinker, [("brain_mask", "anat.@brain_mask")]),
            (anat_outputnode, sinker, [("wm_mask_file", "anat.@wm_mask")]),
            (anat_outputnode, sinker, [("gm_mask_file", "anat.@gm_mask")]),
            (anat_outputnode, sinker, [("csf_mask_file", "anat.@csf_mask")]),
            (anat_outputnode, sinker, [("roi_volumes", "anat.@roivs")]),
            (anat_outputnode, sinker, [("roi_colorLUTs", "anat.@luts")]),
            (anat_outputnode, sinker, [("roi_graphMLs", "anat.@graphmls")]),
            (anat_outputnode, sinker, [("roi_volumes_stats", "anat.@stats")]),
            (anat_outputnode, sinker, [
             ("brain_eroded", "anat.@brainmask_eroded")]),
            (anat_outputnode, sinker, [("wm_eroded", "anat.@wm_eroded")]),
            (anat_outputnode, sinker, [("csf_eroded", "anat.@csf_eroded")])
        ])

        self.flow = anat_flow
        return anat_flow

    def process(self):
        """

        Returns
        -------

        """
        # Enable the use of the W3C PROV data model to capture and represent provenance in Nipype
        # config.enable_provenance()

        # Process time
        self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        if '_' in self.subject:
            self.subject = self.subject.split('_')[0]

        # old_subject = self.subject

        if self.global_conf.subject_session == '':
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory, "cmp", self.subject)
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, "nipype", self.subject)
        else:
            cmp_deriv_subject_directory = os.path.join(self.output_directory, "cmp", self.subject,
                                                       self.global_conf.subject_session)
            nipype_deriv_subject_directory = os.path.join(self.output_directory, "nipype", self.subject,
                                                          self.global_conf.subject_session)

            self.subject = "_".join(
                (self.subject, self.global_conf.subject_session))

        if not os.path.exists(os.path.join(nipype_deriv_subject_directory, "anatomical_pipeline")):
            try:
                os.makedirs(os.path.join(
                    nipype_deriv_subject_directory, "anatomical_pipeline"))
            except os.error:
                print("%s was already existing" % os.path.join(
                    nipype_deriv_subject_directory, "anatomical_pipeline"))

        # Initialization
        if os.path.isfile(os.path.join(nipype_deriv_subject_directory, "anatomical_pipeline", "pypeline.log")):
            os.unlink(os.path.join(nipype_deriv_subject_directory,
                                   "anatomical_pipeline", "pypeline.log"))
        config.update_config(
            {'logging': {'log_directory': os.path.join(nipype_deriv_subject_directory, "anatomical_pipeline"),
                         'log_to_file': True},
             'execution': {'remove_unnecessary_outputs': False,
                           'stop_on_first_crash': True,
                           'stop_on_first_rerun': False,
                           'use_relative_paths': True,
                           'crashfile_format': "txt"}
             })
        logging.update_logging(config)
        iflogger = logging.getLogger('nipype.interface')

        iflogger.info("**** Processing ****")
        anat_flow = self.create_pipeline_flow(cmp_deriv_subject_directory=cmp_deriv_subject_directory,
                                              nipype_deriv_subject_directory=nipype_deriv_subject_directory)
        anat_flow.write_graph(graph2use='colored',
                              format='svg', simple_form=True)

        if (self.number_of_cores != 1):
            anat_flow.run(plugin='MultiProc', plugin_args={
                          'n_procs': self.number_of_cores})
        else:
            anat_flow.run()

        # self.fill_stages_outputs()

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

        # shutil.copy(os.path.join(self.base_directory,"derivatives","cmp",self.subject,'pypeline.log'),outdir)

        iflogger.info("**** Processing finished ****")

        return True, 'Processing successful'
