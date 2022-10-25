# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of classes and functions for handling non-GUI general events."""

# General imports
import multiprocessing
import fnmatch

import sys
import os
import warnings

from traits.api import *

from bids import BIDSLayout

# Own imports
from cmp.pipelines.anatomical import anatomical as Anatomical_pipeline
from cmp.pipelines.diffusion import diffusion as Diffusion_pipeline
from cmp.pipelines.functional import fMRI as FMRI_pipeline
from cmp.pipelines.functional import eeg as EEG_pipeline

from cmtklib.config import (
    anat_load_config_json,
    anat_save_config,
    dmri_load_config_json,
    dmri_save_config,
    fmri_load_config_json,
    fmri_save_config,
    eeg_load_config_json,
    eeg_save_config
)
from cmtklib.bids.io import (
    __cmp_directory__,
    __nipype_directory__,
    __freesurfer_directory__
)
from cmtklib.bids.utils import write_derivative_description

# Ignore some warnings
warnings.filterwarnings(
    "ignore",
    message="UserWarning: No valid root directory found for domain 'derivatives'."
    " Falling back on the Layout's root directory. If this isn't the intended behavior, "
    "make sure the config file for this domain includes a 'root' key.",
)


class ProjectInfo(HasTraits):
    """Class used to store all properties of a processing project.

    Attributes
    -----------
    base_directory: traits.Directory
        BIDS dataset root directory

    output_directory: traits.Directory
        Output directory

    bids_layout : bids.BIDSLayout
        Instance of pybids `BIDSLayout`

    subjects : traits.List
        List of subjects in the dataset

    subject :
        Subject being processed
        in the form ``sub-XX``

    subject_sessions : traits.List
        List of sessions for the subject being processed

    subject_session : trait.Str
        Session of the subject being processed
        in the form ``ses-YY``

    diffusion_imaging_model : traits.Str
        Diffusion imaging model that can be
        'DSI', 'DTI', 'HARDI' or 'multishell'

    dmri_bids_acqs : traits.List
        List diffusion imaging models extracted from ``acq-<label>`` filename part.

    dmri_bids_acq :
        Diffusion imaging model being processed

    anat_runs : traits.List
        List of run labels for T1w scans with multiple runs

    anat_run : traits.Str
        Run being processed for T1w scans with multiple runs

    dmri_runs : traits.List
        List of run labels for DWI scans with multiple runs

    dmri_run : traits.Str
        Run being processed for DWI scans with multiple runs

    fmri_runs : traits.List
        List of run labels for fMRI scans with multiple runs

    fmri_run : traits.Str
        Run being processed for fMRI scans with multiple runs

    parcellation_scheme : traits.Str
        Parcellation scheme used
        (Default: 'Lausanne2018')

    atlas_info : traits.Dict
        Dictionary storing parcellation atlas information
        See :class:`~cmp.parcellation.parcellation.ParcellationStage` for more details

    freesurfer_subjects_dir : traits.Str
        Freesurfer subjects directory

    freesurfer_subject_id  : traits.Str
        Freesurfer subject ID

    t1_available : Bool
        True if T1w scans were found
        (Default: False)

    dmri_available : Bool
        True if DWI scans were found
        (Default: False)

    fmri_available : Bool
        True if fMRI scans were found
        (Default: False)

    eeg_available : Bool
        True if EEG recordings were found
        (Default: False)

    anat_config_error_msg : traits.Str
        Error message for the anatomical pipeline configuration file

    anat_config_to_load : traits.Str
        Path to a configuration file for the anatomical pipeline

    anat_available_config : traits.List
        List of configuration files for the anatomical pipeline

    anat_stage_names : traits.List
        List of anatomical pipeline stage names

    anat_custom_last_stage : traits.Str
        Custom last anatomical pipeline stage to be processed

    dmri_config_error_msg : traits.Str
        Error message for the diffusion pipeline configuration file

    dmri_config_to_load : traits.Str
        Path to a configuration file for the diffusion pipeline

    dmri_available_config : traits.List
        List of configuration files for the anatomical pipeline

    dmri_stage_names : traits.List
        List of diffusion pipeline stage names

    dmri_custom_last_stage : traits.Str
        Custom last diffusion pipeline stage to be processed

    fmri_config_error_msg : traits.Str
        Error message for the fMRI pipeline configuration file

    fmri_config_to_load : traits.Str
        Path to a configuration file for the fMRI pipeline

    fmri_available_config : traits.List
        List of configuration files for the fMRI pipeline

    fmri_stage_names : traits.List
        List of fMRI pipeline stage names

    fmri_custom_last_stage : traits.Str
        Custom last fMRI pipeline stage to be processed

    eeg_config_error_msg : traits.Str
        Error message for the EEG pipeline configuration file

    eeg_config_to_load : traits.Str
        Path to a configuration file for the EEG pipeline

    eeg_available_config : traits.List
        List of configuration files for the EEG pipeline

    eeg_stage_names : traits.List
        List of EEG pipeline stage names

    eeg_custom_last_stage : traits.Str
        Custom last EEG pipeline stage to be processed

    number_of_cores : int
        Number of cores used by Nipype workflow execution engine
        to distribute independent processing nodes
        (Must be in the range of your local resources)
    """

    base_directory = Directory
    output_directory = Directory

    bids_layout = Instance(BIDSLayout)
    subjects = List([])
    subject = Enum(values="subjects")

    number_of_subjects = Int()

    subject_sessions = List([])
    subject_session = Enum(values="subject_sessions")

    anat_warning_msg = Str(
        "\nWarning: selected directory is already configured for anatomical data processing.\n\n"
        "Do you want to reset the configuration to default parameters ?\n"
    )
    dmri_warning_msg = Str(
        "\nWarning: selected directory is already configured for diffusion data processing.\n\n"
        "Do you want to reset the configuration to default parameters ?\n"
    )
    fmri_warning_msg = Str(
        "\nWarning: selected directory is already configured for resting-state data processing.\n\n"
        "Do you want to reset the configuration to default parameters ?\n"
    )

    # process_type = Enum('diffusion',['diffusion','fMRI'])
    diffusion_imaging_model = Enum("DTI", ["DSI", "DTI", "HARDI", "multishell"])
    parcellation_scheme = Str("Lausanne2018")
    atlas_info = Dict()
    freesurfer_subjects_dir = Str("")
    freesurfer_subject_id = Str("")

    pipeline_processing_summary = List()

    t1_available = Bool(False)
    dmri_available = Bool(False)
    fmri_available = Bool(False)
    eeg_available = Bool(False)

    anat_config_error_msg = Str("")
    anat_config_to_load = Str()
    anat_available_config = List()
    anat_config_to_load_msg = Str(
        "Several configuration files available. Select which one to load:\n"
    )
    anat_last_date_processed = Str("Not yet processed")
    anat_last_stage_processed = Str("Not yet processed")

    anat_stage_names = List
    anat_custom_last_stage = Str

    dmri_config_error_msg = Str("")
    dmri_config_to_load = Str()
    dmri_available_config = List()
    dmri_config_to_load_msg = Str(
        "Several configuration files available. Select which one to load:\n"
    )
    dmri_last_date_processed = Str("Not yet processed")
    dmri_last_stage_processed = Str("Not yet processed")

    dmri_stage_names = List
    dmri_custom_last_stage = Str

    fmri_config_error_msg = Str("")
    fmri_config_to_load = Str()
    fmri_available_config = List()
    fmri_config_to_load_msg = Str(
        "Several configuration files available. Select which one to load:\n"
    )
    fmri_last_date_processed = Str("Not yet processed")
    fmri_last_stage_processed = Str("Not yet processed")

    fmri_stage_names = List
    fmri_custom_last_stage = Str

    eeg_config_error_msg = Str('')
    eeg_config_to_load = Str()
    eeg_available_config = List()
    eeg_config_to_load_msg = Str(
        'Several configuration files available. Select which one to load:\n')
    eeg_last_date_processed = Str('Not yet processed')
    eeg_last_stage_processed = Str('Not yet processed')

    eeg_stage_names = List
    eeg_custom_last_stage = Str

    number_of_cores = Enum(1, list(range(1, multiprocessing.cpu_count() + 1)))


def refresh_folder(
    bids_directory, derivatives_directory, subject, input_folders, session=None
):
    """Creates (if needed) the folder hierarchy.

    Parameters
    ----------
    bids_directory : os.path
        BIDS dataset root directory

    derivatives_directory : os.path
        Output (derivatives) directory

    subject : string
        BIDS subject label (``sub-XX``)

    input_folders : List of string
        List of folder to be created in ``derivatives_directory``/'cmp-<version>'/``subject``

    session : string
        BIDS session label (``ses-YY``)
    """
    paths = []

    if session is None or session == "":
        paths.append(os.path.join(derivatives_directory, __freesurfer_directory__, subject))
        paths.append(os.path.join(derivatives_directory, __cmp_directory__, subject))
        paths.append(os.path.join(derivatives_directory, __nipype_directory__, subject))

        for in_f in input_folders:
            paths.append(os.path.join(derivatives_directory, __cmp_directory__, subject, in_f))

    else:
        paths.append(
            os.path.join(
                derivatives_directory, __freesurfer_directory__, "%s_%s" % (subject, session)
            )
        )
        paths.append(os.path.join(derivatives_directory, __cmp_directory__, subject, session))
        paths.append(os.path.join(derivatives_directory, __nipype_directory__, subject, session))

        for in_f in input_folders:
            paths.append(
                os.path.join(derivatives_directory, __cmp_directory__, subject, session, in_f)
            )

    for full_p in paths:
        if not os.path.exists(full_p):
            try:
                os.makedirs(full_p)
            except os.error:
                print("%s was already existing" % full_p)
            finally:
                print("Created directory %s" % full_p)

    write_derivative_description(bids_directory, derivatives_directory, __cmp_directory__)
    write_derivative_description(bids_directory, derivatives_directory, __freesurfer_directory__)
    write_derivative_description(bids_directory, derivatives_directory, __nipype_directory__)


def init_dmri_project(project_info, bids_layout, is_new_project, gui=True, debug=False):
    """Initialize the diffusion processing pipeline.

    Parameters
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of ``cmp.project.CMP_Project_Info`` object

    bids_layout : bids.BIDSLayout
        Instance of ``BIDSLayout`` object

    is_new_project : bool
        Specify if it corresponds or not to a new project.
        If `True`, it will create initial pipeline configuration files.

    gui : bool
        Might be obsolete and removed in future versions

    debug : bool
        If `True`, display extra prints to support debugging

    Returns
    -------
    dmri_pipeline : Instance(cmp.pipelines.diffusion.diffusion.DiffusionPipeline)
        `DiffusionPipeline` object instance
    """
    dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(project_info)

    bids_directory = os.path.abspath(project_info.base_directory)

    derivatives_directory = os.path.abspath(project_info.output_directory)

    if len(project_info.subject_sessions) > 0:
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            dmri_pipeline.input_folders,
            session=project_info.subject_session,
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject, project_info.subject_session
        )
    else:
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            dmri_pipeline.input_folders,
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject
        )

    dmri_inputs_checked = dmri_pipeline.check_input(layout=bids_layout, gui=gui)
    if dmri_inputs_checked:
        if (
            is_new_project and dmri_pipeline is not None
        ):
            print("> Initialize dmri project")
            if not os.path.exists(subject_derivatives_directory):
                try:
                    os.makedirs(subject_derivatives_directory)
                except os.error:
                    print("... Info : %s was already existing" % subject_derivatives_directory)
                finally:
                    print("... Info : Created directory %s" % subject_derivatives_directory)

            if (project_info.subject_session != "") and (
                project_info.subject_session is not None
            ):
                project_info.dmri_config_file = os.path.join(
                    subject_derivatives_directory,
                    "%s_%s_diffusion_config.json"
                    % (project_info.subject, project_info.subject_session),
                )
            else:
                project_info.dmri_config_file = os.path.join(
                    subject_derivatives_directory,
                    "%s_diffusion_config.json" % project_info.subject,
                )

            if os.path.exists(project_info.dmri_config_file):
                warn_res = project_info.configure_traits(view="dmri_warning_view")
                if warn_res:
                    print(
                        "... Read : Diffusion config file (%s)"
                        % project_info.dmri_config_file
                    )
                    dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
                else:
                    return None
            else:
                print(
                    "... Create : Diffusion config file (%s)"
                    % project_info.dmri_config_file
                )
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
        else:
            if debug:  # pragma: no cover
                print("int_project dmri_pipeline.global_config.subjects : ")
                print(dmri_pipeline.global_conf.subjects)

            dmri_conf_loaded = dmri_load_config_json(
                dmri_pipeline, project_info.dmri_config_file
            )

            if not dmri_conf_loaded:
                return None

        dmri_pipeline.config_file = project_info.dmri_config_file
    else:
        print("INFO: Missing diffusion inputs")

    return dmri_inputs_checked, dmri_pipeline


def init_fmri_project(project_info, bids_layout, is_new_project, gui=True, debug=False):
    """Initialize the fMRI processing pipeline.

    Parameters
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of ``cmp.project.CMP_Project_Info`` object

    bids_layout : bids.BIDSLayout
        Instance of ``BIDSLayout`` object

    is_new_project : bool
        Specify if it corresponds or not to a new project.
        If `True`, it will create initial pipeline configuration files.

    gui : bool
        Might be obsolete and removed in future versions

    debug : bool
        If `True`, display extra prints to support debugging

    Returns
    -------
    fmri_pipeline : Instance(cmp.pipelines.functional.fMRI.fMRIPipeline)
        `fMRIPipeline` object instance
    """
    fmri_pipeline = FMRI_pipeline.fMRIPipeline(project_info)

    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)

    if len(project_info.subject_sessions) > 0:
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            fmri_pipeline.input_folders,
            session=project_info.subject_session,
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject, project_info.subject_session
        )
    else:
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            fmri_pipeline.input_folders,
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject
        )

    fmri_inputs_checked = fmri_pipeline.check_input(layout=bids_layout, gui=gui)
    if fmri_inputs_checked:
        if (
            is_new_project and fmri_pipeline is not None
        ):
            print("> Initialize fmri project")
            if not os.path.exists(subject_derivatives_directory):
                try:
                    os.makedirs(subject_derivatives_directory)
                except os.error:
                    print("... Info : %s was already existing" % subject_derivatives_directory)
                finally:
                    print("... Info : Created directory %s" % subject_derivatives_directory)

            if (project_info.subject_session != "") and (
                project_info.subject_session is not None
            ):
                project_info.fmri_config_file = os.path.join(
                    subject_derivatives_directory,
                    "%s_%s_fMRI_config.json"
                    % (project_info.subject, project_info.subject_session),
                )
            else:
                project_info.fmri_config_file = os.path.join(
                    subject_derivatives_directory, "%s_fMRI_config.json" % project_info.subject
                )

            if os.path.exists(project_info.fmri_config_file):
                warn_res = project_info.configure_traits(view="fmri_warning_view")
                if warn_res:
                    print(
                        "... Read : fMRI config file (%s)"
                        % project_info.fmri_config_file
                    )
                    fmri_load_config_json(fmri_pipeline, project_info.fmri_config_file)
                else:
                    return None
            else:
                print(
                    "... Create : fMRI config file (%s)" % project_info.fmri_config_file
                )
                fmri_save_config(fmri_pipeline, project_info.fmri_config_file)
        else:
            if debug:  # pragma: no cover
                print("int_project fmri_pipeline.global_config.subjects : ")
                print(fmri_pipeline.global_conf.subjects)

            fmri_conf_loaded = fmri_load_config_json(
                fmri_pipeline, project_info.fmri_config_file
            )

            if not fmri_conf_loaded:
                return None

        fmri_pipeline.config_file = project_info.fmri_config_file
    else:
        print("INFO : Missing fmri inputs")

    return fmri_inputs_checked, fmri_pipeline


def init_anat_project(project_info, is_new_project, debug=False):
    """Initialize the anatomical processing pipeline.

    Parameters
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of ``cmp.project.CMP_Project_Info`` object

    is_new_project : bool
        Specify if it corresponds or not to a new project.
        If `True`, it will create initial pipeline configuration files.

    debug : bool
        If `True`, display extra prints to support debugging

    Returns
    -------
    anat_pipeline : Instance(cmp.pipelines.anatomical.anatomical.AnatomicalPipeline)
        `AnatomicalPipeline` object instance
    """
    anat_pipeline = Anatomical_pipeline.AnatomicalPipeline(project_info)

    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)

    if (project_info.subject_session != "") and (
        project_info.subject_session is not None
    ):
        if debug:  # pragma: no cover
            print("Refresh folder WITH session")
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            anat_pipeline.input_folders,
            session=project_info.subject_session,
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject, project_info.subject_session
        )
    else:
        if debug:  # pragma: no cover
            print("Refresh folder WITHOUT session")
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            anat_pipeline.input_folders,
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject
        )

    if is_new_project and anat_pipeline is not None:
        print("> Initialize anatomical project")
        if not os.path.exists(subject_derivatives_directory):
            try:
                os.makedirs(subject_derivatives_directory)
                print("... Info : Created directory %s" % subject_derivatives_directory)
            except os.error:
                print("... Info: %s was already existing" % subject_derivatives_directory)

        if (project_info.subject_session != "") and (
            project_info.subject_session is not None
        ):
            project_info.anat_config_file = os.path.join(
                subject_derivatives_directory,
                "%s_%s_anatomical_config.json"
                % (project_info.subject, project_info.subject_session),
            )
        else:
            project_info.anat_config_file = os.path.join(
                subject_derivatives_directory, "%s_anatomical_config.json" % project_info.subject
            )

        if os.path.exists(project_info.anat_config_file):
            warn_res = project_info.configure_traits(view="anat_warning_view")
            if warn_res:
                anat_save_config(anat_pipeline, project_info.anat_config_file)
            else:
                return None
        else:
            anat_save_config(anat_pipeline, project_info.anat_config_file)

    else:
        if debug:  # pragma: no cover
            print("int_project anat_pipeline.global_config.subjects : ")
            print(anat_pipeline.global_conf.subjects)

        anat_conf_loaded = anat_load_config_json(
            anat_pipeline, project_info.anat_config_file
        )

        if not anat_conf_loaded:
            return None

    anat_pipeline.config_file = project_info.anat_config_file

    return anat_pipeline


def init_eeg_project(project_info, is_new_project, debug=False):
    """Initialize the eeg processing pipeline.

    Parameters
    ----------
    project_info : cmp.project.CMP_Project_Info
        Instance of ``cmp.project.CMP_Project_Info`` object

    is_new_project : bool
        Specify if it corresponds or not to a new project.
        If `True`, it will create initial pipeline configuration files.

    debug : bool
        If `True`, display extra prints to support debugging

    Returns
    -------
    eeg_pipeline : Instance(cmp.pipelines.functional.eeg.EEGPipeline)
        `EEGPipeline` object instance
    """
    eeg_pipeline = EEG_pipeline.EEGPipeline(project_info)
    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)

    if (project_info.subject_session != '') and (project_info.subject_session is not None):
        if debug:  # pragma: no cover
            print('Refresh folder WITH session')
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            eeg_pipeline.input_folders,
            session=project_info.subject_session
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject, project_info.subject_session
        )
    else:
        if debug:  # pragma: no cover
            print('Refresh folder WITHOUT session')
        refresh_folder(
            bids_directory,
            derivatives_directory,
            project_info.subject,
            eeg_pipeline.input_folders
        )
        subject_derivatives_directory = os.path.join(
            derivatives_directory, project_info.subject
        )

    if is_new_project and eeg_pipeline is not None:
        print("> Initialize eeg project")
        if not os.path.exists(subject_derivatives_directory):
            try:
                os.makedirs(subject_derivatives_directory)
                print("... Info : Created directory %s" %
                      subject_derivatives_directory)
            except os.error:  # pragma: no cover
                print("... Info: %s was already existing" %
                      subject_derivatives_directory)
        if (project_info.subject_session != '') and (project_info.subject_session is not None):
            project_info.eeg_config_file = os.path.join(
                subject_derivatives_directory, '%s_%s_eeg_config.json' % (
                    project_info.subject, project_info.subject_session
                )
            )
        else:
            project_info.eeg_config_file = os.path.join(
                subject_derivatives_directory, '%s_eeg_config.json' % project_info.subject)

        if os.path.exists(project_info.eeg_config_file):
            print(f' .. WARNING: Overwrite EEG pipeline configuration file to {project_info.eeg_config_file}')
        eeg_save_config(eeg_pipeline, project_info.eeg_config_file)

        eeg_inputs_checked = True

    else:
        if debug:  # pragma: no cover
            print("init_project eeg_pipeline.global_config.subjects : ")
            print(eeg_pipeline.global_conf.subjects)

        eeg_conf_loaded = eeg_load_config_json(eeg_pipeline, project_info.eeg_config_file)

        eeg_inputs_checked = eeg_pipeline.check_input()

        if not eeg_conf_loaded:  # pragma: no cover
            raise FileNotFoundError(f"Problem to load the eeg pipeline config file {project_info.eeg_config_file}")

    eeg_pipeline.config_file = project_info.eeg_config_file

    return eeg_inputs_checked, eeg_pipeline


def update_anat_last_processed(project_info, pipeline):  # pragma: no cover
    """Update last processing information of a :class:`~cmp.pipelines.anatomical.anatomical.AnatomicalPipeline`.

    Parameters
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of `CMP_Project_Info` object

    pipeline : cmp.pipelines.anatomical.anatomical.AnatomicalPipeline
        Instance of `AnatomicalPipeline` object
    """
    # last date
    if os.path.exists(
        os.path.join(project_info.output_directory, __nipype_directory__, project_info.subject)
    ):
        if (
            project_info.anat_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.anat_last_date_processed
        ):
            pipeline.anat_last_date_processed = pipeline.now
            project_info.anat_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.output_directory,
            __nipype_directory__,
            project_info.subject,
            "anatomical_pipeline",
        )
    ):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
            os.path.join(
                project_info.output_directory,
                __nipype_directory__,
                project_info.subject,
                "anatomical_pipeline",
            )
        ):
            for dirname in fnmatch.filter(dirnames, "*_stage"):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + "_stage" in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.anat_last_stage_processed = stage

    # last parcellation scheme
    project_info.parcellation_scheme = pipeline.parcellation_scheme
    project_info.atlas_info = pipeline.atlas_info


def update_dmri_last_processed(project_info, pipeline):  # pragma: no cover
    """Update last processing information of an :class:`~cmp.pipelines.diffusion.diffusion.DiffusionPipeline`.

    Parameters
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of `CMP_Project_Info` object

    pipeline : cmp.pipelines.diffusion.diffusion.DiffusionPipeline
        Instance of `DiffusionPipeline` object
    """
    # last date
    if os.path.exists(
        os.path.join(project_info.output_directory, __nipype_directory__, project_info.subject)
    ):
        if (
            project_info.dmri_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.dmri_last_date_processed
        ):
            pipeline.dmri_last_date_processed = pipeline.now
            project_info.dmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.output_directory,
            __nipype_directory__,
            project_info.subject,
            "diffusion_pipeline",
        )
    ):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
            os.path.join(
                project_info.output_directory,
                __nipype_directory__,
                project_info.subject,
                "diffusion_pipeline",
            )
        ):
            for dirname in fnmatch.filter(dirnames, "*_stage"):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + "_stage" in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


def update_fmri_last_processed(project_info, pipeline):  # pragma: no cover
    """Update last processing information of an :class:`~cmp.pipelines.functional.fMRI.fMRIPipeline`.

    Parameters
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of `CMP_Project_Info` object

    pipeline : cmp.pipelines.functional.fMRI.fMRIPipeline
        Instance of `fMRIPipeline` object
    """
    # last date
    if os.path.exists(
        os.path.join(project_info.output_directory, __nipype_directory__, project_info.subject)
    ):
        if (
            project_info.fmri_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.fmri_last_date_processed
        ):
            pipeline.fmri_last_date_processed = pipeline.now
            project_info.fmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.output_directory,
            __nipype_directory__,
            project_info.subject,
            "fMRI_pipeline")
    ):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
            os.path.join(
                project_info.output_directory,
                __nipype_directory__,
                project_info.subject,
                "fMRI_pipeline",
            )
        ):
            for dirname in fnmatch.filter(dirnames, "*_stage"):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + "_stage" in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


def update_eeg_last_processed(project_info, pipeline):  # pragma: no cover
    """Update last processing information of a :py:class:`~cmp.pipelines.functional.eeg.EEGPipeline`.

    Parameters
    ----------
    project_info : cmp.project.CMP_Project_Info
        Instance of `CMP_Project_Info` object

    pipeline : cmp.pipelines.functional.eeg.EEGPipeline
        Instance of `EEGPipeline` object
    """
    # last date
    if os.path.exists(
        os.path.join(project_info.output_directory, __nipype_directory__, project_info.subject)
    ):
        if (
            project_info.eeg_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.anat_last_date_processed
        ):
            pipeline.eeg_last_date_processed = pipeline.now
            project_info.eeg_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.output_directory,
            __nipype_directory__,
            project_info.subject,
            'eeg_pipeline')
    ):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
            os.path.join(
                project_info.output_directory,
                __nipype_directory__,
                project_info.subject,
                'eeg_pipeline'
            )
        ):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.eeg_last_stage_processed = stage

    # last parcellation scheme
    project_info.parcellation_scheme = pipeline.parcellation_scheme
    project_info.atlas_info = pipeline.atlas_info


def run_individual(
    bids_dir,
    output_dir,
    participant_label,
    session_label,
    anat_pipeline_config,
    dwi_pipeline_config,
    func_pipeline_config,
    eeg_pipeline_config,
    number_of_threads=1,
):
    """Function that creates the processing pipeline for complete coverage.

    Parameters
    ----------
    bids_dir : string
        BIDS dataset root directory

    output_dir : string
        Output (derivatives) directory

    participant_label : string
        BIDS participant / subject label (``sub-XX``)

    session_label : string
        BIDS session label (``ses-XX``)

    anat_pipeline_config : string
        Path to anatomical pipeline configuration file

    dwi_pipeline_config : string
        Path to diffusion pipeline configuration file

    func_pipeline_config : string
        Path to fMRI pipeline configuration file

    eeg_pipeline_config : string
        Path to EEG pipeline configuration file

    number_of_threads : int
        Number of threads used by programs relying on the OpenMP library
    """
    exit_code = 0

    project = ProjectInfo()
    project.base_directory = os.path.abspath(bids_dir)
    project.output_directory = os.path.abspath(output_dir)
    project.subjects = ["{}".format(participant_label)]
    project.subject = "{}".format(participant_label)

    try:
        bids_layout = BIDSLayout(project.base_directory)
    except Exception:
        print("Exception : Raised at BIDSLayout")
        sys.exit(1)

    if session_label is not None:
        project.subject_sessions = ["{}".format(session_label)]
        project.subject_session = "{}".format(session_label)
        print("INFO : Detected session(s)")
    else:
        print("INFO : No detected session")
        project.subject_sessions = [""]
        project.subject_session = ""

    project.anat_config_file = os.path.abspath(anat_pipeline_config)

    # Perform only the anatomical pipeline
    if dwi_pipeline_config is None and func_pipeline_config is None and eeg_pipeline_config is None:

        _, exit_code, _, _ = run_anat_pipeline(project, bids_layout, number_of_threads)

    else:  # Perform anatomical pipeline and diffusion and/or fMRI and/or EEG pipeline
        anat_pipeline, exit_code, anat_valid_outputs, msg = run_anat_pipeline(project, bids_layout, number_of_threads)

        if not anat_valid_outputs or exit_code == 1:
            print(msg)
            exit_code = 1
            return exit_code

        project.freesurfer_subjects_dir = anat_pipeline.stages["Segmentation"].config.freesurfer_subjects_dir
        project.freesurfer_subject_id = anat_pipeline.stages["Segmentation"].config.freesurfer_subject_id

        # Perform the anatomical and the diffusion pipelines
        if dwi_pipeline_config is not None and func_pipeline_config is None and eeg_pipeline_config is None:
            project.dmri_config_file = os.path.abspath(dwi_pipeline_config)
            exit_code = run_dmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code

        # Perform the anatomical and the fMRI pipelines
        elif func_pipeline_config is not None and dwi_pipeline_config is None and eeg_pipeline_config is None:
            project.fmri_config_file = os.path.abspath(func_pipeline_config)
            exit_code = run_fmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code

        # Perform the anatomical and the EEG pipeline
        elif eeg_pipeline_config is not None and dwi_pipeline_config is None and func_pipeline_config is None:
            project.eeg_config_file = os.path.abspath(eeg_pipeline_config)
            exit_code = run_eeg_pipeline(project, anat_pipeline)
            if exit_code == 1:
                return exit_code

        # Perform anatomical/diffusion/fMRI pipeline
        elif dwi_pipeline_config is not None and func_pipeline_config is not None and eeg_pipeline_config is None:
            project.dmri_config_file = os.path.abspath(dwi_pipeline_config)
            project.fmri_config_file = os.path.abspath(func_pipeline_config)
            exit_code = run_dmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code
            exit_code = run_fmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code

        # Perform anatomical/diffusion/EEG pipeline
        elif dwi_pipeline_config is not None and eeg_pipeline_config is not None and func_pipeline_config is None:
            project.dmri_config_file = os.path.abspath(dwi_pipeline_config)
            project.eeg_config_file = os.path.abspath(eeg_pipeline_config)
            exit_code = run_dmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code
            exit_code = run_eeg_pipeline(project, anat_pipeline)
            if exit_code == 1:
                return exit_code

        # Perform all pipelines (anatomical/diffusion/fMRI/EEG)
        elif dwi_pipeline_config is not None and eeg_pipeline_config is not None and func_pipeline_config is not None:
            project.dmri_config_file = os.path.abspath(dwi_pipeline_config)
            project.fmri_config_file = os.path.abspath(func_pipeline_config)
            project.eeg_config_file = os.path.abspath(eeg_pipeline_config)
            exit_code = run_dmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code
            exit_code = run_fmri_pipeline(project, bids_layout, anat_pipeline)
            if exit_code == 1:
                return exit_code
            exit_code = run_eeg_pipeline(project, anat_pipeline)
            if exit_code == 1:
                return exit_code

    return exit_code


def run_anat_pipeline(project, bids_layout, number_of_threads):
    """Initialize and run anatomical pipeline based on `project.anat_config_file` pipeline configuration, that has to be set a-priori."""
    anat_pipeline = init_anat_project(project, False)
    if anat_pipeline is not None:
        anat_valid_inputs = anat_pipeline.check_input(bids_layout, gui=False)

        print(f"--- Set Freesurfer and ANTs to use {number_of_threads} threads by the means of OpenMP")
        anat_pipeline.stages["Segmentation"].config.number_of_threads = number_of_threads

        if anat_valid_inputs:
            print(">> Process anatomical pipeline")
            anat_pipeline.process()
            anat_valid_outputs, msg = anat_pipeline.check_output()
            anat_pipeline.fill_stages_outputs()
            exit_code = 0
        else:  # pragma: no cover
            print("ERROR : Invalid inputs for anatomical pipeline")
            exit_code = 1

    return anat_pipeline, exit_code, anat_valid_outputs, msg


def run_dmri_pipeline(project, bids_layout, anat_pipeline):
    """Initialize and run diffusion pipeline based on `project.dmri_config_file` pipeline configuration, that has to be set a-priori."""
    dmri_valid_inputs, dmri_pipeline = init_dmri_project(
        project, bids_layout, False
    )
    if dmri_pipeline is not None:
        dmri_pipeline.parcellation_scheme = anat_pipeline.parcellation_scheme
        dmri_pipeline.atlas_info = anat_pipeline.atlas_info
        if anat_pipeline.parcellation_scheme == "Custom":
            dmri_pipeline.custom_atlas_name = anat_pipeline.stages["Parcellation"].config.custom_parcellation.atlas
            dmri_pipeline.custom_atlas_res = anat_pipeline.stages["Parcellation"].config.custom_parcellation.res
        if dmri_valid_inputs:
            dmri_pipeline.process()
            dmri_pipeline.fill_stages_outputs()
            exit_code = 0
        else:  # pragma: no cover
            print("   ... ERROR : Invalid inputs for diffusion pipeline")
            exit_code = 1
    else:  # pragma: no cover
        print("   ... ERROR : Diffusion pipeline is None")
        exit_code = 1
    return exit_code


def run_fmri_pipeline(project, bids_layout, anat_pipeline):
    """Initialize and run fMRI pipeline based on `project.fmri_config_file` pipeline configuration, that has to be set a-priori."""
    fmri_valid_inputs, fmri_pipeline = init_fmri_project(
        project, bids_layout, False
    )
    if fmri_pipeline is not None:
        fmri_pipeline.parcellation_scheme = anat_pipeline.parcellation_scheme
        fmri_pipeline.atlas_info = anat_pipeline.atlas_info
        fmri_pipeline.subjects_dir = anat_pipeline.stages["Segmentation"].config.freesurfer_subjects_dir
        fmri_pipeline.subject_id = anat_pipeline.stages["Segmentation"].config.freesurfer_subject_id
        if anat_pipeline.parcellation_scheme == "Custom":
            fmri_pipeline.custom_atlas_name = anat_pipeline.stages["Parcellation"].config.custom_parcellation.atlas
            fmri_pipeline.custom_atlas_res = anat_pipeline.stages["Parcellation"].config.custom_parcellation.res
        print("Freesurfer subjects dir: {}".format(fmri_pipeline.subjects_dir))
        print("Freesurfer subject id: {}".format(fmri_pipeline.subject_id))

        if fmri_valid_inputs:
            print(">> Process fMRI pipeline")
            fmri_pipeline.process()
            fmri_pipeline.fill_stages_outputs()
            exit_code = 0
        else:  # pragma: no cover
            print("   ... ERROR : Invalid inputs for the fMRI pipeline")
            exit_code = 1
    return exit_code


def run_eeg_pipeline(project, anat_pipeline):
    """Initialize and run EEG pipeline based on `project.eeg_config_file` pipeline configuration, that has to be set a-priori."""
    eeg_valid_inputs, eeg_pipeline = init_eeg_project(
        project, False
    )
    if eeg_pipeline is not None:
        eeg_pipeline.parcellation_scheme = anat_pipeline.parcellation_scheme
        eeg_pipeline.atlas_info = anat_pipeline.atlas_info
        # eeg_pipeline.subjects_dir = anat_pipeline.stages["Segmentation"].config.freesurfer_subjects_dir
        # eeg_pipeline.subject_id = anat_pipeline.stages["Segmentation"].config.freesurfer_subject_id
        # if anat_pipeline.parcellation_scheme == "Custom":
        #     eeg_pipeline.custom_atlas_name = anat_pipeline.stages["Parcellation"].config.custom_parcellation.atlas
        #     eeg_pipeline.custom_atlas_res = anat_pipeline.stages["Parcellation"].config.custom_parcellation.res
        # print("Freesurfer subjects dir: {}".format(eeg_pipeline.subjects_dir))
        # print("Freesurfer subject id: {}".format(eeg_pipeline.subject_id))

        if eeg_valid_inputs:
            print(">> Process EEG pipeline")
            eeg_pipeline.process()
            eeg_pipeline.fill_stages_outputs()
            exit_code = 0
        else:  # pragma: no cover
            print("   ... ERROR : Invalid inputs for the EEG pipeline")
            exit_code = 1
    return exit_code
