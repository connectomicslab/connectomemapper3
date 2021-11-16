# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of segmentation config and stage UI classes."""

# General imports
import subprocess
from traits.api import *
from traitsui.api import *

# Own imports
from cmp.stages.segmentation.segmentation import SegmentationConfig, SegmentationStage


class SegmentationConfigUI(SegmentationConfig):
    """Class that extends the :class:`SegmentationConfig` with graphical components.

    Attributes
    ----------
    custom_brainmask_group : traits.ui.VGroup
        VGroup that displays the different parts of
        a custom BIDS brain mask file

    custom_gm_mask_group : traits.ui.VGroup
        VGroup that displays the different parts of a
        custom BIDS gray matter mask file

    custom_wm_mask_group : traits.ui.VGroup
        VGroup that displays the different parts of a
        custom BIDS white matter mask file

    custom_csf_mask_group : traits.ui.VGroup
        VGroup that displays the different parts of a
        custom BIDS CSF mask file

    custom_aparcaseg_group : traits.ui.VGroup
        VGroup that displays the different parts of a
        custom BIDS-formatted Freesurfer's aparc+aseg file

    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for the stage

    See also
    ---------
    cmp.stages.segmentation.segmentation.SegmentationConfig
    """

    custom_brainmask_group = VGroup(
        Item('custom_brainmask.custom_derivatives_dir'),
        Item('custom_brainmask.desc', style='readonly'),
        Item('custom_brainmask.suffix', style='readonly'),
        label="Custom brain mask"
    )

    custom_gm_mask_group = VGroup(
        Item('custom_gm_mask.custom_derivatives_dir'),
        Item('custom_gm_mask.desc'),
        Item('custom_gm_mask.label', style='readonly'),
        Item('custom_gm_mask.suffix', style='readonly'),
        label="Custom gray matter mask"
    )

    custom_wm_mask_group = VGroup(
        Item('custom_wm_mask.custom_derivatives_dir'),
        Item('custom_wm_mask.desc'),
        Item('custom_wm_mask.label', style='readonly'),
        Item('custom_wm_mask.suffix', style='readonly'),
        label="Custom white matter mask"
    )

    custom_csf_mask_group = VGroup(
        Item('custom_csf_mask.custom_derivatives_dir'),
        Item('custom_csf_mask.desc'),
        Item('custom_csf_mask.label', style='readonly'),
        Item('custom_csf_mask.suffix', style='readonly'),
        label="Custom CSF mask"
    )

    custom_aparcaseg_group = VGroup(
        Item('custom_aparcaseg.custom_derivatives_dir'),
        Item('custom_aparcaseg.desc', style='readonly'),
        Item('custom_aparcaseg.suffix', style='readonly'),
        label="Custom Freesurfer aparc+aseg (used by MRtrix3 to build the 5TT image)"
    )

    traits_view = View(
        Item("seg_tool", label="Segmentation tool"),
        Group(
            HGroup(
                "make_isotropic",
                Item(
                    "isotropic_vox_size",
                    label="Voxel size (mm)",
                    visible_when="make_isotropic",
                ),
            ),
            Item(
                "isotropic_interpolation",
                label="Interpolation",
                visible_when="make_isotropic",
            ),
            Item(
                "number_of_threads",
                label="Number of threads used for multithreading in Freesurfer and ANTs",
            ),
            "brain_mask_extraction_tool",
            Item(
                "ants_templatefile",
                label="Template",
                visible_when='brain_mask_extraction_tool == "ANTs"',
            ),
            Item(
                "ants_probmaskfile",
                label="Probability mask",
                visible_when='brain_mask_extraction_tool == "ANTs"',
            ),
            Item(
                "ants_regmaskfile",
                label="Extraction mask",
                visible_when='brain_mask_extraction_tool == "ANTs"',
            ),
            "freesurfer_args",
            visible_when="seg_tool=='Freesurfer'",
        ),
        Group(
            Include('custom_brainmask_group'),
            Include('custom_gm_mask_group'),
            Include('custom_wm_mask_group'),
            Include('custom_csf_mask_group'),
            Include('custom_aparcaseg_group'),
            visible_when="seg_tool=='Custom segmentation'",
        ),
    )


class SegmentationStageUI(SegmentationStage):
    """Class that extends the :class:`SegmentationStage` with graphical components.

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
    cmp.stages.segmentation.segmentation.SegmentationStage
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
        height=400,
        width=450,
        kind="livemodal",
        title="Edit stage configuration",
        buttons=["OK", "Cancel"],
    )

    # General and UI members
    def __init__(self, subject, session, bids_dir, output_dir):
        """Constructor of the SegmentationStageUI class.

        Parameters
        -----------
        bids_dir : path
            BIDS root directory

        output_dir : path
            Output directory

        See also
        ---------
        cmp.stages.segmentation.segmentation.SegmentationStage.__init_
        cmp.cmpbidsappmanager.stages.segmentation.segmentation.SegmentationStageUI
        """
        SegmentationStage.__init__(self, subject, session, bids_dir, output_dir)
        self.config = SegmentationConfigUI()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
