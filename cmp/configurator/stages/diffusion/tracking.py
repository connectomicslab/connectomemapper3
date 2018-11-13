# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Tracking methods and workflows of the diffusion stage
"""

from traits.api import *
from traitsui.api import *


class DTB_tracking_config(HasTraits):
    imaging_model = Str
    flip_input = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    angle = Int(60)
    step_size = Float(1.0)
    seeds = Int(32)

    traits_view = View(Item('flip_input',style='custom'),'angle','step_size','seeds')

class Dipy_tracking_config(HasTraits):
    imaging_model = Str
    tracking_mode = Str
    SD = Bool
    number_of_seeds = Int(1000)
    fa_thresh = Float(0.2)
    step_size = Float(0.5)
    max_angle = Float(25.0)
    sh_order = Int(8)

    use_act = Bool(False, desc='Use FAST for partial volume estimation and Anatomically-Constrained Tractography (ACT) tissue classifier')
    fast_number_of_classes = Int(3)

    traits_view = View( Item('number_of_seeds',label="Number of seeds"),
                        Item('step_size',label="Step size)"),
                        Item('max_angle',label="Max angle (degree)"),
                        HGroup(
                            Item('use_act',label="Anatomically-Constrained Tractography using FAST"),
                            Item('fast_number_of_classes', label='Number of tissue classes (FAST)')
                            ),
                        Item('fa_thresh',label="FA threshold (classifier)",visible_when='use_act == False')
                        )

    def _SD_changed(self,new):
        if self.tracking_mode == "Deterministic" and not new:
            self.curvature = 2.0
        elif self.tracking_mode == "Deterministic" and new:
            self.curvature = 0.0
        elif self.tracking_mode == "Probabilistic":
            self.curvature = 1.0

    def _tracking_mode_changed(self,new):
        if new == "Deterministic" and not self.SD:
            self.curvature = 2.0
        elif new == "Deterministic" and self.SD:
            self.curvature = 0.0
        elif new == "Probabilistic":
            self.curvature = 1.0

    def _curvature_changed(self,new):
        if new <= 0.000001:
            self.curvature = 0.0

class MRtrix_tracking_config(HasTraits):
    tracking_mode = Str
    SD = Bool
    desired_number_of_tracks = Int(1000000)
    # max_number_of_seeds = Int(1000000000)
    curvature = Float(2.0)
    step_size = Float(0.5)
    min_length = Float(5)
    max_length = Float(500)
    angle = Float(45)
    cutoff_value = Float(1)

    use_act = Bool(True, desc="Anatomically-Constrained Tractography (ACT) based on Freesurfer parcellation")
    seed_from_gmwmi = Bool(False, desc="Seed from Grey Matter / White Matter interface (requires Anatomically-Constrained Tractography (ACT))")
    crop_at_gmwmi = Bool(True, desc="Crop streamline endpoints more precisely as they cross the GM-WM interface (requires Anatomically-Constrained Tractography (ACT))")
    backtrack = Bool(True, desc="Allow tracks to be truncated (requires Anatomically-Constrained Tractography (ACT))")

    traits_view = View( VGroup('desired_number_of_tracks',
                               # 'max_number_of_seeds',
                               HGroup('min_length','max_length'),
                               'angle',
                   			   Item('curvature',label="Curvature radius"),'step_size',
                               'cutoff_value',
                               label='Streamline settings'
                               ),
                        VGroup(
                            Item('use_act',label='Use ACT based on Freesurfer parcellation'),
                            Item('crop_at_gmwmi',visible_when='use_act'),
                            Item('backtrack',visible_when='use_act'),
                            Item('seed_from_gmwmi',visible_when='use_act'),
                            label='Anatomically-Constrained Tractography (ACT)'
                            )
		              )

    def _SD_changed(self,new):
        if self.tracking_mode == "Deterministic" and not new:
            self.curvature = 2.0
        elif self.tracking_mode == "Deterministic" and new:
            self.curvature = 0.0
        elif self.tracking_mode == "Probabilistic":
            self.curvature = 1.0

    def _use_act_changed(self,new):
        if new == False:
            self.crop_at_gmwmi = False
            self.seed_from_gmwmi = False
            self.backtrack = False
        else:
            self.crop_at_gmwmi = True
            self.seed_from_gmwmi = True
            self.backtrack = False

    def _tracking_mode_changed(self,new):
        if new == "Deterministic" and not self.SD:
            self.curvature = 2.0
        elif new == "Deterministic" and self.SD:
            self.curvature = 0.0
        elif new == "Probabilistic":
            self.curvature = 1.0

    def _curvature_changed(self,new):
        if new <= 0.000001:
            self.curvature = 0.0

class Camino_tracking_config(HasTraits):
    imaging_model = Str
    tracking_mode = Str
    inversion_index = Int(1) # 1=='dt' which is the default local_model in reconstruction.py
    fallback_index = Int(1) # 1=='dt' which is the default fallback_index in reconstruction.py
    angle = Float(60)
    cross_angle = Float(20)
    trace = Float(0.0000000021)
    units = Enum(["m^2/s","s/mm^2"])
    tracking_model = Str('dt')
    snr = Float(20)
    iterations = Int(50)
    pdf = Enum(['bingham', 'watson', 'acg'])
    traits_view = View( 'angle',
                        Item('snr',visible_when="tracking_mode=='Probabilistic'"),
                        Item('iterations',visible_when="tracking_mode=='Probabilistic'"),
                        Item('pdf',visible_when="tracking_mode=='Probabilistic'"),
                        Item('cross_angle', label="Crossing angle", visible_when='(tracking_mode=="Probabilistic") and (inversion_index > 9)'),
                        HGroup('trace','units')
                        )

    def _units_changed(self,new):
        if new == "s/mm^2":
            self.trace = self.trace * 1000000
        elif new == "m^2/s":
            self.trace = self.trace / 1000000


class FSL_tracking_config(HasTraits):
    number_of_samples = Int(5000)
    number_of_steps = Int(2000)
    distance_threshold = Float(0)
    curvature_threshold = Float(0.2)

    traits_view = View('number_of_samples','number_of_steps','distance_threshold','curvature_threshold')

class Gibbs_tracking_config(HasTraits):
    iterations = Int(100000000)
    particle_length=Float(1.5)
    particle_width=Float(0.5)
    particle_weight=Float(0.0003)
    temp_start=Float(0.1)
    temp_end=Float(0.001)
    inexbalance=Int(-2)
    fiber_length=Float(20)
    curvature_threshold=Float(90)

    traits_view = View('iterations','particle_length','particle_width','particle_weight','temp_start','temp_end','inexbalance','fiber_length','curvature_threshold')

class DTK_tracking_config(HasTraits):
    angle_threshold = Int(60)
    mask1_threshold_auto = Bool(True)
    mask1_threshold = List([0.0,1.0])
    mask1_input = Enum('DWI',['B0','DWI'])

    traits_view = View('mask1_input','angle_threshold','mask1_threshold_auto',
                        Item('mask1_threshold',enabled_when='mask1_threshold_auto==False'))
