# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper Controler for handling GUI and non GUI general events."""

# Global imports
import os
import fnmatch
import glob
import shutil

import warnings

# Own imports
from traits.trait_types import Enum, Bool, String, Password, Directory, List, Button
from traitsui.editors import EnumEditor
from traitsui.group import VGroup, HGroup, Group
from traitsui.include import Include
from traitsui.item import Item, spring
from traitsui.qt4.extra.qt_view import QtView
from traitsui.view import View

import cmp.project

from cmtklib.bids.io import __cmp_directory__, __nipype_directory__, __freesurfer_directory__
from cmtklib.config import (
    anat_load_config_json,
    anat_save_config,
    dmri_load_config_json,
    dmri_save_config,
    fmri_load_config_json,
    fmri_save_config,
)
from cmtklib.util import (
    print_warning, print_error
)

from cmp.bidsappmanager.gui.globals import modal_width
from cmp.bidsappmanager.pipelines.anatomical import anatomical as anatomical_pipeline
from cmp.bidsappmanager.pipelines.diffusion import diffusion as diffusion_pipeline
from cmp.bidsappmanager.pipelines.functional import fMRI as fMRI_pipeline

warnings.filterwarnings(
    "ignore", message="No valid root directory found for domain 'derivatives'."
)


def clean_cache(bids_root):
    """Clean cache stored in /tmp.

    Target issue related to that a dataset directory is mounted into /tmp and
    used for caching by java/matlab/matplotlib/xvfb-run in the container image.

    Parameters
    ----------
    bids_root : string
        BIDS root dataset directory
    """
    print_warning("> Clean generated docker image cache")

    for d in glob.glob(os.path.join(bids_root, " hsperfdata_cmp")):
        print_warning("... DEL: {}".format(d))
        shutil.rmtree(d)

    for f in glob.glob(os.path.join(bids_root, "._java*")):
        print_warning("... DEL: {}".format(f))
        os.remove(f)

    for f in glob.glob(os.path.join(bids_root, "mri_segstats.tmp*")):
        print_warning("... DEL: {}".format(f))
        os.remove(f)

    for d in glob.glob(os.path.join(bids_root, "MCR_*")):
        print_warning("... DEL: {}".format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, "matplotlib*")):
        print_warning("... DEL: {}".format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, "xvfb-run.*")):
        print_warning("... DEL: {}".format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, ".X11*")):
        print_warning("... DEL: {}".format(d))
        shutil.rmtree(d)

    for d in glob.glob(os.path.join(bids_root, ".X11-unix")):
        print_warning("... DEL: {}".format(d))
        shutil.rmtree(d)

    for f in glob.glob(os.path.join(bids_root, ".X99*")):
        print_warning("... DEL: {}".format(f))
        os.remove(d)


def is_tool(name):
    """Check whether `name` is on PATH."""

    from distutils.spawn import find_executable

    return find_executable(name) is not None


def refresh_folder(derivatives_directory, subject, input_folders, session=None):
    """Creates (if needed) the folder hierarchy.

    Parameters
    ----------
    derivatives_directory : string

    subject : string
        Subject label (``sub-XX``) for which we create the output folder hierarchy

    session : string
        Subject session label (``ses-YY``)

    input_folders : list of string
        List of folders to create in ``derivative_directory/sub-XX/(ses-YY)/`` folder
        for the given ``subject``
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
                print_warning("  .. INFO: %s was already existing" % full_p)
            finally:
                print("  .. INFO: Created directory %s" % full_p)


def init_dmri_project(project_info, bids_layout, is_new_project, gui=True):
    """Create and initialize a :class:`DiffusionPipelineUI` instance

    Parameters
    ----------
    project_info : ProjectInfoUI
        Instance of :class:`ProjectInfoUI` class

    bids_layout : bids.BIDSLayout
        PyBIDS BIDS Layout object describing the BIDS dataset

    is_new_project : bool
        If True, this is a new project which has been never processed

    gui : bool
        If True, display messages in GUI
    """
    dmri_pipeline = diffusion_pipeline.DiffusionPipelineUI(project_info)

    derivatives_directory = os.path.join(project_info.base_directory, "derivatives")

    if (project_info.subject_session != "") and (
        project_info.subject_session is not None
    ):
        refresh_folder(
            derivatives_directory,
            project_info.subject,
            dmri_pipeline.input_folders,
            session=project_info.subject_session,
        )
    else:
        refresh_folder(
            derivatives_directory, project_info.subject, dmri_pipeline.input_folders
        )

    dmri_inputs_checked = dmri_pipeline.check_input(layout=bids_layout, gui=gui)
    if dmri_inputs_checked:
        if is_new_project and dmri_pipeline is not None:
            print("> Initialize dMRI project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print_warning(
                        "  .. INFO: %s was already existing" % derivatives_directory
                    )
                finally:
                    print("  .. INFO: Created directory %s" % derivatives_directory)

            if (project_info.subject_session != "") and (
                project_info.subject_session is not None
            ):
                project_info.dmri_config_file = os.path.join(
                    derivatives_directory,
                    "%s_%s_diffusion_config.json"
                    % (project_info.subject, project_info.subject_session),
                )
            else:
                project_info.dmri_config_file = os.path.join(
                    derivatives_directory,
                    "%s_diffusion_config.json" % project_info.subject,
                )

            if os.path.exists(project_info.dmri_config_file):
                warn_res = project_info.configure_traits(view="dmri_warning_view")
                if warn_res:
                    print(
                        "  .. INFO: Read diffusion config file (%s)"
                        % project_info.dmri_config_file
                    )
                    dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
                else:
                    return None
            else:
                print(
                    "  .. INFO: Create diffusion config file (%s)"
                    % project_info.dmri_config_file
                )
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
        else:
            print("> Load dMRI project")
            dmri_conf_loaded = dmri_load_config_json(
                dmri_pipeline, project_info.dmri_config_file
            )

            if not dmri_conf_loaded:
                return None

        dmri_pipeline.config_file = project_info.dmri_config_file
    else:
        print_error("  .. ERROR: Missing diffusion inputs")

    return dmri_inputs_checked, dmri_pipeline


def init_fmri_project(project_info, bids_layout, is_new_project, gui=True):
    """Create and initialize a :class:`fMRIPipelineUI` instance

    Parameters
    ----------
    project_info : ProjectInfoUI
        Instance of :class:`ProjectInfoUI` class

    bids_layout : bids.BIDSLayout
        PyBIDS BIDS Layout object describing the BIDS dataset

    is_new_project : bool
        If True, this is a new project which has been never processed

    gui : bool
        If True, display messgae in GUI
    """
    fmri_pipeline = fMRI_pipeline.fMRIPipelineUI(project_info)

    derivatives_directory = os.path.join(project_info.base_directory, "derivatives")

    if (project_info.subject_session != "") and (
        project_info.subject_session is not None
    ):
        refresh_folder(
            derivatives_directory,
            project_info.subject,
            fmri_pipeline.input_folders,
            session=project_info.subject_session,
        )
    else:
        refresh_folder(
            derivatives_directory, project_info.subject, fmri_pipeline.input_folders
        )

    fmri_inputs_checked = fmri_pipeline.check_input(layout=bids_layout, gui=gui)
    if fmri_inputs_checked:
        if is_new_project and fmri_pipeline is not None:
            print("> Initialize fMRI project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("  .. INFO: %s was already existing" % derivatives_directory)
                finally:
                    print("  .. INFO: Created directory %s" % derivatives_directory)

            if (project_info.subject_session != "") and (
                project_info.subject_session is not None
            ):
                project_info.fmri_config_file = os.path.join(
                    derivatives_directory,
                    "%s_%s_fMRI_config.json"
                    % (project_info.subject, project_info.subject_session),
                )
            else:
                project_info.fmri_config_file = os.path.join(
                    derivatives_directory, "%s_fMRI_config.json" % project_info.subject
                )

            if os.path.exists(project_info.fmri_config_file):
                warn_res = project_info.configure_traits(view="fmri_warning_view")
                if warn_res:
                    print(
                        "  .. INFO: Read fMRI config file (%s)"
                        % project_info.fmri_config_file
                    )
                    fmri_load_config_json(fmri_pipeline, project_info.fmri_config_file)
                else:
                    return None
            else:
                print(
                    "  .. INFO: Create fMRI config file (%s)"
                    % project_info.fmri_config_file
                )
                fmri_save_config(fmri_pipeline, project_info.fmri_config_file)
        else:
            print("> Load fMRI project")
            fmri_conf_loaded = fmri_load_config_json(
                fmri_pipeline, project_info.fmri_config_file
            )

            if not fmri_conf_loaded:
                return None

        fmri_pipeline.config_file = project_info.fmri_config_file
    else:
        print("  .. INFO: Missing fMRI inputs")

    return fmri_inputs_checked, fmri_pipeline


def init_anat_project(project_info, is_new_project):
    """Create and initialize a :class:`AnatomicalPipelineUI` instance

    Parameters
    ----------
    project_info : ProjectInfoUI
        Instance of :class:`ProjectInfoUI` class

    is_new_project : bool
        If True, this is a new project which has been never processed
    """
    anat_pipeline = anatomical_pipeline.AnatomicalPipelineUI(project_info)

    derivatives_directory = os.path.join(project_info.base_directory, "derivatives")

    if is_new_project and anat_pipeline is not None:  # and dmri_pipelineis not None:
        print("> Initialize anatomical project")
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print("  .. INFO: %s was already existing" % derivatives_directory)
            finally:
                print("  .. INFO: Created directory %s" % derivatives_directory)

        if (project_info.subject_session != "") and (
            project_info.subject_session is not None
        ):
            project_info.anat_config_file = os.path.join(
                derivatives_directory,
                "%s_%s_anatomical_config.json"
                % (project_info.subject, project_info.subject_session),
            )
        else:
            project_info.anat_config_file = os.path.join(
                derivatives_directory,
                "%s_anatomical_config.json" % project_info.subject,
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
        print("> Load anatomical project")
        anat_conf_loaded = anat_load_config_json(
            anat_pipeline, project_info.anat_config_file
        )

        if not anat_conf_loaded:
            return None

    if (project_info.subject_session != "") and (
        project_info.subject_session is not None
    ):
        refresh_folder(
            derivatives_directory,
            project_info.subject,
            anat_pipeline.input_folders,
            session=project_info.subject_session,
        )
    else:
        refresh_folder(
            derivatives_directory, project_info.subject, anat_pipeline.input_folders
        )

    anat_pipeline.config_file = project_info.anat_config_file

    return anat_pipeline


def update_anat_last_processed(project_info, pipeline):
    """Update anatomical pipeline processing information

    Parameters
    ----------
    project_info : ProjectInfoUI
        Instance of :class:`ProjectInfoUI` class

    pipeline : AnatomicalPipelineUI
        Instance of :class:`AnatomicalPipelineUI`
    """
    # last date
    if os.path.exists(
        os.path.join(
            project_info.base_directory, "derivatives", __cmp_directory__, project_info.subject
        )
    ):
        # out_dirs = os.listdir(os.path.join(
        #    project_info.base_directory, 'derivatives', 'cmp', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (
            project_info.anat_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.anat_last_date_processed
        ):
            pipeline.anat_last_date_processed = pipeline.now
            project_info.anat_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.base_directory,
            "derivatives",
            __cmp_directory__,
            project_info.subject,
            "tmp",
            "anatomical_pipeline",
        )
    ):
        stage_dirs = []
        for __, dirnames, _ in os.walk(
            os.path.join(
                project_info.base_directory,
                "derivatives",
                __cmp_directory__,
                project_info.subject,
                "tmp",
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


def update_dmri_last_processed(project_info, pipeline):
    """Update diffusion pipeline processing information

    Parameters
    ----------
    project_info : ProjectInfoUI
        Instance of :class:`ProjectInfoUI` class

    pipeline : DiffusionPipelineUI
        Instance of :class:`DiffusionPipelineUI`
    """
    # last date
    if os.path.exists(
        os.path.join(
            project_info.base_directory, "derivatives", __cmp_directory__, project_info.subject
        )
    ):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.base_directory, 'derivatives', 'cmp', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (
            project_info.dmri_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.dmri_last_date_processed
        ):
            pipeline.dmri_last_date_processed = pipeline.now
            project_info.dmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.base_directory,
            "derivatives",
            __cmp_directory__,
            project_info.subject,
            "tmp",
            "diffusion_pipeline",
        )
    ):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
            os.path.join(
                project_info.base_directory,
                "derivatives",
                __cmp_directory__,
                project_info.subject,
                "tmp",
                "diffusion_pipeline",
            )
        ):
            for dirname in fnmatch.filter(dirnames, "*_stage"):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + "_stage" in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


def update_fmri_last_processed(project_info, pipeline):
    """Update functional MRI pipeline processing information

    Parameters
    ----------
    project_info : ProjectInfoUI
        Instance of :class:`ProjectInfoUI` class

    pipeline : fMRIPipelineUI
        Instance of :class:`fMRIPipelineUI`
    """
    # last date
    if os.path.exists(
        os.path.join(
            project_info.base_directory, "derivatives", __cmp_directory__, project_info.subject
        )
    ):
        # out_dirs = os.listdir(os.path.join(
        #     project_info.base_directory, 'derivatives', 'cmp', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (
            project_info.fmri_last_date_processed == "Not yet processed"
            or pipeline.now > project_info.fmri_last_date_processed
        ):
            pipeline.fmri_last_date_processed = pipeline.now
            project_info.fmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(
        os.path.join(
            project_info.base_directory,
            "derivatives",
            __cmp_directory__,
            project_info.subject,
            "tmp",
            "fMRI_pipeline",
        )
    ):
        stage_dirs = []
        for _, dirnames, _ in os.walk(
            os.path.join(
                project_info.base_directory,
                "derivatives",
                __cmp_directory__,
                project_info.subject,
                "tmp",
                "fMRI_pipeline",
            )
        ):
            for dirname in fnmatch.filter(dirnames, "*_stage"):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + "_stage" in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


class ProjectInfoUI(cmp.project.ProjectInfo):
    """Class that extends the :class:`ProjectInfo` with graphical components.

    It supports graphically the setting of all processing properties / attributes
    of an :class:`ProjectInfo` instance.

    Attributes
    -----------
    creation_mode : traits.Enum
        Mode for loading the dataset. Valid values are
        'Load BIDS dataset', 'Install Datalad BIDS dataset'

    install_datalad_dataset_via_ssh : traits.Bool
        If set to True install the datalad dataset from a remote server
        via ssh.(True by default)

    ssh_user : traits.Str
        Remote server username.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    ssh_pwd <traits.Password>
        Remote server password.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    ssh_remote : traits.Str
        Remote server IP or URL.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    datalad_dataset_path : traits.Directory
        Path to the datalad dataset on the remote server.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    summary_view_button : traits.ui.Button
        Button that shows the pipeline processing summary table

    pipeline_processing_summary_view : traits.ui.VGroup
        TraitsUI VGroup that contains ``Item('pipeline_processing_summary')``

    dataset_view : traits.ui.View
        TraitsUI View that shows a summary of project settings and
        modality available for a given subject

    traits_view : QtView
        TraitsUI QtView that includes the View 'dataset_view'

    create_view : traits.ui.View
        Dialog view to create a BIDS Dataset

    subject_view : traits.ui.View
        Dialog view to select of subject

    subject_session_view : traits.ui.View
        Dialog view to select the subject session

    dmri_bids_acq_view : traits.ui.View
        Dialog view to select the diffusion acquisition model

    anat_warning_view : traits.ui.View
        View that displays a warning message regarding
        the anatomical T1w data

    anat_config_error_view : traits.ui.View
        Error view that displays an error message regarding
        the configuration of the anatomical pipeline

    dmri_warning_view : traits.ui.View
        View that displays a warning message regarding
        the diffusion MRI data

    dmri_config_error_view : traits.ui.View
        View that displays an error message regarding
        the configuration of the diffusion pipeline

    fmri_warning_view : traits.ui.View
        View that displays a warning message regarding
        the functional MRI data

    fmri_config_error_view : traits.ui.View
        View that displays an error message regarding
        the configuration of the fMRI pipeline

    open_view : traits.ui.View
        Dialog view to load a BIDS Dataset

    anat_select_config_to_load : traits.ui.View
        Dialog view to load the configuration file of the anatomical pipeline

    diffusion_imaging_model_select_view : traits.ui.View
        Dialog view to select the diffusion acquisition model

    dmri_select_config_to_load : traits.ui.View
        Dialog view to load the configuration file of the diffusion MRI pipeline

    fmri_select_config_to_load : traits.ui.View
        Dialog view to load the configuration file of the fMRI pipeline
    """

    creation_mode = Enum("Load BIDS dataset", "Install Datalad BIDS dataset")
    install_datalad_dataset_via_ssh = Bool(True)
    ssh_user = String("remote_username")
    ssh_pwd = Password("")
    ssh_remote = String("IP address/ Machine name")
    datalad_dataset_path = Directory("/shared/path/to/existing/datalad/dataset")

    anat_runs = List()
    anat_run = Enum(values="anat_runs")

    dmri_runs = List()
    dmri_run = Enum(values="dmri_runs")

    fmri_runs = List()
    fmri_run = Enum(values="fmri_runs")

    summary_view_button = Button("Pipeline processing summary")

    pipeline_processing_summary_view = VGroup(Item("pipeline_processing_summary"))

    dataset_view = VGroup(
        VGroup(
            HGroup(
                Item(
                    "base_directory",
                    width=-0.3,
                    style="readonly",
                    label="",
                    resizable=True,
                ),
                Item(
                    "number_of_subjects",
                    width=-0.3,
                    style="readonly",
                    label="Number of participants",
                    resizable=True,
                ),
                "summary_view_button",
            ),
            label="BIDS Dataset",
        ),
        spring,
        HGroup(
            Group(Item("subject", style="simple", show_label=True, resizable=True)),
            Group(
                Item(
                    "subject_session", style="simple", label="Session", resizable=True
                ),
                visible_when='subject_session!=""',
            ),
            springy=True,
        ),
        spring,
        Group(
            Item("t1_available", style="readonly", label="T1", resizable=True),
            HGroup(
                Item(
                    "dmri_available",
                    style="readonly",
                    label="Diffusion",
                    resizable=True,
                ),
                Item(
                    "diffusion_imaging_model",
                    label="Model",
                    resizable=True,
                    enabled_when="dmri_available",
                ),
            ),
            Item("fmri_available", style="readonly", label="BOLD", resizable=True),
            label="Modalities",
        ),
        spring,
        Group(
            Item(
                "anat_last_date_processed",
                label="Anatomical pipeline",
                style="readonly",
                resizable=True,
                enabled_when="t1_available",
            ),
            Item(
                "dmri_last_date_processed",
                label="Diffusion pipeline",
                style="readonly",
                resizable=True,
                enabled_when="dmri_available",
            ),
            Item(
                "fmri_last_date_processed",
                label="fMRI pipeline",
                style="readonly",
                resizable=True,
                enabled_when="fmri_available",
            ),
            label="Last date processed",
        ),
        spring,
        Group(
            Item("number_of_cores", resizable=True), label="Processing configuration"
        ),
        "550",
        spring,
        springy=True,
    )

    traits_view = QtView(Include("dataset_view"))

    create_view = View(
        Item("creation_mode", style="custom"),
        Group(
            Group(
                Item("base_directory", label="BIDS Dataset"),
                visible_when='creation_mode=="Load BIDS dataset"',
            ),
            Group(
                Item("install_datalad_dataset_via_ssh"),
                visible_when='creation_mode=="Install Datalad/BIDS dataset"',
            ),
            Group(
                Item(
                    "ssh_remote",
                    label="Remote ssh server",
                    visible_when="install_datalad_dataset_via_ssh",
                ),
                Item(
                    "ssh_user",
                    label="Remote username",
                    visible_when="install_datalad_dataset_via_ssh",
                ),
                Item(
                    "ssh_pwd",
                    label="Remote password",
                    visible_when="install_datalad_dataset_via_ssh",
                ),
                Item(
                    "datalad_dataset_path",
                    label="Datalad/BIDS Dataset Path/URL to be installed",
                ),
                Item("base_directory", label="Installation directory"),
                visible_when='creation_mode=="Install Datalad/BIDS dataset"',
            ),
        ),
        kind="livemodal",
        title="Data creation: BIDS dataset selection",
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=["OK", "Cancel"],
    )

    subject_view = View(
        Group(Item("subject", label="Selected Subject")),
        kind="modal",
        title="Subject and session selection",
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=["OK", "Cancel"],
    )

    subject_session_view = View(
        Group(
            Item("subject", style="readonly", label="Selected Subject"),
            Item("subject_session", label="Selected Session"),
        ),
        kind="modal",
        title="Session selection",
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=["OK", "Cancel"],
    )

    dmri_bids_acq_view = View(
        Group(
            Item("dmri_bids_acq", label="Selected model"),
        ),
        kind="modal",
        title="Selection of diffusion acquisition model",
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=["OK", "Cancel"],
    )

    anat_warning_view = View(
        Group(
            Item("anat_warning_msg", style="readonly", show_label=False),
        ),
        title="Warning : Anatomical T1w data",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    anat_config_error_view = View(
        Group(
            Item("anat_config_error_msg", style="readonly", show_label=False),
        ),
        title="Error",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    dmri_warning_view = View(
        Group(
            Item("dmri_warning_msg", style="readonly", show_label=False),
        ),
        title="Warning : Diffusion MRI data",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    dmri_config_error_view = View(
        Group(
            Item("dmri_config_error_msg", style="readonly", show_label=False),
        ),
        title="Error",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    fmri_warning_view = View(
        Group(
            Item("fmri_warning_msg", style="readonly", show_label=False),
        ),
        title="Warning : fMRI data",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    fmri_config_error_view = View(
        Group(
            Item("fmri_config_error_msg", style="readonly", show_label=False),
        ),
        title="Error",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    open_view = View(
        Item("creation_mode", label="Mode"),
        Group(
            Item("install_datalad_dataset_via_ssh"),
            Item(
                "ssh_remote",
                label="Remote ssh server",
                visible_when="install_datalad_dataset_via_ssh",
            ),
            Item(
                "ssh_user",
                label="Remote username",
                visible_when="install_datalad_dataset_via_ssh",
            ),
            Item(
                "ssh_pwd",
                label="Remote password",
                visible_when="install_datalad_dataset_via_ssh",
            ),
            Item(
                "datalad_dataset_path",
                label="Datalad/BIDS Dataset Path/URL to be installed",
            ),
            Item("base_directory", label="Installation directory"),
            visible_when='creation_mode=="Install Datalad BIDS dataset"',
        ),
        Group(
            Item("base_directory", label="BIDS Dataset"),
            visible_when='creation_mode=="Load BIDS dataset"',
        ),
        kind="livemodal",
        title="BIDS Dataset Creation/Loading",
        # style_sheet=style_sheet,
        width=600,
        height=250,
        buttons=["OK", "Cancel"],
    )

    anat_select_config_to_load = View(
        Group(
            Item("anat_config_to_load_msg", style="readonly", show_label=False),
            Item(
                "anat_config_to_load",
                style="custom",
                editor=EnumEditor(name="anat_available_config"),
                show_label=False,
            ),
        ),
        title="Select configuration for anatomical pipeline",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    anat_custom_map_view = View(
        Group(
            Item(
                "anat_custom_last_stage",
                editor=EnumEditor(name="anat_stage_names"),
                style="custom",
                show_label=False,
            ),
        ),
        title="Select until which stage to process the anatomical pipeline.",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    diffusion_imaging_model_select_view = View(
        Group(
            Item("diffusion_imaging_model", label="Diffusion MRI modality"),
        ),
        title="Please select diffusion MRI modality",
        kind="modal",
        width=modal_width,
        buttons=["OK", "Cancel"],
    )

    dmri_select_config_to_load = View(
        Group(
            Item("dmri_config_to_load_msg", style="readonly", show_label=False),
        ),
        Item(
            "dmri_config_to_load",
            style="custom",
            editor=EnumEditor(name="dmri_available_config"),
            show_label=False,
        ),
        title="Select configuration for diffusion pipeline",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    dmri_custom_map_view = View(
        Group(
            Item(
                "dmri_custom_last_stage",
                editor=EnumEditor(name="dmri_stage_names"),
                style="custom",
                show_label=False,
            ),
        ),
        title="Select until which stage to process the diffusion pipeline.",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    fmri_select_config_to_load = View(
        Group(
            Item("fmri_config_to_load_msg", style="readonly", show_label=False),
        ),
        Item(
            "fmri_config_to_load",
            style="custom",
            editor=EnumEditor(name="fmri_available_config"),
            show_label=False,
        ),
        title="Select configuration for fMRI pipeline",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    fmri_custom_map_view = View(
        Group(
            Item(
                "fmri_custom_last_stage",
                editor=EnumEditor(name="fmri_stage_names"),
                style="custom",
                show_label=False,
            ),
        ),
        title="Select until which stage to process the fMRI pipeline.",
        kind="modal",
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=["OK", "Cancel"],
    )

    def _summary_view_button_fired(self):
        self.configure_traits(view="pipeline_processing_summary_view")