# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of EEG preprocessing config and stage UI classes."""

import subprocess
from traits.api import *
from traitsui.api import *

from cmp.stages.eeg.preprocessing import (
    EEGPreprocessingConfig,
    EEGPreprocessingStage,
)


class EEGPreprocessingConfigUI(EEGPreprocessingConfig):
    """Class that extends the :class:`cmp.stages.eeg.preprocessing.EEGPreprocessingConfig` with graphical components.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for the stage

    See also
    ---------
    cmp.stages.eeg.preprocessing.EEGPreprocessingConfig
    """

    eeg_ts_file_group = VGroup(
        Item('object.eeg_ts_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.eeg_ts_file.task', label="task", style='readonly'),
        Item('object.eeg_ts_file.desc', label="desc"),
        Item('object.eeg_ts_file.suffix', label="suffix", style='readonly'),
        Item('object.eeg_ts_file.extension', label="extension"),
        label="Preprocessed EEG recording file"
    )

    events_file_group = VGroup(
        Item('object.events_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.events_file.task', label="task", style='readonly'),
        Item('object.events_file.desc', label="desc"),
        Item('object.events_file.suffix', label="suffix", style='readonly'),
        label="Recording events file",
        enabled_when='object.eeg_ts_file.extension=="set"'
    )

    bids_electrodes_file_group = VGroup(
        Item('object.bids_electrodes_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.bids_electrodes_file.task', label="task", style='readonly'),
        Item('object.bids_electrodes_file.desc', label="desc"),
        Item('object.bids_electrodes_file.suffix', label="suffix", style='readonly'),
        Item('object.bids_electrodes_file.extension', label="extension", style='readonly'),
        label="Electrodes file (BIDS)",
        enabled_when='object.eeg_ts_file.extension=="set"'
    )

    cartool_electrodes_file_group = VGroup(
        Item('object.cartool_electrodes_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.cartool_electrodes_file.desc', label="desc"),
        Item('object.cartool_electrodes_file.suffix', label="suffix", style='readonly'),
        Item('object.cartool_electrodes_file.extension', label="extension", style='readonly'),
        label="Electrodes file (Cartool)",
        enabled_when='object.eeg_ts_file.extension=="set"'
    )

    traits_view = View(
        VGroup(
            VGroup(
                Item("task_label"),
                Group(
                    Include('eeg_ts_file_group'),
                ),
                Group(
                    Include('events_file_group'),
                ),
                Item("electrodes_file_fmt",
                     enabled_when='object.eeg_ts_file.extension=="set"'),
                Group(
                    Include("bids_electrodes_file_group"),
                    visible_when='electrodes_file_fmt=="BIDS"'
                ),
                Group(
                    Include("cartool_electrodes_file_group"),
                    visible_when='electrodes_file_fmt=="Cartool"'
                ),
                label="EEG Preprocessed inputs",
            ),
            HGroup(
                Item("t_min", label="Start time"),
                Item("t_max", label="End time"),
                label="Epochs time window",
                enabled_when='object.eeg_ts_file.extension=="set"'
            )
        ),
        width=0.4,
        height=0.6,
    )


class EEGPreprocessingStageUI(EEGPreprocessingStage):
    """Class that extends the :class:`cmp.stages.eeg.preprocessing.EEGPreprocessingStage` with graphical components.

    Attributes
    ----------
    inspect_output_button : traits.ui.Button
        Button that displays the selected output in an appropriate viewer
        (present only in the window for quality inspection)

    inspect_outputs_view : traits.ui.View
        TraitsUI view that displays the quality inspection window of this stage

    config_view : traits.ui.View
        TraitsUI view that displays the configuration window of this stage

    See also
    ---------
    cmp.stages.eeg.preprocessing.EEGPreprocessingStage
    """

    inspect_output_button = Button("View")

    inspect_outputs_view = View(
        Group(
            Item("name", editor=TitleEditor(), show_label=False),
            Group(
                Item("inspect_outputs_enum", show_label=False),
                Item(
                    "inspect_output_button",
                    enabled_when='inspect_outputs_enum!="Outputs not available"',
                    show_label=False,
                ),
                label="View outputs",
                show_border=True,
            ),
        ),
        scrollable=True,
        resizable=True,
        kind="livemodal",
        title="Inspect stage outputs",
        buttons=["OK", "Cancel"],
    )

    config_view = View(
        Group(
            Item("name", editor=TitleEditor(), show_label=False),
            Group(
                Item("config", style="custom", show_label=False),
                label="Configuration",
                show_border=True,
            ),
        ),
        scrollable=True,
        resizable=True,
        height=650,
        width=450,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    # General and UI members
    def __init__(self, subject, session, bids_dir, output_dir):
        """Constructor of the EEGPreprocessingStageUI class.

        Parameters
        -----------
        subject : str
            Subject label

        session : str
            Session label

        bids_dir : path
            BIDS root directory

        output_dir : path
            Output directory

        See also
        ---------
        cmp.stages.eeg.preprocessing.EEGPreprocessingStage.__init_
        cmp.cmpbidsappmanager.stages.eeg.preprocessing.EEGPreprocessingStageUI
        """
        EEGPreprocessingStage.__init__(
            self, subject=subject, session=session, bids_dir=bids_dir, output_dir=output_dir
        )
        self.config = EEGPreprocessingConfigUI()
        self.config.eeg_ts_file.on_trait_change(self._reload_view, 'extension')

    def _reload_view(self, new):
        self.define_inspect_outputs()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])

