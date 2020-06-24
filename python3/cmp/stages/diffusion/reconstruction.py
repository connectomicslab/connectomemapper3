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
import shutil
from traits.api import *
import pkg_resources

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.mrtrix as mrtrix
import nipype.interfaces.camino as camino
from nipype.utils.filemanip import split_filename

from nipype.interfaces.base import CommandLine, CommandLineInputSpec, \
    traits, TraitedSpec, BaseInterface, BaseInterfaceInputSpec
import nipype.interfaces.base as nibase

from cmtklib.interfaces.mrtrix3 import Erode, MRtrix_mul, MRThreshold, MRConvert, EstimateResponseForSH, \
    ConstrainedSphericalDeconvolution, DWI2Tensor, Tensor2Vector
from nipype.interfaces.mrtrix3.reconst import FitTensor, EstimateFOD
from nipype.interfaces.mrtrix3.utils import TensorMetrics
# from nipype.interfaces.mrtrix3.preprocess import ResponseSD
from cmtklib.interfaces.misc import flipBvec, flipTable
from cmtklib.interfaces.dipy import DTIEstimateResponseSH, CSD, SHORE
# from nipype.interfaces.dipy import CSD

from nipype import logging

iflogger = logging.getLogger('nipype.interface')


# Reconstruction configuration

class Dipy_recon_config(HasTraits):
    imaging_model = Str
    # flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    flip_table_axis = List(['x', 'y', 'z'])
    # gradient_table = File
    local_model_editor = Dict({False: '1:Tensor', True: '2:Constrained Spherical Deconvolution'})
    local_model = Bool(True)
    lmax_order = Enum([2, 4, 6, 8, 10, 12, 14, 16])
    # normalize_to_B0 = Bool(False)
    single_fib_thr = Float(0.7, min=0, max=1)
    recon_mode = Str
    
    mapmri = Bool(False)
    
    tracking_processing_tool = Enum('MRtrix', 'Dipy')
    
    laplacian_regularization = traits.Bool(True, usedefault=True, desc=('Apply laplacian regularization'))
    
    laplacian_weighting = traits.Float(0.05, usedefault=True, desc=('Regularization weight'))
    
    positivity_constraint = traits.Bool(True, usedefault=True, desc=('Apply positivity constraint'))
    
    radial_order = traits.Int(8, usedefault=True,
                              desc=('radial order'))
    
    small_delta = traits.Float(0.02, mandatory=True,
                               desc=('Small data for gradient table (pulse duration)'))
    
    big_delta = traits.Float(0.5, mandatory=True,
                             desc=('Small data for gradient table (time interval)'))
    
    radial_order_values = traits.List([2, 4, 6, 8, 10, 12])
    shore_radial_order = Enum(6, values='radial_order_values', usedefault=True,
                              desc=('Even number that represents the order of the basis'))
    shore_zeta = traits.Int(700, usedefault=True, desc=('Scale factor'))
    shore_lambdaN = traits.Float(1e-8, usedefault=True, desc=('radial regularisation constant'))
    shore_lambdaL = traits.Float(1e-8, usedefault=True, desc=('angular regularisation constant'))
    shore_tau = traits.Float(0.025330295910584444, desc=(
        'Diffusion time. By default the value that makes q equal to the square root of the b-value.'))
    
    shore_constrain_e0 = traits.Bool(False, usedefault=True, desc=('Constrain the optimization such that E(0) = 1.'))
    shore_positive_constraint = traits.Bool(False, usedefault=True, desc=('Constrain the propagator to be positive.'))
    
    def _imaging_model_changed(self, new):
        if new == 'DSI':
            pass
        elif new == 'DTI':
            self.local_model_editor = {False: '1:Tensor', True: '2:Constrained Spherical Deconvolution'}
        elif new == 'multi-shell':
            self.local_model_editor = {True: 'Constrained Spherical Deconvolution'}
            self.local_model = True
    
    def _recon_mode_changed(self, new):
        if new == 'Probabilistic' and self.imaging_model != 'DSI':
            self.local_model_editor = {True: 'Constrained Spherical Deconvolution'}
            self.local_model = True
        elif new == 'Probabilistic' and self.imaging_model == 'DSI':
            pass
        else:
            self.local_model_editor = {False: '1:Tensor', True: '2:Constrained Spherical Deconvolution'}


class MRtrix_recon_config(HasTraits):
    # gradient_table = File
    flip_table_axis = List(['x', 'y', 'z'])
    local_model_editor = Dict({False: '1:Tensor', True: '2:Constrained Spherical Deconvolution'})
    local_model = Bool(True)
    lmax_order = Enum([2, 4, 6, 8, 10, 12, 14, 16])
    normalize_to_B0 = Bool(False)
    single_fib_thr = Float(0.7, min=0, max=1)
    recon_mode = Str
    
    def _imaging_model_changed(self, new):
        if new == 'DTI':
            self.local_model_editor = {False: '1:Tensor', True: '2:Constrained Spherical Deconvolution'}
        elif new == 'multi-shell':
            self.local_model_editor = {True: 'Constrained Spherical Deconvolution'}
            self.local_model = True
    
    def _recon_mode_changed(self, new):
        if new == 'Probabilistic':
            self.local_model_editor = {True: 'Constrained Spherical Deconvolution'}
            self.local_model = True
        else:
            self.local_model_editor = {False: '1:Tensor', True: '2:Constrained Spherical Deconvolution'}


def create_dipy_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    inputnode = pe.Node(interface=util.IdentityInterface(
        fields=["diffusion", "diffusion_resampled", "brain_mask_resampled", "wm_mask_resampled", "bvals", "bvecs"]),
                        name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(
        fields=["DWI", "FA", "AD", "MD", "RD", "fod", "model", "eigVec", "RF", "grad", "bvecs", "shore_maps",
                "mapmri_maps"], mandatory_inputs=True), name="outputnode")
    
    # Flip gradient table
    flip_bvecs = pe.Node(interface=flipBvec(), name='flip_bvecs')
    
    flip_bvecs.inputs.flipping_axis = config.flip_table_axis
    flip_bvecs.inputs.delimiter = ' '
    flip_bvecs.inputs.header_lines = 0
    flip_bvecs.inputs.orientation = 'h'
    flow.connect([
        (inputnode, flip_bvecs, [("bvecs", "bvecs")]),
        (flip_bvecs, outputnode, [("bvecs_flipped", "bvecs")])
    ])
    
    # Compute single fiber voxel mask
    dipy_erode = pe.Node(interface=Erode(out_filename="wm_mask_resampled.nii.gz"), name="dipy_erode")
    dipy_erode.inputs.number_of_passes = 1
    dipy_erode.inputs.filtertype = 'erode'
    
    flow.connect([
        (inputnode, dipy_erode, [("wm_mask_resampled", 'in_file')])
    ])
    
    if config.imaging_model != 'DSI':
        # Tensor -> EigenVectors / FA, AD, MD, RD maps
        dipy_tensor = pe.Node(interface=DTIEstimateResponseSH(), name='dipy_tensor')
        dipy_tensor.inputs.auto = True
        dipy_tensor.inputs.roi_radius = 10
        dipy_tensor.inputs.fa_thresh = config.single_fib_thr
        
        flow.connect([
            (inputnode, dipy_tensor, [('diffusion_resampled', 'in_file')]),
            (inputnode, dipy_tensor, [('bvals', 'in_bval')]),
            (flip_bvecs, dipy_tensor, [('bvecs_flipped', 'in_bvec')]),
            (dipy_erode, dipy_tensor, [('out_file', 'in_mask')])
        ])
        
        flow.connect([
            (dipy_tensor, outputnode, [("response", "RF")]),
            (dipy_tensor, outputnode, [("fa_file", "FA")]),
            (dipy_tensor, outputnode, [("ad_file", "AD")]),
            (dipy_tensor, outputnode, [("md_file", "MD")]),
            (dipy_tensor, outputnode, [("rd_file", "RD")])
        ])
        
        if not config.local_model:
            flow.connect([
                (inputnode, outputnode, [('diffusion_resampled', 'DWI')]),
                (dipy_tensor, outputnode, [("dti_model", "model")])
            ])
            # Tensor -> Eigenvectors
            # mrtrix_eigVectors = pe.Node(interface=Tensor2Vector(),name="mrtrix_eigenvectors")
        
        # Constrained Spherical Deconvolution
        else:
            # Perform spherical deconvolution
            dipy_CSD = pe.Node(interface=CSD(), name="dipy_CSD")
            
            # if config.tracking_processing_tool != 'Dipy':
            dipy_CSD.inputs.save_shm_coeff = True
            dipy_CSD.inputs.out_shm_coeff = 'diffusion_shm_coeff.nii.gz'
            
            # dipy_CSD.inputs.save_fods=True
            # dipy_CSD.inputs.out_fods='diffusion_fODFs.nii.gz'
            
            if config.lmax_order != 'Auto':
                dipy_CSD.inputs.sh_order = config.lmax_order
            
            dipy_CSD.inputs.fa_thresh = config.single_fib_thr
            
            flow.connect([
                (inputnode, dipy_CSD, [('diffusion_resampled', 'in_file')]),
                (inputnode, dipy_CSD, [('bvals', 'in_bval')]),
                (flip_bvecs, dipy_CSD, [('bvecs_flipped', 'in_bvec')]),
                # (dipy_tensor, dipy_CSD,[('out_mask','in_mask')]),
                # (dipy_erode, dipy_CSD,[('out_file','in_mask')]),
                (inputnode, dipy_CSD, [("brain_mask_resampled", 'in_mask')]),
                # (dipy_tensor, dipy_CSD,[('response','response')]),
                (dipy_CSD, outputnode, [('model', 'model')])
            ])
            
            if config.tracking_processing_tool != 'Dipy':
                flow.connect([
                    (dipy_CSD, outputnode, [('out_shm_coeff', 'DWI')])
                ])
            else:
                flow.connect([
                    (inputnode, outputnode, [('diffusion_resampled', 'DWI')])
                ])
    else:
        # Perform SHORE reconstruction (DSI)
        
        dipy_SHORE = pe.Node(interface=SHORE(), name="dipy_SHORE")
        
        if config.tracking_processing_tool == 'MRtrix':
            dipy_SHORE.inputs.tracking_processing_tool = 'mrtrix'
        elif config.tracking_processing_tool == 'Dipy':
            dipy_SHORE.inputs.tracking_processing_tool = 'dipy'
        
        # if config.tracking_processing_tool != 'Dipy':
        # dipy_SHORE.inputs.save_shm_coeff = True
        # dipy_SHORE.inputs.out_shm_coeff='diffusion_shm_coeff.nii.gz'
        
        dipy_SHORE.inputs.radial_order = int(config.shore_radial_order)
        dipy_SHORE.inputs.zeta = config.shore_zeta
        dipy_SHORE.inputs.lambdaN = config.shore_lambdaN
        dipy_SHORE.inputs.lambdaL = config.shore_lambdaL
        dipy_SHORE.inputs.tau = config.shore_tau
        dipy_SHORE.inputs.constrain_e0 = config.shore_constrain_e0
        dipy_SHORE.inputs.positive_constraint = config.shore_positive_constraint
        # dipy_SHORE.inputs.save_shm_coeff = True
        # dipy_SHORE.inputs.out_shm_coeff = 'diffusion_shore_shm_coeff.nii.gz'
        
        shore_maps_merge = pe.Node(interface=util.Merge(3), name="merge_shore_maps")
        
        flow.connect([
            (inputnode, dipy_SHORE, [('diffusion_resampled', 'in_file')]),
            (inputnode, dipy_SHORE, [('bvals', 'in_bval')]),
            (flip_bvecs, dipy_SHORE, [('bvecs_flipped', 'in_bvec')]),
            # (dipy_tensor, dipy_CSD,[('out_mask','in_mask')]),
            # (dipy_erode, dipy_SHORE,[('out_file','in_mask')]),
            # (inputnode,dipy_SHORE,[("wm_mask_resampled",'in_mask')]),
            (inputnode, dipy_SHORE, [("brain_mask_resampled", 'in_mask')]),
            # (dipy_tensor, dipy_CSD,[('response','response')]),
            (dipy_SHORE, outputnode, [('model', 'model')]),
            (dipy_SHORE, outputnode, [('fodf', 'fod')]),
            (dipy_SHORE, outputnode, [('GFA', 'FA')])
        ])
        
        flow.connect([
            (dipy_SHORE, shore_maps_merge, [('GFA', 'in1'),
                                            ('MSD', 'in2'),
                                            ('RTOP', 'in3')]),
            (shore_maps_merge, outputnode, [('out', 'shore_maps')])
        ])
        
        flow.connect([
            (inputnode, outputnode, [('diffusion_resampled', 'DWI')])
        ])
    
    if config.mapmri:
        from cmtklib.interfaces.dipy import MAPMRI
        dipy_MAPMRI = pe.Node(interface=MAPMRI(), name='dipy_mapmri')
        
        dipy_MAPMRI.inputs.laplacian_regularization = config.laplacian_regularization
        dipy_MAPMRI.inputs.laplacian_weighting = config.laplacian_weighting
        dipy_MAPMRI.inputs.positivity_constraint = config.positivity_constraint
        dipy_MAPMRI.inputs.radial_order = config.radial_order
        dipy_MAPMRI.inputs.small_delta = config.small_delta
        dipy_MAPMRI.inputs.big_delta = config.big_delta
        
        mapmri_maps_merge = pe.Node(interface=util.Merge(8), name="merge_mapmri_maps")
        
        flow.connect([
            (inputnode, dipy_MAPMRI, [('diffusion_resampled', 'in_file')]),
            (inputnode, dipy_MAPMRI, [('bvals', 'in_bval')]),
            (flip_bvecs, dipy_MAPMRI, [('bvecs_flipped', 'in_bvec')])
        ])
        
        flow.connect([
            (dipy_MAPMRI, mapmri_maps_merge, [('rtop_file', 'in1'),
                                              ('rtap_file', 'in2'),
                                              ('rtpp_file', 'in3'),
                                              ('msd_file', 'in4'),
                                              ('qiv_file', 'in5'),
                                              ('ng_file', 'in6'),
                                              ('ng_perp_file', 'in7'),
                                              ('ng_para_file', 'in8')]),
            (mapmri_maps_merge, outputnode, [('out', 'mapmri_maps')])
        ])
    
    return flow


def create_mrtrix_recon_flow(config):
    # TODO Add AD and RD maps
    flow = pe.Workflow(name="reconstruction")
    inputnode = pe.Node(
        interface=util.IdentityInterface(fields=["diffusion", "diffusion_resampled", "wm_mask_resampled", "grad"]),
        name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI", "FA", "ADC", "tensor", "eigVec", "RF", "grad"],
                                                          mandatory_inputs=True), name="outputnode")
    
    # Flip gradient table
    flip_table = pe.Node(interface=flipTable(), name='flip_table')
    
    flip_table.inputs.flipping_axis = config.flip_table_axis
    flip_table.inputs.delimiter = ' '
    flip_table.inputs.header_lines = 0
    flip_table.inputs.orientation = 'v'
    flow.connect([
        (inputnode, flip_table, [("grad", "table")]),
        (flip_table, outputnode, [("table", "grad")])
    ])
    # flow.connect([
    #             (inputnode,outputnode,[("grad","grad")])
    #             ])
    
    # Tensor
    mrtrix_tensor = pe.Node(interface=DWI2Tensor(), name='mrtrix_make_tensor')
    
    flow.connect([
        (inputnode, mrtrix_tensor, [('diffusion_resampled', 'in_file')]),
        (flip_table, mrtrix_tensor, [("table", "encoding_file")]),
    ])
    
    # Tensor -> FA map
    mrtrix_tensor_metrics = pe.Node(interface=TensorMetrics(out_fa='FA.mif', out_adc='ADC.mif'),
                                    name='mrtrix_tensor_metrics')
    convert_Tensor = pe.Node(interface=MRConvert(out_filename="dwi_tensor.nii.gz"), name='convert_tensor')
    convert_FA = pe.Node(interface=MRConvert(out_filename="FA.nii.gz"), name='convert_FA')
    convert_ADC = pe.Node(interface=MRConvert(out_filename="ADC.nii.gz"), name='convert_ADC')
    
    flow.connect([
        (mrtrix_tensor, convert_Tensor, [('tensor', 'in_file')]),
        (mrtrix_tensor, mrtrix_tensor_metrics, [('tensor', 'in_file')]),
        (mrtrix_tensor_metrics, convert_FA, [('out_fa', 'in_file')]),
        (mrtrix_tensor_metrics, convert_ADC, [('out_adc', 'in_file')]),
        (convert_Tensor, outputnode, [("converted", "tensor")]),
        (convert_FA, outputnode, [("converted", "FA")]),
        (convert_ADC, outputnode, [("converted", "ADC")])
    ])
    
    # Tensor -> Eigenvectors
    mrtrix_eigVectors = pe.Node(interface=Tensor2Vector(), name="mrtrix_eigenvectors")
    
    flow.connect([
        (mrtrix_tensor, mrtrix_eigVectors, [('tensor', 'in_file')]),
        (mrtrix_eigVectors, outputnode, [('vector', 'eigVec')])
    ])
    
    # Constrained Spherical Deconvolution
    if config.local_model:
        print("CSD true")
        # Compute single fiber voxel mask
        mrtrix_erode = pe.Node(interface=Erode(out_filename='wm_mask_res_eroded.nii.gz'), name="mrtrix_erode")
        mrtrix_erode.inputs.number_of_passes = 1
        mrtrix_erode.inputs.filtertype = 'erode'
        mrtrix_mul_eroded_FA = pe.Node(interface=MRtrix_mul(), name='mrtrix_mul_eroded_FA')
        mrtrix_mul_eroded_FA.inputs.out_filename = "diffusion_resampled_tensor_FA_masked.mif"
        mrtrix_thr_FA = pe.Node(interface=MRThreshold(out_file='FA_th.mif'), name='mrtrix_thr')
        mrtrix_thr_FA.inputs.abs_value = config.single_fib_thr
        
        flow.connect([
            (inputnode, mrtrix_erode, [("wm_mask_resampled", 'in_file')]),
            (mrtrix_erode, mrtrix_mul_eroded_FA, [('out_file', 'input2')]),
            (mrtrix_tensor_metrics, mrtrix_mul_eroded_FA, [('out_fa', 'input1')]),
            (mrtrix_mul_eroded_FA, mrtrix_thr_FA, [('out_file', 'in_file')])
        ])
        # Compute single fiber response function
        mrtrix_rf = pe.Node(interface=EstimateResponseForSH(), name="mrtrix_rf")
        # if config.lmax_order != 'Auto':
        mrtrix_rf.inputs.maximum_harmonic_order = int(config.lmax_order)
        
        mrtrix_rf.inputs.algorithm = 'tournier'
        # mrtrix_rf.inputs.normalise = config.normalize_to_B0
        flow.connect([
            (inputnode, mrtrix_rf, [("diffusion_resampled", "in_file")]),
            (mrtrix_thr_FA, mrtrix_rf, [("thresholded", "mask_image")]),
            (flip_table, mrtrix_rf, [("table", "encoding_file")]),
        ])
        
        # Perform spherical deconvolution
        mrtrix_CSD = pe.Node(interface=ConstrainedSphericalDeconvolution(), name="mrtrix_CSD")
        mrtrix_CSD.inputs.algorithm = 'csd'
        mrtrix_CSD.inputs.maximum_harmonic_order = int(config.lmax_order)
        # mrtrix_CSD.inputs.normalise = config.normalize_to_B0
        
        convert_CSD = pe.Node(interface=MRConvert(out_filename="spherical_harmonics_image.nii.gz"), name='convert_CSD')
        
        flow.connect([
            (inputnode, mrtrix_CSD, [('diffusion_resampled', 'in_file')]),
            (mrtrix_rf, mrtrix_CSD, [('response', 'response_file')]),
            (mrtrix_rf, outputnode, [('response', 'RF')]),
            (inputnode, mrtrix_CSD, [("wm_mask_resampled", 'mask_image')]),
            (flip_table, mrtrix_CSD, [("table", "encoding_file")]),
            (mrtrix_CSD, convert_CSD, [('spherical_harmonics_image', 'in_file')]),
            (convert_CSD, outputnode, [("converted", "DWI")])
            # (mrtrix_CSD,outputnode,[('spherical_harmonics_image','DWI')])
        ])
    else:
        flow.connect([
            (inputnode, outputnode, [('diffusion_resampled', 'DWI')])
        ])
    
    return flow
