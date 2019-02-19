# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Reconstruction methods and workflows
"""

# General imports
import re
import os
from traits.api import *
from traitsui.api import *
import pkg_resources

from cmp.stages.diffusion.reconstruction import Dipy_recon_config, MRtrix_recon_config

# Reconstruction configuration

class Dipy_recon_configUI(Dipy_recon_config):

    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))

    traits_view = View(#Item('gradient_table',label='Gradient table (x,y,z,b):'),
                       Item('flip_table_axis',style='custom',label='Flip bvecs:'),
                       #Item('custom_gradient_table',enabled_when='gradient_table_file=="Custom..."'),
               #Item('b_value'),
               #Item('b0_volumes'),
                       Group(
                            Item('local_model',editor=EnumEditor(name='local_model_editor')),
                            Group(
                                Item('lmax_order'),
                                #Item('normalize_to_B0'),
                                Item('single_fib_thr',label = 'FA threshold'),
                                visible_when='local_model'
                                ),
                            visible_when='imaging_model != "DSI"'
                            ),
                       Group(
                            Item('shore_radial_order',label='Radial order'),
                            Item('shore_zeta',label='Scale factor (zeta)'),
                            Item('shore_lambdaN',label='Radial regularization constant'),
                            Item('shore_lambdaL',label='Angular regularization constant'),
                            Item('shore_tau',label='Diffusion time (s)'),
                            Item('shore_constrain_e0',label='Constrain the optimization such that E(0) = 1.'),
                            Item('shore_positive_constraint',label='Constrain the propagator to be positive.'),
                            label='Parameters of SHORE reconstruction model',
                            visible_when='imaging_model == "DSI"'
                            ),
                       Item('mapmri'),
                       Group(
                            VGroup(
                                Item('radial_order'),
                                HGroup(Item('small_delta'),Item('big_delta'))
                            ),
                            HGroup(
                                Item('laplacian_regularization'),Item('laplacian_weighting')
                            ),
                            Item('positivity_constraint'),
                            label="MAP_MRI settings",
                            visible_when='mapmri'
                       )
                    )


class MRtrix_recon_configUI(MRtrix_recon_config):

    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))

    traits_view = View(#Item('gradient_table',label='Gradient table (x,y,z,b):'),
                       Item('flip_table_axis',style='custom',label='Flip gradient table:'),
                       #Item('custom_gradient_table',enabled_when='gradient_table_file=="Custom..."'),
		       #Item('b_value'),
		       #Item('b0_volumes'),
                       Item('local_model',editor=EnumEditor(name='local_model_editor')),
		       Group(Item('lmax_order'),
		       Item('normalize_to_B0'),
		       Item('single_fib_thr',label = 'FA threshold'),visible_when='local_model'),
                       )

# class DTK_recon_config(HasTraits):
#     imaging_model = Str
#     maximum_b_value = Int(1000)
#     gradient_table_file = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
#                           'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256','Custom...'])
#     gradient_table = Str
#     custom_gradient_table = File
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     dsi_number_of_directions = Enum([514,257,124])
#     number_of_directions = Int(514)
#     number_of_output_directions = Int(181)
#     recon_matrix_file = Str('DSI_matrix_515x181.dat')
#     apply_gradient_orientation_correction = Bool(True)
#     number_of_averages = Int(1)
#     multiple_high_b_values = Bool(False)
#     number_of_b0_volumes = Int(1)
#
#     compute_additional_maps = List(['gFA','skewness','kurtosis','P0'],
#                                   editor=CheckListEditor(values=['gFA','skewness','kurtosis','P0'],cols=4))
#
#     traits_view = View(Item('maximum_b_value',visible_when='imaging_model=="DTI"'),
#                        Item('gradient_table_file',visible_when='imaging_model!="DSI"'),
#                        Item('dsi_number_of_directions',visible_when='imaging_model=="DSI"'),
#                        Item('number_of_directions',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
#                        Item('custom_gradient_table',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        Item('number_of_averages',visible_when='imaging_model=="DTI"'),
#                        Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
#                        'number_of_b0_volumes',
#                        Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
#                        Item('compute_additional_maps',style='custom',visible_when='imaging_model!="DTI"'),
#                        )
#
#     def _dsi_number_of_directions_changed(self, new):
#         print("Number of directions changed to %d" % new )
#         self.recon_matrix_file = 'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(new)+1}
#
#     def _gradient_table_file_changed(self, new):
#         if new != 'Custom...':
#             self.gradient_table = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),new+'.txt')
#             if os.path.exists('cmtklib'):
#                 self.gradient_table = os.path.abspath(self.gradient_table)
#             self.number_of_directions = int(re.search('\d+',new).group(0))
#
#     def _custom_gradient_table_changed(self, new):
#         self.gradient_table = new
#
#     def _imaging_model_changed(self, new):
#         if new == 'DTI' or new == 'HARDI':
#             self._gradient_table_file_changed(self.gradient_table_file)
#
#
# class Camino_recon_config(HasTraits):
#     b_value = Int (1000)
#     model_type = Enum('Single-Tensor',['Single-Tensor','Two-Tensor','Three-Tensor','Other models'])
#     singleTensor_models = {'dt':'Linear fit','nldt_pos':'Non linear positive semi-definite','nldt':'Unconstrained non linear','ldt_wtd':'Weighted linear'}
#     local_model = Str('dt')
#     local_model_editor = Dict(singleTensor_models)
#     snr = Float(10.0)
#     mixing_eq = Bool()
#     fallback_model = Str('dt')
#     fallback_editor = Dict(singleTensor_models)
#     fallback_index = Int(1) # index for 'dt' which is the default fallback_model
#     inversion = Int(1)
#
#     gradient_table = File
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#
#     traits_view = View(Item('gradient_table',label='Gradient table (x,y,z,b):'),
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        'model_type',
# 		               VGroup(Item('local_model',label="Camino model",editor=EnumEditor(name='local_model_editor')),
#                               Item('snr',visible_when='local_model=="restore"'),
#                               Item('mixing_eq',label='Compartment mixing parameter = 0.5',visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"'),
#                               Item('fallback_model',label='Initialisation and fallback model',editor=EnumEditor(name='fallback_editor'),visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"')
#                        )
#                        )
#
#     def _model_type_changed(self,new):
#         if new == 'Single-Tensor':
#             self.local_model_editor = self.singleTensor_models
#             self.local_model = 'dt'
#             self.mixing_eq = False
#         elif new == 'Two-Tensor':
#             self.local_model_editor = {'cylcyl':'Both Cylindrically symmetric','pospos':'Both positive','poscyl':'One positive, one cylindrically symmetric'}
#             self.local_model = 'cylcyl'
#         elif new == 'Three-Tensor':
#             self.local_model_editor = {'cylcylcyl':'All cylindrically symmetric','pospospos':'All positive','posposcyl':'Two positive, one cylindrically symmetric','poscylcyl':'Two cylindrically symmetric, one positive'}
#             self.local_model = 'cylcylcyl'
#         elif new == 'Other models':
#             self.local_model_editor = {'adc':'ADC','ball_stick':'Ball stick', 'restore':'Restore'}
#             self.local_model = 'adc'
#             self.mixing_eq = False
#
#         self.update_inversion()
#
#     def update_inversion(self):
#         inversion_dict = {'ball_stick':-3, 'restore':-2, 'adc':-1, 'ltd':1, 'dt':1, 'nldt_pos':2,'nldt':4,'ldt_wtd':7,'cylcyl':10, 'pospos':30, 'poscyl':50, 'cylcylcyl':210, 'pospospos':230, 'posposcyl':250, 'poscylcyl':270}
#         if self.model_type == 'Single-Tensor' or self.model_type == 'Other models':
#             self.inversion = inversion_dict[self.local_model]
#         else:# class DTK_recon_config(HasTraits):
#     imaging_model = Str
#     maximum_b_value = Int(1000)
#     gradient_table_file = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
#                           'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256','Custom...'])
#     gradient_table = Str
#     custom_gradient_table = File
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     dsi_number_of_directions = Enum([514,257,124])
#     number_of_directions = Int(514)
#     number_of_output_directions = Int(181)
#     recon_matrix_file = Str('DSI_matrix_515x181.dat')
#     apply_gradient_orientation_correction = Bool(True)
#     number_of_averages = Int(1)
#     multiple_high_b_values = Bool(False)
#     number_of_b0_volumes = Int(1)
#
#     compute_additional_maps = List(['gFA','skewness','kurtosis','P0'],
#                                   editor=CheckListEditor(values=['gFA','skewness','kurtosis','P0'],cols=4))
#
#     traits_view = View(Item('maximum_b_value',visible_when='imaging_model=="DTI"'),
#                        Item('gradient_table_file',visible_when='imaging_model!="DSI"'),
#                        Item('dsi_number_of_directions',visible_when='imaging_model=="DSI"'),
#                        Item('number_of_directions',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
#                        Item('custom_gradient_table',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        Item('number_of_averages',visible_when='imaging_model=="DTI"'),
#                        Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
#                        'number_of_b0_volumes',
#                        Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
#                        Item('compute_additional_maps',style='custom',visible_when='imaging_model!="DTI"'),
#                        )
# # class DTK_recon_config(HasTraits):
#     imaging_model = Str
#     maximum_b_value = Int(1000)
#     gradient_table_file = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
#                           'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256','Custom...'])
#     gradient_table = Str
#     custom_gradient_table = File
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     dsi_number_of_directions = Enum([514,257,124])
#     number_of_directions = Int(514)
#     number_of_output_directions = Int(181)
#     recon_matrix_file = Str('DSI_matrix_515x181.dat')
#     apply_gradient_orientation_correction = Bool(True)
#     number_of_averages = Int(1)
#     multiple_high_b_values = Bool(False)
#     number_of_b0_volumes = Int(1)
#
#     compute_additional_maps = List(['gFA','skewness','kurtosis','P0'],
#                                   editor=CheckListEditor(values=['gFA','skewness','kurtosis','P0'],cols=4))
#
#     traits_view = View(Item('maximum_b_value',visible_when='imaging_model=="DTI"'),
#                        Item('gradient_table_file',visible_when='imaging_model!="DSI"'),
#                        Item('dsi_number_of_directions',visible_when='imaging_model=="DSI"'),
#                        Item('number_of_directions',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
#                        Item('custom_gradient_table',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        Item('number_of_averages',visible_when='imaging_model=="DTI"'),
#                        Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
#                        'number_of_b0_volumes',
#                        Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
#                        Item('compute_additional_maps',style='custom',visible_when='imaging_model!="DTI"'),
#                        )
#
#     def _dsi_number_of_directions_changed(self, new):
#         print("Number of directions changed to %d" % new )
#         self.recon_matrix_file = 'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(new)+1}
#
#     def _gradient_table_file_changed(self, new):
#         if new != 'Custom...':
#             self.gradient_table = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),new+'.txt')
#             if os.path.exists('cmtklib'):
#                 self.gradient_table = os.path.abspath(self.gradient_table)
#             self.number_of_directions = int(re.search('\d+',new).group(0))
#
#     def _custom_gradient_table_changed(self, new):
#         self.gradient_table = new
#
#     def _imaging_model_changed(self, new):
#         if new == 'DTI' or new == 'HARDI':
#             self._gradient_table_file_changed(self.gradient_table_file)
#
#
# class Camino_recon_config(HasTraits):
#     b_value = Int (1000)
#     model_type = Enum('Single-Tensor',['Single-Tensor','Two-Tensor','Three-Tensor','Other models'])
#     singleTensor_models = {'dt':'Linear fit','nldt_pos':'Non linear positive semi-definite','nldt':'Unconstrained non linear','ldt_wtd':'Weighted linear'}
#     local_model = Str('dt')
#     local_model_editor = Dict(singleTensor_models)
#     snr = Float(10.0)
#     mixing_eq = Bool()
#     fallback_model = Str('dt')
#     fallback_editor = Dict(singleTensor_models)
#     fallback_index = Int(1) # index for 'dt' which is the default fallback_model
#     inversion = Int(1)
#
#     gradient_table = File
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#
#     traits_view = View(Item('gradient_table',label='Gradient table (x,y,z,b):'),
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        'model_type',
# 		               VGroup(Item('local_model',label="Camino model",editor=EnumEditor(name='local_model_editor')),
#                               Item('snr',visible_when='local_model=="restore"'),
#                               Item('mixing_eq',label='Compartment mixing parameter = 0.5',visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"'),
#                               Item('fallback_model',label='Initialisation and fallback model',editor=EnumEditor(name='fallback_editor'),visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"')
#                        )
#                        )
#
#     def _model_type_changed(self,new):
#         if new == 'Single-Tensor':
#             self.local_model_editor = self.singleTensor_models
#             self.local_model = 'dt'
#             self.mixing_eq = False
#         elif new == 'Two-Tensor':
#             self.local_model_editor = {'cylcyl':'Both Cylindrically symmetric','pospos':'Both positive','poscyl':'One positive, one cylindrically symmetric'}
#             self.local_model = 'cylcyl'
#         elif new == 'Three-Tensor':
#             self.local_model_editor = {'cylcylcyl':'All cylindrically symmetric','pospospos':'All positive','posposcyl':'Two positive, one cylindrically symmetric','poscylcyl':'Two cylindrically symmetric, one positive'}
#             self.local_model = 'cylcylcyl'
#         elif new == 'Other models':
#             self.local_model_editor = {'adc':'ADC','ball_stick':'Ball stick', 'restore':'Restore'}
#             self.local_model = 'adc'
#             self.mixing_eq = False
#
#         self.update_inversion()
#
#     def update_inversion(self):
#         inversion_dict = {'ball_stick':-3, 'restore':-2, 'adc':-1, 'ltd':1, 'dt':1, 'nldt_pos':2,'nldt':4,'ldt_wtd':7,'cylcyl':10, 'pospos':30, 'poscyl':50, 'cylcylcyl':210, 'pospospos':230, 'posposcyl':250, 'poscylcyl':270}
#         if self.model_type == 'Single-Tensor' or self.model_type == 'Other models':
#             self.inversion = inversion_dict[self.local_model]
#         else:
#             self.inversion = inversion_dict[self.local_model] + inversion_dict[self.fallback_model]
#             self.fallback_index = inversion_dict[self.fallback_model]
#             if self.mixing_eq:
#                 self.inversion = self.inversion + 10
#
#     def _local_model_changed(self,new):
#         self.update_inversion()
#
#     def _mixing_eq_changed(self,new):
#         self.update_inversion()
#
#     def _fallback_model_changed(self,new):
#         self.update_inversion()
#
# class FSL_recon_config(HasTraits):
#
#     b_values = File()
#     b_vectors = File()
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#
#     # BEDPOSTX parameters
#     burn_period = Int(0)
#     fibres_per_voxel = Int(1)
#     jumps = Int(1250)
#     sampling = Int(25)
#     weight = Float(1.00)
#
#     traits_view = View('b_values',
#                        'b_vectors',
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        VGroup('burn_period','fibres_per_voxel','jumps','sampling','weight',show_border=True,label = 'BEDPOSTX parameters'),
#                       )
#
# class Gibbs_recon_config(HasTraits):
#     recon_model = Enum(['Tensor','CSD'])
#     b_values = File()
#     b_vectors = File()
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     sh_order = Enum(4,[2,4,6,8,10,12,14,16])
#     reg_lambda = Float(0.006)
#     csa = Bool(True)
#
#     traits_view = View(Item('recon_model',label='Reconstruction  model:'),
#                        'b_values',
#                        'b_vectors',
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        Group(Item('sh_order',label="Spherical Harmonics order"),
#                              Item('reg_lambda', label="Regularisation lambda factor"),
#                              Item('csa',label="Use constant solid angle"),
#                              show_border=True,label='CSD parameters', visible_when='recon_model == "CSD"'),
# 	           )
#     def _dsi_number_of_directions_changed(self, new):
#         print("Number of directions changed to %d" % new )
#         self.recon_matrix_file = 'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(new)+1}
#
#     def _gradient_table_file_changed(self, new):
#         if new != 'Custom...':
#             self.gradient_table = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),new+'.txt')
#             if os.path.exists('cmtklib'):
#                 self.gradient_table = os.path.abspath(self.gradient_table)
#             self.number_of_directions = int(re.search('\d+',new).group(0))
#
#     def _custom_gradient_table_changed(self, new):
#         self.gradient_table = new
#
#     def _imaging_model_changed(self, new):
#         if new == 'DTI' or new == 'HARDI':
#             self._gradient_table_file_changed(self.gradient_table_file)
#
#
# class Camino_recon_config(HasTraits):
#     b_value = Int (1000)
#     model_type = Enum('Single-Tensor',['Single-Tensor','Two-Tensor','Three-Tensor','Other models'])
#     singleTensor_models = {'dt':'Linear fit','nldt_pos':'Non linear positive semi-definite','nldt':'Unconstrained non linear','ldt_wtd':'Weighted linear'}
#     local_model = Str('dt')
#     local_model_editor = Dict(singleTensor_models)
#     snr = Float(10.0)
#     mixing_eq = Bool()
#     fallback_model = Str('dt')
#     fallback_editor = Dict(singleTensor_models)
#     fallback_index = Int(1) # index for 'dt' which is the default fallback_model
#     inversion = Int(1)
#
#     gradient_table = File
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#
#     traits_view = View(Item('gradient_table',label='Gradient table (x,y,z,b):'),
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        'model_type',
# 		               VGroup(Item('local_model',label="Camino model",editor=EnumEditor(name='local_model_editor')),
#                               Item('snr',visible_when='local_model=="restore"'),
#                               Item('mixing_eq',label='Compartment mixing parameter = 0.5',visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"'),
#                               Item('fallback_model',label='Initialisation and fallback model',editor=EnumEditor(name='fallback_editor'),visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"')
#                        )
#                        )
#
#     def _model_type_changed(self,new):
#         if new == 'Single-Tensor':
#             self.local_model_editor = self.singleTensor_models
#             self.local_model = 'dt'
#             self.mixing_eq = False
#         elif new == 'Two-Tensor':
#             self.local_model_editor = {'cylcyl':'Both Cylindrically symmetric','pospos':'Both positive','poscyl':'One positive, one cylindrically symmetric'}
#             self.local_model = 'cylcyl'
#         elif new == 'Three-Tensor':
#             self.local_model_editor = {'cylcylcyl':'All cylindrically symmetric','pospospos':'All positive','posposcyl':'Two positive, one cylindrically symmetric','poscylcyl':'Two cylindrically symmetric, one positive'}
#             self.local_model = 'cylcylcyl'
#         elif new == 'Other models':
#             self.local_model_editor = {'adc':'ADC','ball_stick':'Ball stick', 'restore':'Restore'}
#             self.local_model = 'adc'
#             self.mixing_eq = False
#
#         self.update_inversion()
#
#     def update_inversion(self):
#         inversion_dict = {'ball_stick':-3, 'restore':-2, 'adc':-1, 'ltd':1, 'dt':1, 'nldt_pos':2,'nldt':4,'ldt_wtd':7,'cylcyl':10, 'pospos':30, 'poscyl':50, 'cylcylcyl':210, 'pospospos':230, 'posposcyl':250, 'poscylcyl':270}
#         if self.model_type == 'Single-Tensor' or self.model_type == 'Other models':
#             self.inversion = inversion_dict[self.local_model]
#         else:
#             self.inversion = inversion_dict[self.local_model] + inversion_dict[self.fallback_model]
#             self.fallback_index = inversion_dict[self.fallback_model]
#             if self.mixing_eq:
#                 self.inversion = self.inversion + 10
#
#     def _local_model_changed(self,new):
#         self.update_inversion()
#
#     def _mixing_eq_changed(self,new):
#         self.update_inversion()
#
#     def _fallback_model_changed(self,new):
#         self.update_inversion()
#
# class FSL_recon_config(HasTraits):
#
#     b_values = File()
#     b_vectors = File()
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#
#     # BEDPOSTX parameters
#     burn_period = Int(0)
#     fibres_per_voxel = Int(1)
#     jumps = Int(1250)
#     sampling = Int(25)
#     weight = Float(1.00)
#
#     traits_view = View('b_values',
#                        'b_vectors',
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        VGroup('burn_period','fibres_per_voxel','jumps','sampling','weight',show_border=True,label = 'BEDPOSTX parameters'),
#                       )
#
# class Gibbs_recon_config(HasTraits):
#     recon_model = Enum(['Tensor','CSD'])
#     b_values = File()
#     b_vectors = File()
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     sh_order = Enum(4,[2,4,6,8,10,12,14,16])
#     reg_lambda = Float(0.006)
#     csa = Bool(True)
#
#     traits_view = View(Item('recon_model',label='Reconstruction  model:'),
#                        'b_values',
#                        'b_vectors',
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        Group(Item('sh_order',label="Spherical Harmonics order"),
#                              Item('reg_lambda', label="Regularisation lambda factor"),
#                              Item('csa',label="Use constant solid angle"),
#                              show_border=True,label='CSD parameters', visible_when='recon_model == "CSD"'),
# 	           )
#             self.inversion = inversion_dict[self.local_model] + inversion_dict[self.fallback_model]
#             self.fallback_index = inversion_dict[self.fallback_model]
#             if self.mixing_eq:
#                 self.inversion = self.inversion + 10
#
#     def _local_model_changed(self,new):
#         self.update_inversion()
#
#     def _mixing_eq_changed(self,new):
#         self.update_inversion()
#
#     def _fallback_model_changed(self,new):
#         self.update_inversion()
#
# class FSL_recon_config(HasTraits):
#
#     b_values = File()
#     b_vectors = File()
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#
#     # BEDPOSTX parameters
#     burn_period = Int(0)
#     fibres_per_voxel = Int(1)
#     jumps = Int(1250)
#     sampling = Int(25)
#     weight = Float(1.00)
#
#     traits_view = View('b_values',
#                        'b_vectors',
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        VGroup('burn_period','fibres_per_voxel','jumps','sampling','weight',show_border=True,label = 'BEDPOSTX parameters'),
#                       )
#
# class Gibbs_recon_config(HasTraits):
#     recon_model = Enum(['Tensor','CSD'])
#     b_values = File()
#     b_vectors = File()
#     flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
#     sh_order = Enum(4,[2,4,6,8,10,12,14,16])
#     reg_lambda = Float(0.006)
#     csa = Bool(True)
#
#     traits_view = View(Item('recon_model',label='Reconstruction  model:'),
#                        'b_values',
#                        'b_vectors',
#                        Item('flip_table_axis',style='custom',label='Flip table:'),
#                        Group(Item('sh_order',label="Spherical Harmonics order"),
#                              Item('reg_lambda', label="Regularisation lambda factor"),
#                              Item('csa',label="Use constant solid angle"),
#                              show_border=True,label='CSD parameters', visible_when='recon_model == "CSD"'),
# 	           )
