# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license ModifFied BSD.

"""Definition of extra preprocessing of functional MRI (post-registration) config and stage UI classes."""

# General imports
import subprocess
from traits.api import *
from traitsui.api import *

# Own imports
from cmp.stages.functional.functionalMRI import FunctionalMRIConfig, FunctionalMRIStage


class FunctionalMRIConfigUI(FunctionalMRIConfig):
    """Class that extends the :class:`FunctionalMRIConfig` with graphical components.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for the stage

    See also
    ---------
    cmp.stages.functional.functionalMRI.FunctionalMRIConfig
    """

    traits_view = View(  # Item('smoothing'),
        # Item('discard_n_volumes'),
        HGroup(
            Item("detrending"),
            Item("detrending_mode", visible_when="detrending"),
            label="Detrending",
            show_border=True,
        ),
        HGroup(
            Item("global_nuisance", label="Global"),
            Item("csf"),
            Item("wm"),
            Item("motion"),
            label="Nuisance factors",
            show_border=True,
        ),
        HGroup(
            Item("lowpass_filter", label="Low cutoff (volumes)"),
            Item("highpass_filter", label="High cutoff (volumes)"),
            label="Bandpass filtering",
            show_border=True,
        ),
    )


class FunctionalMRIStageUI(FunctionalMRIStage):
    """Class that extends the :class:`FunctionalMRIStage` with graphical components.

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
    cmp.stages.functional.functionalMRI.FunctionalMRIStage
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
        height=528,
        width=608,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    def __init__(self, bids_dir, output_dir):
        """Constructor of the FunctionalMRIStageUI class.

        Parameters
        -----------
        bids_dir : path
            BIDS root directory

        output_dir : path
            Output directory

        See also
        ---------
        cmp.stages.functional.functionalMRI.FunctionalMRIStage.__init_
        cmp.cmpbidsappmanager.stages.functional.functionalMRI.FunctionalMRIConfigUI
        """
        FunctionalMRIStage.__init__(self, bids_dir, output_dir)
        self.config = FunctionalMRIConfigUI()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
