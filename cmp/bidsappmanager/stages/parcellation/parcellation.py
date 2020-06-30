# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Parcellation
"""

# General imports
import os
import pickle
import gzip
import pkg_resources

from traits.api import *
from traits.trait_handlers import TraitListObject

from traitsui.api import *

import subprocess

# Own imports
# from cmp.bidsappmanager.stages.common import Stage

from cmp.stages.parcellation.parcellation import ParcellationConfig, ParcellationStage


class ParcellationConfigUI(ParcellationConfig):
    traits_view = View(Item('parcellation_scheme', editor=EnumEditor(name='parcellation_scheme_editor')),
                       Group(
                           'number_of_regions',
                           'atlas_nifti_file',
                           'graphml_file',
                           Group(
                               "csf_file", "brain_file",
                               show_border=True,
                               label="Files for nuisance regression (optional)",
                               visible_when="pipeline_mode=='fMRI'"
                           ),
                           visible_when='parcellation_scheme=="Custom"'
    ),
        Group(
                           'segment_hippocampal_subfields',
                           'segment_brainstem',
                           'include_thalamic_nuclei_parcellation',
                           Item('ants_precision_type', label='ANTs precision type',
                                enabled_when='include_thalamic_nuclei_parcellation'),
                           visible_when='parcellation_scheme=="Lausanne2018"'
    )
    )


class ParcellationStageUI(ParcellationStage):
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
        scrollable=True, resizable=True, height=280, width=450, kind='livemodal', title='Edit stage configuration',
        buttons=['OK', 'Cancel']
    )

    def __init__(self, pipeline_mode, bids_dir, output_dir):
        ParcellationStage.__init__(self, pipeline_mode, bids_dir, output_dir)
        self.config = ParcellationConfigUI()
        self.config.template_thalamus = os.path.join('app', 'connectomemapper3', 'cmtklib', 'data', 'segmentation',
                                                     'thalamus2018', 'mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz')
        self.config.thalamic_nuclei_maps = os.path.join('app', 'connectomemapper3', 'cmtklib', 'data', 'segmentation',
                                                        'thalamus2018', 'Thalamus_Nuclei-HCP-4DSPAMs.nii.gz')
        # FIXME Bids App / local
        # self.config.template_thalamus = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'thalamus2018', 'mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz'))
        # self.config.thalamic_nuclei_maps = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'thalamus2018', 'Thalamus_Nuclei-HCP-4DSPAMs.nii.gz'))

    def _inspect_output_button_fired(self, info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
