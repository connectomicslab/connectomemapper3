# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper Main Window."""

# General imports
import os
import pkg_resources

from pyface.api import ImageResource
from traitsui.qt4.extra.qt_view import QtView
from traitsui.api import *
from traits.api import *

from bids import BIDSLayout

# Own imports
import cmp.project
from cmp.info import __version__

from cmtklib.util import (
    return_button_style_sheet, print_blue
)

import cmp.bidsappmanager.gui.config
import cmp.bidsappmanager.gui.bidsapp
import cmp.bidsappmanager.gui.qc
import cmp.bidsappmanager.gui.handlers
from cmp.bidsappmanager.gui.globals import (
    style_sheet, get_icon
)


class MainWindow(HasTraits):
    """Class that defines the Main window of the Connectome Mapper 3 GUI.

    Attributes
    ----------
    project_info : cmp.bidsappmanager.project.ProjectInfoUI
        Instance of :class:`CMP_Project_InfoUI` that represents the processing project

    anat_pipeline : Instance(HasTraits)
        Instance of anatomical MRI pipeline UI

    dmri_pipeline : Instance(HasTraits)
        Instance of diffusion MRI pipeline UI

    fmri_pipeline : Instance(HasTraits)
        Instance of functional MRI pipeline UI

    bidsapp_ui : cmp.project.ProjectInfo
        Instance of :class:`BIDSAppInterfaceWindow`

    load_dataset : traits.ui.Action
        TraitsUI Action to load a BIDS dataset

    bidsapp : traits.ui.Button
        Button that displays the BIDS App Interface window

    configurator : traits.ui.Button
        Button thats displays the pipeline Configurator window

    quality_control : traits.ui.Button
        Button that displays the pipeline Quality Control / Inspector window

    manager_group : traits.ui.View
        TraitsUI View that describes the content of the main window

    traits_view : QtView
        TraitsUI QtView that includes ``manager_group`` and parameterize
        the window with menu
    """
    project_info = Instance(cmp.project.ProjectInfo)

    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    # configurator_ui = Instance(CMP_PipelineConfigurationWindow)
    bidsapp_ui = Instance(cmp.bidsappmanager.gui.bidsapp.BIDSAppInterfaceWindow)
    # quality_control_ui = Instance(CMP_QualityControlWindow)

    load_dataset = Action(name="Load BIDS Dataset...", action="load_dataset")

    project_info.style_sheet = style_sheet

    configurator = Button("")
    bidsapp = Button("")
    quality_control = Button("")

    view_mode = 1

    manager_group = VGroup(
        spring,
        HGroup(
            spring,
            HGroup(
                Item(
                    "configurator",
                    style="custom",
                    width=200,
                    height=200,
                    resizable=False,
                    label="",
                    show_label=False,
                    style_sheet=return_button_style_sheet(
                        ImageResource(
                            pkg_resources.resource_filename(
                                "cmp",
                                os.path.join(
                                    "bidsappmanager/images", "configurator_200x200.png"
                                ),
                            )
                        ).absolute_path
                    ),
                ),
                show_labels=False,
                label="",
            ),
            spring,
            HGroup(
                Item(
                    "bidsapp",
                    style="custom",
                    width=200,
                    height=200,
                    resizable=False,
                    style_sheet=return_button_style_sheet(
                        ImageResource(
                            pkg_resources.resource_filename(
                                "cmp",
                                os.path.join(
                                    "bidsappmanager/images", "bidsapp_200x200.png"
                                ),
                            )
                        ).absolute_path
                    ),
                ),
                show_labels=False,
                label="",
            ),
            spring,
            HGroup(
                Item(
                    "quality_control",
                    style="custom",
                    width=200,
                    height=200,
                    resizable=False,
                    style_sheet=return_button_style_sheet(
                        ImageResource(
                            pkg_resources.resource_filename(
                                "cmp",
                                os.path.join(
                                    "bidsappmanager/images",
                                    "qualitycontrol_200x200.png",
                                ),
                            )
                        ).absolute_path
                    ),
                ),
                show_labels=False,
                label="",
            ),
            spring,
            springy=True,
            visible_when="handler.project_loaded==True",
        ),
        spring,
        springy=True,
    )

    traits_view = QtView(
        HGroup(
            Include("manager_group"),
        ),
        title="Connectome Mapper {} - BIDS App Manager".format(__version__),
        menubar=MenuBar(
            Menu(
                ActionGroup(
                    load_dataset,
                ),
                ActionGroup(
                    Action(name="Quit", action="_on_close"),
                ),
                name="File",
            ),
        ),
        handler=cmp.bidsappmanager.gui.handlers.MainWindowHandler(),
        style_sheet=style_sheet,
        width=0.5,
        height=0.8,
        resizable=True,  # , scrollable=True , resizable=True
        icon=get_icon("cmp.png"),
    )

    def _bidsapp_fired(self):
        """ Callback of the "bidsapp" button. This displays the BIDS App Interface window."""
        print_blue("[Open BIDS App Window]")
        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        anat_config = os.path.join(
            self.project_info.base_directory, "code/", "ref_anatomical_config.json"
        )
        dmri_config = os.path.join(
            self.project_info.base_directory, "code/", "ref_diffusion_config.json"
        )
        fmri_config = os.path.join(
            self.project_info.base_directory, "code/", "ref_fMRI_config.json"
        )

        self.bidsapp_ui = cmp.bidsappmanager.gui.bidsapp.BIDSAppInterfaceWindow(
            project_info=self.project_info,
            bids_root=self.project_info.base_directory,
            subjects=subjects,
            list_of_subjects_to_be_processed=subjects,
            # anat_config=self.project_info.anat_config_file,
            # dmri_config=self.project_info.dmri_config_file,
            # fmri_config=self.project_info.fmri_config_file
            anat_config=anat_config,
            dmri_config=dmri_config,
            fmri_config=fmri_config,
        )
        self.bidsapp_ui.configure_traits()

    def _configurator_fired(self):
        """Callback of the "configurator" button. This displays the Configurator Window."""
        print_blue("[Open Pipeline Configurator Window]")
        if self.project_info.t1_available:
            if os.path.isfile(self.project_info.anat_config_file):
                print(
                    "  .. Anatomical config file : %s"
                    % self.project_info.anat_config_file
                )

        if self.project_info.dmri_available:
            if os.path.isfile(self.project_info.dmri_config_file):
                print(
                    "  .. Diffusion config file : %s"
                    % self.project_info.dmri_config_file
                )

        if self.project_info.fmri_available:
            if os.path.isfile(self.project_info.fmri_config_file):
                print("  .. fMRI config file : %s" % self.project_info.fmri_config_file)

        self.configurator_ui = cmp.bidsappmanager.gui.config.PipelineConfiguratorWindow(
            project_info=self.project_info,
            anat_pipeline=self.anat_pipeline,
            dmri_pipeline=self.dmri_pipeline,
            fmri_pipeline=self.fmri_pipeline,
            anat_inputs_checked=self.project_info.t1_available,
            dmri_inputs_checked=self.project_info.dmri_available,
            fmri_inputs_checked=self.project_info.fmri_available,
        )

        self.configurator_ui.configure_traits()

    def _quality_control_fired(self):
        """Callback of the "Inspector" button. This displays the Quality Control (Inspector) Window."""
        print_blue("[Open Quality Inspector Window]")
        if self.project_info.t1_available:
            if os.path.isfile(self.project_info.anat_config_file):
                print(
                    "  .. Anatomical config file : %s"
                    % self.project_info.anat_config_file
                )

        if self.project_info.dmri_available:
            if os.path.isfile(self.project_info.dmri_config_file):
                print(
                    "  .. Diffusion config file : %s"
                    % self.project_info.dmri_config_file
                )

        if self.project_info.fmri_available:
            if os.path.isfile(self.project_info.fmri_config_file):
                print("  .. fMRI config file : %s" % self.project_info.fmri_config_file)

        try:
            self.quality_control_ui = cmp.bidsappmanager.gui.qc.QualityInspectorWindow(
                project_info=self.project_info,
                anat_inputs_checked=self.project_info.t1_available,
                dmri_inputs_checked=self.project_info.dmri_available,
                fmri_inputs_checked=self.project_info.fmri_available,
            )
            self.quality_control_ui.configure_traits()
        except Exception as e:
            print(e)
