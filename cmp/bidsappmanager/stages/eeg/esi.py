# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of EEG Source Imaging config and stage UI classes."""

import subprocess
from traits.api import *
from traitsui.api import *

from cmp.stages.eeg.esi import (
    EEGSourceImagingConfig,
    EEGSourceImagingStage,
)


class EEGSourceImagingConfigUI(EEGSourceImagingConfig):
    """Class that extends the :class:`cmp.stages.eeg.esi.EEGSourceImagingConfig` with graphical components.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for the stage

    See also
    ---------
    cmp.stages.eeg.esi.EEGSourceImagingConfig
    """

    mne_electrode_transform_file_group = VGroup(
        Item('object.mne_electrode_transform_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.mne_electrode_transform_file.desc', label="desc"),
        Item('object.mne_electrode_transform_file.suffix', label="suffix", style='readonly'),
        Item('object.mne_electrode_transform_file.extension', label="extension", style='readonly'),
        label="MNE electrode transform"
    )

    cartool_spi_file_group = VGroup(
        Item('object.cartool_spi_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.cartool_spi_file.desc', label="desc"),
        Item('object.cartool_spi_file.suffix', label="suffix", style='readonly'),
        Item('object.cartool_spi_file.extension', label="extension"),
        label="Source space file"
    )

    cartool_invsol_file_group = VGroup(
        Item('object.cartool_invsol_file.toolbox_derivatives_dir', label="Derivatives directory"),
        Item('object.cartool_invsol_file.desc', label="desc"),
        Item('object.cartool_invsol_file.suffix', label="suffix", style='readonly'),
        Item('object.cartool_invsol_file.extension', label="extension"),
        label="Inverse solution file"
    )

    # TODO: Add parcellation traits
    traits_view = View(
        VGroup(
            VGroup(
                Item("parcellation_cmp_dir", label="Toolbox derivatives directory"),
                HGroup(
                    Item("parcellation_scheme", label="Parcellation scheme"),
                    Item("lausanne2018_parcellation_res",
                         label="Scale",
                         visible_when='parcellation_scheme=="Lausanne2018"'),
                ),
                label="Structural parcellation",
            ),
            VGroup(
                Item("esi_tool", label="Tool"),
                VGroup(
                    VGroup(
                        Item("mne_esi_method"),
                        Item("mne_esi_method_snr"),
                        Item("mne_apply_electrode_transform", label="Apply electrode transform"),
                        label="Method"
                    ),
                    Group(
                        Include("mne_electrode_transform_file_group"),
                        visible_when='mne_apply_electrode_transform'
                    ),
                    visible_when='esi_tool=="MNE"'
                ),
                VGroup(
                    VGroup(
                        Group(Include("cartool_spi_file_group")),
                        Group(Include("cartool_invsol_file_group"))
                    ),
                    VGroup(
                        Item("cartool_esi_method"),
                        Item("cartool_esi_lamb"),
                        label="Method"
                    ),
                    VGroup(
                        Item("cartool_svd_toi_begin", label="Start TOI"),
                        Item("cartool_svd_toi_end", label="End TOI"),
                        label="SVD for ROI time courses extraction"
                    ),
                    visible_when='esi_tool=="Cartool"'
                ),
                label="EEG Source Imaging"
            )
        ),
        width=0.4,
        height=0.6,
    )


class EEGSourceImagingStageUI(EEGSourceImagingStage):
    """Class that extends the :class:`cmp.stages.eeg.esi.EEGSourceImagingStage` with graphical components.

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
    cmp.stages.eeg.esi.EEGSourceImagingStage
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
        """Constructor of the EEGSourceImagingStageUI class.

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
        cmp.stages.eeg.esi.EEGSourceImagingStage.__init_
        cmp.cmpbidsappmanager.stages.esi.EEGSourceImagingStageUI
        """
        EEGSourceImagingStage.__init__(
            self, subject=subject, session=session, bids_dir=bids_dir, output_dir=output_dir
        )
        self.config = EEGSourceImagingConfigUI()

    def _inspect_output_button_fired(self, info):
        """Display the selected output when ``inspect_output_button`` is clicked.

        Parameters
        ----------
        info : traits.ui.Button
            Button object
        """
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
