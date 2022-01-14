# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper Output Quality Inspector Window."""

# General imports
import os

from traitsui.qt4.extra.qt_view import QtView
from traitsui.api import *
from traits.api import *

from bids import BIDSLayout

# Own imports
import cmp.project

from cmtklib.bids.io import (
    __cmp_directory__, __freesurfer_directory__
)
from cmtklib.util import (
    BColors,
    print_blue,
    print_error,
)

import cmp.bidsappmanager.project as project
import cmp.bidsappmanager.gui.handlers
from cmp.bidsappmanager.gui.globals import (
    style_sheet, get_icon
)


class QualityInspectorWindow(HasTraits):
    """Class that defines the Quality Inspector Window.

    Attributes
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of :class:`CMP_Project_Info` that represents the processing project

    anat_pipeline : Instance(HasTraits)
        Instance of anatomical MRI pipeline

    dmri_pipeline : Instance(HasTraits)
        Instance of diffusion MRI pipeline

    fmri_pipeline : Instance(HasTraits)
        Instance of functional MRI pipeline

    anat_inputs_checked : traits.Bool
        Indicates if inputs of anatomical pipeline are available
        (Default: False)

    dmri_inputs_checked : traits.Bool
        Indicates if inputs of diffusion pipeline are available
        (Default: False)

    fmri_inputs_checked : traits.Bool
        Indicates if inputs of functional pipeline are available
        (Default: False)

    output_anat_available : traits.Bool
        Indicates if outputs of anatomical pipeline are available
        (Default: False)

    output_dmri_available : traits.Bool
        Indicates if outputs of diffusion pipeline are available
        (Default: False)

    output_fmri_available : traits.Bool
        Indicates if outputs of functional pipeline are available
        (Default: False)

    traits_view : QtView
        TraitsUI QtView that describes the content of the window
    """
    project_info = Instance(cmp.project.ProjectInfo)

    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    anat_inputs_checked = Bool(False)
    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    output_anat_available = Bool(False)
    output_dmri_available = Bool(False)
    output_fmri_available = Bool(False)

    traits_view = QtView(
        Group(
            # Group(
            #     # Include('dataset_view'),label='Data manager',springy=True
            #     Item('project_info',style='custom',show_label=False),label='Data manager',springy=True, dock='tab'
            # ),
            Group(
                Item("anat_pipeline", style="custom", show_label=False),
                visible_when="output_anat_available",
                label="Anatomical pipeline",
                dock="tab",
            ),
            Group(
                Item(
                    "dmri_pipeline",
                    style="custom",
                    show_label=False,
                    visible_when="output_dmri_available",
                ),
                label="Diffusion pipeline",
                dock="tab",
            ),
            Group(
                Item(
                    "fmri_pipeline",
                    style="custom",
                    show_label=False,
                    visible_when="output_fmri_available",
                ),
                label="fMRI pipeline",
                dock="tab",
            ),
            orientation="horizontal",
            layout="tabbed",
            springy=True,
            enabled_when="output_anat_available",
        ),
        title="Connectome Mapper 3 Inspector",
        menubar=MenuBar(
            Menu(
                ActionGroup(
                    Action(name="Quit", action="_on_close"),
                ),
                name="File",
            ),
        ),
        handler=cmp.bidsappmanager.gui.handlers.ConfigQualityWindowHandler(),
        style_sheet=style_sheet,
        width=0.5,
        height=0.8,
        resizable=True,  # scrollable=True,
        icon=get_icon("qualitycontrol.png"),
    )

    error_msg = Str("")
    error_view = View(
        Group(
            Item("error_msg", style="readonly", show_label=False),
        ),
        title="Error",
        kind="modal",
        # style_sheet=style_sheet,
        buttons=["OK"],
    )

    def __init__(
        self,
        project_info=None,
        anat_inputs_checked=False,
        dmri_inputs_checked=False,
        fmri_inputs_checked=False,
    ):
        """Constructor of an :class:``PipelineConfiguratorWindow`` instance.

        Parameters
        ----------
        project_info : cmp.project.ProjectInfo
            :class:`CMP_Project_Info` object (Default: None)

        anat_inputs_checked : traits.Bool
            Boolean that indicates if anatomical pipeline inputs are available
            (Default: False)

        dmri_inputs_checked = : traits.Bool
            Boolean that indicates if diffusion pipeline inputs are available
            (Default: False)

        fmri_inputs_checked : traits.Bool
            Boolean that indicates if functional pipeline inputs are available
            (Default: False)
        """
        print("> Initialize window...")
        self.project_info = project_info

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        aborded = self.select_subject()

        if aborded:
            raise Exception(
                BColors.FAIL
                + " .. ABORDED: The quality control window will not be displayed."
                + "Selection of subject/session was cancelled at initialization."
                + BColors.ENDC
            )

    def select_subject(self):
        """Function to select the subject and session for which to inspect outputs."""
        print("> Selection of subject (and session) for which to inspect outputs")
        valid_selected_subject = False
        select = True
        aborded = False

        while not valid_selected_subject and not aborded:

            # Select subject from BIDS dataset
            np_res = self.project_info.configure_traits(view="subject_view")

            if not np_res:
                aborded = True
                break

            print("  .. INFO: Selected subject: {}".format(self.project_info.subject))

            # Select session if any
            bids_layout = BIDSLayout(self.project_info.base_directory)
            subject = self.project_info.subject.split("-")[1]

            sessions = bids_layout.get(
                target="session", return_type="id", subject=subject
            )

            if len(sessions) > 0:
                print("  .. INFO: Input dataset has sessions")
                print(sessions)

                self.project_info.subject_sessions = []

                for ses in sessions:
                    self.project_info.subject_sessions.append("ses-" + str(ses))

                np_res = self.project_info.configure_traits(view="subject_session_view")

                if not np_res:
                    aborded = True
                    break

                self.project_info.anat_config_file = os.path.join(
                    self.project_info.base_directory,
                    "derivatives",
                    __cmp_directory__,
                    "{}".format(self.project_info.subject),
                    "{}".format(self.project_info.subject_session),
                    "{}_{}_anatomical_config.json".format(
                        self.project_info.subject, self.project_info.subject_session
                    ),
                )
                if os.access(self.project_info.anat_config_file, os.F_OK):
                    print("> Initialize anatomical pipeline")
                    self.anat_pipeline = project.init_anat_project(
                        self.project_info, False
                    )
                else:
                    self.anat_pipeline = None

                if self.dmri_inputs_checked:
                    self.project_info.dmri_config_file = os.path.join(
                        self.project_info.base_directory,
                        "derivatives",
                        __cmp_directory__,
                        "{}".format(self.project_info.subject),
                        "{}".format(self.project_info.subject_session),
                        "{}_{}_diffusion_config.json".format(
                            self.project_info.subject, self.project_info.subject_session
                        ),
                    )
                    if os.access(self.project_info.dmri_config_file, os.F_OK):
                        print("> Initialize diffusion pipeline")
                        (
                            dmri_valid_inputs,
                            self.dmri_pipeline,
                        ) = project.init_dmri_project(
                            self.project_info, bids_layout, False
                        )
                    else:
                        self.dmri_pipeline = None

                    # self.dmri_pipeline.subject = self.project_info.subject
                    # self.dmri_pipeline.global_conf.subject = self.project_info.subject

                if self.fmri_inputs_checked:
                    self.project_info.fmri_config_file = os.path.join(
                        self.project_info.base_directory,
                        "derivatives",
                        __cmp_directory__,
                        "{}".format(self.project_info.subject),
                        "{}".format(self.project_info.subject_session),
                        "{}_{}_fMRI_config.json".format(
                            self.project_info.subject, self.project_info.subject_session
                        ),
                    )
                    if os.access(self.project_info.fmri_config_file, os.F_OK):
                        print("> Initialize fMRI pipeline")
                        (
                            fmri_valid_inputs,
                            self.fmri_pipeline,
                        ) = project.init_fmri_project(
                            self.project_info, bids_layout, False
                        )
                    else:
                        self.fmri_pipeline = None

                    # self.fmri_pipeline.subject = self.project_info.subject
                    # self.fmri_pipeline.global_conf.subject = self.project_info.subject

                # self.anat_pipeline.global_conf.subject_session = self.project_info.subject_session

                # if self.dmri_pipeline is not None:
                #     self.dmri_pipeline.global_conf.subject_session = self.project_info.subject_session
                #
                # if self.fmri_pipeline is not None:
                #     self.fmri_pipeline.global_conf.subject_session = self.project_info.subject_session

                print(
                    "  .. INFO: Selected session %s" % self.project_info.subject_session
                )
                if self.anat_pipeline is not None:
                    self.anat_pipeline.stages[
                        "Segmentation"
                    ].config.freesurfer_subject_id = os.path.join(
                        self.project_info.base_directory,
                        "derivatives",
                        __freesurfer_directory__,
                        "{}_{}".format(
                            self.project_info.subject, self.project_info.subject_session
                        ),
                    )
            else:
                print("  .. INFO: No session detected")
                self.project_info.anat_config_file = os.path.join(
                    self.project_info.base_directory,
                    "derivatives",
                    __cmp_directory__,
                    "{}".format(self.project_info.subject),
                    "{}_anatomical_config.json".format(self.project_info.subject),
                )
                if os.access(self.project_info.anat_config_file, os.F_OK):
                    self.anat_pipeline = project.init_anat_project(
                        self.project_info, False
                    )
                else:
                    self.anat_pipeline = None

                if self.dmri_inputs_checked:
                    self.project_info.dmri_config_file = os.path.join(
                        self.project_info.base_directory,
                        "derivatives",
                        __cmp_directory__,
                        "{}".format(self.project_info.subject),
                        "{}_diffusion_config.json".format(self.project_info.subject),
                    )
                    if os.access(self.project_info.dmri_config_file, os.F_OK):
                        (
                            dmri_valid_inputs,
                            self.dmri_pipeline,
                        ) = project.init_dmri_project(
                            self.project_info, bids_layout, False
                        )
                    else:
                        self.dmri_pipeline = None

                    # self.dmri_pipeline.subject = self.project_info.subject
                    # self.dmri_pipeline.global_conf.subject = self.project_info.subject

                if self.fmri_inputs_checked:
                    self.project_info.fmri_config_file = os.path.join(
                        self.project_info.base_directory,
                        "derivatives",
                        __cmp_directory__,
                        "{}".format(self.project_info.subject),
                        "{}_fMRI_config.json".format(self.project_info.subject),
                    )
                    if os.access(self.project_info.fmri_config_file, os.F_OK):
                        (
                            fmri_valid_inputs,
                            self.fmri_pipeline,
                        ) = project.init_fmri_project(
                            self.project_info, bids_layout, False
                        )
                    else:
                        self.fmri_pipeline = None

                    # self.fmri_pipeline.subject = self.project_info.subject
                    # self.fmri_pipeline.global_conf.subject = self.project_info.subject

                # self.anat_pipeline.global_conf.subject_session = ''
                if self.anat_pipeline is not None:
                    self.anat_pipeline.stages[
                        "Segmentation"
                    ].config.freesurfer_subjects_dir = os.path.join(
                        self.project_info.base_directory,
                        "derivatives",
                        __freesurfer_directory__,
                        "{}".format(self.project_info.subject),
                    )

            if self.anat_pipeline is not None:
                print("> Anatomical pipeline output inspection")
                self.anat_pipeline.view_mode = "inspect_outputs_view"
                for stage in list(self.anat_pipeline.stages.values()):
                    print("  ... Inspect stage {}".format(stage))
                    stage.define_inspect_outputs()
                    # print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (
                        stage.inspect_outputs[0] != "Outputs not available"
                    ):
                        self.output_anat_available = True

            if self.dmri_pipeline is not None:
                print("> Diffusion pipeline output inspection")
                self.dmri_pipeline.view_mode = "inspect_outputs_view"
                for stage in list(self.dmri_pipeline.stages.values()):
                    print("  ... Inspect stage {}".format(stage))
                    stage.define_inspect_outputs()
                    # print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (
                        stage.inspect_outputs[0] != "Outputs not available"
                    ):
                        self.output_dmri_available = True

            if self.fmri_pipeline is not None:
                print("> fMRI pipeline output inspection")
                self.fmri_pipeline.view_mode = "inspect_outputs_view"
                for stage in list(self.fmri_pipeline.stages.values()):
                    print("  ... Inspect stage {}".format(stage))
                    stage.define_inspect_outputs()
                    # print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (
                        stage.inspect_outputs[0] != "Outputs not available"
                    ):
                        self.output_fmri_available = True

            print_blue(
                "  .. Anatomical output(s) available : %s" % self.output_anat_available
            )
            print_blue(
                "  .. Diffusion output(s) available : %s" % self.output_dmri_available
            )
            print_blue(
                "  .. fMRI output(s) available : %s" % self.output_fmri_available
            )

            if (
                self.output_anat_available
                or self.output_dmri_available
                or self.output_fmri_available
            ):
                valid_selected_subject = True
            else:
                self.error_msg = (
                    "  .. ERROR: No output available! "
                    + "Please select another subject (and session if any)!"
                )
                print_error(self.error_msg)
                select = error(
                    message=self.error_msg, title="Error", buttons=["OK", "Cancel"]
                )
                aborded = not select

        return aborded

    def update_diffusion_imaging_model(self, new):
        """Function called when ``diffusion_imaging_model`` is updated."""
        self.dmri_pipeline.diffusion_imaging_model = new
