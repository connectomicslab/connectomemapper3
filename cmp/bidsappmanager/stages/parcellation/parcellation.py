# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of parcellation config and stage UI classes."""

# General imports
import os
import subprocess

from traits.api import *
from traitsui.api import *

# Own imports
from cmp.stages.parcellation.parcellation import ParcellationConfig, ParcellationStage


class ParcellationConfigUI(ParcellationConfig):
    """Class that extends the :class:`ParcellationConfig` with graphical components.

    Attributes
    ----------
    custom_parcellation_view : traits.ui.View
        VGroup that displays the different parts of a custom BIDS parcellation file

    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for the stage

    See also
    ---------
    cmp.stages.parcellation.parcellation.ParcellationConfig
    """

    custom_parcellation_group = VGroup(
        Item('object.custom_parcellation.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.custom_parcellation.atlas', label="atlas"),
        Item('object.custom_parcellation.res', label="res"),
        Item('object.custom_parcellation.suffix', label="suffix", style='readonly'),
        label="Custom parcellation"
    )

    traits_view = View(
        Item(
            "parcellation_scheme", editor=EnumEditor(name="parcellation_scheme_editor")
        ),
        Group(
            Include('custom_parcellation_group'),
            visible_when='parcellation_scheme=="Custom"',
        ),
        Group(
            "segment_hippocampal_subfields",
            "segment_brainstem",
            "include_thalamic_nuclei_parcellation",
            Item(
                "ants_precision_type",
                label="ANTs precision type",
                enabled_when="include_thalamic_nuclei_parcellation",
            ),
            visible_when='parcellation_scheme=="Lausanne2018"',
        ),
    )


class ParcellationStageUI(ParcellationStage):
    """Class that extends the :class:`ParcellationStage` with graphical components.

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
    cmp.stages.parcellation.parcellation.ParcellationStage
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
        height=350,
        width=600,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    def __init__(self, pipeline_mode, subject, session, bids_dir, output_dir):
        """Constructor of the ParcellationStageUI class.

        Parameters
        -----------
        pipeline_mode : string
            Pipeline mode that can be "Diffusion" or "fMRI"

        bids_dir : path
            BIDS root directory

        output_dir : path
            Output directory

        See also
        ---------
        cmp.stages.parcellation.parcellation.ParcellationStage.__init_
        cmp.cmpbidsappmanager.stages.parcellation.parcellation.ParcellationStageUI
        """
        ParcellationStage.__init__(self, pipeline_mode, subject, session, bids_dir, output_dir)
        self.config = ParcellationConfigUI()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
