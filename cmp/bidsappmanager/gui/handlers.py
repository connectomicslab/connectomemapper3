import multiprocessing
import os
import shutil
from subprocess import Popen

from bids import BIDSLayout
from pyface.constant import OK
from pyface.file_dialog import FileDialog
from traits.has_traits import HasTraits
from traits.trait_types import Bool, Instance
from traitsui.handler import Handler
from traitsui.message import error

# Own imports
from cmtklib.config import (
    anat_save_config, get_anat_process_detail_json,
    dmri_save_config, fmri_save_config,
    get_dmri_process_detail_json, get_fmri_process_detail_json,
    anat_load_config_json, dmri_load_config_json,
    fmri_load_config_json, convert_config_ini_2_json
)
from cmtklib.process import run
from cmtklib.util import print_warning, print_error, print_blue

import cmp.bidsappmanager.project
from cmp.bidsappmanager.pipelines.anatomical import anatomical as anatomical_pipeline
from cmp.bidsappmanager.pipelines.diffusion import diffusion as diffusion_pipeline
from cmp.bidsappmanager.pipelines.functional import fMRI as fMRI_pipeline


class ConfigQualityWindowHandler(Handler):
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
        """Function that creates a new :class:`ProjectInfoUI` instance.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print("> Load Project")
        new_project = cmp.bidsappmanager.project.ProjectInfoUI()
        np_res = new_project.configure_traits(view="create_view")
        ui_info.ui.context["object"].handler = self

        if np_res and os.path.exists(new_project.base_directory):
            try:
                bids_layout = BIDSLayout(new_project.base_directory)
                new_project.bids_layout = bids_layout
                print(bids_layout)

                for subj in bids_layout.get_subjects():
                    if "sub-" + str(subj) not in new_project.subjects:
                        new_project.subjects.append("sub-" + str(subj))

                print("  .. INFO: Available subjects : ")
                print(new_project.subjects)
                new_project.number_of_subjects = len(new_project.subjects)

                np_res = new_project.configure_traits(view="subject_view")
                print("  .. INFO: Selected subject : " + new_project.subject)

                subject = new_project.subject.split("-")[1]
                new_project.subject_sessions = [""]
                new_project.subject_session = ""

                sessions = bids_layout.get(
                    target="session", return_type="id", subject=subject
                )

                if len(sessions) > 0:
                    print("Warning: multiple sessions")
                    for ses in sessions:
                        new_project.subject_sessions.append("ses-" + str(ses))
                    np_res = new_project.configure_traits(view="subject_session_view")
                    print(
                        "  .. INFO: Selected session : " + new_project.subject_session
                    )

            except Exception as e:
                msg = "Invalid BIDS dataset. Please see documentation for more details."
                print_warning(f"  .. EXCEPTION: {msg}")
                print_error(f"       : {e}")
                error(message=msg, title="BIDS error")
                return

            self.anat_pipeline = cmp.bidsappmanager.project.init_anat_project(new_project, True)
            if self.anat_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    ui_info.ui.context["object"].project_info = new_project
                    self.anat_pipeline.number_of_cores = new_project.number_of_cores
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context[
                        "object"
                    ].project_info.t1_available = self.anat_inputs_checked

                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_subject_anat_pipeline,
                        "subject",
                    )
                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_session_anat_pipeline,
                        "subject_session",
                    )
                    anat_save_config(
                        self.anat_pipeline,
                        ui_info.ui.context["object"].project_info.anat_config_file,
                    )
                    self.project_loaded = True

                    ui_info.ui.context[
                        "object"
                    ].project_info.parcellation_scheme = get_anat_process_detail_json(
                        new_project, "parcellation_stage", "parcellation_scheme"
                    )
                    ui_info.ui.context[
                        "object"
                    ].project_info.freesurfer_subjects_dir = get_anat_process_detail_json(
                        new_project, "segmentation_stage", "freesurfer_subjects_dir"
                    )
                    ui_info.ui.context[
                        "object"
                    ].project_info.freesurfer_subject_id = get_anat_process_detail_json(
                        new_project, "segmentation_stage", "freesurfer_subject_id"
                    )

                    dmri_inputs_checked, self.dmri_pipeline = cmp.bidsappmanager.project.init_dmri_project(
                        new_project, bids_layout, True
                    )
                    if self.dmri_pipeline is not None:
                        if dmri_inputs_checked:
                            self.dmri_pipeline.number_of_cores = (
                                new_project.number_of_cores
                            )
                            print(
                                "  .. INFO: Number of cores (pipeline) = %s"
                                % self.dmri_pipeline.number_of_cores
                            )
                            self.dmri_pipeline.parcellation_scheme = ui_info.ui.context[
                                "object"
                            ].project_info.parcellation_scheme
                            ui_info.ui.context[
                                "object"
                            ].dmri_pipeline = self.dmri_pipeline
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context[
                                    "object"
                                ].update_subject_dmri_pipeline,
                                "subject",
                            )
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context[
                                    "object"
                                ].update_session_dmri_pipeline,
                                "subject_session",
                            )
                            dmri_save_config(
                                self.dmri_pipeline,
                                ui_info.ui.context[
                                    "object"
                                ].project_info.dmri_config_file,
                            )
                            self.dmri_inputs_checked = dmri_inputs_checked
                            ui_info.ui.context[
                                "object"
                            ].project_info.dmri_available = self.dmri_inputs_checked
                            self.project_loaded = True
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context[
                                    "object"
                                ].update_diffusion_imaging_model,
                                "diffusion_imaging_model",
                            )

                    fmri_inputs_checked, self.fmri_pipeline = cmp.bidsappmanager.project.init_fmri_project(
                        new_project, bids_layout, True
                    )
                    if self.fmri_pipeline is not None:
                        if fmri_inputs_checked:
                            self.fmri_pipeline.number_of_cores = (
                                new_project.number_of_cores
                            )
                            print(
                                "  .. INFO: Number of cores (pipeline) = %s"
                                % self.fmri_pipeline.number_of_cores
                            )
                            self.fmri_pipeline.parcellation_scheme = ui_info.ui.context[
                                "object"
                            ].project_info.parcellation_scheme
                            self.fmri_pipeline.subjects_dir = ui_info.ui.context[
                                "object"
                            ].project_info.freesurfer_subjects_dir
                            self.fmri_pipeline.subject_id = ui_info.ui.context[
                                "object"
                            ].project_info.freesurfer_subject_id
                            ui_info.ui.context[
                                "object"
                            ].fmri_pipeline = self.fmri_pipeline
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context[
                                    "object"
                                ].update_subject_fmri_pipeline,
                                "subject",
                            )
                            ui_info.ui.context["object"].project_info.on_trait_change(
                                ui_info.ui.context[
                                    "object"
                                ].update_session_fmri_pipeline,
                                "subject_session",
                            )
                            fmri_save_config(
                                self.fmri_pipeline,
                                ui_info.ui.context[
                                    "object"
                                ].project_info.fmri_config_file,
                            )
                            self.fmri_inputs_checked = fmri_inputs_checked
                            ui_info.ui.context[
                                "object"
                            ].project_info.fmri_available = self.fmri_inputs_checked
                            self.project_loaded = True

    def load_project(self, ui_info):
        """Function that creates a new :class:`ProjectInfoUI` instance from an existing project.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print("> Load Project")
        loaded_project = cmp.bidsappmanager.project.ProjectInfoUI()
        np_res = loaded_project.configure_traits(view="open_view")
        ui_info.ui.context["object"].handler = self

        print("  .. INFO: BIDS directory: %s" % loaded_project.base_directory)
        try:
            bids_layout = BIDSLayout(loaded_project.base_directory)
            loaded_project.bids_layout = bids_layout

            loaded_project.subjects = []
            for subj in bids_layout.get_subjects():
                if "sub-" + str(subj) not in loaded_project.subjects:
                    loaded_project.subjects.append("sub-" + str(subj))
            loaded_project.subjects.sort()

            print("  .. INFO: Available subjects : ")
            print(loaded_project.subjects)
            loaded_project.number_of_subjects = len(loaded_project.subjects)

        except ValueError as e:
            msg = str(e)
            error(message=msg, title="BIDS error")
            return
        except Exception:
            error(
                message="Invalid BIDS dataset. Please see documentation for more details.",
                title="BIDS error",
            )
            return

        self.anat_inputs_checked = False

        if np_res and os.path.exists(loaded_project.base_directory):
            sessions = []
            for subj in bids_layout.get_subjects():
                subj_sessions = bids_layout.get(
                    target="session", return_type="id", subject=subj
                )
                for subj_session in subj_sessions:
                    sessions.append(subj_session)

            loaded_project.anat_available_config = []

            for subj in bids_layout.get_subjects():
                subj_sessions = bids_layout.get(
                    target="session", return_type="id", subject=subj
                )
                if len(subj_sessions) > 0:
                    for subj_session in subj_sessions:
                        config_file = os.path.join(
                            loaded_project.base_directory,
                            "derivatives",
                            "sub-%s_ses-%s_anatomical_config.json"
                            % (subj, subj_session),
                        )
                        if os.path.isfile(config_file):
                            loaded_project.anat_available_config.append(
                                "sub-%s_ses-%s" % (subj, subj_session)
                            )
                else:
                    config_file = os.path.join(
                        loaded_project.base_directory,
                        "derivatives",
                        "sub-%s_anatomical_config.json" % subj,
                    )
                    if os.path.isfile(config_file):
                        loaded_project.anat_available_config.append("sub-%s" % subj)

            if len(loaded_project.anat_available_config) > 1:
                loaded_project.anat_available_config.sort()
                loaded_project.anat_config_to_load = (
                    loaded_project.anat_available_config[0]
                )
                anat_config_selected = loaded_project.configure_traits(
                    view="anat_select_config_to_load"
                )

                if not anat_config_selected:
                    return 0
            else:
                loaded_project.anat_config_to_load = (
                    loaded_project.anat_available_config[0]
                )

            print(
                "  .. INFO: Anatomical config to load: %s"
                % loaded_project.anat_config_to_load
            )
            loaded_project.anat_config_file = os.path.join(
                loaded_project.base_directory,
                "derivatives",
                "%s_anatomical_config.json" % loaded_project.anat_config_to_load,
            )
            print(
                "  .. INFO: Anatomical config file: %s"
                % loaded_project.anat_config_file
            )

            loaded_project.subject = get_anat_process_detail_json(
                loaded_project, "Global", "subject"
            )
            loaded_project.subject_sessions = [
                "ses-%s" % s
                for s in bids_layout.get(
                    target="session",
                    return_type="id",
                    subject=loaded_project.subject.split("-")[1],
                )
            ]
            if len(loaded_project.subject_sessions) > 0:
                print("  .. INFO: Dataset has session(s)")
                loaded_project.subject_session = get_anat_process_detail_json(
                    loaded_project, "Global", "subject_session"
                )
                print("Selected session : " + loaded_project.subject_session)
            else:
                loaded_project.subject_sessions = [""]
                loaded_project.subject_session = ""
                print("  .. INFO: Dataset has no session")

            loaded_project.parcellation_scheme = get_anat_process_detail_json(
                loaded_project, "parcellation_stage", "parcellation_scheme"
            )
            loaded_project.atlas_info = get_anat_process_detail_json(
                loaded_project, "parcellation_stage", "atlas_info"
            )
            loaded_project.freesurfer_subjects_dir = get_anat_process_detail_json(
                loaded_project, "segmentation_stage", "freesurfer_subjects_dir"
            )
            loaded_project.freesurfer_subject_id = get_anat_process_detail_json(
                loaded_project, "segmentation_stage", "freesurfer_subject_id"
            )

            self.anat_pipeline = cmp.bidsappmanager.project.init_anat_project(loaded_project, False)
            if self.anat_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    cmp.bidsappmanager.project.update_anat_last_processed(
                        loaded_project, self.anat_pipeline
                    )  # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = loaded_project
                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_subject_anat_pipeline,
                        "subject",
                    )
                    ui_info.ui.context["object"].project_info.on_trait_change(
                        ui_info.ui.context["object"].update_session_anat_pipeline,
                        "subject_session",
                    )
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    ui_info.ui.context[
                        "object"
                    ].anat_pipeline.number_of_cores = ui_info.ui.context[
                        "object"
                    ].project_info.number_of_cores
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context[
                        "object"
                    ].project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(
                        self.anat_pipeline,
                        ui_info.ui.context["object"].project_info.anat_config_file,
                    )
                    self.project_loaded = True
                    self.anat_outputs_checked, _ = self.anat_pipeline.check_output()
                    if self.anat_outputs_checked:
                        print("  .. INFO: Available outputs")

            loaded_project.dmri_available_config = []

            subjid = loaded_project.subject.split("-")[1]
            subj_sessions = bids_layout.get(
                target="session", return_type="id", subject=subjid
            )

            if len(subj_sessions) > 0:
                for subj_session in subj_sessions:
                    config_file = os.path.join(
                        loaded_project.base_directory,
                        "derivatives",
                        "%s_ses-%s_diffusion_config.json"
                        % (loaded_project.subject, subj_session),
                    )
                    if (
                        os.path.isfile(config_file)
                        and subj_session == loaded_project.subject_session.split("-")[1]
                    ):
                        loaded_project.dmri_available_config.append(
                            "%s_ses-%s" % (loaded_project.subject, subj_session)
                        )
            else:
                config_file = os.path.join(
                    loaded_project.base_directory,
                    "derivatives",
                    "sub-%s_diffusion_config.json" % loaded_project.subject,
                )
                if os.path.isfile(config_file):
                    loaded_project.dmri_available_config.append(
                        "%s" % loaded_project.subject
                    )

            if len(loaded_project.dmri_available_config) > 1:
                loaded_project.dmri_available_config.sort()
                loaded_project.dmri_config_to_load = (
                    loaded_project.dmri_available_config[0]
                )
                dmri_config_selected = loaded_project.configure_traits(
                    view="dmri_select_config_to_load"
                )
                if not dmri_config_selected:
                    return 0
            elif not loaded_project.dmri_available_config:
                loaded_project.dmri_config_to_load = (
                    "%s_diffusion" % loaded_project.subject
                )
            else:
                loaded_project.dmri_config_to_load = (
                    loaded_project.dmri_available_config[0]
                )

            print(
                "  .. INFO: Diffusion config to load: %s"
                % loaded_project.dmri_config_to_load
            )
            loaded_project.dmri_config_file = os.path.join(
                loaded_project.base_directory,
                "derivatives",
                "%s_diffusion_config.json" % loaded_project.dmri_config_to_load,
            )
            print(
                "  .. INFO: Diffusion config file: %s" % loaded_project.dmri_config_file
            )

            if os.path.isfile(loaded_project.dmri_config_file):
                print("  .. INFO: Load existing diffusion config file")
                loaded_project.process_type = get_dmri_process_detail_json(
                    loaded_project, "Global", "process_type"
                )
                loaded_project.diffusion_imaging_model = get_dmri_process_detail_json(
                    loaded_project, "Global", "diffusion_imaging_model"
                )

                dmri_inputs_checked, self.dmri_pipeline = cmp.bidsappmanager.project.init_dmri_project(
                    loaded_project, bids_layout, False
                )
                if self.dmri_pipeline is not None:
                    if dmri_inputs_checked:
                        cmp.bidsappmanager.project.update_dmri_last_processed(loaded_project, self.dmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_dmri_pipeline,
                            "subject",
                        )
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_dmri_pipeline,
                            "subject_session",
                        )
                        self.dmri_pipeline.parcellation_scheme = (
                            loaded_project.parcellation_scheme
                        )
                        self.dmri_pipeline.atlas_info = loaded_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        ui_info.ui.context[
                            "object"
                        ].dmri_pipeline.number_of_cores = ui_info.ui.context[
                            "object"
                        ].project_info.number_of_cores
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context[
                            "object"
                        ].project_info.dmri_available = self.dmri_inputs_checked
                        dmri_save_config(
                            self.dmri_pipeline,
                            ui_info.ui.context["object"].project_info.dmri_config_file,
                        )
                        self.project_loaded = True
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_diffusion_imaging_model,
                            "diffusion_imaging_model",
                        )
            else:
                dmri_inputs_checked, self.dmri_pipeline = cmp.bidsappmanager.project.init_dmri_project(
                    loaded_project, bids_layout, True
                )
                print_warning(
                    "  .. WARNING: No existing config for diffusion pipeline found - "
                    + "Created new diffusion pipeline with default parameters"
                )
                if (
                    self.dmri_pipeline is not None
                ):  # and self.dmri_pipeline is not None:
                    if dmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_dmri_pipeline,
                            "subject",
                        )
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_dmri_pipeline,
                            "subject_session",
                        )
                        self.dmri_pipeline.number_of_cores = (
                            loaded_project.number_of_cores
                        )
                        print(
                            "  .. INFO: Number of cores (pipeline) = %s"
                            % self.dmri_pipeline.number_of_cores
                        )
                        self.dmri_pipeline.parcellation_scheme = (
                            loaded_project.parcellation_scheme
                        )
                        self.dmri_pipeline.atlas_info = loaded_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        dmri_save_config(
                            self.dmri_pipeline,
                            ui_info.ui.context["object"].project_info.dmri_config_file,
                        )
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context[
                            "object"
                        ].project_info.dmri_available = self.dmri_inputs_checked
                        self.project_loaded = True
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_diffusion_imaging_model,
                            "diffusion_imaging_model",
                        )

            if len(subj_sessions) > 0:
                for subj_session in subj_sessions:
                    config_file = os.path.join(
                        loaded_project.base_directory,
                        "derivatives",
                        "%s_ses-%s_fMRI_config.json"
                        % (loaded_project.subject, subj_session),
                    )
                    if (
                        os.path.isfile(config_file)
                        and subj_session == loaded_project.subject_session.split("-")[1]
                    ):
                        loaded_project.fmri_available_config.append(
                            "%s_ses-%s" % (loaded_project.subject, subj_session)
                        )
            else:
                config_file = os.path.join(
                    loaded_project.base_directory,
                    "derivatives",
                    "sub-%s_fMRI_config.json" % loaded_project.subject,
                )
                if os.path.isfile(config_file):
                    loaded_project.fmri_available_config.append(
                        "sub-%s" % loaded_project.subject
                    )

            if len(loaded_project.fmri_available_config) > 1:
                loaded_project.fmri_available_config.sort()
                loaded_project.fmri_config_to_load = (
                    loaded_project.fmri_available_config[0]
                )
                fmri_config_selected = loaded_project.configure_traits(
                    view="fmri_select_config_to_load"
                )
                if not fmri_config_selected:
                    return 0
            elif not loaded_project.fmri_available_config:
                loaded_project.fmri_config_to_load = "%s_fMRI" % loaded_project.subject
            else:
                loaded_project.fmri_config_to_load = (
                    loaded_project.fmri_available_config[0]
                )

            print(
                "  .. INFO: fMRI config to load: %s"
                % loaded_project.fmri_config_to_load
            )
            loaded_project.fmri_config_file = os.path.join(
                loaded_project.base_directory,
                "derivatives",
                "%s_fMRI_config.json" % loaded_project.fmri_config_to_load,
            )
            print("  .. INFO: fMRI config file: %s" % loaded_project.fmri_config_file)

            if os.path.isfile(loaded_project.fmri_config_file):
                print("  .. INFO: Load existing fmri config file")
                loaded_project.process_type = get_fmri_process_detail_json(
                    loaded_project, "Global", "process_type"
                )

                fmri_inputs_checked, self.fmri_pipeline = cmp.bidsappmanager.project.init_fmri_project(
                    loaded_project, bids_layout, False
                )
                if self.fmri_pipeline is not None:
                    if fmri_inputs_checked:
                        cmp.bidsappmanager.project.update_fmri_last_processed(loaded_project, self.fmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_fmri_pipeline,
                            "subject",
                        )
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_fmri_pipeline,
                            "subject_session",
                        )
                        self.fmri_pipeline.parcellation_scheme = (
                            loaded_project.parcellation_scheme
                        )
                        self.fmri_pipeline.atlas_info = loaded_project.atlas_info
                        self.fmri_pipeline.subjects_dir = (
                            loaded_project.freesurfer_subjects_dir
                        )
                        self.fmri_pipeline.subject_id = (
                            loaded_project.freesurfer_subject_id
                        )
                        ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        ui_info.ui.context[
                            "object"
                        ].fmri_pipeline.number_of_cores = ui_info.ui.context[
                            "object"
                        ].project_info.number_of_cores
                        self.fmri_inputs_checked = fmri_inputs_checked
                        ui_info.ui.context[
                            "object"
                        ].project_info.fmri_available = self.fmri_inputs_checked
                        fmri_save_config(
                            self.fmri_pipeline,
                            ui_info.ui.context["object"].project_info.fmri_config_file,
                        )
                        self.project_loaded = True
            else:
                fmri_inputs_checked, self.fmri_pipeline = cmp.bidsappmanager.project.init_fmri_project(
                    loaded_project, bids_layout, True
                )
                print_warning(
                    "  .. WARNING: No existing config for fMRI pipeline found - "
                    + "Created new fMRI pipeline with default parameters"
                )
                if self.fmri_pipeline is not None:
                    if fmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_subject_fmri_pipeline,
                            "subject",
                        )
                        ui_info.ui.context["object"].project_info.on_trait_change(
                            ui_info.ui.context["object"].update_session_fmri_pipeline,
                            "subject_session",
                        )
                        self.fmri_pipeline.number_of_cores = (
                            loaded_project.number_of_cores
                        )
                        print(
                            "  .. INFO: Number of cores (pipeline) = %s"
                            % self.fmri_pipeline.number_of_cores
                        )
                        self.fmri_pipeline.parcellation_scheme = (
                            loaded_project.parcellation_scheme
                        )
                        self.fmri_pipeline.atlas_info = loaded_project.atlas_info
                        self.fmri_pipeline.subjects_dir = (
                            loaded_project.freesurfer_subjects_dir
                        )
                        self.fmri_pipeline.subject_id = (
                            loaded_project.freesurfer_subject_id
                        )
                        ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        fmri_save_config(
                            self.fmri_pipeline,
                            ui_info.ui.context["object"].project_info.fmri_config_file,
                        )
                        self.fmri_inputs_checked = fmri_inputs_checked
                        ui_info.ui.context[
                            "object"
                        ].project_info.fmri_available = self.fmri_inputs_checked
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
            self.anat_pipeline.global_conf.subject_session = (
                updated_project.subject_session
            )
            self.anat_pipeline.subject_directory = os.path.join(
                updated_project.base_directory,
                updated_project.subject,
                updated_project.subject_session,
            )
            updated_project.anat_config_file = os.path.join(
                updated_project.base_directory,
                "derivatives",
                "%s_%s_anatomical_config.json"
                % (updated_project.subject, updated_project.subject_session),
            )
        else:
            self.anat_pipeline.global_conf.subject_session = ""
            self.anat_pipeline.subject_directory = os.path.join(
                updated_project.base_directory, updated_project.subject
            )
            updated_project.anat_config_file = os.path.join(
                updated_project.base_directory,
                "derivatives",
                "%s_anatomical_config.json" % updated_project.subject,
            )

        self.anat_pipeline.derivatives_directory = os.path.join(
            updated_project.base_directory, "derivatives"
        )

        if os.path.isfile(updated_project.anat_config_file):
            print(
                "  .. INFO: Existing anatomical config file for subject %s: %s"
                % (updated_project.subject, updated_project.anat_config_file)
            )

            updated_project.parcellation_scheme = get_anat_process_detail_json(
                updated_project, "parcellation_stage", "parcellation_scheme"
            )
            updated_project.atlas_info = get_anat_process_detail_json(
                updated_project, "parcellation_stage", "atlas_info"
            )
            updated_project.freesurfer_subjects_dir = get_anat_process_detail_json(
                updated_project, "segmentation_stage", "freesurfer_subjects_dir"
            )
            updated_project.freesurfer_subject_id = get_anat_process_detail_json(
                updated_project, "segmentation_stage", "freesurfer_subject_id"
            )

            self.anat_pipeline = cmp.bidsappmanager.project.init_anat_project(updated_project, False)
            if self.anat_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    cmp.bidsappmanager.project.update_anat_last_processed(
                        updated_project, self.anat_pipeline
                    )  # Not required as the project is new, so no update should be done on processing status
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_anat_pipeline, "subject"
                    )
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_anat_pipeline, "subject_session"
                    )
                    ui_info.anat_pipeline = self.anat_pipeline
                    ui_info.anat_pipeline.number_of_cores = (
                        ui_info.project_info.number_of_cores
                    )
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(
                        self.anat_pipeline, ui_info.project_info.anat_config_file
                    )
                    self.project_loaded = True
                    self.anat_outputs_checked, msg = self.anat_pipeline.check_output()
                    if self.anat_outputs_checked:
                        print("  .. INFO: Available outputs")

        else:
            print(
                "  .. INFO: Unprocessed anatomical data for subject %s"
                % updated_project.subject
            )
            self.anat_pipeline = cmp.bidsappmanager.project.init_anat_project(updated_project, True)
            if self.anat_pipeline is not None:  # and self.dmri_pipeline is not None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_anat_pipeline, "subject"
                    )
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_anat_pipeline, "subject_session"
                    )
                    self.anat_pipeline.number_of_cores = updated_project.number_of_cores
                    ui_info.anat_pipeline = self.anat_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(
                        self.anat_pipeline, ui_info.project_info.anat_config_file
                    )
                    self.project_loaded = True

            ui_info.project_info.parcellation_scheme = get_anat_process_detail_json(
                updated_project, "parcellation_stage", "parcellation_scheme"
            )
            ui_info.project_info.freesurfer_subjects_dir = get_anat_process_detail_json(
                updated_project, "segmentation_stage", "freesurfer_subjects_dir"
            )
            ui_info.project_info.freesurfer_subject_id = get_anat_process_detail_json(
                updated_project, "segmentation_stage", "freesurfer_subject_id"
            )

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
            self.dmri_pipeline.global_conf.subject_session = (
                updated_project.subject_session
            )
            self.dmri_pipeline.subject_directory = os.path.join(
                updated_project.base_directory,
                updated_project.subject,
                updated_project.subject_session,
            )
            updated_project.dmri_config_file = os.path.join(
                updated_project.base_directory,
                "derivatives",
                "%s_%s_diffusion_config.json"
                % (updated_project.subject, updated_project.subject_session),
            )
        else:
            self.dmri_pipeline.global_conf.subject_session = ""
            self.dmri_pipeline.subject_directory = os.path.join(
                updated_project.base_directory, updated_project.subject
            )
            updated_project.dmri_config_file = os.path.join(
                updated_project.base_directory,
                "derivatives",
                "%s_diffusion_config.json" % updated_project.subject,
            )

        self.dmri_pipeline.derivatives_directory = os.path.join(
            updated_project.base_directory, "derivatives"
        )

        if os.path.isfile(updated_project.dmri_config_file):
            print("  .. INFO: Load existing diffusion config file")
            updated_project.process_type = get_dmri_process_detail_json(
                updated_project, "Global", "process_type"
            )
            updated_project.diffusion_imaging_model = get_dmri_process_detail_json(
                updated_project, "diffusion_stage", "diffusion_imaging_model"
            )

            dmri_inputs_checked, self.dmri_pipeline = cmp.bidsappmanager.project.init_dmri_project(
                updated_project, bids_layout, False
            )
            if self.dmri_pipeline is not None:  # and self.dmri_pipeline is not None:
                if dmri_inputs_checked:
                    cmp.bidsappmanager.project.update_dmri_last_processed(updated_project, self.dmri_pipeline)
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_dmri_pipeline, "subject"
                    )
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_dmri_pipeline, "subject_session"
                    )
                    self.dmri_pipeline.parcellation_scheme = (
                        updated_project.parcellation_scheme
                    )
                    self.dmri_pipeline.atlas_info = updated_project.atlas_info
                    ui_info.dmri_pipeline = self.dmri_pipeline
                    ui_info.dmri_pipeline.number_of_cores = (
                        ui_info.project_info.number_of_cores
                    )
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.project_info.dmri_available = self.dmri_inputs_checked
                    dmri_save_config(
                        self.dmri_pipeline, ui_info.project_info.dmri_config_file
                    )
                    self.project_loaded = True
                    ui_info.project_info.on_trait_change(
                        ui_info.update_diffusion_imaging_model,
                        "diffusion_imaging_model",
                    )
        else:
            dmri_inputs_checked, self.dmri_pipeline = cmp.bidsappmanager.project.init_dmri_project(
                updated_project, bids_layout, True
            )
            print_warning(
                "  .. WARNING: No existing config for diffusion pipeline found - "
                + "Created new diffusion pipeline with default parameters"
            )
            if self.dmri_pipeline is not None:  # and self.dmri_pipeline is not None:
                if dmri_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_dmri_pipeline, "subject"
                    )
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_dmri_pipeline, "subject_session"
                    )
                    self.dmri_pipeline.number_of_cores = updated_project.number_of_cores
                    print(
                        "  .. INFO: Number of cores (pipeline) = %s"
                        % self.dmri_pipeline.number_of_cores
                    )
                    self.dmri_pipeline.parcellation_scheme = (
                        updated_project.parcellation_scheme
                    )
                    self.dmri_pipeline.atlas_info = updated_project.atlas_info
                    ui_info.dmri_pipeline = self.dmri_pipeline
                    dmri_save_config(
                        self.dmri_pipeline, ui_info.project_info.dmri_config_file
                    )
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.project_info.dmri_available = self.dmri_inputs_checked
                    self.project_loaded = True
                    ui_info.project_info.on_trait_change(
                        ui_info.update_diffusion_imaging_model,
                        "diffusion_imaging_model",
                    )

        return ui_info

    def update_subject_fmri_pipeline(self, ui_info):
        """Function that updates attributes of the :class:`fMRIPipelineUI` instance.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        ui_info.handler = self

        self.fmri_pipeline.subject = ui_info.project_info.subject
        self.fmri_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.fmri_pipeline.global_conf.subject_session = (
                updated_project.subject_session
            )
            self.fmri_pipeline.subject_directory = os.path.join(
                updated_project.base_directory,
                ui_info.project_info.subject,
                updated_project.subject_session,
            )
            updated_project.fmri_config_file = os.path.join(
                updated_project.base_directory,
                "derivatives",
                "%s_%s_fMRI_config.json"
                % (updated_project.subject, updated_project.subject_session),
            )
        else:
            self.fmri_pipeline.global_conf.subject_session = ""
            self.fmri_pipeline.subject_directory = os.path.join(
                updated_project.base_directory, ui_info.project_info.subject
            )
            updated_project.fmri_config_file = os.path.join(
                updated_project.base_directory,
                "derivatives",
                "%s_fMRI_config.json" % updated_project.subject,
            )

        self.fmri_pipeline.derivatives_directory = os.path.join(
            updated_project.base_directory, "derivatives"
        )

        print(
            "  .. INFO: fMRI config file loaded/created : %s"
            % updated_project.fmri_config_file
        )

        if os.path.isfile(updated_project.fmri_config_file):
            print(
                "  .. INFO: Load existing fMRI config file for subject %s"
                % updated_project.subject
            )
            updated_project.process_type = get_fmri_process_detail_json(
                updated_project, "Global", "process_type"
            )

            fmri_inputs_checked, self.fmri_pipeline = cmp.bidsappmanager.project.init_fmri_project(
                updated_project, bids_layout, False
            )
            if self.fmri_pipeline is not None:
                if fmri_inputs_checked:
                    cmp.bidsappmanager.project.update_fmri_last_processed(updated_project, self.fmri_pipeline)
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_fmri_pipeline, "subject"
                    )
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_fmri_pipeline, "subject_session"
                    )
                    self.fmri_pipeline.parcellation_scheme = (
                        updated_project.parcellation_scheme
                    )
                    self.fmri_pipeline.atlas_info = updated_project.atlas_info
                    self.fmri_pipeline.subjects_dir = (
                        updated_project.freesurfer_subjects_dir
                    )
                    self.fmri_pipeline.subject_id = (
                        updated_project.freesurfer_subject_id
                    )
                    ui_info.fmri_pipeline = self.fmri_pipeline

                    ui_info.fmri_pipeline.number_of_cores = (
                        ui_info.project_info.number_of_cores
                    )
                    self.fmri_inputs_checked = fmri_inputs_checked
                    ui_info.project_info.fmri_available = self.fmri_inputs_checked
                    fmri_save_config(
                        self.fmri_pipeline, ui_info.project_info.fmri_config_file
                    )
                    self.project_loaded = True
        else:
            fmri_inputs_checked, self.fmri_pipeline = cmp.bidsappmanager.project.init_fmri_project(
                updated_project, bids_layout, True
            )
            print_warning(
                "  .. WARNING: No existing config for fMRI pipeline found but available fMRI data - "
                + "Created new fMRI pipeline with default parameters"
            )
            if self.fmri_pipeline is not None:
                if fmri_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(
                        ui_info.update_subject_fmri_pipeline, "subject"
                    )
                    ui_info.project_info.on_trait_change(
                        ui_info.update_session_fmri_pipeline, "subject_session"
                    )
                    self.fmri_pipeline.number_of_cores = updated_project.number_of_cores
                    print(
                        "  .. INFO: Number of cores (pipeline) = %s"
                        % self.fmri_pipeline.number_of_cores
                    )
                    self.fmri_pipeline.parcellation_scheme = (
                        updated_project.parcellation_scheme
                    )
                    self.fmri_pipeline.atlas_info = updated_project.atlas_info
                    self.fmri_pipeline.subjects_dir = (
                        updated_project.freesurfer_subjects_dir
                    )
                    self.fmri_pipeline.subject_id = (
                        updated_project.freesurfer_subject_id
                    )
                    ui_info.fmri_pipeline = self.fmri_pipeline
                    fmri_save_config(
                        self.fmri_pipeline, ui_info.project_info.fmri_config_file
                    )
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
        print_blue("[Save anatomical pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_anatomical_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            anat_save_config(
                ui_info.ui.context["object"].anat_pipeline,
                ui_info.ui.context["object"].project_info.anat_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.anat_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.anat_config_file,
                    dialog.path,
                )

    def load_anat_config_file(self, ui_info):
        """Function that loads the anatomical pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*anatomical_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.anat_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.anat_config_file,
                )
            anat_load_config_json(
                self.anat_pipeline,
                ui_info.ui.context["object"].project_info.anat_config_file,
            )
            # TODO: load_config (anat_ or dmri_ ?)

    @classmethod
    def save_dmri_config_file(self, ui_info):
        """Function that saves the diffusion pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print_blue("[Save anatomical pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_diffusion_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            dmri_save_config(
                ui_info.ui.context["object"].dmri_pipeline,
                ui_info.ui.context["object"].project_info.dmri_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.dmri_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.dmri_config_file,
                    dialog.path,
                )

    def load_dmri_config_file(self, ui_info):
        """Function that loads the diffusion pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*diffusion_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.dmri_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.dmri_config_file,
                )
            dmri_load_config_json(
                self.dmri_pipeline,
                ui_info.ui.context["object"].project_info.dmri_config_file,
            )

    @classmethod
    def save_fmri_config_file(self, ui_info):
        """Function that saves the fMRI pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print_blue("[Save anatomical pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_fMRI_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            fmri_save_config(
                ui_info.ui.context["object"].fmri_pipeline,
                ui_info.ui.context["object"].project_info.fmri_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.fmri_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.fmri_config_file,
                    dialog.path,
                )

    def load_fmri_config_file(self, ui_info):
        """Function that loads the fMRI pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*diffusion_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.fmri_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.fmri_config_file,
                )
            fmri_load_config_json(
                self.fmri_pipeline,
                ui_info.ui.context["object"].project_info.fmri_config_file,
            )


class MainWindowHandler(Handler):
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

    def load_dataset(self, ui_info, debug=False):
        """Function that creates a new :class:`ProjectInfoUI` instance from an existing project.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``

        debug : bool
            If True, print more information for debugging
        """
        loaded_project = cmp.bidsappmanager.project.ProjectInfoUI()
        np_res = loaded_project.configure_traits(view="open_view")
        loaded_project.output_directory = os.path.join(
            loaded_project.base_directory, "derivatives"
        )

        if loaded_project.creation_mode == "Install Datalad BIDS dataset":
            datalad_is_available = cmp.bidsappmanager.project.is_tool("datalad")

            if datalad_is_available:
                print(">>> Datalad dataset installation...")
                if loaded_project.install_datalad_dataset_via_ssh:
                    if loaded_project.ssh_pwd != "":
                        os.environ["REMOTEUSERPWD"] = loaded_project.ssh_pwd
                        cmd = 'datalad install -D "Dataset {} (remote:{}) installed on {}" -s ssh://{}:$REMOTEUSERPWD@{}:{} {}'.format(
                            loaded_project.datalad_dataset_path,
                            loaded_project.ssh_remote,
                            loaded_project.base_directory,
                            loaded_project.ssh_user,
                            loaded_project.ssh_remote,
                            loaded_project.datalad_dataset_path,
                            loaded_project.base_directory,
                        )
                    else:
                        cmd = 'datalad install -D "Dataset {} (remote:{}) installed on {}" -s ssh://{}@{}:{} {}'.format(
                            loaded_project.datalad_dataset_path,
                            loaded_project.ssh_remote,
                            loaded_project.base_directory,
                            loaded_project.ssh_user,
                            loaded_project.ssh_remote,
                            loaded_project.datalad_dataset_path,
                            loaded_project.base_directory,
                        )
                    try:
                        print_blue("... cmd: {}".format(cmd))
                        run(
                            cmd,
                            env={},
                            cwd=os.path.abspath(loaded_project.base_directory),
                        )
                        del os.environ["REMOTEUSERPWD"]
                    except Exception:
                        print("    ERROR: Failed to install datalad dataset via ssh")
                        del os.environ["REMOTEUSERPWD"]
                else:
                    cmd = 'datalad install -D "Dataset {} installed on {}" -s {} {}'.format(
                        loaded_project.datalad_dataset_path,
                        loaded_project.base_directory,
                        loaded_project.datalad_dataset_path,
                        loaded_project.base_directory,
                    )
                    try:
                        print_blue("... cmd: {}".format(cmd))
                        run(
                            cmd,
                            env={},
                            cwd=os.path.abspath(loaded_project.base_directory),
                        )
                    except Exception:
                        print("    ERROR: Failed to install datalad dataset via ssh")
            else:
                print("    ERROR: Datalad is not installed!")

            # Install dataset via datalad
            # datalad install -s ssh://user@IP_ADDRESS:/remote/path/to/ds-example /local/path/to/ds-example
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
                    if "sub-" + str(subj) not in loaded_project.subjects:
                        loaded_project.subjects.append("sub-" + str(subj))
                # loaded_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
                loaded_project.subjects.sort()

                if debug:
                    print("Available subjects : ")
                    print(loaded_project.subjects)
                loaded_project.number_of_subjects = len(loaded_project.subjects)

                loaded_project.subject = loaded_project.subjects[0]
                if debug:
                    print(loaded_project.subject)

                subject = loaded_project.subject.split("-")[1]

                sessions = bids_layout.get(
                    target="session", return_type="id", subject=subject
                )

                if debug:
                    print("Sessions: ")
                    print(sessions)

                if len(sessions) > 0:
                    loaded_project.subject_sessions = ["ses-{}".format(sessions[0])]
                    loaded_project.subject_session = "ses-{}".format(sessions[0])
                else:
                    loaded_project.subject_sessions = [""]
                    loaded_project.subject_session = ""

                if len(sessions) > 0:
                    print(
                        f"    ... Check for available input modalities for subject {subject} of session {sessions[0]}..."
                    )

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="bold",
                            extensions=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available BOLD(s): {}".format(query_files))
                        fmri_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="T1w",
                            extensions=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T1w(s): {}".format(query_files))
                        t1_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="T2w",
                            extensions=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T2w(s): {}".format(query_files))
                        t2_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="dwi",
                            extensions=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available DWI(s): {}".format(query_files))
                        diffusion_available = True

                else:
                    print(
                        f"    ... Check for available input modalities for subject {subject}..."
                    )
                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="T1w", extensions=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T1w(s): {}".format(query_files))
                        t1_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="T2w", extensions=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T2w(s): {}".format(query_files))
                        t2_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="dwi", extensions=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available DWI(s): {}".format(query_files))
                        diffusion_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="bold", extensions=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available BOLD(s): {}".format(query_files))
                        fmri_available = True
            except ValueError as e:
                msg = str(e)
                error(message=msg, title="BIDS error")
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

            if t2_available and debug:
                print("T2 available")

            fmri_inputs_checked = False
            if t1_available and fmri_available:
                fmri_inputs_checked = True
                if debug:
                    print("fmri input check : {}".format(fmri_inputs_checked))

            self.anat_inputs_checked = anat_inputs_checked
            self.dmri_inputs_checked = dmri_inputs_checked
            self.fmri_inputs_checked = fmri_inputs_checked

            if anat_inputs_checked:

                self.anat_pipeline = anatomical_pipeline.AnatomicalPipelineUI(
                    loaded_project
                )
                self.anat_pipeline.number_of_cores = loaded_project.number_of_cores

                code_directory = os.path.join(loaded_project.base_directory, "code")

                anat_config_file = os.path.join(
                    code_directory, "ref_anatomical_config.json"
                )

                # Check for old configuration file with INI format
                # when there is no existing json configuration file
                # and convert it to JSON format if so
                if not os.path.isfile(anat_config_file):
                    anat_config_ini_file = os.path.join(
                        code_directory, "ref_anatomical_config.ini"
                    )
                    if os.path.isfile(anat_config_ini_file):
                        anat_config_file = convert_config_ini_2_json(
                            anat_config_ini_file
                        )

                loaded_project.anat_config_file = anat_config_file

                if self.anat_pipeline is not None and not os.path.isfile(
                    anat_config_file
                ):
                    if not os.path.exists(code_directory):
                        try:
                            os.makedirs(code_directory)
                        except os.error:
                            print_warning("%s was already existing" % code_directory)
                        finally:
                            print("Created directory %s" % code_directory)

                    print(">> Create new reference anatomical config file...")
                    anat_save_config(
                        self.anat_pipeline, loaded_project.anat_config_file
                    )
                else:
                    print(">> Load reference anatomical config file...")
                    # if datalad_is_available:
                    #     print('... Datalad get anatomical config file : {}'.format(loaded_project.anat_config_file))
                    #     cmd = 'datalad run -m "Get reference anatomical config file" bash -c "datalad get code/ref_anatomical_config.json"'
                    #     try:
                    #         print('... cmd: {}'.format(cmd))
                    #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                    #     except Exception:
                    #         print("    ERROR: Failed to get file")

                    anat_load_config_json(
                        self.anat_pipeline, loaded_project.anat_config_file
                    )

                self.anat_pipeline.config_file = loaded_project.anat_config_file

                ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                loaded_project.t1_available = self.anat_inputs_checked

                loaded_project.parcellation_scheme = self.anat_pipeline.stages[
                    "Parcellation"
                ].config.parcellation_scheme
                loaded_project.freesurfer_subjects_dir = self.anat_pipeline.stages[
                    "Segmentation"
                ].config.freesurfer_subjects_dir
                loaded_project.freesurfer_subject_id = self.anat_pipeline.stages[
                    "Segmentation"
                ].config.freesurfer_subject_id

                ui_info.ui.context["object"].project_info = loaded_project

                self.project_loaded = True

                if dmri_inputs_checked:
                    self.dmri_pipeline = diffusion_pipeline.DiffusionPipelineUI(
                        loaded_project
                    )
                    self.dmri_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.dmri_pipeline.parcellation_scheme = ui_info.ui.context[
                        "object"
                    ].project_info.parcellation_scheme

                    code_directory = os.path.join(loaded_project.base_directory, "code")
                    dmri_config_file = os.path.join(
                        code_directory, "ref_diffusion_config.json"
                    )

                    # Check for old configuration file with INI format
                    # when there is no existing json configuration file
                    # and convert it to JSON format if so
                    if not os.path.isfile(dmri_config_file):
                        dmri_config_ini_file = os.path.join(
                            code_directory, "ref_diffusion_config.ini"
                        )
                        if os.path.isfile(dmri_config_ini_file):
                            dmri_config_file = convert_config_ini_2_json(
                                dmri_config_ini_file
                            )

                    loaded_project.dmri_config_file = dmri_config_file
                    self.dmri_pipeline.config_file = dmri_config_file

                    if (
                        not os.path.isfile(dmri_config_file)
                        and self.dmri_pipeline is not None
                    ):

                        # Look for diffusion acquisition model information from filename (acq-*)
                        if loaded_project.subject_session != "":
                            session = loaded_project.subject_session.split("-")[1]
                            diffusion_imaging_models = [
                                i
                                for i in bids_layout.get(
                                    subject=subject,
                                    session=session,
                                    suffix="dwi",
                                    target="acquisition",
                                    return_type="id",
                                    extensions=["nii", "nii.gz"],
                                )
                            ]
                            if debug:
                                print(
                                    "DIFFUSION IMAGING MODELS : {}".format(
                                        diffusion_imaging_models
                                    )
                                )

                            if len(diffusion_imaging_models) > 0:
                                if len(diffusion_imaging_models) > 1:
                                    loaded_project.dmri_bids_acqs = (
                                        diffusion_imaging_models
                                    )
                                    loaded_project.configure_traits(
                                        view="dmri_bids_acq_view"
                                    )
                                else:
                                    loaded_project.dmri_bids_acqs = [
                                        "{}".format(diffusion_imaging_models[0])
                                    ]
                                    loaded_project.dmri_bids_acq = (
                                        diffusion_imaging_models[0]
                                    )

                                if ("dsi" in loaded_project.dmri_bids_acq) or (
                                    "DSI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DSI"
                                elif ("dti" in loaded_project.dmri_bids_acq) or (
                                    "DTI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DTI"
                                elif ("hardi" in loaded_project.dmri_bids_acq) or (
                                    "HARDI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "HARDI"
                                elif ("multishell" in loaded_project.dmri_bids_acq) or (
                                    "MULTISHELL" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = (
                                        "multishell"
                                    )
                                else:
                                    loaded_project.diffusion_imaging_model = "DTI"
                            else:
                                loaded_project.dmri_bids_acqs = [""]
                                loaded_project.dmri_bids_acq = ""
                                loaded_project.configure_traits(
                                    view="diffusion_imaging_model_select_view"
                                )

                            files = [
                                f.filename
                                for f in bids_layout.get(
                                    subject=subject,
                                    session=session,
                                    suffix="dwi",
                                    extensions=["nii", "nii.gz"],
                                )
                            ]

                            if debug:
                                print("****************************************")
                                print(files)
                                print("****************************************")

                            if loaded_project.dmri_bids_acq != "":
                                for file in files:
                                    if loaded_project.dmri_bids_acq in file:
                                        dwi_file = file
                                        if debug:
                                            print(
                                                "Loaded DWI file: {}".format(dwi_file)
                                            )
                                        break
                            else:
                                dwi_file = files[0]
                        else:
                            diffusion_imaging_models = [
                                i
                                for i in bids_layout.get(
                                    subject=subject,
                                    suffix="dwi",
                                    target="acquisition",
                                    return_type="id",
                                    extensions=["nii", "nii.gz"],
                                )
                            ]

                            if len(diffusion_imaging_models) > 0:
                                if len(diffusion_imaging_models) > 1:
                                    loaded_project.dmri_bids_acqs = (
                                        diffusion_imaging_models
                                    )
                                    loaded_project.configure_traits(
                                        view="dmri_bids_acq_view"
                                    )
                                else:
                                    loaded_project.dmri_bids_acq = (
                                        diffusion_imaging_models[0]
                                    )

                                if ("dsi" in loaded_project.dmri_bids_acq) or (
                                    "DSI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DSI"
                                elif ("dti" in loaded_project.dmri_bids_acq) or (
                                    "DTI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DTI"
                                elif ("hardi" in loaded_project.dmri_bids_acq) or (
                                    "HARDI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "HARDI"
                                elif ("multishell" in loaded_project.dmri_bids_acq) or (
                                    "MULTISHELL" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = (
                                        "multishell"
                                    )
                                else:
                                    loaded_project.diffusion_imaging_model = "DTI"
                            else:
                                loaded_project.dmri_bids_acqs = [""]
                                loaded_project.dmri_bids_acq = ""
                                loaded_project.configure_traits(
                                    view="diffusion_imaging_model_select_view"
                                )

                        self.dmri_pipeline.diffusion_imaging_model = (
                            loaded_project.diffusion_imaging_model
                        )
                        self.dmri_pipeline.global_conf.diffusion_imaging_model = (
                            loaded_project.diffusion_imaging_model
                        )
                        self.dmri_pipeline.global_conf.dmri_bids_acq = (
                            loaded_project.dmri_bids_acq
                        )
                        self.dmri_pipeline.stages[
                            "Diffusion"
                        ].diffusion_imaging_model = (
                            loaded_project.diffusion_imaging_model
                        )
                        print(">> Create new reference diffusion config file...")
                        dmri_save_config(self.dmri_pipeline, dmri_config_file)
                    else:
                        print(">> Load reference diffusion config file...")

                        # if datalad_is_available:
                        #     print('... Datalad get reference diffusion config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference anatomical config file" bash -c "datalad get code/ref_diffusion_config.json"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        dmri_load_config_json(
                            self.dmri_pipeline, loaded_project.dmri_config_file
                        )
                        # TODO: check if diffusion imaging model (DSI/DTI/HARDI/multishell) is correct/valid.

                    ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    loaded_project.dmri_available = self.dmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True

                if fmri_inputs_checked:
                    self.fmri_pipeline = fMRI_pipeline.fMRIPipelineUI(loaded_project)
                    self.fmri_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.fmri_pipeline.parcellation_scheme = ui_info.ui.context[
                        "object"
                    ].project_info.parcellation_scheme

                    self.fmri_pipeline.stages["Registration"].pipeline_mode = "fMRI"
                    self.fmri_pipeline.stages[
                        "Registration"
                    ].registration_mode = "FSL (Linear)"
                    self.fmri_pipeline.stages[
                        "Registration"
                    ].registration_mode_trait = ["FSL (Linear)", "BBregister (FS)"]

                    code_directory = os.path.join(loaded_project.base_directory, "code")
                    fmri_config_file = os.path.join(
                        code_directory, "ref_fMRI_config.json"
                    )

                    # Check for old configuration file with INI format
                    # when there is no existing json configuration file
                    # and convert it to JSON format if so
                    if not os.path.isfile(fmri_config_file):
                        fmri_config_ini_file = os.path.join(
                            code_directory, "ref_fMRI_config.ini"
                        )
                        if os.path.isfile(fmri_config_ini_file):
                            fmri_config_file = convert_config_ini_2_json(
                                fmri_config_ini_file
                            )

                    loaded_project.fmri_config_file = fmri_config_file
                    self.fmri_pipeline.config_file = fmri_config_file

                    if (
                        not os.path.isfile(fmri_config_file)
                        and self.fmri_pipeline is not None
                    ):
                        print(">> Create new reference fMRI config file...")
                        fmri_save_config(self.fmri_pipeline, fmri_config_file)
                    else:
                        print(">> Load reference fMRI config file...")

                        # if datalad_is_available:
                        #     print('... Datalad get reference fMRI config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference fMRI config file" bash -c "datalad get code/ref_fMRI_config.json"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        fmri_load_config_json(
                            self.fmri_pipeline, loaded_project.fmri_config_file
                        )

                    ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                    loaded_project.fmri_available = self.fmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True


class BIDSAppInterfaceWindowHandler(Handler):
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
            print(
                "BIDS root directory : {}".format(
                    ui_info.ui.context["object"].bids_root
                )
            )
        else:
            print_error("Error: BIDS root invalid!")
            ui_info.ui.context["object"].settings_checked = False

        if os.path.isfile(ui_info.ui.context["object"].anat_config):
            print(
                "Anatomical configuration file : {}".format(
                    ui_info.ui.context["object"].anat_config
                )
            )
        else:
            print_error(
                "Error: Configuration file for anatomical pipeline not existing!"
            )
            ui_info.ui.context["object"].settings_checked = False

        if os.path.isfile(ui_info.ui.context["object"].dmri_config):
            print(
                "Diffusion configuration file : {}".format(
                    ui_info.ui.context["object"].dmri_config
                )
            )
        else:
            print_warning(
                "Warning: Configuration file for diffusion pipeline not existing!"
            )

        if os.path.isfile(ui_info.ui.context["object"].fmri_config):
            print(
                "fMRI configuration file : {}".format(
                    ui_info.ui.context["object"].fmri_config
                )
            )
        else:
            print_warning("Warning: Configuration file for fMRI pipeline not existing!")

        if os.path.isfile(ui_info.ui.context["object"].fs_license):
            print(
                "Freesurfer license : {}".format(
                    ui_info.ui.context["object"].fs_license
                )
            )
        else:
            print_error(
                "Error: Invalid Freesurfer license ({})!".format(
                    ui_info.ui.context["object"].fs_license
                )
            )
            ui_info.ui.context["object"].settings_checked = False

        msg = f'Valid inputs for BIDS App : {ui_info.ui.context["object"].settings_checked}'
        if ui_info.ui.context["object"].settings_checked:
            print(msg)
        else:
            print_error(msg)

        print("Docker running ? {}".format(ui_info.ui.context["object"].docker_running))
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
        cmd = [
            "docker",
            "run",
            "-it",
            "--rm",
            "-v",
            "{}:/bids_dataset".format(ui_info.ui.context["object"].bids_root),
            "-v",
            "{}/derivatives:/outputs".format(ui_info.ui.context["object"].bids_root),
            # '-v', '{}:/bids_dataset/derivatives/freesurfer/fsaverage'.format(ui_info.ui.context["object"].fs_average),
            "-v",
            "{}:/opt/freesurfer/license.txt".format(
                ui_info.ui.context["object"].fs_license
            ),
            "-v",
            "{}:/code/ref_anatomical_config.json".format(
                ui_info.ui.context["object"].anat_config
            ),
        ]

        if ui_info.ui.context["object"].run_dmri_pipeline:
            cmd.append("-v")
            cmd.append(
                "{}:/code/ref_diffusion_config.json".format(
                    ui_info.ui.context["object"].dmri_config
                )
            )

        if ui_info.ui.context["object"].run_fmri_pipeline:
            cmd.append("-v")
            cmd.append(
                "{}:/code/ref_fMRI_config.json".format(
                    ui_info.ui.context["object"].fmri_config
                )
            )

        cmd.append("-u")
        cmd.append("{}:{}".format(os.geteuid(), os.getegid()))

        cmd.append("sebastientourbier/connectomemapper-bidsapp:latest")
        cmd.append("/bids_dataset")
        cmd.append("/outputs")
        cmd.append("participant")

        cmd.append("--participant_label")
        cmd.append("{}".format(participant_label))

        cmd.append("--anat_pipeline_config")
        cmd.append("/code/ref_anatomical_config.json")

        if ui_info.ui.context["object"].run_dmri_pipeline:
            cmd.append("--dwi_pipeline_config")
            cmd.append("/code/ref_diffusion_config.json")

        if ui_info.ui.context["object"].run_fmri_pipeline:
            cmd.append("--func_pipeline_config")
            cmd.append("/code/ref_fMRI_config.json")

        print_blue(" ".join(cmd))

        log_filename = os.path.join(
            ui_info.ui.context["object"].bids_root,
            "derivatives/cmp",
            "sub-{}_log-cmpbidsapp.txt".format(participant_label),
        )

        with open(log_filename, "w+") as log:
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
        print("[Start BIDS App]")

        maxprocs = multiprocessing.cpu_count()
        processes = []

        ui_info.ui.context["object"].docker_running = True

        for label in ui_info.ui.context["object"].list_of_subjects_to_be_processed:
            while len(processes) == maxprocs:
                self.manage_bidsapp_procs(processes)

            proc = self.start_bidsapp_process(ui_info, label=label)
            processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        print("Processing with BIDS App Finished")

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