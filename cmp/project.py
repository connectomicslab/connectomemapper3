# Copyright (C) 2009-2019, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper Controler for handling non GUI general events
"""
from cmtklib.bids.utils import write_derivative_description
from cmp.pipelines.anatomical import anatomical as Anatomical_pipeline
from cmp.pipelines.diffusion import diffusion as Diffusion_pipeline
from cmp.pipelines.functional import fMRI as FMRI_pipeline
from cmtklib.config import anat_load_config, anat_save_config, \
    dmri_load_config, dmri_save_config, fmri_load_config, fmri_save_config
# from cmtklib.util import remove_aborded_interface_pickles, fix_dataset_directory_in_pickles
from bids import BIDSLayout
import multiprocessing
import fnmatch

import glob
import os
import shutil
from traits.api import *

# import pickle
# import gzip

import warnings

warnings.filterwarnings("ignore",
                        message="UserWarning: No valid root directory found for domain 'derivatives'. Falling back on the Layout's root directory. If this isn't the intended behavior, make sure the config file for this domain includes a 'root' key.")

# Global imports


# Own imports
# import pipelines.diffusion.diffusion as Diffusion_pipeline


##from cmp.configurator.project import fix_dataset_directory_in_pickles, remove_aborded_interface_pickles

# import CMP_MainWindow
# import pipelines.egg.eeg as EEG_pipeline

class CMP_Project_Info(HasTraits):
    base_directory = Directory
    output_directory = Directory

    bids_layout = Instance(BIDSLayout)
    subjects = List([])
    subject = Enum(values='subjects')

    number_of_subjects = Int()

    subject_sessions = List([])
    subject_session = Enum(values='subject_sessions')

    # current_subj = Str()
    anat_warning_msg = Str(
        '\nWarning: selected directory is already configured for anatomical data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    dmri_warning_msg = Str(
        '\nWarning: selected directory is already configured for diffusion data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    fmri_warning_msg = Str(
        '\nWarning: selected directory is already configured for resting-state data processing.\n\nDo you want to reset the configuration to default parameters ?\n')

    # process_type = Enum('diffusion',['diffusion','fMRI'])
    diffusion_imaging_model = Enum('DTI', ['DSI', 'DTI', 'HARDI'])
    parcellation_scheme = Str('Lausanne2008')
    atlas_info = Dict()
    freesurfer_subjects_dir = Str('')
    freesurfer_subject_id = Str('')

    pipeline_processing_summary = List()

    t1_available = Bool(False)
    dmri_available = Bool(False)
    fmri_available = Bool(False)

    anat_config_error_msg = Str('')
    anat_config_to_load = Str()
    anat_available_config = List()
    anat_config_to_load_msg = Str(
        'Several configuration files available. Select which one to load:\n')
    anat_last_date_processed = Str('Not yet processed')
    anat_last_stage_processed = Str('Not yet processed')

    anat_stage_names = List
    anat_custom_last_stage = Str

    dmri_config_error_msg = Str('')
    dmri_config_to_load = Str()
    dmri_available_config = List()
    dmri_config_to_load_msg = Str(
        'Several configuration files available. Select which one to load:\n')
    dmri_last_date_processed = Str('Not yet processed')
    dmri_last_stage_processed = Str('Not yet processed')

    dmri_stage_names = List
    dmri_custom_last_stage = Str

    fmri_config_error_msg = Str('')
    fmri_config_to_load = Str()
    fmri_available_config = List()
    fmri_config_to_load_msg = Str(
        'Several configuration files available. Select which one to load:\n')
    fmri_last_date_processed = Str('Not yet processed')
    fmri_last_stage_processed = Str('Not yet processed')

    fmri_stage_names = List
    fmri_custom_last_stage = Str

    number_of_cores = Enum(1, list(range(1, multiprocessing.cpu_count() + 1)))


# Creates (if needed) the folder hierarchy
#
def refresh_folder(bids_directory, derivatives_directory, subject, input_folders, session=None):
    paths = []

    if session is None or session == '':
        paths.append(os.path.join(
            derivatives_directory, 'freesurfer', subject))
        paths.append(os.path.join(derivatives_directory, 'cmp', subject))
        paths.append(os.path.join(derivatives_directory, 'nipype', subject))

        for in_f in input_folders:
            paths.append(os.path.join(
                derivatives_directory, 'cmp', subject, in_f))
            # paths.append(os.path.join(derivatives_directory,'nipype',subject,in_f))

    else:
        paths.append(os.path.join(derivatives_directory,
                                  'freesurfer', '%s_%s' % (subject, session)))
        paths.append(os.path.join(
            derivatives_directory, 'cmp', subject, session))
        paths.append(os.path.join(derivatives_directory,
                                  'nipype', subject, session))

        for in_f in input_folders:
            paths.append(os.path.join(derivatives_directory,
                                      'cmp', subject, session, in_f))
            # paths.append(os.path.join(derivatives_directory,'nipype',subject,session,in_f))

    for full_p in paths:
        if not os.path.exists(full_p):
            try:
                os.makedirs(full_p)
            except os.error:
                print("%s was already existing" % full_p)
            finally:
                print("Created directory %s" % full_p)

    write_derivative_description(bids_directory, derivatives_directory, 'cmp')
    write_derivative_description(
        bids_directory, derivatives_directory, 'freesurfer')
    write_derivative_description(
        bids_directory, derivatives_directory, 'nipype')


def init_dmri_project(project_info, bids_layout, is_new_project, gui=True, debug=False):
    dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(project_info)

    bids_directory = os.path.abspath(project_info.base_directory)

    derivatives_directory = os.path.abspath(project_info.output_directory)

    if len(project_info.subject_sessions) > 0:
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, dmri_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(bids_directory, derivatives_directory,
                       project_info.subject, dmri_pipeline.input_folders)

    dmri_inputs_checked = dmri_pipeline.check_input(
        layout=bids_layout, gui=gui)
    if dmri_inputs_checked:
        if is_new_project and dmri_pipeline is not None:  # and dmri_pipelineis not None:
            print("> Initialize dmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("... Info : %s was already existing" %
                          derivatives_directory)
                finally:
                    print("... Info : Created directory %s" %
                          derivatives_directory)

            if (project_info.subject_session != '') and (project_info.subject_session is not None):
                project_info.dmri_config_file = os.path.join(derivatives_directory, '%s_%s_diffusion_config.ini' % (
                    project_info.subject, project_info.subject_session))
            else:
                project_info.dmri_config_file = os.path.join(derivatives_directory,
                                                             '%s_diffusion_config.ini' % (project_info.subject))

            if os.path.exists(project_info.dmri_config_file):
                warn_res = project_info.configure_traits(
                    view='dmri_warning_view')
                if warn_res:
                    print("... Read : Diffusion config file (%s)" %
                          project_info.dmri_config_file)
                    dmri_save_config(
                        dmri_pipeline, project_info.dmri_config_file)
                else:
                    return None
            else:
                print("... Create : Diffusion config file (%s)" %
                      project_info.dmri_config_file)
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
        else:
            if debug:
                print("int_project dmri_pipeline.global_config.subjects : ")
                print(dmri_pipeline.global_conf.subjects)

            dmri_conf_loaded = dmri_load_config(
                dmri_pipeline, project_info.dmri_config_file)

            if not dmri_conf_loaded:
                return None

        dmri_pipeline.config_file = project_info.dmri_config_file
    else:
        print("INFO: Missing diffusion inputs")

    return dmri_inputs_checked, dmri_pipeline


def init_fmri_project(project_info, bids_layout, is_new_project, gui=True, debug=False):
    fmri_pipeline = FMRI_pipeline.fMRIPipeline(project_info)

    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)

    if len(project_info.subject_sessions) > 0:
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, fmri_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(bids_directory, derivatives_directory,
                       project_info.subject, fmri_pipeline.input_folders)

    fmri_inputs_checked = fmri_pipeline.check_input(
        layout=bids_layout, gui=gui, debug=False)
    if fmri_inputs_checked:
        if is_new_project and fmri_pipeline is not None:  # and fmri_pipelineis not None:
            print("> Initialize fmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("... Info : %s was already existing" %
                          derivatives_directory)
                finally:
                    print("... Info : Created directory %s" %
                          derivatives_directory)

            if (project_info.subject_session != '') and (project_info.subject_session is not None):
                project_info.fmri_config_file = os.path.join(derivatives_directory, '%s_%s_fMRI_config.ini' % (
                    project_info.subject, project_info.subject_session))
            else:
                project_info.fmri_config_file = os.path.join(derivatives_directory,
                                                             '%s_fMRI_config.ini' % (project_info.subject))

            if os.path.exists(project_info.fmri_config_file):
                warn_res = project_info.configure_traits(
                    view='fmri_warning_view')
                if warn_res:
                    print("... Read : fMRI config file (%s)" %
                          project_info.fmri_config_file)
                    fmri_load_config(
                        fmri_pipeline, project_info.fmri_config_file)
                else:
                    return None
            else:
                print("... Create : fMRI config file (%s)" %
                      project_info.fmri_config_file)
                fmri_save_config(fmri_pipeline, project_info.fmri_config_file)
        else:
            if debug:
                print("int_project fmri_pipeline.global_config.subjects : ")
                print(fmri_pipeline.global_conf.subjects)

            fmri_conf_loaded = fmri_load_config(
                fmri_pipeline, project_info.fmri_config_file)

            if not fmri_conf_loaded:
                return None

        fmri_pipeline.config_file = project_info.fmri_config_file
    else:
        print("INFO : Missing fmri inputs")

    return fmri_inputs_checked, fmri_pipeline


def init_anat_project(project_info, is_new_project, debug=False):
    anat_pipeline = Anatomical_pipeline.AnatomicalPipeline(project_info)

    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)

    if (project_info.subject_session != '') and (project_info.subject_session is not None):
        if debug:
            print('Refresh folder WITH session')
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, anat_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        if debug:
            print('Refresh folder WITHOUT session')
        refresh_folder(bids_directory, derivatives_directory,
                       project_info.subject, anat_pipeline.input_folders)

    if is_new_project and anat_pipeline is not None:  # and dmri_pipelineis not None:
        print("> Initialize anatomical project")
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print("... Info: %s was already existing" %
                      derivatives_directory)
            finally:
                print("... Info : Created directory %s" %
                      derivatives_directory)

        if (project_info.subject_session != '') and (project_info.subject_session is not None):
            project_info.anat_config_file = os.path.join(derivatives_directory, '%s_%s_anatomical_config.ini' % (
                project_info.subject, project_info.subject_session))
        else:
            project_info.anat_config_file = os.path.join(derivatives_directory,
                                                         '%s_anatomical_config.ini' % (project_info.subject))

        if os.path.exists(project_info.anat_config_file):
            warn_res = project_info.configure_traits(view='anat_warning_view')
            if warn_res:
                anat_save_config(anat_pipeline, project_info.anat_config_file)
            else:
                return None
        else:
            anat_save_config(anat_pipeline, project_info.anat_config_file)

    else:
        if debug:
            print("int_project anat_pipeline.global_config.subjects : ")
            print(anat_pipeline.global_conf.subjects)

        anat_conf_loaded = anat_load_config(
            anat_pipeline, project_info.anat_config_file)

        if not anat_conf_loaded:
            return None

    anat_pipeline.config_file = project_info.anat_config_file

    return anat_pipeline


def update_anat_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject)):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.output_directory, 'nipype', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (project_info.anat_last_date_processed == "Not yet processed" or
                pipeline.now > project_info.anat_last_date_processed):
            pipeline.anat_last_date_processed = pipeline.now
            project_info.anat_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
            os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'anatomical_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(
                os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'anatomical_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.anat_last_stage_processed = stage

    # last parcellation scheme
    project_info.parcellation_scheme = pipeline.parcellation_scheme
    project_info.atlas_info = pipeline.atlas_info


def update_dmri_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject)):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.output_directory, 'nipype', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (project_info.dmri_last_date_processed == "Not yet processed" or
                pipeline.now > project_info.dmri_last_date_processed):
            pipeline.dmri_last_date_processed = pipeline.now
            project_info.dmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
            os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'diffusion_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(
                os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'diffusion_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


def update_fmri_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject)):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.output_directory, 'nipype', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (project_info.fmri_last_date_processed == "Not yet processed" or
                pipeline.now > project_info.fmri_last_date_processed):
            pipeline.fmri_last_date_processed = pipeline.now
            project_info.fmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'fMRI_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(
                os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'fMRI_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage
