# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
"""

from traits.api import *

from nipype.interfaces.base import traits, BaseInterface, BaseInterfaceInputSpec, CommandLineInputSpec, CommandLine, \
    InputMultiPath, OutputMultiPath, TraitedSpec, Interface, InterfaceResult, isdefined
import nipype.interfaces.utility as util

from cmp.stages.common import Stage

import os
import pickle
import gzip
import glob
import pkg_resources

import nipype.pipeline.engine as pe
import nipype.pipeline as pip
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.utility as util
import nipype.interfaces.mrtrix as mrt
import nipype.interfaces.ants as ants
import nipype.interfaces.dipy as dipy

import nibabel as nib

# from cmp.pipelines.common import MRThreshold, ExtractMRTrixGrad
from cmtklib.interfaces.mrtrix3 import DWIDenoise, DWIBiasCorrect, MRConvert, MRThreshold, ExtractFSLGrad, \
    ExtractMRTrixGrad, Generate5tt, GenerateGMWMInterface
import cmtklib.interfaces.fsl as cmp_fsl
from cmtklib.interfaces.misc import ExtractPVEsFrom5TT, UpdateGMWMInterfaceSeeding

from nipype.interfaces.mrtrix3.preprocess import ResponseSD


class PreprocessingConfig(HasTraits):
    total_readout = Float(0.0)
    description = Str('description')
    denoising = Bool(False)
    denoising_algo = Enum('MRtrix (MP-PCA)', ['MRtrix (MP-PCA)', 'Dipy (NLM)'])
    dipy_noise_model = Enum('Rician', ['Rician', 'Gaussian'])
    bias_field_correction = Bool(False)
    bias_field_algo = Enum('ANTS N4', ['ANTS N4', 'FSL FAST'])
    eddy_current_and_motion_correction = Bool(True)
    eddy_correction_algo = Enum('FSL eddy_correct', 'FSL eddy')
    eddy_correct_motion_correction = Bool(True)
    # start_vol = Int(0)
    # end_vol = Int()
    # max_vol = Int()
    # max_str = Str
    partial_volume_estimation = Bool(True)
    fast_use_priors = Bool(True)
    
    # DWI resampling selection
    resampling = Tuple(1, 1, 1)
    interpolation = Enum(['interpolate', 'weighted', 'nearest', 'sinc', 'cubic'])


class splitBvecBvalInputSpec(BaseInterfaceInputSpec):
    bvecs = File(exists=True)
    bvals = File(exists=True)
    start = Int(0)
    end = Int(300)
    delimiter = Str()
    orientation = Enum(['v', 'h'])


class splitBvecBvalOutputSpec(TraitedSpec):
    bvecs_split = File(exists=True)
    bvals_split = File(exists=True)


class splitBvecBval(BaseInterface):
    input_spec = splitBvecBvalInputSpec
    output_spec = splitBvecBvalOutputSpec
    
    def _run_interface(self, runtime):
        import numpy as np
        
        f_bvecs = open(self.inputs.bvecs, 'r')
        if self.inputs.delimiter == ' ':
            bvecs = np.loadtxt(f_bvecs)
        else:
            bvecs = np.loadtxt(f_bvecs, delimiter=self.inputs.delimiter)
        f_bvecs.close()
        
        f_bvals = open(self.inputs.bvals, 'r')
        if self.inputs.delimiter == ' ':
            bvals = np.loadtxt(f_bvals)
        else:
            bvals = np.loadtxt(f_bvals, delimiter=self.inputs.delimiter)
        f_bvals.close()
        
        if self.inputs.orientation == 'v':
            bvecs = bvecs[self.inputs.start:self.inputs.end + 1, :]
            bvals = bvals[self.inputs.start:self.inputs.end + 1]
        elif self.inputs.orientation == 'h':
            bvecs = bvecs[:, self.inputs.start:self.inputs.end + 1]
            bvals = bvals[self.inputs.start:self.inputs.end + 1]
        
        out_f = file(os.path.abspath('dwi_split.bvec'), 'a')
        np.savetxt(out_f, bvecs, delimiter=self.inputs.delimiter)
        out_f.close()
        
        out_f = file(os.path.abspath('dwi_split.bval'), 'a')
        np.savetxt(out_f, bvals.T, newline=self.inputs.delimiter)
        out_f.close()
        
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["bvecs_split"] = os.path.abspath('dwi_split.bvec')
        outputs["bvals_split"] = os.path.abspath('dwi_split.bval')
        return outputs


class PreprocessingStage(Stage):
    # General and UI members
    def __init__(self):
        self.name = 'preprocessing_stage'
        self.config = PreprocessingConfig()
        self.inputs = ["diffusion", "bvecs", "bvals", "T1", "aparc_aseg", "aseg", "brain", "brain_mask", "wm_mask_file",
                       "roi_volumes"]
        self.outputs = ["diffusion_preproc", "bvecs_rot", "bvals", "dwi_brain_mask", "T1", "act_5TT", "gmwmi", "brain",
                        "brain_mask", "brain_mask_full", "wm_mask_file", "partial_volume_files", "roi_volumes"]
    
    def create_workflow(self, flow, inputnode, outputnode):
        # print inputnode
        processing_input = pe.Node(interface=util.IdentityInterface(
            fields=['diffusion', 'aparc_aseg', 'aseg', 'bvecs', 'bvals', 'grad', 'acqp', 'index', 'T1', 'brain',
                    'brain_mask', 'wm_mask_file', 'roi_volumes']), name='processing_input')
        
        # For DSI acquisition: extract the hemisphere that contains the data
        # if self.config.start_vol > 0 or self.config.end_vol < self.config.max_vol:
        #
        #     split_vol = pe.Node(interface=splitDiffusion(),name='split_vol')
        #     split_vol.inputs.start = self.config.start_vol
        #     split_vol.inputs.end = self.config.end_vol
        #
        #     split_bvecbval = pe.Node(interface=splitBvecBval(),name='split_bvecsbvals')
        #     split_bvecbval.inputs.start = self.config.start_vol
        #     split_bvecbval.inputs.end = self.config.end_vol
        #     split_bvecbval.inputs.orientation = 'h'
        #     split_bvecbval.inputs.delimiter = ' '
        #
        #     flow.connect([
        #                 (inputnode,split_vol,[('diffusion','in_file')]),
        #                 (split_vol,processing_input,[('data','diffusion')]),
        #                 (inputnode,split_bvecbval,[('bvecs','bvecs'),('bvals','bvals')]),
        #                 (split_bvecbval,processing_input,[('bvecs_split','bvecs'),('bvals_split','bvals')])
        #                 ])
        #
        # else:
        
        flow.connect([
            (inputnode, processing_input, [('diffusion', 'diffusion'), ('bvecs', 'bvecs'), ('bvals', 'bvals')]),
        ])
        
        flow.connect([
            (inputnode, processing_input,
             [('T1', 'T1'), ('aparc_aseg', 'aparc_aseg'), ('aseg', 'aseg'), ('brain', 'brain'),
              ('brain_mask', 'brain_mask'), ('wm_mask_file', 'wm_mask_file'), ('roi_volumes', 'roi_volumes')]),
            (processing_input, outputnode, [('bvals', 'bvals')])
        ])
        
        # Conversion to MRTrix image format ".mif", grad_fsl=(inputnode.inputs.bvecs,inputnode.inputs.bvals)
        mr_convert = pe.Node(interface=MRConvert(stride=[1, 2, +3, +4]), name='mr_convert')
        mr_convert.inputs.quiet = True
        mr_convert.inputs.force_writing = True
        
        concatnode = pe.Node(interface=util.Merge(2), name='concatnode')
        
        def convertList2Tuple(lists):
            # print "******************************************",tuple(lists)
            return tuple(lists)
        
        flow.connect([
            # (processing_input,concatnode,[('bvecs','in1'),('bvals','in2')]),
            (processing_input, concatnode, [('bvecs', 'in1')]),
            (processing_input, concatnode, [('bvals', 'in2')]),
            (concatnode, mr_convert, [(('out', convertList2Tuple), 'grad_fsl')])
        ])
        
        # Convert Freesurfer data
        mr_convert_brainmask = pe.Node(
            interface=MRConvert(out_filename='brainmaskfull.nii.gz', stride=[1, 2, 3], output_datatype='float32'),
            name='mr_convert_brain_mask')
        mr_convert_brain = pe.Node(
            interface=MRConvert(out_filename='anat_masked.nii.gz', stride=[1, 2, 3], output_datatype='float32'),
            name='mr_convert_brain')
        mr_convert_T1 = pe.Node(
            interface=MRConvert(out_filename='anat.nii.gz', stride=[1, 2, 3], output_datatype='float32'),
            name='mr_convert_T1')
        mr_convert_roi_volumes = pe.Node(
            interface=ApplymultipleMRConvert(stride=[1, 2, 3], output_datatype='float32', extension='nii'),
            name='mr_convert_roi_volumes')
        mr_convert_wm_mask_file = pe.Node(
            interface=MRConvert(out_filename='wm_mask_file.nii.gz', stride=[1, 2, 3], output_datatype='float32'),
            name='mr_convert_wm_mask_file')
        
        flow.connect([
            (processing_input, mr_convert_brainmask, [('brain_mask', 'in_file')]),
            (processing_input, mr_convert_brain, [('brain', 'in_file')]),
            (processing_input, mr_convert_T1, [('T1', 'in_file')]),
            (processing_input, mr_convert_roi_volumes, [('roi_volumes', 'in_files')]),
            (processing_input, mr_convert_wm_mask_file, [('wm_mask_file', 'in_file')])
        ])
        
        # if self.config.partial_volume_estimation:
        #     pve_extractor_from_5tt = pe.Node(interface=ExtractPVEsFrom5TT(),name='pve_extractor_from_5tt')
        #     pve_extractor.inputs.pve_csf_file = 'pve_0.nii.gz'
        #     pve_extractor.inputs.pve_csf_file = 'pve_1.nii.gz'
        #     pve_extractor.inputs.pve_csf_file = 'pve_2.nii.gz'
        #
        #     flow.connect([
        #                 (mrtrix_5tt,pve_extractor_from_5tt,[('out_file','in_5tt')]),
        #                 (processing_input,pve_extractor_from_5tt,[('T1','ref_image')]),
        #                 ])
        
        # from nipype.interfaces import fsl
        # # Run FAST for partial volume estimation (WM;GM;CSF)
        # fastr = pe.Node(interface=fsl.FAST(),name='fastr')
        # fastr.inputs.out_basename = 'fast_'
        # fastr.inputs.number_classes = 3
        #
        # if self.config.fast_use_priors:
        #     fsl_flirt = pe.Node(interface=fsl.FLIRT(out_file='Template2Input.nii.gz',out_matrix_file='template2input.mat'),name="linear_registration")
        #     #fsl_flirt.inputs.in_file = os.environ['FSLDIR']+'/data/standard/MNI152_T1_1mm.nii.gz'
        #     template_path = os.path.join('data', 'segmentation', 'ants_template_IXI')
        #     fsl_flirt.inputs.in_file = pkg_resources.resource_filename('cmtklib', os.path.join(template_path, 'T_template2.nii.gz'))
        #     #fsl_flirt.inputs.dof = self.config.dof
        #     #fsl_flirt.inputs.cost = self.config.fsl_cost
        #     #fsl_flirt.inputs.no_search = self.config.no_search
        #     fsl_flirt.inputs.verbose = True
        #
        #     flow.connect([
        #                 (mr_convert_T1, fsl_flirt, [('converted','reference')]),
        #                 ])
        #
        #     fastr.inputs.use_priors = True
        #     fastr.inputs.other_priors = [pkg_resources.resource_filename('cmtklib', os.path.join(template_path,'3Class-Priors','priors1.nii.gz')),
        #                                  pkg_resources.resource_filename('cmtklib', os.path.join(template_path,'3Class-Priors','priors2.nii.gz')),
        #                                  pkg_resources.resource_filename('cmtklib', os.path.join(template_path,'3Class-Priors','priors3.nii.gz'))
        #                                 ]
        #     flow.connect([
        #                 (fsl_flirt, fastr, [('out_matrix_file','init_transform')]),
        #                 ])
        #
        # flow.connect([
        #             (mr_convert_brain,fastr,[('converted','in_files')]),
        #             # (fastr,outputnode,[('partial_volume_files','partial_volume_files')])
        #             ])
        
        # Threshold converted Freesurfer brainmask into a binary mask
        mr_threshold_brainmask = pe.Node(interface=MRThreshold(abs_value=1, out_file='brain_mask.nii.gz'),
                                         name='mr_threshold_brainmask')
        
        flow.connect([
            (mr_convert_brainmask, mr_threshold_brainmask, [('converted', 'in_file')])
        ])
        
        # Extract b0 and create DWI mask
        flirt_dwimask_pre = pe.Node(interface=fsl.FLIRT(out_file='brain2b0.nii.gz', out_matrix_file='brain2b0aff'),
                                    name='flirt_dwimask_pre')
        costs = ['mutualinfo', 'corratio', 'normcorr', 'normmi', 'leastsq', 'labeldiff', 'bbr']
        flirt_dwimask_pre.inputs.cost = costs[3]
        flirt_dwimask_pre.inputs.cost_func = costs[3]
        flirt_dwimask_pre.inputs.dof = 6
        flirt_dwimask_pre.inputs.no_search = False
        
        flirt_dwimask = pe.Node(
            interface=fsl.FLIRT(out_file='dwi_brain_mask.nii.gz', apply_xfm=True, interp='nearestneighbour'),
            name='flirt_dwimask')
        
        mr_convert_b0 = pe.Node(interface=MRConvert(out_filename='b0.nii.gz', stride=[+1, +2, +3]),
                                name='mr_convert_b0')
        mr_convert_b0.inputs.extract_at_axis = 3
        mr_convert_b0.inputs.extract_at_coordinate = [0]
        
        flow.connect([
            (processing_input, mr_convert_b0, [('diffusion', 'in_file')])
        ])
        
        flow.connect([
            (mr_convert_T1, flirt_dwimask_pre, [('converted', 'in_file')]),
            (mr_convert_b0, flirt_dwimask_pre, [('converted', 'reference')]),
            (mr_convert_b0, flirt_dwimask, [('converted', 'reference')]),
            (flirt_dwimask_pre, flirt_dwimask, [('out_matrix_file', 'in_matrix_file')]),
            (mr_threshold_brainmask, flirt_dwimask, [('thresholded', 'in_file')])
        ])
        
        # Diffusion data denoising
        if self.config.denoising:
            if self.config.denoising_algo == "MRtrix (MP-PCA)":
                mr_convert.inputs.out_filename = 'diffusion.mif'
                dwi_denoise = pe.Node(
                    interface=DWIDenoise(out_file='diffusion_denoised.mif', out_noisemap='diffusion_noisemap.mif'),
                    name='dwi_denoise')
                dwi_denoise.inputs.force_writing = True
                dwi_denoise.inputs.debug = True
                dwi_denoise.ignore_exception = True
                
                flow.connect([
                    # (processing_input,mr_convert,[('diffusion','in_file')]),
                    (processing_input, mr_convert, [('diffusion', 'in_file')]),
                    (mr_convert, dwi_denoise, [('converted', 'in_file')]),
                    (flirt_dwimask, dwi_denoise, [('out_file', 'mask')]),
                ])
            
            elif self.config.denoising_algo == "Dipy (NLM)":
                mr_convert.inputs.out_filename = 'diffusion_denoised.mif'
                dwi_denoise = pe.Node(interface=dipy.Denoise(), name='dwi_denoise')
                if self.config.dipy_noise_model == "Gaussian":
                    dwi_denoise.inputs.noise_model = "gaussian"
                elif self.config.dipy_noise_model == "Rician":
                    dwi_denoise.inputs.noise_model = "rician"
                
                flow.connect([
                    (processing_input, dwi_denoise, [('diffusion', 'in_file')]),
                    (flirt_dwimask, dwi_denoise, [('out_file', 'in_mask')]),
                    (dwi_denoise, mr_convert, [('out_file', 'in_file')])
                ])
        else:
            mr_convert.inputs.out_filename = 'diffusion.mif'
            flow.connect([
                (processing_input, mr_convert, [('diffusion', 'in_file')])
            ])
        
        mr_convert_b = pe.Node(interface=MRConvert(out_filename='diffusion_corrected.nii.gz', stride=[+1, +2, +3, +4]),
                               name='mr_convert_b')
        
        if self.config.bias_field_correction:
            if self.config.bias_field_algo == "ANTS N4":
                dwi_biascorrect = pe.Node(
                    interface=DWIBiasCorrect(use_ants=True, out_bias='diffusion_denoised_biasfield.mif'),
                    name='dwi_biascorrect')
            elif self.config.bias_field_algo == "FSL FAST":
                dwi_biascorrect = pe.Node(
                    interface=DWIBiasCorrect(use_fsl=True, out_bias='diffusion_denoised_biasfield.mif'),
                    name='dwi_biascorrect')
            
            dwi_biascorrect.inputs.debug = True
            
            if self.config.denoising:
                if self.config.denoising_algo == "MRtrix (MP-PCA)":
                    flow.connect([
                        (dwi_denoise, dwi_biascorrect, [('out_file', 'in_file')]),
                        (flirt_dwimask, dwi_biascorrect, [('out_file', 'mask')]),
                        (dwi_biascorrect, mr_convert_b, [('out_file', 'in_file')])
                    ])
                elif self.config.denoising_algo == "Dipy (NLM)":
                    flow.connect([
                        (mr_convert, dwi_biascorrect, [('converted', 'in_file')]),
                        (flirt_dwimask, dwi_biascorrect, [('out_file', 'mask')]),
                        (dwi_biascorrect, mr_convert_b, [('out_file', 'in_file')])
                    ])
            else:
                flow.connect([
                    (mr_convert, dwi_biascorrect, [('converted', 'in_file')]),
                    (flirt_dwimask, dwi_biascorrect, [('out_file', 'mask')])
                ])
        else:
            if self.config.denoising:
                if self.config.denoising_algo == "MRtrix (MP-PCA)":
                    flow.connect([
                        (dwi_denoise, mr_convert_b, [('out_file', 'in_file')])
                    ])
                elif self.config.denoising_algo == "Dipy (NLM)":
                    flow.connect([
                        (mr_convert, mr_convert_b, [('converted', 'in_file')])
                    ])
            else:
                flow.connect([
                    (mr_convert, mr_convert_b, [('converted', 'in_file')])
                ])
        
        extract_grad_mrtrix = pe.Node(interface=ExtractMRTrixGrad(out_grad_mrtrix='grad.txt'),
                                      name='extract_grad_mrtrix')
        flow.connect([
            (mr_convert, extract_grad_mrtrix, [("converted", "in_file")])
        ])
        # extract_grad_fsl = pe.Node(interface=mrt.MRTrixInfo(out_grad_mrtrix=('diffusion_denoised.bvec','diffusion_denoised.bval')),name='extract_grad_fsl')
        
        # TODO extract the total readout directly from the BIDS json file
        acqpnode = pe.Node(interface=CreateAcqpFile(total_readout=self.config.total_readout), name='acqpnode')
        
        indexnode = pe.Node(interface=CreateIndexFile(), name='indexnode')
        flow.connect([
            (extract_grad_mrtrix, indexnode, [("out_grad_mrtrix", "in_grad_mrtrix")])
        ])
        
        fs_mriconvert = pe.Node(
            interface=fs.MRIConvert(out_type='niigz', out_file='diffusion_preproc_resampled.nii.gz'),
            name="diffusion_resample")
        fs_mriconvert.inputs.vox_size = self.config.resampling
        fs_mriconvert.inputs.resample_type = self.config.interpolation
        
        mr_convert_b0_resample = pe.Node(interface=MRConvert(out_filename='b0_resampled.nii.gz', stride=[+1, +2, +3]),
                                         name='mr_convert_b0_resample')
        mr_convert_b0_resample.inputs.extract_at_axis = 3
        mr_convert_b0_resample.inputs.extract_at_coordinate = [0]
        
        # fs_mriconvert_b0 = pe.Node(interface=fs.MRIConvert(out_type='niigz',out_file='b0_resampled.nii.gz'),name="b0_resample")
        # fs_mriconvert_b0.inputs.vox_size = self.config.resampling
        # fs_mriconvert_b0.inputs.resample_type = self.config.interpolation
        
        flow.connect([
            (fs_mriconvert, mr_convert_b0_resample, [('out_file', 'in_file')]),
        ])
        
        # resampling Freesurfer data and setting output type to short
        fs_mriconvert_T1 = pe.Node(interface=fs.MRIConvert(out_type='niigz', out_file='anat_resampled.nii.gz'),
                                   name="anat_resample")
        fs_mriconvert_T1.inputs.vox_size = self.config.resampling
        fs_mriconvert_T1.inputs.resample_type = self.config.interpolation
        
        flow.connect([
            (mr_convert_T1, fs_mriconvert_T1, [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_T1,[('converted','reslice_like')]),
            (fs_mriconvert_T1, outputnode, [('out_file', 'T1')])
        ])
        
        fs_mriconvert_brain = pe.Node(
            interface=fs.MRIConvert(out_type='niigz', out_file='anat_masked_resampled.nii.gz'),
            name="anat_masked_resample")
        fs_mriconvert_brain.inputs.vox_size = self.config.resampling
        fs_mriconvert_brain.inputs.resample_type = self.config.interpolation
        
        flow.connect([
            (mr_convert_brain, fs_mriconvert_brain, [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_brain,[('converted','reslice_like')]),
            (fs_mriconvert_brain, outputnode, [('out_file', 'brain')])
        ])
        
        fs_mriconvert_brainmask = pe.Node(
            interface=fs.MRIConvert(out_type='niigz', resample_type='nearest', out_file='brain_mask_resampled.nii.gz'),
            name="brain_mask_resample")
        fs_mriconvert_brainmask.inputs.vox_size = self.config.resampling
        flow.connect([
            (mr_threshold_brainmask, fs_mriconvert_brainmask, [('thresholded', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_brainmask,[('converted','reslice_like')]),
            (fs_mriconvert_brainmask, outputnode, [('out_file', 'brain_mask')])
        ])
        
        fs_mriconvert_brainmaskfull = pe.Node(
            interface=fs.MRIConvert(out_type='niigz', out_file='brain_mask_full_resampled.nii.gz'),
            name="brain_mask_full_resample")
        fs_mriconvert_brainmaskfull.inputs.vox_size = self.config.resampling
        fs_mriconvert_brainmaskfull.inputs.resample_type = self.config.interpolation
        flow.connect([
            (mr_convert_brainmask, fs_mriconvert_brainmaskfull, [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_brainmaskfull,[('converted','reslice_like')]),
            (fs_mriconvert_brainmaskfull, outputnode, [('out_file', 'brain_mask_full')])
        ])
        
        fs_mriconvert_wm_mask = pe.Node(
            interface=fs.MRIConvert(out_type='niigz', resample_type='nearest', out_file='wm_mask_resampled.nii.gz'),
            name="wm_mask_resample")
        fs_mriconvert_wm_mask.inputs.vox_size = self.config.resampling
        flow.connect([
            (mr_convert_wm_mask_file, fs_mriconvert_wm_mask, [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_wm_mask,[('converted','reslice_like')]),
            (fs_mriconvert_wm_mask, outputnode, [('out_file', 'wm_mask_file')])
        ])
        
        fs_mriconvert_ROIs = pe.MapNode(interface=fs.MRIConvert(out_type='niigz', resample_type='nearest'),
                                        iterfield=['in_file'], name="ROIs_resample")
        fs_mriconvert_ROIs.inputs.vox_size = self.config.resampling
        flow.connect([
            (mr_convert_roi_volumes, fs_mriconvert_ROIs, [('converted_files', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_ROIs,[('converted','reslice_like')]),
            (fs_mriconvert_ROIs, outputnode, [("out_file", "roi_volumes")])
        ])
        
        # fs_mriconvert_PVEs = pe.MapNode(interface=fs.MRIConvert(out_type='niigz'),name="PVEs_resample",iterfield=['in_file'])
        # fs_mriconvert_PVEs.inputs.vox_size = self.config.resampling
        # fs_mriconvert_PVEs.inputs.resample_type = self.config.interpolation
        # flow.connect([
        #             (fastr,fs_mriconvert_PVEs,[('partial_volume_files','in_file')]),
        #             #(mr_convert_b0_resample,fs_mriconvert_ROIs,[('converted','reslice_like')]),
        #             (fs_mriconvert_PVEs,outputnode,[("out_file","partial_volume_files")])
        #             ])
        
        fs_mriconvert_dwimask = pe.Node(interface=fs.MRIConvert(out_type='niigz', resample_type='nearest',
                                                                out_file='dwi_brain_mask_resampled.nii.gz'),
                                        name="dwi_brainmask_resample")
        # fs_mriconvert_dwimask.inputs.vox_size = self.config.resampling
        flow.connect([
            (flirt_dwimask, fs_mriconvert_dwimask, [('out_file', 'in_file')]),
            (mr_convert_b0_resample, fs_mriconvert_dwimask, [('converted', 'reslice_like')]),
            (fs_mriconvert_dwimask, outputnode, [('out_file', 'dwi_brain_mask')])
        ])
        
        # TODO Implementation of FSL Topup
        
        if self.config.eddy_current_and_motion_correction:
            
            if self.config.eddy_correction_algo == 'FSL eddy_correct':
                
                eddy_correct = pe.Node(interface=fsl.EddyCorrect(ref_num=0, out_file='eddy_corrected.nii.gz'),
                                       name='eddy_correct')
                
                flow.connect([
                    (processing_input, outputnode, [("bvecs", "bvecs_rot")])
                ])
                
                if self.config.eddy_correct_motion_correction:
                    
                    mc_flirt = pe.Node(
                        interface=fsl.MCFLIRT(out_file='motion_corrected.nii.gz', ref_vol=0, save_mats=True),
                        name='motion_correction')
                    flow.connect([
                        (mr_convert_b, mc_flirt, [("converted", "in_file")])
                    ])
                    
                    # FIXME rotate b vectors after motion correction (mcflirt)
                    
                    flow.connect([
                        (mc_flirt, eddy_correct, [("out_file", "in_file")])
                    ])
                else:
                    
                    flow.connect([
                        (mr_convert_b, eddy_correct, [("converted", "in_file")])
                    ])
                
                # # DTK needs fixed number of directions (512)
                # if self.config.start_vol > 0 and self.config.end_vol == self.config.max_vol:
                #     merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                #     flow.connect([
                #                 (split_vol,merge_filenames,[("padding1","in1")]),
                #                 (eddy_correct,merge_filenames,[("eddy_corrected","in2")]),
                #                 ])
                #     merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                #     flow.connect([
                #                 (merge_filenames,merge,[("out","in_files")]),
                #                 ])
                #     flow.connect([
                #                 (merge,fs_mriconvert,[('merged_file','in_file')]),
                #                 (fs_mriconvert,outputnode,[("out_file","diffusion_preproc")])
                #                 ])
                # elif self.config.start_vol > 0 and self.config.end_vol < self.config.max_vol:
                #     merge_filenames = pe.Node(interface=util.Merge(3),name='merge_files')
                #     flow.connect([
                #                 (split_vol,merge_filenames,[("padding1","in1")]),
                #                 (eddy_correct,merge_filenames,[("eddy_corrected","in2")]),
                #                 (split_vol,merge_filenames,[("padding2","in3")]),
                #                 ])
                #     merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                #     flow.connect([
                #                 (merge_filenames,merge,[("out","in_files")])
                #                 ])
                #     flow.connect([
                #                 (merge,fs_mriconvert,[('merged_file','in_file')]),
                #                 (fs_mriconvert,outputnode,[("out_file","diffusion_preproc")])
                #                 ])
                # elif self.config.start_vol == 0 and self.config.end_vol < self.config.max_vol:
                #     merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                #     flow.connect([
                #                 (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                #                 (split_vol,merge_filenames,[("padding2","in2")]),
                #                 ])
                #     merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                #     flow.connect([
                #                 (merge_filenames,merge,[("out","in_files")])
                #                 ])
                #     flow.connect([
                #                 (merge,fs_mriconvert,[('merged_file','in_file')]),
                #                 (fs_mriconvert,outputnode,[("out_file","diffusion_preproc")])
                #                 ])
                # else:
                flow.connect([
                    (eddy_correct, fs_mriconvert, [('eddy_corrected', 'in_file')]),
                    (fs_mriconvert, outputnode, [("out_file", "diffusion_preproc")])
                ])
            
            else:
                eddy_correct = pe.Node(interface=cmp_fsl.EddyOpenMP(out_file="eddy_corrected.nii.gz", verbose=True),
                                       name='eddy')
                flow.connect([
                    (mr_convert_b, eddy_correct, [("converted", "in_file")]),
                    (processing_input, eddy_correct, [("bvecs", "bvecs")]),
                    (processing_input, eddy_correct, [("bvals", "bvals")]),
                    (flirt_dwimask, eddy_correct, [("out_file", "mask")]),
                    (indexnode, eddy_correct, [("index", "index")]),
                    (acqpnode, eddy_correct, [("acqp", "acqp")])
                ])
                
                flow.connect([
                    (eddy_correct, outputnode, [("bvecs_rotated", "bvecs_rot")])
                ])
                
                # # DTK needs fixed number of directions (512)
                # if self.config.start_vol > 0 and self.config.end_vol == self.config.max_vol:
                #     merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                #     flow.connect([
                #                 (split_vol,merge_filenames,[("padding1","in1")]),
                #                 (eddy_correct,merge_filenames,[("eddy_corrected","in1")])
                #                 ])
                #     merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                #     flow.connect([
                #                 (merge_filenames,merge,[("out","in_files")]),
                #                 ])
                #     # resampling diffusion image and setting output type to short
                #     flow.connect([
                #                 (merge,fs_mriconvert,[('merged_file','in_file')]),
                #                 (fs_mriconvert,outputnode,[("out_file","diffusion_preproc")])
                #                 ])
                #
                # elif self.config.start_vol > 0 and self.config.end_vol < self.config.max_vol:
                #     merge_filenames = pe.Node(interface=util.Merge(3),name='merge_files')
                #     flow.connect([
                #                 (split_vol,merge_filenames,[("padding1","in1")]),
                #                 (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                #                 (split_vol,merge_filenames,[("padding2","in3")])
                #                 ])
                #     merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                #     flow.connect([
                #                 (merge_filenames,merge,[("out","in_files")]),
                #                 ])
                #     # resampling diffusion image and setting output type to short
                #     flow.connect([
                #                 (merge,fs_mriconvert,[('merged_file','in_file')]),
                #                 (fs_mriconvert,outputnode,[("out_file","diffusion_preproc")])
                #                 ])
                # elif self.config.start_vol == 0 and self.config.end_vol < self.config.max_vol:
                #     merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                #     flow.connect([
                #                 (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                #                 (split_vol,merge_filenames,[("padding2","in2")])
                #                 ])
                #     merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                #     flow.connect([
                #                 (merge_filenames,merge,[("out","in_files")]),
                #                 ])
                #     # resampling diffusion image and setting output type to short
                #     flow.connect([
                #                 (merge,fs_mriconvert,[('merged_file','in_file')]),
                #                 (fs_mriconvert,outputnode,[("out_file","diffusion_preproc")])
                #                 ])
                # else:
                # resampling diffusion image and setting output type to short
                flow.connect([
                    (eddy_correct, fs_mriconvert, [('eddy_corrected', 'in_file')]),
                    (fs_mriconvert, outputnode, [("out_file", "diffusion_preproc")])
                ])
        else:
            # resampling diffusion image and setting output type to short
            flow.connect([
                (mr_convert_b, fs_mriconvert, [("converted", "in_file")]),
                (fs_mriconvert, outputnode, [("out_file", "diffusion_preproc")]),
                (inputnode, outputnode, [("bvecs", "bvecs_rot")])
            ])
        
        # #mr_convertB.inputs.grad_fsl = ('bvecs', 'bvals')
        # flow.connect([
        #             (mr_convertF,mr_convertB,[("converted","in_file")])
        #             ])
        
        # else:
        #     if self.config.start_vol > 0 and self.config.end_vol == self.config.max_vol:
        #         merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
        #         flow.connect([
        #                     (split_vol,merge_filenames,[("padding1","in1")]),
        #                     (mc_flirt,merge_filenames,[("out_file","in2")]),
        #                     ])
        #         merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
        #         flow.connect([
        #                     (merge_filenames,merge,[("out","in_files")]),
        #                     (merge,outputnode,[("merged_file","diffusion_preproc")])
        #                     ])
        #     elif self.config.start_vol > 0 and self.config.end_vol < self.config.max_vol:
        #         merge_filenames = pe.Node(interface=util.Merge(3),name='merge_files')
        #         flow.connect([
        #                     (split_vol,merge_filenames,[("padding1","in1")]),
        #                     (mc_flirt,merge_filenames,[("out_file","in2")]),
        #                     (split_vol,merge_filenames,[("padding2","in3")]),
        #                     ])
        #         merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
        #         flow.connect([
        #                     (merge_filenames,merge,[("out","in_files")]),
        #                     (merge,outputnode,[("merged_file","diffusion_preproc")])
        #                     ])
        #     elif self.config.start_vol == 0 and self.config.end_vol < self.config.max_vol:
        #         merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
        #         flow.connect([
        #                     (mc_flirt,merge_filenames,[("out_file","in1")]),
        #                     (split_vol,merge_filenames,[("padding2","in2")]),
        #                     ])
        #         merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
        #         flow.connect([
        #                     (merge_filenames,merge,[("out","in_files")]),
        #                     (merge,outputnode,[("merged_file","diffusion_preproc")])
        #                     ])
        #     else:
        #         flow.connect([
        #                     (mc_flirt,outputnode,[("out_file","diffusion_preproc")])
        #                     ])
        
        fs_mriconvert_5tt = pe.Node(interface=fs.MRIConvert(out_type='niigz', out_file='act_5tt_resampled.nii.gz'),
                                    name="5tt_resample")
        fs_mriconvert_5tt.inputs.vox_size = self.config.resampling
        fs_mriconvert_5tt.inputs.resample_type = self.config.interpolation
        
        mrtrix_5tt = pe.Node(interface=Generate5tt(out_file='mrtrix_5tt.nii.gz'), name='mrtrix_5tt')
        mrtrix_5tt.inputs.algorithm = 'freesurfer'
        # mrtrix_5tt.inputs.algorithm = 'hsvs'
        
        flow.connect([
            (processing_input, mrtrix_5tt, [('aparc_aseg', 'in_file')]),
            (mrtrix_5tt, fs_mriconvert_5tt, [('out_file', 'in_file')]),
            (fs_mriconvert_5tt, outputnode, [('out_file', 'act_5TT')]),
        ])
        
        # if self.config.partial_volume_estimation:
        pve_extractor_from_5tt = pe.Node(interface=ExtractPVEsFrom5TT(), name='pve_extractor_from_5tt')
        pve_extractor_from_5tt.inputs.pve_csf_file = 'pve_0.nii.gz'
        pve_extractor_from_5tt.inputs.pve_gm_file = 'pve_1.nii.gz'
        pve_extractor_from_5tt.inputs.pve_wm_file = 'pve_2.nii.gz'
        
        flow.connect([
            (mrtrix_5tt, pve_extractor_from_5tt, [('out_file', 'in_5tt')]),
            (processing_input, pve_extractor_from_5tt, [('T1', 'ref_image')]),
        ])
        
        fs_mriconvert_PVEs = pe.MapNode(interface=fs.MRIConvert(out_type='niigz'), iterfield=['in_file'],
                                        name="PVEs_resample")
        fs_mriconvert_PVEs.inputs.vox_size = self.config.resampling
        fs_mriconvert_PVEs.inputs.resample_type = self.config.interpolation
        flow.connect([
            (pve_extractor_from_5tt, fs_mriconvert_PVEs, [('partial_volume_files', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_ROIs,[('converted','reslice_like')]),
            (fs_mriconvert_PVEs, outputnode, [("out_file", "partial_volume_files")])
        ])
        
        fs_mriconvert_gmwmi = pe.Node(interface=fs.MRIConvert(out_type='niigz', out_file='gmwmi_resampled.nii.gz'),
                                      name="gmwmi_resample")
        fs_mriconvert_gmwmi.inputs.vox_size = self.config.resampling
        fs_mriconvert_gmwmi.inputs.resample_type = self.config.interpolation
        
        mrtrix_gmwmi = pe.Node(interface=GenerateGMWMInterface(out_file='gmwmi.nii.gz'), name='mrtrix_gmwmi')
        
        update_gmwmi = pe.Node(interface=UpdateGMWMInterfaceSeeding(), name='update_gmwmi')
        update_gmwmi.inputs.out_gmwmi_file = 'gmwmi_proc.nii.gz'
        
        flow.connect([
            (mrtrix_5tt, mrtrix_gmwmi, [('out_file', 'in_file')]),
            (mrtrix_gmwmi, update_gmwmi, [('out_file', 'in_gmwmi_file')]),
            (processing_input, update_gmwmi, [('roi_volumes', 'in_roi_volumes')]),
            (update_gmwmi, fs_mriconvert_gmwmi, [('out_gmwmi_file', 'in_file')]),
            (fs_mriconvert_gmwmi, outputnode, [('out_file', 'gmwmi')]),
        ])
    
    def define_inspect_outputs(self):
        # print "stage_dir : %s" % self.stage_dir
        if self.config.denoising:
            denoising_results_path = os.path.join(self.stage_dir, "dwi_denoise", "result_dwi_denoise.pklz")
            if (os.path.exists(denoising_results_path)):
                dwi_denoise_results = pickle.load(gzip.open(denoising_results_path))
                # print dwi_denoise_results.outputs.out_file
                self.inspect_outputs_dict['DWI denoised image'] = ['mrview', dwi_denoise_results.outputs.out_file]
                if self.config.denoising_algo == "MRtrix (MP-PCA)":
                    # print dwi_denoise_results.outputs.out_noisemap
                    self.inspect_outputs_dict['Noise map'] = ['mrview', dwi_denoise_results.outputs.out_noisemap]
        
        if self.config.bias_field_correction:
            bias_field_correction_results_path = os.path.join(self.stage_dir, "dwi_biascorrect",
                                                              "result_dwi_biascorrect.pklz")
            if (os.path.exists(bias_field_correction_results_path)):
                dwi_biascorrect_results = pickle.load(gzip.open(bias_field_correction_results_path))
                # print dwi_biascorrect_results.outputs.out_file
                # print dwi_biascorrect_results.outputs.out_bias
                self.inspect_outputs_dict['Bias field corrected image'] = ['mrview',
                                                                           dwi_biascorrect_results.outputs.out_file]
                self.inspect_outputs_dict['Bias field'] = ['mrview', dwi_biascorrect_results.outputs.out_bias]
        
        if self.config.eddy_current_and_motion_correction:
            if self.config.eddy_correction_algo == 'FSL eddy_correct':
                eddy_results_path = os.path.join(self.stage_dir, "eddy_correct", "result_eddy_correct.pklz")
                if (os.path.exists(eddy_results_path)):
                    eddy_results = pickle.load(gzip.open(eddy_results_path))
                    self.inspect_outputs_dict['Eddy current corrected image'] = ['mrview',
                                                                                 eddy_results.outputs.eddy_corrected]
            else:
                eddy_results_path = os.path.join(self.stage_dir, "eddy", "result_eddy.pklz")
                if (os.path.exists(eddy_results_path)):
                    eddy_results = pickle.load(gzip.open(eddy_results_path))
                    self.inspect_outputs_dict['Eddy current corrected image'] = ['mrview',
                                                                                 eddy_results.outputs.eddy_corrected]
        
        self.inspect_outputs = sorted([key.encode('ascii', 'ignore') for key in self.inspect_outputs_dict.keys()],
                                      key=str.lower)
    
    def has_run(self):
        if not self.config.eddy_current_and_motion_correction:
            if not self.config.denoising and not self.config.bias_field_correction:
                return True
            else:
                return os.path.exists(os.path.join(self.stage_dir, "mr_convert_b", "result_mr_convert_b.pklz"))
        else:
            return os.path.exists(os.path.join(self.stage_dir, "eddy", "result_eddy.pklz"))


class splitDiffusion_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True)
    start = Int(0)
    end = Int()


class splitDiffusion_OutputSpec(TraitedSpec):
    data = File(exists=True)
    padding1 = File(exists=False)
    padding2 = File(exists=False)


class splitDiffusion(BaseInterface):
    input_spec = splitDiffusion_InputSpec
    output_spec = splitDiffusion_OutputSpec
    
    def _run_interface(self, runtime):
        diffusion_file = nib.load(self.inputs.in_file)
        diffusion = diffusion_file.get_data()
        affine = diffusion_file.get_affine()
        dim = diffusion.shape
        if self.inputs.start > 0 and self.inputs.end > dim[3] - 1:
            error('End volume is set to %d but it should be bellow %d' % (self.inputs.end, dim[3] - 1))
        padding_idx1 = range(0, self.inputs.start)
        if len(padding_idx1) > 0:
            temp = diffusion[:, :, :, 0:self.inputs.start]
            nib.save(nib.nifti1.Nifti1Image(temp, affine), os.path.abspath('padding1.nii.gz'))
        temp = diffusion[:, :, :, self.inputs.start:self.inputs.end + 1]
        nib.save(nib.nifti1.Nifti1Image(temp, affine), os.path.abspath('data.nii.gz'))
        padding_idx2 = range(self.inputs.end, dim[3] - 1)
        if len(padding_idx2) > 0:
            temp = diffusion[:, :, :, self.inputs.end + 1:dim[3]]
            nib.save(nib.nifti1.Nifti1Image(temp, affine), os.path.abspath('padding2.nii.gz'))
        
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["data"] = os.path.abspath('data.nii.gz')
        if os.path.exists(os.path.abspath('padding1.nii.gz')):
            outputs["padding1"] = os.path.abspath('padding1.nii.gz')
        if os.path.exists(os.path.abspath('padding2.nii.gz')):
            outputs["padding2"] = os.path.abspath('padding2.nii.gz')
        return outputs


# class ConcatOutputsAsTuple(Interface):
#     """join two inputs into a tuple
#     """
#     def __init__(self, *args, **inputs):
#         self._populate_inputs()

#     def _populate_inputs(self):
#         self.inputs = Bunch(input1=None,
#                             input2=None)

#     def get_input_info(self):
#         return []

#     def outputs(self):
#         return Bunch(output=None)

#     def aggregate_outputs(self):
#         outputs = self.outputs()
#         outputs.output =  (self.inputs.input1,self.inputs.input2)
#         # if isinstance(self.inputs.input1,str) and isinstance(self.inputs.input2,str):
#         #     outputs.output =  (self.inputs.input1,self.inputs.input2)
#         # else:
#         #     outputs.output.extend(self.inputs.input2)
#         return outputs

#     def run(self, cwd=None):
#         """Execute this module.
#         """
#         runtime = Bunch(returncode=0,
#                         stdout=None,
#                         stderr=None)
#         outputs=self.aggregate_outputs()
#         return InterfaceResult(deepcopy(self), runtime, outputs=outputs)
class CreateAcqpFileInputSpec(BaseInterfaceInputSpec):
    total_readout = Float(0.0)


class CreateAcqpFileOutputSpec(TraitedSpec):
    acqp = File(exists=True)


class CreateAcqpFile(BaseInterface):
    input_spec = CreateAcqpFileInputSpec
    output_spec = CreateAcqpFileOutputSpec
    
    def _run_interface(self, runtime):
        import numpy as np
        
        # Matrix giving phase-encoding direction (3 first columns) and total read out time (4th column)
        # For phase encoding A << P <=> y-direction
        # Total readout time = Echo spacing x EPI factor x 0.001 [s]
        mat = np.array([['0', '1', '0', str(self.inputs.total_readout)],
                        ['0', '-1', '0', str(self.inputs.total_readout)]])
        
        out_f = file(os.path.abspath('acqp.txt'), 'a')
        np.savetxt(out_f, mat, fmt="%s", delimiter=' ')
        out_f.close()
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["acqp"] = os.path.abspath('acqp.txt')
        return outputs


class CreateIndexFileInputSpec(BaseInterfaceInputSpec):
    in_grad_mrtrix = File(exists=True, mandatory=True, desc='Input DWI gradient table in MRTric format')


class CreateIndexFileOutputSpec(TraitedSpec):
    index = File(exists=True)


class CreateIndexFile(BaseInterface):
    input_spec = CreateIndexFileInputSpec
    output_spec = CreateIndexFileOutputSpec
    
    def _run_interface(self, runtime):
        axis_dict = {'x': 0, 'y': 1, 'z': 2}
        import numpy as np
        
        with open(self.inputs.in_grad_mrtrix, 'r') as f:
            for i, l in enumerate(f):
                pass
        
        lines = i + 1
        
        mat = np.ones((1, lines))
        
        out_f = file(os.path.abspath('index.txt'), 'a')
        np.savetxt(out_f, mat, delimiter=' ', fmt="%1.0g")
        out_f.close()
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["index"] = os.path.abspath('index.txt')
        return outputs


class ConcatOutputsAsTupleInputSpec(BaseInterfaceInputSpec):
    input1 = File(exists=True)
    input2 = File(exists=True)


class ConcatOutputsAsTupleOutputSpec(TraitedSpec):
    out_tuple = traits.Tuple(File(exists=True), File(exists=True))


class ConcatOutputsAsTuple(BaseInterface):
    input_spec = ConcatOutputsAsTupleInputSpec
    output_spec = ConcatOutputsAsTupleOutputSpec
    
    def _run_interface(self, runtime):
        self._outputs().out_tuple = (self.inputs.input1, self.inputs.input2)
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_tuple"] = (self.inputs.input1, self.inputs.input2)
        return outputs


class ApplymultipleMRConvertInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(File(desc='files to be registered', mandatory=True, exists=True))
    stride = traits.List(traits.Int, argstr='-stride %s', sep=',',
                         position=3, minlen=3, maxlen=4,
                         desc='Three to four comma-separated numbers specifying the strides of the output data in memory. The actual strides produced will depend on whether the output image format can support it..')
    output_datatype = traits.Enum("float32", "float32le", "float32be", "float64", "float64le", "float64be", "int64",
                                  "uint64", "int64le", "uint64le", "int64be", "uint64be", "int32", "uint32", "int32le",
                                  "uint32le", "int32be", "uint32be", "int16", "uint16", "int16le", "uint16le",
                                  "int16be", "uint16be", "cfloat32", "cfloat32le", "cfloat32be", "cfloat64",
                                  "cfloat64le", "cfloat64be", "int8", "uint8", "bit", argstr='-datatype %s', position=2,
                                  desc='"specify output image data type. Valid choices are: float32, float32le, float32be, float64, float64le, float64be, int64, uint64, int64le, uint64le, int64be, uint64be, int32, uint32, int32le, uint32le, int32be, uint32be, int16, uint16, int16le, uint16le, int16be, uint16be, cfloat32, cfloat32le, cfloat32be, cfloat64, cfloat64le, cfloat64be, int8, uint8, bit."')  # , usedefault=True)
    extension = traits.Enum("mif", "nii", "float", "char", "short", "int", "long", "double", position=4,
                            desc='"i.e. Bfloat". Can be "char", "short", "int", "long", "float" or "double"',
                            usedefault=True)


class ApplymultipleMRConvertOutputSpec(TraitedSpec):
    converted_files = OutputMultiPath(File())


class ApplymultipleMRConvert(BaseInterface):
    input_spec = ApplymultipleMRConvertInputSpec
    output_spec = ApplymultipleMRConvertOutputSpec
    
    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            # Extract image filename (only) and create output image filename (no renaming)
            out_filename = in_file.split('/')[-1]
            ax = MRConvert(in_file=in_file, stride=self.inputs.stride, out_filename=out_filename,
                           output_datatype=self.inputs.output_datatype, extension=self.inputs.extension)
            ax.run()
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['converted_files'] = glob.glob(os.path.abspath("*.nii.gz"))
        return outputs
