# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Diffusion reconstruction and tractography
"""

# General imports
import os
import gzip
import pickle

from traits.api import *
from traitsui.api import *

import subprocess

# Own imports
# from cmp.bidsappmanager.stages.common import Stage
from cmp.bidsappmanager.stages.diffusion.reconstruction import *
from cmp.bidsappmanager.stages.diffusion.tracking import *

from cmp.stages.diffusion.diffusion import DiffusionConfig, DiffusionStage


class DiffusionConfigUI(DiffusionConfig):
    traits_view = View(
        Item('diffusion_imaging_model', style='readonly'),
        HGroup(
            Item('dilate_rois'),  # ,visible_when='processing_tool!="DTK"'),
            Item('dilation_radius', visible_when='dilate_rois', label="radius")
        ),
        Group(Item('recon_processing_tool', label='Reconstruction processing tool',
                   editor=EnumEditor(name='recon_processing_tool_editor')),
              # Item('dtk_recon_config',style='custom',visible_when='processing_tool=="DTK"'),
              Item('dipy_recon_config', style='custom',
                   visible_when='recon_processing_tool=="Dipy"'),
              Item('mrtrix_recon_config', style='custom',
                   visible_when='recon_processing_tool=="MRtrix"'),
              # Item('camino_recon_config',style='custom',visible_when='processing_tool=="Camino"'),
              # Item('fsl_recon_config',style='custom',visible_when='processing_tool=="FSL"'),
              # Item('gibbs_recon_config',style='custom',visible_when='processing_tool=="Gibbs"'),
              label='Reconstruction', show_border=True, show_labels=False,
              visible_when='tracking_processing_tool!=Custom'),
        Group(Item('tracking_processing_tool', label='Tracking processing tool',
                   editor=EnumEditor(name='tracking_processing_tool_editor')),
              Item('diffusion_model', editor=EnumEditor(name='diffusion_model_editor'),
                   visible_when='tracking_processing_tool!="Custom"'),
              # Item('dtb_tracking_config',style='custom',visible_when='processing_tool=="DTK"'),
              Item('dipy_tracking_config', style='custom',
                   visible_when='tracking_processing_tool=="Dipy"'),
              Item('mrtrix_tracking_config', style='custom',
                   visible_when='tracking_processing_tool=="MRtrix"'),
              # Item('camino_tracking_config',style='custom',visible_when='processing_tool=="Camino"'),
              # Item('fsl_tracking_config',style='custom',visible_when='processing_tool=="FSL"'),
              # Item('gibbs_tracking_config',style='custom',visible_when='processing_tool=="Gibbs"'),
              label='Tracking', show_border=True, show_labels=False),
        Group(
            Item('custom_track_file', style='simple'),
            visible_when='tracking_processing_tool=="Custom"'),
        height=750,
        width=500
    )

    def __init__(self):
        DiffusionConfig.__init__(self)
        # self.dtk_recon_config = DTK_recon_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_recon_config = Dipy_recon_configUI(imaging_model=self.diffusion_imaging_model,
                                                     recon_mode=self.diffusion_model,
                                                     tracking_processing_tool=self.tracking_processing_tool)
        self.mrtrix_recon_config = MRtrix_recon_configUI(imaging_model=self.diffusion_imaging_model,
                                                         recon_mode=self.diffusion_model)
        # self.camino_recon_config = Camino_recon_config(imaging_model=self.diffusion_imaging_model)
        # self.fsl_recon_config = FSL_recon_config()
        # self.gibbs_recon_config = Gibbs_recon_config()
        # self.dtk_tracking_config = DTK_tracking_config()
        # self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_tracking_config = Dipy_tracking_configUI(imaging_model=self.diffusion_imaging_model,
                                                           tracking_mode=self.diffusion_model,
                                                           SD=self.mrtrix_recon_config.local_model)
        self.mrtrix_tracking_config = MRtrix_tracking_configUI(tracking_mode=self.diffusion_model,
                                                               SD=self.mrtrix_recon_config.local_model)
        # self.camino_tracking_config = Camino_tracking_config(imaging_model=self.diffusion_imaging_model,tracking_mode=self.diffusion_model)
        # self.fsl_tracking_config = FSL_tracking_config()
        # self.gibbs_tracking_config = Gibbs_tracking_config()

        self.mrtrix_recon_config.on_trait_change(
            self.update_mrtrix_tracking_SD, 'local_model')
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_SD, 'local_model')
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_sh_order, 'lmax_order')

        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'model_type')
        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'local_model')
        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'inversion')
        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'fallback_index')


class DiffusionStageUI(DiffusionStage):
    inspect_output_button = Button('View')

    inspect_outputs_view = View(Group(
        Item('name', editor=TitleEditor(), show_label=False),
        Group(
            Item('inspect_outputs_enum', show_label=False),
            Item('inspect_output_button', enabled_when='inspect_outputs_enum!="Outputs not available"',
                 show_label=False),
            label='View outputs', show_border=True
        )
    ),
        scrollable=True, resizable=True, kind='livemodal', title='Inspect stage outputs', buttons=['OK', 'Cancel']
    )

    config_view = View(Group(
        Item('name', editor=TitleEditor(), show_label=False),
        Group(
            Item('config', style='custom', show_label=False),
            label='Configuration', show_border=True
        ),
    ),
        scrollable=True, resizable=True, height=900, width=500, kind='livemodal', title='Edit stage configuration',
        buttons=['OK', 'Cancel']
    )

    def __init__(self, bids_dir, output_dir):
        DiffusionStage.__init__(self, bids_dir, output_dir)
        self.config = DiffusionConfigUI()

    def _inspect_output_button_fired(self, info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
