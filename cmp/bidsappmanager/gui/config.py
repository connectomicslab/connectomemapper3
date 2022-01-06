# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper Pipeline Configurator Window."""

# General imports
import os

import pkg_resources

from pyface.api import ImageResource
from traitsui.qt4.extra.qt_view import QtView
from traitsui.api import *
from traits.api import *

# Own imports
import cmp.project
from cmtklib.util import (
    return_button_style_sheet,
    print_blue
)

import cmp.bidsappmanager.project as project
import cmp.bidsappmanager.gui.handlers
from cmp.bidsappmanager.gui.globals import (
    style_sheet, get_icon
)

# Remove warnings visible whenever you import scipy (or another package)
# that was compiled against an older numpy than is installed.
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


class PipelineConfiguratorWindow(HasTraits):
    """Class that defines the Pipeline Configurator Window.

    Attributes
    ----------
    project_info : cmp.project.ProjectInfo
        Instance of :class:`CMP_Project_Info` that represents the processing project

    anat_pipeline : Instance(HasTraits)
        Instance of anatomical MRI pipeline UI

    dmri_pipeline : Instance(HasTraits)
        Instance of diffusion MRI pipeline UI

    fmri_pipeline : Instance(HasTraits)
        Instance of functional MRI pipeline UI

    anat_inputs_checked : traits.Bool
            Boolean that indicates if anatomical pipeline inputs are available
            (Default: False)

        dmri_inputs_checked = : traits.Bool
            Boolean that indicates if diffusion pipeline inputs are available
            (Default: False)

        fmri_inputs_checked : traits.Bool
            Boolean that indicates if functional pipeline inputs are available
            (Default: False)

    anat_save_config : traits.ui.Action
        TraitsUI Action to save the anatomical pipeline configuration

    dmri_save_config : traits.ui.Action
        TraitsUI Action to save the diffusion pipeline configuration

    fmri_save_config : traits.ui.Action
        TraitsUI Action to save the functional pipeline configuration

    save_all_config : traits.ui.Button
        Button to save all configuration files at once

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

    anat_save_config = Action(
        name="Save anatomical pipeline configuration as...",
        action="save_anat_config_file",
    )
    dmri_save_config = Action(
        name="Save diffusion pipeline configuration as...",
        action="save_dmri_config_file",
    )
    fmri_save_config = Action(
        name="Save fMRI pipeline configuration as...", action="save_fmri_config_file"
    )

    # anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file')
    # dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='load_dmri_config_file')
    # fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='load_fmri_config_file')

    save_all_config = Button("")

    traits_view = QtView(
        Group(
            Group(
                Item("anat_pipeline", style="custom", show_label=False),
                label="Anatomical pipeline",
                dock="tab",
            ),
            Group(
                Item(
                    "dmri_pipeline",
                    style="custom",
                    show_label=False,
                    enabled_when="dmri_inputs_checked",
                    visible_when="dmri_inputs_checked",
                ),
                label="Diffusion pipeline",
                dock="tab",
            ),
            Group(
                Item(
                    "fmri_pipeline",
                    style="custom",
                    show_label=False,
                    enabled_when="fmri_inputs_checked",
                    visible_when="fmri_inputs_checked",
                ),
                label="fMRI pipeline",
                dock="tab",
            ),
            orientation="horizontal",
            layout="tabbed",
            springy=True,
            enabled_when="anat_inputs_checked",
        ),
        spring,
        HGroup(
            spring,
            Item(
                "save_all_config",
                style="custom",
                width=315,
                height=35,
                resizable=False,
                label="",
                show_label=False,
                style_sheet=return_button_style_sheet(
                    ImageResource(
                        pkg_resources.resource_filename(
                            "resources",
                            os.path.join("buttons", "configurator-saveall.png"),
                        )
                    ).absolute_path
                ),
                enabled_when="anat_inputs_checked==True",
            ),
            spring,
            show_labels=False,
            label="",
        ),
        title="Connectome Mapper 3 Configurator",
        menubar=MenuBar(
            Menu(
                ActionGroup(anat_save_config, dmri_save_config, fmri_save_config),
                ActionGroup(Action(name="Quit", action="_on_close")),
                name="File",
            )
        ),
        handler=cmp.bidsappmanager.gui.handlers.ConfigQualityWindowHandler(),
        style_sheet=style_sheet,
        buttons=[],
        width=0.5,
        height=0.8,
        resizable=True,  # scrollable=True,
        icon=get_icon("configurator.png"),
    )

    def __init__(
        self,
        project_info=None,
        anat_pipeline=None,
        dmri_pipeline=None,
        fmri_pipeline=None,
        anat_inputs_checked=False,
        dmri_inputs_checked=False,
        fmri_inputs_checked=False,
    ):
        """Constructor of an :class:``PipelineConfiguratorWindow`` instance.

        Parameters
        ----------
        project_info : cmp.project.ProjectInfo
            :class:`CMP_Project_Info` object (Default: None)

        anat_pipeline <cmp.bidsappmanager.pipelines.anatomical.AnatomicalPipelineUI>
            Instance of :class:`cmp.bidsappmanager.pipelines.anatomical.AnatomicalPipelineUI`
            (Default: None)

        dmri_pipeline <cmp.bidsappmanager.pipelines.diffusion.DiffusionPipelineUI>
            Instance of :class:`cmp.bidsappmanager.pipelines.diffusion.DiffusionPipelineUI`
            (Default: None)

        fmri_pipeline <cmp.bidsappmanager.pipelines.functional.fMRIPipelineUI>
            Instance of :class:`cmp.bidsappmanager.pipelines.functional.fMRIPipelineUI`
            (Default: None)

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

        self.anat_pipeline = anat_pipeline
        self.dmri_pipeline = dmri_pipeline
        self.fmri_pipeline = fmri_pipeline

        if self.anat_pipeline is not None:
            self.anat_pipeline.view_mode = "config_view"

        if self.dmri_pipeline is not None:
            self.dmri_pipeline.view_mode = "config_view"

        if self.fmri_pipeline is not None:
            self.fmri_pipeline.view_mode = "config_view"

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

    def update_diffusion_imaging_model(self, new):
        self.dmri_pipeline.diffusion_imaging_model = new

    def _save_all_config_fired(self):
        print_blue("[Save all pipeline configuration files]")

        if self.anat_inputs_checked:
            anat_config_file = os.path.join(
                self.project_info.base_directory, "code", "ref_anatomical_config.json"
            )
            project.anat_save_config(self.anat_pipeline, anat_config_file)
            print("  * Anatomical config saved as  {}".format(anat_config_file))

        if self.dmri_inputs_checked:
            dmri_config_file = os.path.join(
                self.project_info.base_directory, "code", "ref_diffusion_config.json"
            )
            project.dmri_save_config(self.dmri_pipeline, dmri_config_file)
            print("  * Diffusion config saved as  {}".format(dmri_config_file))

        if self.fmri_inputs_checked:
            fmri_config_file = os.path.join(
                self.project_info.base_directory, "code", "ref_fMRI_config.json"
            )
            project.fmri_save_config(self.fmri_pipeline, fmri_config_file)
            print("  * fMRI config saved as  {}".format(fmri_config_file))
