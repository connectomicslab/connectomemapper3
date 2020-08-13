# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Tracking methods and workflows of the diffusion stage
"""

from traits.api import *
from traitsui.api import *

from cmp.stages.diffusion.tracking import Dipy_tracking_config, MRtrix_tracking_config


class Dipy_tracking_configUI(Dipy_tracking_config):
    traits_view = View(VGroup(
        Group(
            Item('seed_density', label="Seed density"),
            Item('step_size', label="Step size"),
            Item('max_angle', label="Max angle (degree)"),
            Item('fa_thresh', label="FA threshold (classifier)",
                 visible_when='seed_from_gmwmi is False'),
            label='Streamlines settings',
            orientation='vertical'
        ),
        Group(
            Item('use_act', label="Use PFT"),
            Item('seed_from_gmwmi', visible_when='use_act'),
            # Item('fast_number_of_classes', label='Number of tissue classes (FAST)')
            label='Particle Filtering Tractography (PFT)',
            visible_when='tracking_mode=="Probabilistic"',
            orientation='vertical'
        )
    ),
    )


class MRtrix_tracking_configUI(MRtrix_tracking_config):
    traits_view = View(VGroup(
        Group(
            'desired_number_of_tracks',
            # 'max_number_of_seeds',
            HGroup('min_length', 'max_length'),
            'angle',
            Item('curvature', label="Curvature radius"),
            'step_size',
            'cutoff_value',
            label='Streamline settings',
            orientation='vertical'
        ),
        Group(
            Item('use_act', label='Use ACT'),
            Item('crop_at_gmwmi', visible_when='use_act'),
            Item('backtrack', visible_when='use_act',
                 enabled_when='tracking_mode=="Probabilistic"'),
            Item('seed_from_gmwmi', visible_when='use_act'),
            label='Anatomically-Constrained Tractography (ACT)',
            orientation='vertical'
        )
    ),
    )

# class DTB_tracking_config(HasTraits):
#     imaging_model = Str
#     flip_input = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     angle = Int(60)
#     step_size = Float(1.0)
#     seeds = Int(32)
#
#     traits_view = View(Item('flip_input',style='custom'),'angle','step_size','seeds')
#
#
# class Camino_tracking_config(HasTraits):
#     imaging_model = Str
#     tracking_mode = Str
#     inversion_index = Int(1) # 1=='dt' which is the default local_model in reconstruction.py
#     fallback_index = Int(1) # 1=='dt' which is the default fallback_index in reconstruction.py
#     angle = Float(60)
#     cross_angle = Float(20)
#     trace = Float(0.0000000021)
#     units = Enum(["m^2/s","s/mm^2"])
#     tracking_model = Str('dt')
#     snr = Float(20)
#     iterations = Int(50)
#     pdf = Enum(['bingham', 'watson', 'acg'])
#     traits_view = View( 'angle',
#                         Item('snr',visible_when="tracking_mode=='Probabilistic'"),
#                         Item('iterations',visible_when="tracking_mode=='Probabilistic'"),
#                         Item('pdf',visible_when="tracking_mode=='Probabilistic'"),
#                         Item('cross_angle', label="Crossing angle", visible_when='(tracking_mode=="Probabilistic") and (inversion_index > 9)'),
#                         HGroup('trace','units')
#                         )
#
#     def _units_changed(self,new):
#         if new == "s/mm^2":
#             self.trace = self.trace * 1000000
#         elif new == "m^2/s":
#             self.trace = self.trace / 1000000
#
#
# class FSL_tracking_config(HasTraits):
#     number_of_samples = Int(5000)
#     number_of_steps = Int(2000)
#     distance_threshold = Float(0)
#     curvature_threshold = Float(0.2)
#
#     traits_view = View('number_of_samples','number_of_steps','distance_threshold','curvature_threshold')
#
# class Gibbs_tracking_config(HasTraits):
#     iterations = Int(100000000)
#     particle_length=Float(1.5)
#     particle_width=Float(0.5)
#     particle_weight=Float(0.0003)
#     temp_start=Float(0.1)
#     temp_end=Float(0.001)
#     inexbalance=Int(-2)
#     fiber_length=Float(20)
#     curvature_threshold=Float(90)
#
#     traits_view = View('iterations','particle_length','particle_width','particle_weight','temp_start','temp_end','inexbalance','fiber_length','curvature_threshold')
#
# class DTK_tracking_config(HasTraits):
#     angle_threshold = Int(60)
#     mask1_threshold_auto = Bool(True)
#     mask1_threshold = List([0.0,1.0])
#     mask1_input = Enum('DWI',['B0','DWI'])
#
#     traits_view = View('mask1_input','angle_threshold','mask1_threshold_auto',
#                         Item('mask1_threshold',enabled_when='mask1_threshold_auto==False'))
