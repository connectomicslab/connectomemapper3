# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of EEG connectome config and stage UI classes."""

# Global imports
import subprocess

from traits.api import *
from traitsui.api import *

# Own imports
from cmp.stages.connectome.eeg_connectome import (
    EEGConnectomeConfig, EEGConnectomeStage
)


class EEGConnectomeConfigUI(EEGConnectomeConfig):
    """Class that extends the :class:`cmp.stages.connectome.eeg_connectome.EEGConnectomeConfig` with graphical components.

    Attributes
    ----------
    output_types : list of string
        A list of ``output_types``. Valid ``output_types`` are
        'gpickle', 'mat', 'cff', 'graphml'

    connectivity_metrics : list of string
        A list of time/frequency connectivity metrics to stored. Valid ``connectivity_metrics`` are
        'coh', 'cohy', 'imcoh', 'plv', 'ciplv', 'ppc', 'pli', 'wpli', and 'wpli2_debiased'

    traits_view : traits.ui.View
        TraitsUI view that displays the Attributes of this class

    See also
    ---------
    cmp.stages.connectome.eeg_connectome.EEGConnectomeConfig
    """

    output_types = List(
        ["gpickle"],
        editor=CheckListEditor(values=["gpickle", "mat", "cff", "graphml"], cols=4),
    )

    connectivity_metrics = List(
        [
            'coh', 'cohy', 'imcoh',
            'plv', 'ciplv', 'ppc',
            'pli', 'wpli', 'wpli2_debiased'
        ],
        editor=CheckListEditor(
            values=[
                'coh', 'cohy', 'imcoh',
                'plv', 'ciplv', 'ppc',
                'pli', 'wpli', 'wpli2_debiased'
            ],
            cols=4,
        ),
    )

    traits_view = View(
        Item("output_types", style="custom"),
        Group(
            Item("connectivity_metrics", label="Metrics", style="custom"),
            label="Connectivity matrix",
            show_border=True,
        ),
    )


class EEGConnectomeStageUI(EEGConnectomeStage):
    """Class that extends the :class:`cmp.stages.connectome.eeg_connectome.EEGConnectomeStage` with graphical components.

    Attributes
    ----------
    log_visualization : traits.Bool
        Log visualization that might be obsolete as this has been detached
        after creation of the bidsappmanager (Default: True)

    circular_layout : traits.Bool
        Visualization of the connectivity matrix using a circular layout
        that might be obsolete as this has been detached after creation
        of the bidsappmanager (Default: False)

    inspect_output_button : traits.ui.Button
        Button that displays the selected connectivity matrix
        in the graphical component for quality inspection

    inspect_outputs_view : traits.ui.View
        TraitsUI view that displays the quality inspection window of this stage

    config_view : traits.ui.View
        TraitsUI view that displays the configuration window of this stage

    See also
    ---------
    cmp.stages.connectome.eeg_connectome.EEGConnectomeStage
    """

    log_visualization = Bool(True)
    circular_layout = Bool(False)

    inspect_output_button = Button("View")

    inspect_outputs_view = View(
        Group(
            Item("name", editor=TitleEditor(), show_label=False),
            Group(
                Item("log_visualization", label="Log scale"),
                Item("circular_layout", label="Circular layout"),
                label="Visualization",
                show_border=True,
            ),
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
        height=270,
        width=670,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    def __init__(self, subject, session, bids_dir, output_dir):
        """Constructor of the EEGConnectomeStageUI class.

        Parameters
        ----------
        subject : str
            Subject label

        session : str
            Session label

        bids_dir : traits.Directory
            BIDS root directory

        output_dir : traits.Directory
            Output directory

        See also
        ---------
        cmp.stages.connectome.eeg_connectome.EEGConnectomeStage.__init__
        """
        EEGConnectomeStage.__init__(self, bids_dir, output_dir, subject, session)
        self.config = EEGConnectomeConfigUI()

    def _log_visualization_changed(self, new):
        """Update the value of log_visualization in the config.

        Parameters
        ----------
        new : traits.Bool
            New value
        """
        self.define_inspect_outputs(
            log_visualization=new,
            circular_layout=self.circular_layout
        )

    def _circular_layout_changed(self, new):
        """Update the value of circular_layout in the config.

        Parameters
        ----------
        new : traits.Bool
            New value
        """
        self.define_inspect_outputs(
            log_visualization=self.log_visualization,
            circular_layout=new
        )

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
