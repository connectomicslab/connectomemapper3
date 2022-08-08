# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""EEG pipeline UI Class definition."""

import os
import shutil

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.api import ImageResource

# Own imports
from cmtklib.bids.io import __cmp_directory__, __nipype_directory__
from cmp.bidsappmanager.stages.eeg.preprocessing import (
    EEGPreprocessingStageUI,
)
from cmp.bidsappmanager.stages.eeg.esi import EEGSourceImagingStageUI
from cmp.bidsappmanager.stages.connectome.eeg_connectome import EEGConnectomeStageUI
from cmp.pipelines.functional.eeg import EEGPipeline
from cmtklib.util import return_button_style_sheet


class EEGPipelineUI(EEGPipeline):
    """Class that extends the :class:`~cmp.pipelines.functional.eeg.EEGPipeline` with graphical components.

    Attributes
    ----------
    preprocessing : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the preprocessing stage depending on the ``view_mode``

    sourceimaging : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the source imaging stage depending on the ``view_mode``

    connectome : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the connectome stage depending on the ``view_mode``

    view_mode : ['config_view', 'inspect_outputs_view']
        Variable used to control the display of either (1) the configuration
        or (2) the quality inspection of stage of the pipeline

    pipeline_group : traitsUI panel
        Panel defining the layout of the buttons of the stages with corresponding images

    traits_view : QtView
        QtView that includes the ``pipeline_group`` panel

    See also
    ---------
    cmp.pipelines.functional.eeg.EEGPipeline
    """

    view_mode = Enum("config_view", ["config_view", "inspect_outputs_view"])

    preprocessing = Button("EEGPreprocessing")
    sourceimaging = Button("EEGSourceImaging")
    connectome = Button("EEGConnectome")

    pipeline_group = VGroup(
        HGroup(
            spring,
            UItem(
                "preprocessing",
                style="custom",
                width=222,
                height=130,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("eeg_preprocessing").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
        ),
        HGroup(
            spring,
            UItem(
                "sourceimaging",
                style="custom",
                width=222,
                height=130,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("eeg_sourceimaging").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
        ),
        HGroup(
            spring,
            UItem(
                "connectome",
                style="custom",
                width=222,
                height=130,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("eeg_connectome").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
        ),
        spring,
        springy=True,
    )

    traits_view = QtView(Include("pipeline_group"))

    def __init__(self, project_info):
        """Constructor of the EEGPipelineUI class.

        Parameters
        -----------
        project_info : cmp.project.ProjectInfoUI
            CMP_Project_Info object that stores general information
            such as the BIDS root and output directories (see
            :class_`cmp.project.CMP_Project_Info` for more details)

        See also
        ---------
        cmp.pipelines.functional.eeg.EEGPipeline.__init__
        """
        EEGPipeline.__init__(self, project_info)

        self.stages = {
            "EEGPreprocessing": EEGPreprocessingStageUI(
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
                subject=self.subject,
                session=self.global_conf.subject_session,
            ),
            "EEGSourceImaging": EEGSourceImagingStageUI(
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
                subject=self.subject,
                session=self.global_conf.subject_session
            ),
            "EEGConnectome": EEGConnectomeStageUI(
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
                subject=self.subject,
                session=self.global_conf.subject_session
            ),
        }

        self.parcellation_cmp_dir = self.stages["EEGSourceImaging"].config.parcellation_cmp_dir

        self.stages["EEGSourceImaging"].config.parcellation_scheme = self.parcellation_scheme

        self.stages["EEGSourceImaging"].config.on_trait_change(self._update_parcellation_scheme, 'parcellation_scheme')
        self.stages["EEGSourceImaging"].config.on_trait_change(self._update_lausanne2018_parcellation_res, 'lausanne2018_parcellation_res')
        self.stages["EEGSourceImaging"].config.on_trait_change(self._update_parcellation_cmp_dir, 'parcellation_cmp_dir')

        for stage in list(self.stages.keys()):
            if project_info.subject_session != "":
                self.stages[stage].stage_dir = os.path.join(
                    self.base_directory,
                    "derivatives",
                    __nipype_directory__,
                    self.subject,
                    project_info.subject_session,
                    self.pipeline_name,
                    self.stages[stage].name,
                )
            else:
                self.stages[stage].stage_dir = os.path.join(
                    self.base_directory,
                    "derivatives",
                    __nipype_directory__,
                    self.subject,
                    self.pipeline_name,
                    self.stages[stage].name,
                )

    def _preprocessing_fired(self, info):
        """Method that displays the window for the preprocessing stage.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The preprocessing button object
        """
        self.stages["EEGPreprocessing"].configure_traits(view=self.view_mode)

    def _sourceimaging_fired(self, info):
        """Method that displays the window for the Source Imaging (Inverse solution) stage.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The extra sourceimaging button object
        """
        self.stages["EEGSourceImaging"].configure_traits(view=self.view_mode)

    def _connectome_fired(self, info):
        """Method that displays the window for the connectome stage of the EEG pipeline.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The connectome button object
        """
        self.stages["EEGConnectome"].configure_traits(view=self.view_mode)
