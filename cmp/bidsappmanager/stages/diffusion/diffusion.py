# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of diffusion reconstruction and tracking config and stage UI classes."""

# General imports
import subprocess
from traits.api import *
from traitsui.api import *

# Own imports
from cmp.bidsappmanager.stages.diffusion.reconstruction import *
from cmp.bidsappmanager.stages.diffusion.tracking import *
from cmp.stages.diffusion.diffusion import DiffusionConfig, DiffusionStage


class DiffusionConfigUI(DiffusionConfig):
    """Class that extends the :class:`DiffusionConfig` with graphical components.

    It includes the graphical components defining the configuration of the diffusion
    reconstruction and tractography sub-stages.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the Diffusion Stage Parameter Attributes
        of this class

    See also
    ---------
    cmp.stages.diffusion.diffusion.DiffusionConfig
    """

    traits_view = View(
        Item("diffusion_imaging_model", style="readonly"),
        HGroup(
            Item("dilate_rois"),
            Item("dilation_radius", visible_when="dilate_rois", label="radius"),
        ),
        Group(
            Item(
                "recon_processing_tool",
                label="Reconstruction processing tool",
                editor=EnumEditor(name="recon_processing_tool_editor"),
            ),
            Item(
                "dipy_recon_config",
                style="custom",
                visible_when='recon_processing_tool=="Dipy"',
            ),
            Item(
                "mrtrix_recon_config",
                style="custom",
                visible_when='recon_processing_tool=="MRtrix"',
            ),
            label="Reconstruction",
            show_border=True,
            show_labels=False,
            visible_when="tracking_processing_tool!=Custom",
        ),
        Group(
            Item(
                "tracking_processing_tool",
                label="Tracking processing tool",
                editor=EnumEditor(name="tracking_processing_tool_editor"),
            ),
            Item(
                "diffusion_model",
                editor=EnumEditor(name="diffusion_model_editor"),
                visible_when='tracking_processing_tool!="Custom"',
            ),
            Item(
                "dipy_tracking_config",
                style="custom",
                visible_when='tracking_processing_tool=="Dipy"',
            ),
            Item(
                "mrtrix_tracking_config",
                style="custom",
                visible_when='tracking_processing_tool=="MRtrix"',
            ),
            label="Tracking",
            show_border=True,
            show_labels=False,
        ),
        Group(
            Item("custom_track_file", style="simple"),
            visible_when='tracking_processing_tool=="Custom"',
        ),
        height=750,
        width=500,
    )

    def __init__(self):
        """Constructor of the DiffusionConfigUI class.

        See also
        ---------
        cmp.stages.diffusion.diffusion.DiffusionConfig.__init__
        cmp.cmpbidsappmanager.stages.diffusion.reconstruction.Dipy_recon_configUI
        cmp.cmpbidsappmanager.stages.diffusion.reconstruction.MRtrix_recon_configUI
        cmp.cmpbidsappmanager.stages.diffusion.tracking.Dipy_tracking_configUI
        cmp.cmpbidsappmanager.stages.diffusion.tracking.MRtrix_tracking_configUI
        """
        DiffusionConfig.__init__(self)
        self.dipy_recon_config = Dipy_recon_configUI(
            imaging_model=self.diffusion_imaging_model,
            recon_mode=self.diffusion_model,
            tracking_processing_tool=self.tracking_processing_tool,
        )
        self.mrtrix_recon_config = MRtrix_recon_configUI(
            imaging_model=self.diffusion_imaging_model, recon_mode=self.diffusion_model
        )
        self.dipy_tracking_config = Dipy_tracking_configUI(
            imaging_model=self.diffusion_imaging_model,
            tracking_mode=self.diffusion_model,
            SD=self.mrtrix_recon_config.local_model,
        )
        self.mrtrix_tracking_config = MRtrix_tracking_configUI(
            tracking_mode=self.diffusion_model, SD=self.mrtrix_recon_config.local_model
        )

        self.mrtrix_recon_config.on_trait_change(
            self.update_mrtrix_tracking_SD, "local_model"
        )
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_SD, "local_model"
        )
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_sh_order, "lmax_order"
        )


class DiffusionStageUI(DiffusionStage):
    """Class that extends the :class:`DiffusionStage` with graphical components.

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
    cmp.stages.diffusion.diffusion.DiffusionStage
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
        height=900,
        width=500,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    def __init__(self, bids_dir, output_dir):
        """Constructor of the DiffusionStageUI class.

        Parameters
        -----------
        bids_dir : path
            BIDS root directory

        output_dir : path
            Output directory

        See also
        ---------
        cmp.stages.diffusion.diffusion.DiffusionStage.__init_
        cmp.cmpbidsappmanager.stages.diffusion.diffusion.DiffusionConfigUI
        """
        DiffusionStage.__init__(self, bids_dir, output_dir)
        self.config = DiffusionConfigUI()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
