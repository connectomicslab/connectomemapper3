# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP segmentation stage
"""

# General imports
import os
import pickle
import gzip
import pkg_resources

from traits.api import *
from traitsui.api import *

import subprocess

# Own imports
# from cmp.bidsappmanager.stages.common import Stage

from cmp.stages.segmentation.segmentation import SegmentationConfig, SegmentationStage


class SegmentationConfigUI(SegmentationConfig):
    traits_view = View(Item('seg_tool', label="Segmentation tool"),
                       Group(
                           HGroup('make_isotropic',
                                  Item('isotropic_vox_size', label="Voxel size (mm)", visible_when='make_isotropic')),
                           Item('isotropic_interpolation', label='Interpolation',
                                visible_when='make_isotropic'),
                           'brain_mask_extraction_tool',
                           Item('ants_templatefile', label='Template',
                                visible_when='brain_mask_extraction_tool == "ANTs"'),
                           Item('ants_probmaskfile', label='Probability mask',
                                visible_when='brain_mask_extraction_tool == "ANTs"'),
                           Item('ants_regmaskfile', label='Extraction mask',
                                visible_when='brain_mask_extraction_tool == "ANTs"'),
                           Item('brain_mask_path', label='Brain mask path',
                                visible_when='brain_mask_extraction_tool == "Custom"'),
                           'freesurfer_args',
                           # 'use_existing_freesurfer_data',
                           # Item('freesurfer_subjects_dir', enabled_when='use_existing_freesurfer_data == True'),
                           # Item('freesurfer_subject_id',editor=EnumEditor(name='freesurfer_subject_id_trait'), enabled_when='use_existing_freesurfer_data == True'),
                           visible_when="seg_tool=='Freesurfer'"),
                       Group(
                           'white_matter_mask',
                           Item('brain_mask_path', label='Brain mask'),
                           visible_when='seg_tool=="Custom segmentation"')
                       )


class SegmentationStageUI(SegmentationStage):
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
        scrollable=True, resizable=True, height=400, width=450, kind='livemodal', title='Edit stage configuration',
        buttons=['OK', 'Cancel']
    )

    # General and UI members
    def __init__(self, bids_dir, output_dir):
        SegmentationStage.__init__(self, bids_dir, output_dir)
        self.config = SegmentationConfigUI()

    def _inspect_output_button_fired(self, info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
