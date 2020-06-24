# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP registration stage
"""

# General imports
import os
import pickle
import gzip

from traitsui.api import *
from traits.api import *

import subprocess

# Own imports
# from cmp.bidsappmanager.stages.common import Stage

from cmp.stages.registration.registration import RegistrationConfig, RegistrationStage


class RegistrationConfigUI(RegistrationConfig):
    traits_view = View(
        Item('registration_mode', editor=EnumEditor(name='registration_mode_trait')),
        Group(Item('uses_qform'),
              Item('dof'),
              Item('fsl_cost', label="FLIRT metric"),
              Item('no_search'),
              Item('flirt_args'),
              label='FSL registration settings', show_border=True, visible_when='registration_mode=="FSL"'),
        Group(Item('uses_qform'),
              Item('dof'),
              Item('fsl_cost', label="FLIRT metric"),
              Item('no_search'),
              Item('flirt_args'),
              label='FSL registration settings', show_border=True, visible_when='registration_mode=="FSL (Linear)"'),
        Group(
            Group(
                HGroup(
                    Item('ants_interpolation', label="Interpolation"),
                    Item('ants_bspline_interpolation_parameters', label="Parameters",
                         visible_when='ants_interpolation=="BSpline"'),
                    Item('ants_gauss_interpolation_parameters', label="Parameters",
                         visible_when='ants_interpolation=="Gaussian"'),
                    Item('ants_multilab_interpolation_parameters', label="Parameters",
                         visible_when='ants_interpolation=="MultiLabel"')
                ),
                HGroup(
                    Item('ants_lower_quantile', label='winsorize lower quantile'),
                    Item('ants_upper_quantile', label='winsorize upper quantile')
                ),
                HGroup(
                    Item('ants_convergence_thresh', label='Convergence threshold'),
                    Item('ants_convergence_winsize', label='Convergence window size')
                ),
                HGroup(
                    Item('use_float_precision', label='Use float precision to save memory'),
                ),
                label="General", show_border=False
            ),
            Group(
                Item('ants_linear_cost', label="Metric"),
                Item('ants_linear_gradient_step', label="Gradient step size"),
                HGroup(
                    Item('ants_linear_sampling_strategy', label="Sampling strategy"),
                    Item('ants_linear_sampling_perc', label="Sampling percentage",
                         visible_when='ants_linear_sampling_strategy!="None"')
                ),
                Item('ants_linear_gradient_step', label="Gradient step size"),
                label="Rigid + Affine", show_border=False
            ),
            Item('ants_perform_syn', label='Symmetric diffeomorphic SyN registration'),
            Group(
                Item('ants_nonlinear_cost', label="Metric"),
                Item('ants_nonlinear_gradient_step', label="Gradient step size"),
                Item('ants_nonlinear_update_field_variance', label="Update field variance in voxel space"),
                Item('ants_nonlinear_total_field_variance', label="Total field variance in voxel space"),
                label="SyN (symmetric diffeomorphic registration)", show_border=False, visible_when='ants_perform_syn'
            ),
            label='ANTs registration settings', show_border=True, visible_when='registration_mode=="ANTs"'
        ),
        Group('init', 'contrast_type',
              label='BBregister registration settings', show_border=True,
              visible_when='registration_mode=="BBregister (FS)"'),
        kind='live',
    )


class RegistrationStageUI(RegistrationStage):
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
        scrollable=True, resizable=True, width=620, kind='livemodal', title='Inspect stage outputs',
        buttons=['OK', 'Cancel']
    )
    
    config_view = View(Group(
        Item('name', editor=TitleEditor(), show_label=False),
        Group(
            Item('config', style='custom', show_label=False),
            label='Configuration', show_border=True
        ),
    ),
        scrollable=True, resizable=True, height=650, width=650, kind='livemodal', title='Edit stage configuration',
        buttons=['OK', 'Cancel']
    )
    
    config_view_fmri = View(Group(
        Item('name', editor=TitleEditor(), show_label=False),
        Group(
            Item('config', style='custom', show_label=False),
            label='Configuration', show_border=True
        ),
    ),
        scrollable=True, resizable=True, height=366, width=336, kind='livemodal', title='Edit stage configuration',
        buttons=['OK', 'Cancel']
    )
    
    def __init__(self, pipeline_mode):
        RegistrationStage.__init__(self, pipeline_mode)
        self.config = RegistrationConfigUI()
        self.config.pipeline = pipeline_mode
        if self.config.pipeline == "fMRI":
            self.config.registration_mode = 'FSL (Linear)'
            self.config.registration_mode_trait = ['FSL (Linear)', 'BBregister (FS)']
            self.inputs = self.inputs + ["eroded_csf", "eroded_wm", "eroded_brain"]
            self.outputs = self.outputs + ["eroded_wm_registered_crop", "eroded_csf_registered_crop",
                                           "eroded_brain_registered_crop"]
    
    def _inspect_output_button_fired(self, info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
