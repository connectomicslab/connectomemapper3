# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper Controler for handling GUI and non GUI general events."""

# Global imports
import os
import fnmatch
import glob
import shutil
import multiprocessing
from subprocess import Popen

from traitsui.api import *
from traits.api import *
import warnings

from bids import BIDSLayout
from pyface.api import FileDialog, OK

# Own imports
from . import core
from . import gui
from cmp.bidsappmanager.pipelines.anatomical import anatomical as Anatomical_pipeline
from cmp.bidsappmanager.pipelines.diffusion import diffusion as Diffusion_pipeline
from cmp.bidsappmanager.pipelines.functional import fMRI as FMRI_pipeline
from cmtklib.config import anat_load_config_ini, anat_save_config, \
    dmri_load_config_ini, dmri_save_config, fmri_load_config_ini, fmri_save_config, \
    get_anat_process_detail_ini, get_dmri_process_detail_ini, get_fmri_process_detail_ini


warnings.filterwarnings(
    "ignore", message="No valid root directory found for domain 'derivatives'.")


def clean_cache(bids_root):
    """Clean cache stored in /tmp.

    Target issue related to that a dataset directory is mounted into /tmp and 
    used for caching by java/matlab/matplotlib/xvfb-run in the container image.

    Parameters
    ----------
    bids_root : string
        BIDS root dataset directory
    """
    print('> Clean docker image cache stored in /tmp')

    for d in glob.glob(os.path.join(bids_root, ' hsperfdata_cmp')):
        print('... DEL: {}'.format(d))
        shutil.rmtree(d)

    for f in glob.glob(os.path.join(bids_root, '._java*')):
        print('... DEL: {}'.format(f))
        os.remove(f)

    for f in glob.glob(os.path.join(bids_root, 'mri_segstats.tmp*')):
        print('... DEL: {}'.format(f))
        os.remove(f)

    for d in glob.glob(os.path.join(bids_root, 'MCR_*')):
        print('... DEL: {}'.format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, 'matplotlib*')):
        print('... DEL: {}'.format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, 'xvfb-run.*')):
        print('... DEL: {}'.format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, '.X11*')):
        print('... DEL: {}'.format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, '.X11-unix')):
        print('... DEL: {}'.format(d))
        shutil.rmtree(d)

    for f in glob.glob(os.path.join(bids_root, '.X99*')):
        print('... DEL: {}'.format(f))
        os.remove(d)


def is_tool(name):
    """Check whether `name` is on PATH."""

    from distutils.spawn import find_executable

    return find_executable(name) is not None


# 
#
def refresh_folder(derivatives_directory, subject, input_folders, session=None):
    """Creates (if needed) the folder hierarchy.

    Parameters
    ----------
    derivatives_directory : string

    subject : string
        Subject label (``sub-XX``) for which we create the output folder hierarchy 

    input_folders : list of string
        List of folders to create in ``derivative_directory/sub-XX/(ses-YY)/`` folder
        for the given ``subject``
    """
    paths = []

    if session is None or session == '':
        paths.append(os.path.join(
            derivatives_directory, 'freesurfer', subject))
        paths.append(os.path.join(derivatives_directory, 'cmp', subject))
        paths.append(os.path.join(derivatives_directory, 'nipype', subject))

        for in_f in input_folders:
            paths.append(os.path.join(
                derivatives_directory, 'cmp', subject, in_f))
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

    for full_p in paths:
        if not os.path.exists(full_p):
            try:
                os.makedirs(full_p)
            except os.error:
                print("%s was already existing" % full_p)
            finally:
                print("Created directory %s" % full_p)


def init_dmri_project(project_info, bids_layout, is_new_project, gui=True):
    """Create and initialize a :class:`DiffusionPipelineUI` instance

    Parameters
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` class

    bids_layout : bids.BIDSLayout
        PyBIDS BIDS Layout object describing the BIDS dataset

    is_new_project : bool
        If True, this is a new project which has been never processed
    """
    dmri_pipeline = Diffusion_pipeline.DiffusionPipelineUI(project_info)

    derivatives_directory = os.path.join(
        project_info.base_directory, 'derivatives')

    if (project_info.subject_session != '') and (project_info.subject_session is not None):
        refresh_folder(derivatives_directory, project_info.subject, dmri_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(derivatives_directory,
                       project_info.subject, dmri_pipeline.input_folders)

    dmri_inputs_checked = dmri_pipeline.check_input(
        layout=bids_layout, gui=gui)
    if dmri_inputs_checked:
        if is_new_project and dmri_pipeline is not None:
            print("Initialize dmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("%s was already existing" % derivatives_directory)
                finally:
                    print("Created directory %s" % derivatives_directory)

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
                    print("Read diffusion config file (%s)" %
                          project_info.dmri_config_file)
                    dmri_save_config(
                        dmri_pipeline, project_info.dmri_config_file)
                else:
                    return None
            else:
                print("Create diffusion config file (%s)" %
                      project_info.dmri_config_file)
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
        else:
            dmri_conf_loaded = dmri_load_config_ini(dmri_pipeline, project_info.dmri_config_file)

            if not dmri_conf_loaded:
                return None

        dmri_pipeline.config_file = project_info.dmri_config_file
    else:
        print("Missing diffusion inputs")

    return dmri_inputs_checked, dmri_pipeline


def init_fmri_project(project_info, bids_layout, is_new_project, gui=True):
    """Create and initialize a :class:`fMRIPipelineUI` instance

    Parameters
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` class

    bids_layout : bids.BIDSLayout
        PyBIDS BIDS Layout object describing the BIDS dataset

    is_new_project : bool
        If True, this is a new project which has been never processed
    """
    fmri_pipeline = FMRI_pipeline.fMRIPipelineUI(project_info)

    derivatives_directory = os.path.join(
        project_info.base_directory, 'derivatives')

    if (project_info.subject_session != '') and (project_info.subject_session is not None):
        refresh_folder(derivatives_directory, project_info.subject, fmri_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(derivatives_directory,
                       project_info.subject, fmri_pipeline.input_folders)

    fmri_inputs_checked = fmri_pipeline.check_input(
        layout=bids_layout, gui=gui)
    if fmri_inputs_checked:
        if is_new_project and fmri_pipeline is not None:
            print("Initialize fmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("%s was already existing" % derivatives_directory)
                finally:
                    print("Created directory %s" % derivatives_directory)

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
                    print("Read fMRI config file (%s)" %
                          project_info.fmri_config_file)
                    fmri_load_config_ini(
                        fmri_pipeline, project_info.fmri_config_file)
                else:
                    return None
            else:
                print("Create fMRI config file (%s)" %
                      project_info.fmri_config_file)
                fmri_save_config(fmri_pipeline, project_info.fmri_config_file)
        else:
            fmri_conf_loaded = fmri_load_config_ini(
                fmri_pipeline, project_info.fmri_config_file)

            if not fmri_conf_loaded:
                return None

        fmri_pipeline.config_file = project_info.fmri_config_file
    else:
        print("Missing fmri inputs")

    return fmri_inputs_checked, fmri_pipeline


def init_anat_project(project_info, is_new_project):
    """Create and initialize a :class:`AnatomicalPipelineUI` instance

    Parameters
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` class

    bids_layout : bids.BIDSLayout
        PyBIDS BIDS Layout object describing the BIDS dataset

    is_new_project : bool
        If True, this is a new project which has been never processed
    """
    anat_pipeline = Anatomical_pipeline.AnatomicalPipelineUI(project_info)

    derivatives_directory = os.path.join(project_info.base_directory, 'derivatives')

    if is_new_project and anat_pipeline is not None:  # and dmri_pipelineis not None:
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print("%s was already existing" % derivatives_directory)
            finally:
                print("Created directory %s" % derivatives_directory)

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
        anat_conf_loaded = anat_load_config_ini(
            anat_pipeline, project_info.anat_config_file)

        if not anat_conf_loaded:
            return None

    if (project_info.subject_session != '') and (project_info.subject_session is not None):
        refresh_folder(derivatives_directory, project_info.subject, anat_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(derivatives_directory,
                       project_info.subject, anat_pipeline.input_folders)

    anat_pipeline.config_file = project_info.anat_config_file

    return anat_pipeline


def update_anat_last_processed(project_info, pipeline):
    """Update anatomical pipeline processing information 

    Parameters
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` class

    pipeline : AnatomicalPipelineUI
        Instance of :class:`AnatomicalPipelineUI`
    """
    # last date
    if os.path.exists(os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject)):
        # out_dirs = os.listdir(os.path.join(
        #    project_info.base_directory, 'derivatives', 'cmp', project_info.subject))
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
    if os.path.exists(os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject, 'tmp',
                                   'anatomical_pipeline')):
        stage_dirs = []
        for __, dirnames, _ in os.walk(
                os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject, 'tmp',
                             'anatomical_pipeline')):
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
    """Update diffusion pipeline processing information 

    Parameters
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` class

    pipeline : DiffusionPipelineUI
        Instance of :class:`DiffusionPipelineUI`
    """
    # last date
    if os.path.exists(os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject)):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.base_directory, 'derivatives', 'cmp', project_info.subject))
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
    if os.path.exists(os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject, 'tmp',
                                   'diffusion_pipeline')):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
                os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject, 'tmp',
                             'diffusion_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


def update_fmri_last_processed(project_info, pipeline):
    """Update functional MRI pipeline processing information 

    Parameters
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` class

    pipeline : fMRIPipelineUI
        Instance of :class:`fMRIPipelineUI`
    """
    # last date
    if os.path.exists(os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject)):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.base_directory, 'derivatives', 'cmp', project_info.subject))
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
    if os.path.exists(os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject, 'tmp',
                                   'fMRI_pipeline')):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
                os.path.join(project_info.base_directory, 'derivatives', 'cmp', project_info.subject, 'tmp',
                             'fMRI_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


class CMP_ConfigQualityWindowHandler(Handler):
    """Event handler of the Configurator and Inspector (Quality Control) windows.

    Attributes
    ----------
    project_loaded : traits.Bool
        Indicate if project has been successfully loaded
        (Default: False)

    anat_pipeline : Instance(HasTraits)
        Instance of :class:`AnatomicalPipelineUI` class

    anat_inputs_checked : traits.Bool
        Indicate if anatomical pipeline inputs are available
        (Default: False)

    anat_outputs_checked : traits.Bool
        Indicate if anatomical pipeline outputs are available
        (Default: False)

    anatomical_processed : traits.Bool
        Indicate if anatomical pipeline was run
        (Default: False)

    dmri_pipeline : Instance(HasTraits)
        Instance of :class:`DiffusionPipelineUI` class

    dmri_inputs_checked : traits.Bool
        Indicate if diffusion pipeline inputs are available
        (Default: False)

    dmri_processed : traits.Bool
        Indicate if diffusion pipeline was run
        (Default: False)

    fmri_pipeline : Instance(HasTraits)
        Instance of :class:`fMRIPipelineUI` class

    fmri_inputs_checked : traits.Bool
        Indicate if fMRI pipeline inputs are available
        (Default: False)

    fmri_processed : traits.Bool
        Indicate if fMRI pipeline was run
        (Default: False)
    """

    project_loaded = Bool(False)

    anat_pipeline = Instance(HasTraits)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    anatomical_processed = Bool(False)

    dmri_pipeline = Instance(HasTraits)
    dmri_inputs_checked = Bool(False)
    dmri_processed = Bool(False)

    fmri_pipeline = Instance(HasTraits)
    fmri_inputs_checked = Bool(False)
    fmri_processed = Bool(False)

    def new_project(self, ui_info):
        """Function that creates a new :class:`CMP_Project_InfoUI` instance.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        new_project = gui.CMP_Project_InfoUI()
        np_res = new_project.configure_traits(view='create_view')
        ui_info.ui.context["object"].handler = self

        if np_res and os.path.exists(new_project.base_directory):
            try:
                bids_layout = BIDSLayout(new_project.base_directory)
                new_project.bids_layout = bids_layout
                print(bids_layout)

                for subj in bids_layout.get_subjects():
                    if 'sub-' + str(subj) not in new_project.subjects:
                        new_project.subjects.append('sub-' + str(subj))

                print("Available subjects : ")
                print(new_project.subjects)
                new_project.number_of_subjects = len(new_project.subjects)

                np_res = new_project.configure_traits(view='subject_view')
                print("Selected subject : " + new_project.subject)

                subject = new_project.subject.split('-')[1]
                print("Subject: %s" % subject)

                new_project.subject_sessions = ['']
                new_project.subject_session = ''

                sessions = bids_layout.get(
                    target='session', return_type='id', subject=subject)

                print("Sessions: ")
                print(sessions)

                if len(sessions) > 0:
                    print("Warning: multiple sessions")
                    for ses in sessions:
                        new_project.subject_sessions.append('ses-' + str(ses))
                    np_res = new_project.configure_traits(
                        view='subject_session_view')
                    print("Selected session : " + new_project.subject_session)

            except Exception:
                error(
                    message="Invalid BIDS dataset. Please see documentation for more details.", title="BIDS error")
                return

            self.anat_pipeline = init_anat_project(new_project, True)
            if self.anat_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(
                    bids_layout)
                if anat_inputs_checked:
                    ui_info.ui.context["object"].project_info = new_project
                    self.anat_pipeline.number_of_cores = new_project.number_of_cores
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked

                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_subject_anat_pipeline, 'subject')
                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_session_anat_pipeline, 'subject_session')
                    anat_save_config(
                        self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True

                    ui_info.ui.context["object"].project_info.parcellation_scheme = get_anat_process_detail_ini(
                            new_project, 'parcellation_stage', 'parcellation_scheme')
                    ui_info.ui.context["object"].project_info.freesurfer_subjects_dir = get_anat_process_detail_ini(
                            new_project, 'segmentation_stage', 'freesurfer_subjects_dir')
                    ui_info.ui.context["object"].project_info.freesurfer_subject_id = get_anat_process_detail_ini(
                            new_project, 'segmentation_stage', 'freesurfer_subject_id')
                    
                    dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(
                            new_project, bids_layout, True)
                    if self.dmri_pipeline is not None:
                        if dmri_inputs_checked:
                            self.dmri_pipeline.number_of_cores = new_project.number_of_cores
                            print("number of cores (pipeline): %s" %
                                  self.dmri_pipeline.number_of_cores)
                            self.dmri_pipeline.parcellation_scheme = ui_info.ui.context[
                                "object"].project_info.parcellation_scheme
                            ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context["object"].update_subject_dmri_pipeline, 'subject')
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context["object"].update_session_dmri_pipeline, 'subject_session')
                            dmri_save_config(self.dmri_pipeline,
                                             ui_info.ui.context["object"].project_info.dmri_config_file)
                            self.dmri_inputs_checked = dmri_inputs_checked
                            ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                            self.project_loaded = True
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context["object"].update_diffusion_imaging_model, 'diffusion_imaging_model')

                    fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(
                        new_project, bids_layout, True)
                    if self.fmri_pipeline is not None:
                        if fmri_inputs_checked:
                            self.fmri_pipeline.number_of_cores = new_project.number_of_cores
                            print("number of cores (pipeline): %s" %
                                  self.fmri_pipeline.number_of_cores)
                            self.fmri_pipeline.parcellation_scheme = ui_info.ui.context[
                                "object"].project_info.parcellation_scheme
                            self.fmri_pipeline.subjects_dir = ui_info.ui.context[
                                "object"].project_info.freesurfer_subjects_dir
                            self.fmri_pipeline.subject_id = ui_info.ui.context[
                                "object"].project_info.freesurfer_subject_id
                            ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context["object"].update_subject_fmri_pipeline, 'subject')
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context["object"].update_session_fmri_pipeline, 'subject_session')
                            fmri_save_config(self.fmri_pipeline,
                                             ui_info.ui.context["object"].project_info.fmri_config_file)
                            self.fmri_inputs_checked = fmri_inputs_checked
                            ui_info.ui.context["object"].project_info.fmri_available = self.fmri_inputs_checked
                            self.project_loaded = True

    def load_project(self, ui_info):
        """Function that creates a new :class:`CMP_Project_InfoUI` instance from an existing project.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        loaded_project = gui.CMP_Project_InfoUI()
        np_res = loaded_project.configure_traits(view='open_view')
        ui_info.ui.context["object"].handler = self

        print("Base dir: %s" % loaded_project.base_directory)
        try:
            bids_layout = BIDSLayout(loaded_project.base_directory)
            loaded_project.bids_layout = bids_layout

            loaded_project.subjects = []
            for subj in bids_layout.get_subjects():
                print("sub: %s" % subj)
                if 'sub-' + str(subj) not in loaded_project.subjects:
                    loaded_project.subjects.append('sub-' + str(subj))
            loaded_project.subjects.sort()

            print("Available subjects : ")
            print(loaded_project.subjects)
            loaded_project.number_of_subjects = len(loaded_project.subjects)

        except Exception:
            error(message="Invalid BIDS dataset. Please see documentation for more details.",
                  title="BIDS error")
            return

        self.anat_inputs_checked = False

        print(loaded_project.subjects)

        if np_res and os.path.exists(loaded_project.base_directory):
            sessions = []
            for subj in bids_layout.get_subjects():
                subj_sessions = bids_layout.get(
                    target='session', return_type='id', subject=subj)
                for subj_session in subj_sessions:
                    sessions.append(subj_session)

            print("sessions:")
            print(sessions)

            loaded_project.anat_available_config = []

            for subj in bids_layout.get_subjects():
                subj_sessions = bids_layout.get(
                    target='session', return_type='id', subject=subj)
                if len(subj_sessions) > 0:
                    for subj_session in subj_sessions:
                        config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                                   "sub-%s_ses-%s_anatomical_config.ini" % (subj, subj_session))
                        if os.path.isfile(config_file):
                            loaded_project.anat_available_config.append(
                                "sub-%s_ses-%s" % (subj, subj_session))
                else:
                    config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                               "sub-%s_anatomical_config.ini" % (subj))
                    if os.path.isfile(config_file):
                        loaded_project.anat_available_config.append(
                            "sub-%s" % (subj))
                        print("no session")

            print("loaded_project.anat_available_config : ")
            print(loaded_project.anat_available_config)

            if len(loaded_project.anat_available_config) > 1:
                loaded_project.anat_available_config.sort()
                loaded_project.anat_config_to_load = loaded_project.anat_available_config[0]
                anat_config_selected = loaded_project.configure_traits(
                    view='anat_select_config_to_load')

                if not anat_config_selected:
                    return 0
            else:
                loaded_project.anat_config_to_load = loaded_project.anat_available_config[0]

            print("Anatomical config to load: %s" %
                  loaded_project.anat_config_to_load)
            loaded_project.anat_config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                                           '%s_anatomical_config.ini' % loaded_project.anat_config_to_load)
            print("Anatomical config file: %s" %
                  loaded_project.anat_config_file)

            loaded_project.subject = get_anat_process_detail_ini(
                loaded_project, 'Global', 'subject')
            loaded_project.subject_sessions = ["ses-%s" % s for s in bids_layout.get(target='session', return_type='id',
                                                                                     subject=loaded_project.subject.split('-')[
                                                                                         1])]

            if len(loaded_project.subject_sessions) > 0:

                loaded_project.subject_session = get_anat_process_detail_ini(
                    loaded_project, 'Global', 'subject_session')
                print("Selected session : " + loaded_project.subject_session)
            else:
                loaded_project.subject_sessions = ['']
                loaded_project.subject_session = ''
                print("No session")

            loaded_project.parcellation_scheme = get_anat_process_detail_ini(
                    loaded_project, 'parcellation_stage', 'parcellation_scheme')
            loaded_project.atlas_info = get_anat_process_detail_ini(
                    loaded_project, 'parcellation_stage', 'atlas_info')
            loaded_project.freesurfer_subjects_dir = get_anat_process_detail_ini(
                    loaded_project, 'segmentation_stage', 'freesurfer_subjects_dir')
            loaded_project.freesurfer_subject_id = get_anat_process_detail_ini(
                    loaded_project, 'segmentation_stage', 'freesurfer_subject_id')

            self.anat_pipeline = init_anat_project(loaded_project, False)
            if self.anat_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(
                    bids_layout)
                if anat_inputs_checked:
                    update_anat_last_processed(loaded_project,
                                               self.anat_pipeline)  # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = loaded_project
                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_subject_anat_pipeline, 'subject')
                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_session_anat_pipeline, 'subject_session')
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    ui_info.ui.context["object"].anat_pipeline.number_of_cores = ui_info.ui.context[
                        "object"].project_info.number_of_cores
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(
                        self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True
                    self.anat_outputs_checked, _ = self.anat_pipeline.check_output()
                    print("anat_outputs_checked : %s" %
                          self.anat_outputs_checked)

            loaded_project.dmri_available_config = []

            subjid = loaded_project.subject.split("-")[1]
            subj_sessions = bids_layout.get(
                target='session', return_type='id', subject=subjid)

            if len(subj_sessions) > 0:
                for subj_session in subj_sessions:
                    config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                               "%s_ses-%s_diffusion_config.ini" % (
                                                   loaded_project.subject, subj_session))
                    print("config_file: %s " % config_file)
                    if os.path.isfile(config_file) and subj_session == loaded_project.subject_session.split("-")[1]:
                        loaded_project.dmri_available_config.append(
                            "%s_ses-%s" % (loaded_project.subject, subj_session))
            else:
                config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                           "sub-%s_diffusion_config.ini" % (loaded_project.subject))
                if os.path.isfile(config_file):
                    loaded_project.dmri_available_config.append(
                        "%s" % (loaded_project.subject))
                    print("no session")

            print("loaded_project.dmri_available_config:")
            print(loaded_project.dmri_available_config)

            if len(loaded_project.dmri_available_config) > 1:
                loaded_project.dmri_available_config.sort()
                loaded_project.dmri_config_to_load = loaded_project.dmri_available_config[0]
                dmri_config_selected = loaded_project.configure_traits(
                    view='dmri_select_config_to_load')
                if not dmri_config_selected:
                    return 0
            elif not loaded_project.dmri_available_config:
                loaded_project.dmri_config_to_load = '%s_diffusion' % loaded_project.subject
            else:
                loaded_project.dmri_config_to_load = loaded_project.dmri_available_config[0]

            print("Diffusion config to load: %s" %
                  loaded_project.dmri_config_to_load)
            loaded_project.dmri_config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                                           '%s_diffusion_config.ini' % loaded_project.dmri_config_to_load)
            print("Diffusion config file: %s" %
                  loaded_project.dmri_config_file)

            if os.path.isfile(loaded_project.dmri_config_file):
                print("Load existing diffusion config file")
                loaded_project.process_type = get_dmri_process_detail_ini(
                        loaded_project, 'Global', 'process_type')
                loaded_project.diffusion_imaging_model = get_dmri_process_detail_ini(
                        loaded_project, 'Global', 'diffusion_imaging_model')

                dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(
                    loaded_project, bids_layout, False)
                if self.dmri_pipeline is not None:
                    if dmri_inputs_checked:
                        update_dmri_last_processed(
                            loaded_project, self.dmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_dmri_pipeline, 'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_dmri_pipeline, 'subject_session')
                        self.dmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.dmri_pipeline.atlas_info = loaded_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        ui_info.ui.context["object"].dmri_pipeline.number_of_cores = ui_info.ui.context["object"].project_info.number_of_cores
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                        dmri_save_config(
                            self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                        self.project_loaded = True
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_diffusion_imaging_model, 'diffusion_imaging_model')
            else:
                dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(
                    loaded_project, bids_layout, True)
                print(
                    "No existing config for diffusion pipeline found - Created new diffusion pipeline with default parameters")
                if self.dmri_pipeline is not None:  # and self.dmri_pipeline is not None:
                    if dmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_dmri_pipeline, 'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_dmri_pipeline, 'subject_session')
                        self.dmri_pipeline.number_of_cores = loaded_project.number_of_cores
                        print("number of cores (pipeline): %s" %
                              self.dmri_pipeline.number_of_cores)
                        self.dmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.dmri_pipeline.atlas_info = loaded_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        dmri_save_config(
                            self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                        self.project_loaded = True
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_diffusion_imaging_model, 'diffusion_imaging_model')

            if len(subj_sessions) > 0:
                for subj_session in subj_sessions:
                    config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                               "%s_ses-%s_fMRI_config.ini" % (loaded_project.subject, subj_session))
                    print("config_file: %s " % config_file)
                    if os.path.isfile(config_file) and subj_session == loaded_project.subject_session.split("-")[1]:
                        loaded_project.fmri_available_config.append(
                            "%s_ses-%s" % (loaded_project.subject, subj_session))
            else:
                config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                           "sub-%s_fMRI_config.ini" % (loaded_project.subject))
                if os.path.isfile(config_file):
                    loaded_project.fmri_available_config.append(
                        "sub-%s" % (loaded_project.subject))
                    print("no session")

            print("loaded_project.fmri_available_config:")
            print(loaded_project.fmri_available_config)

            if len(loaded_project.fmri_available_config) > 1:
                loaded_project.fmri_available_config.sort()
                loaded_project.fmri_config_to_load = loaded_project.fmri_available_config[0]
                fmri_config_selected = loaded_project.configure_traits(
                    view='fmri_select_config_to_load')
                if not fmri_config_selected:
                    return 0
            elif not loaded_project.fmri_available_config:
                loaded_project.fmri_config_to_load = '%s_fMRI' % loaded_project.subject
            else:
                loaded_project.fmri_config_to_load = loaded_project.fmri_available_config[0]

            print("fMRI config to load: %s" %
                  loaded_project.fmri_config_to_load)
            loaded_project.fmri_config_file = os.path.join(loaded_project.base_directory, 'derivatives',
                                                           '%s_fMRI_config.ini' % loaded_project.fmri_config_to_load)
            print("fMRI config file: %s" % loaded_project.fmri_config_file)

            if os.path.isfile(loaded_project.fmri_config_file):
                print("Load existing fmri config file")
                loaded_project.process_type = get_fmri_process_detail_ini(
                    loaded_project, 'Global', 'process_type')

                fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(loaded_project, bids_layout, False)
                if self.fmri_pipeline is not None:
                    if fmri_inputs_checked:
                        update_fmri_last_processed(
                            loaded_project, self.fmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_fmri_pipeline, 'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_fmri_pipeline, 'subject_session')
                        self.fmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.fmri_pipeline.atlas_info = loaded_project.atlas_info
                        self.fmri_pipeline.subjects_dir = loaded_project.freesurfer_subjects_dir
                        self.fmri_pipeline.subject_id = loaded_project.freesurfer_subject_id
                        ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        ui_info.ui.context["object"].fmri_pipeline.number_of_cores = ui_info.ui.context[
                            "object"].project_info.number_of_cores
                        self.fmri_inputs_checked = fmri_inputs_checked
                        ui_info.ui.context["object"].project_info.fmri_available = self.fmri_inputs_checked
                        fmri_save_config(
                            self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)
                        self.project_loaded = True
            else:
                fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(loaded_project, bids_layout, True)
                print(
                    "No existing config for fMRI pipeline found - Created new fMRI pipeline with default parameters")
                if self.fmri_pipeline is not None:
                    if fmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_fmri_pipeline, 'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_fmri_pipeline, 'subject_session')
                        self.fmri_pipeline.number_of_cores = loaded_project.number_of_cores
                        print("number of cores (pipeline): %s" %
                              self.fmri_pipeline.number_of_cores)
                        self.fmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.fmri_pipeline.atlas_info = loaded_project.atlas_info
                        self.fmri_pipeline.subjects_dir = loaded_project.freesurfer_subjects_dir
                        self.fmri_pipeline.subject_id = loaded_project.freesurfer_subject_id
                        ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        fmri_save_config(
                            self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)
                        self.fmri_inputs_checked = fmri_inputs_checked
                        ui_info.ui.context["object"].project_info.fmri_available = self.fmri_inputs_checked
                        self.project_loaded = True

    def update_subject_anat_pipeline(self, ui_info):
        """Function that updates attributes of the :class:`AnatomicalPipelineUI` instance.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        ui_info.handler = self

        self.anat_pipeline.subject = ui_info.project_info.subject
        self.anat_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.anat_pipeline.global_conf.subject_session = updated_project.subject_session
            self.anat_pipeline.subject_directory = os.path.join(updated_project.base_directory, updated_project.subject,
                                                                updated_project.subject_session)
            updated_project.anat_config_file = os.path.join(updated_project.base_directory, 'derivatives',
                                                            '%s_%s_anatomical_config.ini' % (
                                                                updated_project.subject, updated_project.subject_session))
        else:
            self.anat_pipeline.global_conf.subject_session = ''
            self.anat_pipeline.subject_directory = os.path.join(
                updated_project.base_directory, updated_project.subject)
            updated_project.anat_config_file = os.path.join(updated_project.base_directory, 'derivatives',
                                                            '%s_anatomical_config.ini' % (updated_project.subject))

        self.anat_pipeline.derivatives_directory = os.path.join(
            updated_project.base_directory, 'derivatives')

        if os.path.isfile(updated_project.anat_config_file):
            print("Existing anatomical config file for subject %s: %s" % (
                updated_project.subject, updated_project.anat_config_file))

            updated_project.parcellation_scheme = get_anat_process_detail_ini(
                    updated_project, 'parcellation_stage', 'parcellation_scheme')
            updated_project.atlas_info = get_anat_process_detail_ini(
                    updated_project, 'parcellation_stage', 'atlas_info')
            updated_project.freesurfer_subjects_dir = get_anat_process_detail_ini(
                    updated_project, 'segmentation_stage', 'freesurfer_subjects_dir')
            updated_project.freesurfer_subject_id = get_anat_process_detail_ini(
                    updated_project, 'segmentation_stage', 'freesurfer_subject_id')

            self.anat_pipeline = init_anat_project(updated_project, False)
            if self.anat_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(
                    bids_layout)
                if anat_inputs_checked:
                    update_anat_last_processed(updated_project,
                                               self.anat_pipeline)  # Not required as the project is new, so no update should be done on processing status
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_anat_pipeline, 'subject')
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_anat_pipeline, 'subject_session')
                    ui_info.anat_pipeline = self.anat_pipeline
                    ui_info.anat_pipeline.number_of_cores = ui_info.project_info.number_of_cores
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline,
                                     ui_info.project_info.anat_config_file)
                    self.project_loaded = True
                    self.anat_outputs_checked, msg = self.anat_pipeline.check_output()
                    print("anat_outputs_checked : %s" % self.anat_outputs_checked)

        else:
            print("Unprocessed anatomical data for subject %s" % updated_project.subject)
            self.anat_pipeline = init_anat_project(updated_project, True)
            if self.anat_pipeline is not None:  # and self.dmri_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(
                    bids_layout)
                if anat_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_anat_pipeline, 'subject')
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_anat_pipeline, 'subject_session')
                    self.anat_pipeline.number_of_cores = updated_project.number_of_cores
                    ui_info.anat_pipeline = self.anat_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline,
                                     ui_info.project_info.anat_config_file)
                    self.project_loaded = True

            ui_info.project_info.parcellation_scheme = get_anat_process_detail_ini(
                    updated_project, 'parcellation_stage', 'parcellation_scheme')
            ui_info.project_info.freesurfer_subjects_dir = get_anat_process_detail_ini(
                    updated_project, 'segmentation_stage', 'freesurfer_subjects_dir')
            ui_info.project_info.freesurfer_subject_id = get_anat_process_detail_ini(
                    updated_project, 'segmentation_stage', 'freesurfer_subject_id')

        return ui_info

    def update_subject_dmri_pipeline(self, ui_info):
        """Function that updates attributes of the :class:`DiffusionPipelineUI` instance.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        self.dmri_pipeline.subject = ui_info.project_info.subject
        self.dmri_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.dmri_pipeline.global_conf.subject_session = updated_project.subject_session
            self.dmri_pipeline.subject_directory = os.path.join(updated_project.base_directory, updated_project.subject,
                                                                updated_project.subject_session)
            updated_project.dmri_config_file = os.path.join(updated_project.base_directory, 'derivatives',
                                                            '%s_%s_diffusion_config.ini' % (
                                                                updated_project.subject, updated_project.subject_session))
        else:
            self.dmri_pipeline.global_conf.subject_session = ''
            self.dmri_pipeline.subject_directory = os.path.join(
                updated_project.base_directory, updated_project.subject)
            updated_project.dmri_config_file = os.path.join(updated_project.base_directory, 'derivatives',
                                                            '%s_diffusion_config.ini' % (updated_project.subject))

        self.dmri_pipeline.derivatives_directory = os.path.join(
            updated_project.base_directory, 'derivatives')

        if os.path.isfile(updated_project.dmri_config_file):
            print("Load existing diffusion config file")
            updated_project.process_type = get_dmri_process_detail_ini(
                    updated_project, 'Global', 'process_type')
            updated_project.diffusion_imaging_model = get_dmri_process_detail_ini(
                    updated_project, 'diffusion_stage', 'diffusion_imaging_model')

            dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(updated_project, bids_layout, False)
            if self.dmri_pipeline is not None:  # and self.dmri_pipeline is not None:
                if dmri_inputs_checked:
                    update_dmri_last_processed(
                        updated_project, self.dmri_pipeline)
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_dmri_pipeline, 'subject')
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_dmri_pipeline, 'subject_session')
                    self.dmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.dmri_pipeline.atlas_info = updated_project.atlas_info
                    ui_info.dmri_pipeline = self.dmri_pipeline
                    ui_info.dmri_pipeline.number_of_cores = ui_info.project_info.number_of_cores
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.project_info.dmri_available = self.dmri_inputs_checked
                    dmri_save_config(self.dmri_pipeline,
                                     ui_info.project_info.dmri_config_file)
                    self.project_loaded = True
                    ui_info.project_info.on_trait_change(ui_info.update_diffusion_imaging_model,
                                                         'diffusion_imaging_model')
        else:
            dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(updated_project, bids_layout, True)
            print("No existing config for diffusion pipeline found - Created new diffusion pipeline with default parameters")
            if self.dmri_pipeline is not None:  # and self.dmri_pipeline is not None:
                if dmri_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_dmri_pipeline, 'subject')
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_dmri_pipeline, 'subject_session')
                    self.dmri_pipeline.number_of_cores = updated_project.number_of_cores
                    print("number of cores (pipeline): %s" %
                          self.dmri_pipeline.number_of_cores)
                    self.dmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.dmri_pipeline.atlas_info = updated_project.atlas_info
                    ui_info.dmri_pipeline = self.dmri_pipeline
                    dmri_save_config(self.dmri_pipeline,
                                     ui_info.project_info.dmri_config_file)
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.project_info.dmri_available = self.dmri_inputs_checked
                    self.project_loaded = True
                    ui_info.project_info.on_trait_change(ui_info.update_diffusion_imaging_model,
                                                         'diffusion_imaging_model')

        return ui_info

    def update_subject_fmri_pipeline(self, ui_info):
        """Function that updates attributes of the :class:`fMRIPipelineUI` instance.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        ui_info.handler = self

        print(ui_info)
        print(ui_info.project_info)

        self.fmri_pipeline.subject = ui_info.project_info.subject
        self.fmri_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.fmri_pipeline.global_conf.subject_session = updated_project.subject_session
            self.fmri_pipeline.subject_directory = os.path.join(updated_project.base_directory,
                                                                ui_info.project_info.subject,
                                                                updated_project.subject_session)
            updated_project.fmri_config_file = os.path.join(updated_project.base_directory, 'derivatives',
                                                            '%s_%s_fMRI_config.ini' % (
                                                                updated_project.subject, updated_project.subject_session))
        else:
            self.fmri_pipeline.global_conf.subject_session = ''
            self.fmri_pipeline.subject_directory = os.path.join(updated_project.base_directory,
                                                                ui_info.project_info.subject)
            updated_project.fmri_config_file = os.path.join(updated_project.base_directory, 'derivatives',
                                                            '%s_fMRI_config.ini' % (updated_project.subject))

        self.fmri_pipeline.derivatives_directory = os.path.join(
            updated_project.base_directory, 'derivatives')

        print("fMRI config file loaded/created : %s" %
              updated_project.fmri_config_file)

        if os.path.isfile(updated_project.fmri_config_file):
            print("Load existing fMRI config file for subject %s" %
                  updated_project.subject)
            updated_project.process_type = get_fmri_process_detail_ini(
                updated_project, 'Global', 'process_type')

            fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(
                updated_project, bids_layout, False)
            if self.fmri_pipeline is not None:
                if fmri_inputs_checked:
                    update_fmri_last_processed(
                        updated_project, self.fmri_pipeline)
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_fmri_pipeline, 'subject')
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_fmri_pipeline, 'subject_session')
                    self.fmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.fmri_pipeline.atlas_info = updated_project.atlas_info
                    self.fmri_pipeline.subjects_dir = updated_project.freesurfer_subjects_dir
                    self.fmri_pipeline.subject_id = updated_project.freesurfer_subject_id
                    ui_info.fmri_pipeline = self.fmri_pipeline

                    ui_info.fmri_pipeline.number_of_cores = ui_info.project_info.number_of_cores
                    self.fmri_inputs_checked = fmri_inputs_checked
                    ui_info.project_info.fmri_available = self.fmri_inputs_checked
                    fmri_save_config(self.fmri_pipeline,
                                     ui_info.project_info.fmri_config_file)
                    self.project_loaded = True
        else:
            fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(
                updated_project, bids_layout, True)
            print("No existing config for fMRI pipeline found but available fMRI data- Created new fMRI pipeline with default parameters")
            if self.fmri_pipeline is not None:
                if fmri_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_fmri_pipeline, 'subject')
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_fmri_pipeline, 'subject_session')
                    self.fmri_pipeline.number_of_cores = updated_project.number_of_cores
                    print("number of cores (pipeline): %s" %
                          self.fmri_pipeline.number_of_cores)
                    self.fmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.fmri_pipeline.atlas_info = updated_project.atlas_info
                    self.fmri_pipeline.subjects_dir = updated_project.freesurfer_subjects_dir
                    self.fmri_pipeline.subject_id = updated_project.freesurfer_subject_id
                    ui_info.fmri_pipeline = self.fmri_pipeline
                    fmri_save_config(self.fmri_pipeline,
                                     ui_info.project_info.fmri_config_file)
                    self.fmri_inputs_checked = fmri_inputs_checked
                    ui_info.project_info.fmri_available = self.fmri_inputs_checked
                    self.project_loaded = True

        return ui_info

    @classmethod
    def show_bidsapp_window(ui_info):
        """Function that shows the BIDS App Interface Window.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with this handler
        """
        print("Show BIDS App interface")
        ui_info.ui.context["object"].show_bidsapp_interface()

    @classmethod
    def save_anat_config_file(self, ui_info):
        """Function that saves the anatomical pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="save as",
                            default_filename=os.path.join(ui_info.ui.context["object"].project_info.base_directory,
                                                          'code', 'ref_anatomical_config.ini'))
        dialog.open()
        if dialog.return_code == OK:
            anat_save_config(ui_info.ui.context["object"].anat_pipeline,
                             ui_info.ui.context["object"].project_info.anat_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.anat_config_file:
                shutil.copy(
                    ui_info.ui.context["object"].project_info.anat_config_file, dialog.path)

    def load_anat_config_file(self, ui_info):
        """Function that loads the anatomical pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*anatomical_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.anat_config_file:
                shutil.copy(
                    dialog.path, ui_info.ui.context["object"].project_info.anat_config_file)
            anat_load_config_ini(
                self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
            # TODO: load_config (anat_ or dmri_ ?)

    @classmethod
    def save_dmri_config_file(self, ui_info):
        """Function that saves the diffusion pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="save as",
                            default_filename=os.path.join(ui_info.ui.context["object"].project_info.base_directory,
                                                          'code', 'ref_diffusion_config.ini'))
        dialog.open()
        if dialog.return_code == OK:
            dmri_save_config(ui_info.ui.context["object"].dmri_pipeline,
                             ui_info.ui.context["object"].project_info.dmri_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.dmri_config_file:
                shutil.copy(
                    ui_info.ui.context["object"].project_info.dmri_config_file, dialog.path)

    def load_dmri_config_file(self, ui_info):
        """Function that loads the diffusion pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*diffusion_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.dmri_config_file:
                shutil.copy(
                    dialog.path, ui_info.ui.context["object"].project_info.dmri_config_file)
            dmri_load_config_ini(
                self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)

    @classmethod
    def save_fmri_config_file(self, ui_info):
        """Function that saves the fMRI pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="save as",
                            default_filename=os.path.join(ui_info.ui.context["object"].project_info.base_directory,
                                                          'code', 'ref_fMRI_config.ini'))
        dialog.open()
        if dialog.return_code == OK:
            fmri_save_config(ui_info.ui.context["object"].fmri_pipeline,
                             ui_info.ui.context["object"].project_info.fmri_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.fmri_config_file:
                shutil.copy(
                    ui_info.ui.context["object"].project_info.fmri_config_file, dialog.path)

    def load_fmri_config_file(self, ui_info):
        """Function that loads the fMRI pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*diffusion_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.fmri_config_file:
                shutil.copy(
                    dialog.path, ui_info.ui.context["object"].project_info.fmri_config_file)
            fmri_load_config_ini(
                self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)


class CMP_MainWindowHandler(Handler):
    """Event handler of the Configurator and Inspector (Quality Control) windows.

    Attributes
    ----------
    project_loaded : traits.Bool
        Indicate if project has been successfully loaded
        (Default: False)

    anat_pipeline : Instance(HasTraits)
        Instance of :class:`AnatomicalPipelineUI` class

    anat_inputs_checked : traits.Bool
        Indicate if anatomical pipeline inputs are available
        (Default: False)

    anat_outputs_checked : traits.Bool
        Indicate if anatomical pipeline outputs are available
        (Default: False)

    anatomical_processed : traits.Bool
        Indicate if anatomical pipeline was run
        (Default: False)

    dmri_pipeline : Instance(HasTraits)
        Instance of :class:`DiffusionPipelineUI` class

    dmri_inputs_checked : traits.Bool
        Indicate if diffusion pipeline inputs are available
        (Default: False)

    dmri_processed : traits.Bool
        Indicate if diffusion pipeline was run
        (Default: False)

    fmri_pipeline : Instance(HasTraits)
        Instance of :class:`fMRIPipelineUI` class

    fmri_inputs_checked : traits.Bool
        Indicate if fMRI pipeline inputs are available
        (Default: False)

    fmri_processed : traits.Bool
        Indicate if fMRI pipeline was run
        (Default: False)
    """

    project_loaded = Bool(False)

    anat_pipeline = Instance(HasTraits)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    anatomical_processed = Bool(False)

    dmri_pipeline = Instance(HasTraits)
    dmri_inputs_checked = Bool(False)
    dmri_processed = Bool(False)

    fmri_pipeline = Instance(HasTraits)
    fmri_inputs_checked = Bool(False)
    fmri_processed = Bool(False)

    def load_dataset(self, ui_info, debug=True):
        """Function that creates a new :class:`CMP_Project_InfoUI` instance from an existing project.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        loaded_project = gui.CMP_Project_InfoUI()
        np_res = loaded_project.configure_traits(view='open_view')
        loaded_project.output_directory = os.path.join(
            loaded_project.base_directory, 'derivatives')

        if loaded_project.creation_mode == "Install Datalad BIDS dataset":
            datalad_is_available = is_tool('datalad')

            if datalad_is_available:
                print('>>> Datalad dataset installation...')
                if loaded_project.install_datalad_dataset_via_ssh:
                    if loaded_project.ssh_pwd != '':
                        os.environ['REMOTEUSERPWD'] = loaded_project.ssh_pwd
                        cmd = 'datalad install -D "Dataset {} (remote:{}) installed on {}" -s ssh://{}:$REMOTEUSERPWD@{}:{} {}'.format(
                            loaded_project.datalad_dataset_path,
                            loaded_project.ssh_remote,
                            loaded_project.base_directory,
                            loaded_project.ssh_user,
                            loaded_project.ssh_remote,
                            loaded_project.datalad_dataset_path,
                            loaded_project.base_directory)
                    else:
                        cmd = 'datalad install -D "Dataset {} (remote:{}) installed on {}" -s ssh://{}@{}:{} {}'.format(
                            loaded_project.datalad_dataset_path,
                            loaded_project.ssh_remote,
                            loaded_project.base_directory,
                            loaded_project.ssh_user,
                            loaded_project.ssh_remote,
                            loaded_project.datalad_dataset_path,
                            loaded_project.base_directory)
                    try:
                        print('... cmd: {}'.format(cmd))
                        core.run(cmd, env={}, cwd=os.path.abspath(
                            loaded_project.base_directory))
                        del os.environ['REMOTEUSERPWD']
                    except Exception:
                        print("    ERROR: Failed to install datalad dataset via ssh")
                        del os.environ['REMOTEUSERPWD']
                else:
                    cmd = 'datalad install -D "Dataset {} installed on {}" -s {} {}'.format(
                        loaded_project.datalad_dataset_path,
                        loaded_project.base_directory,
                        loaded_project.datalad_dataset_path,
                        loaded_project.base_directory)
                    try:
                        print('... cmd: {}'.format(cmd))
                        core.run(cmd, env={}, cwd=os.path.abspath(
                            loaded_project.base_directory))
                    except Exception:
                        print("    ERROR: Failed to install datalad dataset via ssh")
            else:
                print('    ERROR: Datalad is not installed!')

            # Install dataset via datalad
            # datalad install -s ssh://tourbier@155.105.77.64:/home/tourbier/Data/ds-newtest /media/localadmin/HagmannHDD/Seb/ds-newtest5
            #

        t1_available = False
        t2_available = False
        diffusion_available = False
        fmri_available = False

        # print("Local BIDS dataset: %s" % loaded_project.base_directory)
        if np_res:
            try:
                bids_layout = BIDSLayout(loaded_project.base_directory)
                print(bids_layout)

                loaded_project.bids_layout = bids_layout

                loaded_project.subjects = []
                for subj in bids_layout.get_subjects():
                    if debug:
                        print("sub: %s" % subj)
                    if 'sub-' + str(subj) not in loaded_project.subjects:
                        loaded_project.subjects.append('sub-' + str(subj))
                # loaded_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
                loaded_project.subjects.sort()

                print("Available subjects : ")
                print(loaded_project.subjects)
                loaded_project.number_of_subjects = len(loaded_project.subjects)

                loaded_project.subject = loaded_project.subjects[0]
                if debug:
                    print(loaded_project.subject)

                subject = loaded_project.subject.split('-')[1]

                sessions = bids_layout.get(
                    target='session', return_type='id', subject=subject)

                if debug:
                    print("Sessions: ")
                    print(sessions)

                if len(sessions) > 0:
                    loaded_project.subject_sessions = [
                        'ses-{}'.format(sessions[0])]
                    loaded_project.subject_session = 'ses-{}'.format(sessions[0])
                else:
                    loaded_project.subject_sessions = ['']
                    loaded_project.subject_session = ''

                if len(sessions) > 0:
                    print(
                        '    ... Check for available input modalities in the first session...')

                    import bids
                    print(bids.__version__)
                    print(subject)
                    print(sessions[0])
                    query_files = [f.filename for f in bids_layout.get(subject=subject, session=sessions[0], suffix='bold',
                                                                       extensions=['nii', 'nii.gz'])]
                    print(query_files)
                    if len(query_files) > 0:
                        if debug:
                            print("BOLD available: {}".format(query_files))
                        fmri_available = True

                    query_files = [f.filename for f in bids_layout.get(subject=subject, session=sessions[0], suffix='T1w',
                                                                       extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("T1w available: {}".format(query_files))
                        t1_available = True

                    query_files = [f.filename for f in bids_layout.get(subject=subject, session=sessions[0], suffix='T2w',
                                                                       extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("T2w available: {}".format(query_files))
                        t2_available = True

                    query_files = [f.filename for f in bids_layout.get(subject=subject, session=sessions[0], suffix='dwi',
                                                                       extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("DWI available: {}".format(query_files))
                        diffusion_available = True

                else:
                    print('    ... Check for available input modalities...')
                    query_files = [f.filename for f in
                                   bids_layout.get(subject=subject, suffix='T1w', extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("T1w available: {}".format(query_files))
                        t1_available = True

                    query_files = [f.filename for f in
                                   bids_layout.get(subject=subject, suffix='T2w', extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("T2w available: {}".format(query_files))
                        t2_available = True

                    query_files = [f.filename for f in
                                   bids_layout.get(subject=subject, suffix='dwi', extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("DWI available: {}".format(query_files))
                        diffusion_available = True

                    query_files = [f.filename for f in
                                   bids_layout.get(subject=subject, suffix='bold', extensions=['nii', 'nii.gz'])]
                    if len(query_files) > 0:
                        if debug:
                            print("BOLD available: {}".format(query_files))
                        fmri_available = True

            except Exception:
                error(message="Invalid BIDS dataset. Please see documentation for more details.",
                      title="BIDS error")
                return

            ui_info.ui.context["object"].project_info = loaded_project

            anat_inputs_checked = False
            if t1_available:
                anat_inputs_checked = True

            dmri_inputs_checked = False
            if t1_available and diffusion_available:
                dmri_inputs_checked = True

            if t2_available:
                print('T2 available')

            fmri_inputs_checked = False
            if t1_available and fmri_available:
                fmri_inputs_checked = True
                print('fmri input check : {}'.format(fmri_inputs_checked))

            self.anat_inputs_checked = anat_inputs_checked
            self.dmri_inputs_checked = dmri_inputs_checked
            self.fmri_inputs_checked = fmri_inputs_checked

            if anat_inputs_checked:

                self.anat_pipeline = Anatomical_pipeline.AnatomicalPipelineUI(
                    loaded_project)
                self.anat_pipeline.number_of_cores = loaded_project.number_of_cores

                code_directory = os.path.join(
                    loaded_project.base_directory, 'code')

                anat_config_file = os.path.join(
                    loaded_project.base_directory, 'code', 'ref_anatomical_config.ini')
                loaded_project.anat_config_file = anat_config_file

                # and dmri_pipelineis not None:
                if self.anat_pipeline is not None and not os.path.isfile(anat_config_file):
                    if not os.path.exists(code_directory):
                        try:
                            os.makedirs(code_directory)
                        except os.error:
                            print("%s was already existing" % code_directory)
                        finally:
                            print("Created directory %s" % code_directory)

                    anat_save_config(self.anat_pipeline,
                                     loaded_project.anat_config_file)
                    print(">> Created reference anatomical config file :  %s" %
                          loaded_project.anat_config_file)

                else:
                    print(">> Loaded reference anatomical config file :  %s" %
                          loaded_project.anat_config_file)
                    # if datalad_is_available:
                    #     print('... Datalad get anatomical config file : {}'.format(loaded_project.anat_config_file))
                    #     cmd = 'datalad run -m "Get reference anatomical config file" bash -c "datalad get code/ref_anatomical_config.ini"'
                    #     try:
                    #         print('... cmd: {}'.format(cmd))
                    #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                    #     except Exception:
                    #         print("    ERROR: Failed to get file")

                    anat_load_config_ini(
                        self.anat_pipeline, loaded_project.anat_config_file)

                self.anat_pipeline.config_file = loaded_project.anat_config_file

                ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                loaded_project.t1_available = self.anat_inputs_checked

                loaded_project.parcellation_scheme = get_anat_process_detail_ini(
                        loaded_project, 'parcellation_stage', 'parcellation_scheme')
                loaded_project.freesurfer_subjects_dir = get_anat_process_detail_ini(
                        loaded_project, 'segmentation_stage', 'freesurfer_subjects_dir')
                loaded_project.freesurfer_subject_id = get_anat_process_detail_ini(
                        loaded_project, 'segmentation_stage', 'freesurfer_subject_id')

                ui_info.ui.context["object"].project_info = loaded_project

                self.project_loaded = True

                if dmri_inputs_checked:
                    self.dmri_pipeline = Diffusion_pipeline.DiffusionPipelineUI(
                        loaded_project)
                    self.dmri_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.dmri_pipeline.parcellation_scheme = ui_info.ui.context[
                        "object"].project_info.parcellation_scheme

                    code_directory = os.path.join(
                        loaded_project.base_directory, 'code')

                    dmri_config_file = os.path.join(
                        code_directory, 'ref_diffusion_config.ini')
                    loaded_project.dmri_config_file = dmri_config_file

                    self.dmri_pipeline.config_file = dmri_config_file

                    if not os.path.isfile(dmri_config_file) and self.dmri_pipeline is not None:

                        # Look for diffusion acquisition model information from filename (acq-*)
                        if loaded_project.subject_session != '':
                            session = loaded_project.subject_session.split('-')[1]
                            diffusion_imaging_models = [i for i in
                                                        bids_layout.get(subject=subject, session=session, suffix='dwi',
                                                                        target='acquisition', return_type='id',
                                                                        extensions=['nii', 'nii.gz'])]
                            if debug:
                                print('DIFFUSION IMAGING MODELS : {}'.format(
                                    diffusion_imaging_models))

                            if len(diffusion_imaging_models) > 0:
                                if len(diffusion_imaging_models) > 1:
                                    loaded_project.dmri_bids_acqs = diffusion_imaging_models
                                    loaded_project.configure_traits(
                                        view='dmri_bids_acq_view')
                                else:
                                    loaded_project.dmri_bids_acqs = [
                                        '{}'.format(diffusion_imaging_models[0])]
                                    loaded_project.dmri_bids_acq = diffusion_imaging_models[0]

                                if ('dsi' in loaded_project.dmri_bids_acq) or ('DSI' in loaded_project.dmri_bids_acq):
                                    loaded_project.diffusion_imaging_model = 'DSI'
                                elif ('dti' in loaded_project.dmri_bids_acq) or ('DTI' in loaded_project.dmri_bids_acq):
                                    loaded_project.diffusion_imaging_model = 'DTI'
                                elif ('hardi' in loaded_project.dmri_bids_acq) or ('HARDI' in loaded_project.dmri_bids_acq):
                                    loaded_project.diffusion_imaging_model = 'HARDI'
                                else:
                                    loaded_project.diffusion_imaging_model = 'DTI'
                            else:
                                loaded_project.dmri_bids_acqs = ['']
                                loaded_project.dmri_bids_acq = ''
                                loaded_project.configure_traits(
                                    view='diffusion_imaging_model_select_view')

                            files = [f.filename for f in bids_layout.get(subject=subject, session=session, suffix='dwi',
                                                                         extensions=['nii', 'nii.gz'])]

                            if debug:
                                print('****************************************')
                                print()
                                print('****************************************')
                                print(files)
                                print('****************************************')

                            if (loaded_project.dmri_bids_acq != ''):
                                for file in files:
                                    if (loaded_project.dmri_bids_acq in file):
                                        dwi_file = file
                                        print('Loaded DWI file: {}'.format(dwi_file))
                                        break
                            else:
                                dwi_file = files[0]
                        else:
                            diffusion_imaging_models = [i for i in
                                                        bids_layout.get(subject=subject, suffix='dwi', target='acquisition',
                                                                        return_type='id', extensions=['nii', 'nii.gz'])]

                            if len(diffusion_imaging_models) > 0:
                                if len(diffusion_imaging_models) > 1:
                                    loaded_project.dmri_bids_acqs = diffusion_imaging_models
                                    loaded_project.configure_traits(
                                        view='dmri_bids_acq_view')
                                else:
                                    loaded_project.dmri_bids_acq = diffusion_imaging_models[0]

                                if ('dsi' in loaded_project.dmri_bids_acq) or ('DSI' in loaded_project.dmri_bids_acq):
                                    loaded_project.diffusion_imaging_model = 'DSI'
                                elif ('dti' in loaded_project.dmri_bids_acq) or ('DTI' in loaded_project.dmri_bids_acq):
                                    loaded_project.diffusion_imaging_model = 'DTI'
                                elif ('hardi' in loaded_project.dmri_bids_acq) or ('HARDI' in loaded_project.dmri_bids_acq):
                                    loaded_project.diffusion_imaging_model = 'HARDI'
                                else:
                                    loaded_project.diffusion_imaging_model = 'DTI'
                            else:
                                loaded_project.dmri_bids_acqs = ['']
                                loaded_project.dmri_bids_acq = ''
                                loaded_project.configure_traits(
                                    view='diffusion_imaging_model_select_view')

                        self.dmri_pipeline.diffusion_imaging_model = loaded_project.diffusion_imaging_model
                        self.dmri_pipeline.global_conf.diffusion_imaging_model = loaded_project.diffusion_imaging_model
                        self.dmri_pipeline.global_conf.dmri_bids_acq = loaded_project.dmri_bids_acq
                        self.dmri_pipeline.stages[
                            "Diffusion"].diffusion_imaging_model = loaded_project.diffusion_imaging_model
                        dmri_save_config(self.dmri_pipeline, dmri_config_file)
                        print(">> Created reference diffusion config file :  %s" %
                              loaded_project.dmri_config_file)
                    else:
                        print(">> Loaded reference diffusion config file :  %s" %
                              loaded_project.dmri_config_file)

                        # if datalad_is_available:
                        #     print('... Datalad get reference diffusion config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference anatomical config file" bash -c "datalad get code/ref_diffusion_config.ini"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        dmri_load_config_ini(
                            self.dmri_pipeline, loaded_project.dmri_config_file)
                        # TODO: check if diffusion imaging model (DSI/DTI/HARDI) is correct/valid.

                    ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    loaded_project.dmri_available = self.dmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True

                if fmri_inputs_checked:
                    self.fmri_pipeline = FMRI_pipeline.fMRIPipelineUI(
                        loaded_project)
                    self.fmri_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.fmri_pipeline.parcellation_scheme = ui_info.ui.context[
                        "object"].project_info.parcellation_scheme

                    self.fmri_pipeline.stages["Registration"].pipeline_mode = 'fMRI'
                    self.fmri_pipeline.stages["Registration"].registration_mode = 'FSL (Linear)'
                    self.fmri_pipeline.stages["Registration"].registration_mode_trait = [
                        'FSL (Linear)', 'BBregister (FS)']

                    code_directory = os.path.join(
                        loaded_project.base_directory, 'code')

                    fmri_config_file = os.path.join(
                        code_directory, 'ref_fMRI_config.ini')
                    loaded_project.fmri_config_file = fmri_config_file

                    self.fmri_pipeline.config_file = fmri_config_file

                    if not os.path.isfile(fmri_config_file) and self.fmri_pipeline is not None:
                        fmri_save_config(self.fmri_pipeline, fmri_config_file)
                        print("Created reference fMRI config file :  %s" %
                              loaded_project.fmri_config_file)
                    else:
                        print("Loaded reference fMRI config file :  %s" %
                              loaded_project.fmri_config_file)

                        # if datalad_is_available:
                        #     print('... Datalad get reference fMRI config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference fMRI config file" bash -c "datalad get code/ref_fMRI_config.ini"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        fmri_load_config_ini(
                            self.fmri_pipeline, loaded_project.fmri_config_file)

                    ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                    loaded_project.fmri_available = self.fmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True


class CMP_BIDSAppWindowHandler(Handler):
    """Event handler of the BIDS App Interface window.

    Attributes
    ----------
    docker_process : subprocess.Popen
        Instance of ``subprocess.Popen`` where BIDS App docker image is run
    """

    docker_process = Instance(Popen)

    def check_settings(self, ui_info):
        """Function that checks if all parameters are properly set before execution of the BIDS App.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        ui_info.ui.context["object"].settings_checked = True
        ui_info.ui.context["object"].handler = self

        if os.path.isdir(ui_info.ui.context["object"].bids_root):
            print("BIDS root directory : {}".format(
                ui_info.ui.context["object"].bids_root))
        else:
            print("Error: BIDS root invalid!")
            ui_info.ui.context["object"].settings_checked = False

        if os.path.isfile(ui_info.ui.context["object"].anat_config):
            print("Anatomical configuration file : {}".format(
                ui_info.ui.context["object"].anat_config))
        else:
            print("Error: Configuration file for anatomical pipeline not existing!")
            ui_info.ui.context["object"].settings_checked = False

        if os.path.isfile(ui_info.ui.context["object"].dmri_config):
            print("Diffusion configuration file : {}".format(
                ui_info.ui.context["object"].dmri_config))
        else:
            print("Warning: Configuration file for diffusion pipeline not existing!")

        if os.path.isfile(ui_info.ui.context["object"].fmri_config):
            print("fMRI configuration file : {}".format(
                ui_info.ui.context["object"].fmri_config))
        else:
            print("Warning: Configuration file for fMRI pipeline not existing!")

        if os.path.isfile(ui_info.ui.context["object"].fs_license):
            print("Freesurfer license : {}".format(
                ui_info.ui.context["object"].fs_license))
        else:
            print("Error: Invalid Freesurfer license ({})!".format(
                ui_info.ui.context["object"].fs_license))
            ui_info.ui.context["object"].settings_checked = False

        print("Valid inputs for BIDS App : {}".format(
            ui_info.ui.context["object"].settings_checked))
        print("Docker running ? {}".format(
            ui_info.ui.context["object"].docker_running))
        return True

    @classmethod
    def start_bidsapp_process(ui_info, participant_label):
        """Function that runs the BIDS App on a single subject.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with this handler
        participant_label : string
            Label of the participant / subject (e.g. ``"01"``, no "sub-" prefix)
        """
        cmd = ['docker', 'run', '-it', '--rm',
               '-v', '{}:/bids_dataset'.format(
                   ui_info.ui.context["object"].bids_root),
               '-v', '{}/derivatives:/outputs'.format(
                   ui_info.ui.context["object"].bids_root),
               # '-v', '{}:/bids_dataset/derivatives/freesurfer/fsaverage'.format(ui_info.ui.context["object"].fs_average),
               '-v', '{}:/opt/freesurfer/license.txt'.format(
                   ui_info.ui.context["object"].fs_license),
               '-v', '{}:/code/ref_anatomical_config.ini'.format(ui_info.ui.context["object"].anat_config)]

        if ui_info.ui.context["object"].run_dmri_pipeline:
            cmd.append('-v')
            cmd.append(
                '{}:/code/ref_diffusion_config.ini'.format(ui_info.ui.context["object"].dmri_config))

        if ui_info.ui.context["object"].run_fmri_pipeline:
            cmd.append('-v')
            cmd.append(
                '{}:/code/ref_fMRI_config.ini'.format(ui_info.ui.context["object"].fmri_config))

        cmd.append('-u')
        cmd.append('{}:{}'.format(os.geteuid(), os.getegid()))

        cmd.append('sebastientourbier/connectomemapper-bidsapp:latest')
        cmd.append('/bids_dataset')
        cmd.append('/outputs')
        cmd.append('participant')

        cmd.append('--participant_label')
        cmd.append('{}'.format(participant_label))

        cmd.append('--anat_pipeline_config')
        cmd.append('/code/ref_anatomical_config.ini')

        if ui_info.ui.context["object"].run_dmri_pipeline:
            cmd.append('--dwi_pipeline_config')
            cmd.append('/code/ref_diffusion_config.ini')

        if ui_info.ui.context["object"].run_fmri_pipeline:
            cmd.append('--func_pipeline_config')
            cmd.append('/code/ref_fMRI_config.ini')

        print(cmd)

        log_filename = os.path.join(ui_info.ui.context["object"].bids_root, 'derivatives/cmp',
                                    'sub-{}_log-cmpbidsapp.txt'.format(participant_label))

        with open(log_filename, 'w+') as log:
            proc = Popen(cmd, stdout=log, stderr=log)

        return proc

    @classmethod
    def manage_bidsapp_procs(self, proclist):
        """Function that managed the parallelized BIDS App Popen process.

        Parameters
        ----------
        proclist
            List of ``Popen`` processes running the BIDS App on a single subject
        """
        for proc in proclist:
            if proc.poll() is not None:
                proclist.remove(proc)

    def start_bids_app(self, ui_info):
        """Main function that runs the BIDS App on a set or sub-set of participants.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with this handler
        """
        print("Start BIDS App")

        maxprocs = multiprocessing.cpu_count()
        processes = []

        ui_info.ui.context["object"].docker_running = True

        # fix_dataset_directory_in_pickles(
        #     local_dir=ui_info.ui.context["object"].bids_root, mode='bidsapp')

        for label in ui_info.ui.context["object"].list_of_subjects_to_be_processed:
            while len(processes) == maxprocs:
                self.manage_bidsapp_procs(processes)

            proc = self.start_bidsapp_process(ui_info, label=label)
            processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        # fix_dataset_directory_in_pickles(
        #     local_dir=ui_info.ui.context["object"].bids_root, mode='local')

        print('Processing with BIDS App Finished')

        ui_info.ui.context["object"].docker_running = False

        return True

    @classmethod
    def stop_bids_app(ui_info):
        """Function that stops the BIDS execution.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with this handler
        """
        print("Stop BIDS App")
        # self.docker_process.kill()
        ui_info.ui.context["object"].docker_running = False
        return True
