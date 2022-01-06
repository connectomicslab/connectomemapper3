# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of fMRI preprocessing config and stage UI classes."""

# General imports
import subprocess
from traits.api import *
from traitsui.api import *

# Own imports
from cmp.stages.preprocessing.fmri_preprocessing import (
    PreprocessingConfig,
    PreprocessingStage,
)


class PreprocessingConfigUI(PreprocessingConfig):
    """Class that extends the (functional) :class:`PreprocessingConfig` with graphical components.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for the stage

    See also
    ---------
    cmp.stages.preprocessing.fmri_preprocessing.PreprocessingConfig
    """

    traits_view = View(
        "discard_n_volumes",
        "despiking",
        "slice_timing",
        Item("repetition_time", visible_when='slice_timing!="none"'),
        "motion_correction",
    )


class PreprocessingStageUI(PreprocessingStage):
    """Class that extends the (functional) :class:`PreprocessingStage` with graphical components.

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
    cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage
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
        height=280,
        width=350,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    # General and UI members
    def __init__(self, bids_dir, output_dir):
        """Constructor of the functional PreprocessingStageUI class.

        Parameters
        -----------
        bids_dir : path
            BIDS root directory

        output_dir : path
            Output directory

        See also
        ---------
        cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage.__init_
        cmp.cmpbidsappmanager.stages.preprocessing.fmri_preprocessing.PreprocessingStageUI
        """
        PreprocessingStage.__init__(self, bids_dir, output_dir)
        self.config = PreprocessingConfigUI()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
