# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
"""
# from pyface.message_dialog import error
import os
import glob

from traits.api import *

from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, \
    TraitedSpec, Interface
import nipype.interfaces.utility as util

import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.dipy as dipy

from cmp.stages.common import Stage

import cmtklib.interfaces.fsl as cmp_fsl
# from cmp.pipelines.common import MRThreshold, ExtractMRTrixGrad
from cmtklib.interfaces.mrtrix3 import DWIDenoise, DWIBiasCorrect, MRConvert, \
    MRThreshold, ExtractMRTrixGrad, Generate5tt, \
    GenerateGMWMInterface, ApplymultipleMRConvert
from cmtklib.interfaces.misc import ExtractPVEsFrom5TT, UpdateGMWMInterfaceSeeding, \
    CreateIndexFile, CreateAcqpFile


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
    interpolation = Enum(
        ['interpolate', 'weighted', 'nearest', 'sinc', 'cubic'])


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

        with open(os.path.abspath('dwi_split.bvec'), 'a') as out_f:
            np.savetxt(out_f, bvecs, delimiter=self.inputs.delimiter)

        with open(os.path.abspath('dwi_split.bval'), 'a') as out_f:
            np.savetxt(out_f, bvals.T, newline=self.inputs.delimiter)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["bvecs_split"] = os.path.abspath('dwi_split.bvec')
        outputs["bvals_split"] = os.path.abspath('dwi_split.bval')
        return outputs


class PreprocessingStage(Stage):
    # General and UI members
    def __init__(self, bids_dir, output_dir):
        self.name = 'preprocessing_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = PreprocessingConfig()
        self.inputs = ["diffusion", "bvecs", "bvals", "T1", "aparc_aseg", "aseg", "brain", "brain_mask", "wm_mask_file",
                       "roi_volumes"]
        self.outputs = ["diffusion_preproc", "bvecs_rot", "bvals", "diffusion_noisemap", "diffusion_biasfield", "dwi_brain_mask",
                        "T1", "act_5TT", "gmwmi", "brain", "brain_mask", "brain_mask_full", "wm_mask_file", "partial_volume_files",
                        "roi_volumes"]

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
            (inputnode, processing_input, [
             ('diffusion', 'diffusion'), ('bvecs', 'bvecs'), ('bvals', 'bvals')]),
        ])

        flow.connect([
            (inputnode, processing_input,
             [('T1', 'T1'), ('aparc_aseg', 'aparc_aseg'), ('aseg', 'aseg'), ('brain', 'brain'),
              ('brain_mask', 'brain_mask'), ('wm_mask_file', 'wm_mask_file'), ('roi_volumes', 'roi_volumes')]),
            (processing_input, outputnode, [('bvals', 'bvals')])
        ])

        # Conversion to MRTrix image format ".mif", grad_fsl=(inputnode.inputs.bvecs,inputnode.inputs.bvals)
        mr_convert = pe.Node(interface=MRConvert(
            stride=[1, 2, +3, +4]), name='mr_convert')
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
            (concatnode, mr_convert, [
             (('out', convertList2Tuple), 'grad_fsl')])
        ])

        # Convert Freesurfer data
        mr_convert_brainmask = pe.Node(
            interface=MRConvert(out_filename='brainmaskfull.nii.gz', stride=[
                                1, 2, 3], output_datatype='float32'),
            name='mr_convert_brain_mask')
        mr_convert_brain = pe.Node(
            interface=MRConvert(out_filename='anat_masked.nii.gz', stride=[
                                1, 2, 3], output_datatype='float32'),
            name='mr_convert_brain')
        mr_convert_T1 = pe.Node(
            interface=MRConvert(out_filename='anat.nii.gz', stride=[
                                1, 2, 3], output_datatype='float32'),
            name='mr_convert_T1')
        mr_convert_roi_volumes = pe.Node(
            interface=ApplymultipleMRConvert(
                stride=[1, 2, 3], output_datatype='float32', extension='nii'),
            name='mr_convert_roi_volumes')
        mr_convert_wm_mask_file = pe.Node(
            interface=MRConvert(out_filename='wm_mask_file.nii.gz', stride=[
                                1, 2, 3], output_datatype='float32'),
            name='mr_convert_wm_mask_file')

        flow.connect([
            (processing_input, mr_convert_brainmask,
             [('brain_mask', 'in_file')]),
            (processing_input, mr_convert_brain, [('brain', 'in_file')]),
            (processing_input, mr_convert_T1, [('T1', 'in_file')]),
            (processing_input, mr_convert_roi_volumes,
             [('roi_volumes', 'in_files')]),
            (processing_input, mr_convert_wm_mask_file,
             [('wm_mask_file', 'in_file')])
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
            (mr_convert_brainmask, mr_threshold_brainmask,
             [('converted', 'in_file')])
        ])

        # Extract b0 and create DWI mask
        flirt_dwimask_pre = pe.Node(interface=fsl.FLIRT(out_file='brain2b0.nii.gz', out_matrix_file='brain2b0aff'),
                                    name='flirt_dwimask_pre')
        costs = ['mutualinfo', 'corratio', 'normcorr',
                 'normmi', 'leastsq', 'labeldiff', 'bbr']
        flirt_dwimask_pre.inputs.cost = costs[3]
        flirt_dwimask_pre.inputs.cost_func = costs[3]
        flirt_dwimask_pre.inputs.dof = 6
        flirt_dwimask_pre.inputs.no_search = False

        flirt_dwimask = pe.Node(
            interface=fsl.FLIRT(out_file='dwi_brain_mask.nii.gz',
                                apply_xfm=True, interp='nearestneighbour'),
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
            (flirt_dwimask_pre, flirt_dwimask, [
             ('out_matrix_file', 'in_matrix_file')]),
            (mr_threshold_brainmask, flirt_dwimask,
             [('thresholded', 'in_file')])
        ])

        # Diffusion data denoising
        if self.config.denoising:

            mr_convert_noise = pe.Node(interface=MRConvert(out_filename='diffusion_noisemap.nii.gz', stride=[+1, +2, +3, +4]),
                                       name='mr_convert_noise')

            if self.config.denoising_algo == "MRtrix (MP-PCA)":
                mr_convert.inputs.out_filename = 'diffusion.mif'
                dwi_denoise = pe.Node(
                    interface=DWIDenoise(
                        out_file='diffusion_denoised.mif', out_noisemap='diffusion_noisemap.mif'),
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
                dwi_denoise = pe.Node(
                    interface=dipy.Denoise(), name='dwi_denoise')
                if self.config.dipy_noise_model == "Gaussian":
                    dwi_denoise.inputs.noise_model = "gaussian"
                elif self.config.dipy_noise_model == "Rician":
                    dwi_denoise.inputs.noise_model = "rician"

                flow.connect([
                    (processing_input, dwi_denoise,
                     [('diffusion', 'in_file')]),
                    (flirt_dwimask, dwi_denoise, [('out_file', 'in_mask')]),
                    (dwi_denoise, mr_convert, [('out_file', 'in_file')])
                ])

            flow.connect([
                (dwi_denoise, mr_convert_noise, [('out_file', 'in_file')]),
                (mr_convert_noise, outputnode, [('converted', 'diffusion_noisemap')])
            ])
        else:
            mr_convert.inputs.out_filename = 'diffusion.mif'
            flow.connect([
                (processing_input, mr_convert, [('diffusion', 'in_file')])
            ])

        mr_convert_b = pe.Node(interface=MRConvert(out_filename='diffusion_corrected.nii.gz', stride=[+1, +2, +3, +4]),
                               name='mr_convert_b')

        if self.config.bias_field_correction:

            mr_convert_bias = pe.Node(interface=MRConvert(out_filename='diffusion_biasfield.nii.gz', stride=[+1, +2, +3, +4]),
                                      name='mr_convert_bias')

            if self.config.bias_field_algo == "ANTS N4":
                dwi_biascorrect = pe.Node(
                    interface=DWIBiasCorrect(
                        use_ants=True, out_bias='diffusion_denoised_biasfield.mif'),
                    name='dwi_biascorrect')
            elif self.config.bias_field_algo == "FSL FAST":
                dwi_biascorrect = pe.Node(
                    interface=DWIBiasCorrect(
                        use_fsl=True, out_bias='diffusion_denoised_biasfield.mif'),
                    name='dwi_biascorrect')

            dwi_biascorrect.inputs.debug = True

            if self.config.denoising:
                if self.config.denoising_algo == "MRtrix (MP-PCA)":
                    flow.connect([
                        (dwi_denoise, dwi_biascorrect,
                         [('out_file', 'in_file')]),
                        (flirt_dwimask, dwi_biascorrect,
                         [('out_file', 'mask')]),
                        (dwi_biascorrect, mr_convert_b,
                         [('out_file', 'in_file')])
                    ])
                elif self.config.denoising_algo == "Dipy (NLM)":
                    flow.connect([
                        (mr_convert, dwi_biascorrect,
                         [('converted', 'in_file')]),
                        (flirt_dwimask, dwi_biascorrect,
                         [('out_file', 'mask')]),
                        (dwi_biascorrect, mr_convert_b,
                         [('out_file', 'in_file')])
                    ])
            else:
                flow.connect([
                    (mr_convert, dwi_biascorrect, [('converted', 'in_file')]),
                    (flirt_dwimask, dwi_biascorrect, [('out_file', 'mask')])
                ])

            flow.connect([
                (dwi_biascorrect, mr_convert_bias, [('out_file', 'in_file')]),
                (mr_convert_bias, outputnode, [('converted', 'diffusion_biasfield')])
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
        acqpnode = pe.Node(interface=CreateAcqpFile(
            total_readout=self.config.total_readout), name='acqpnode')

        indexnode = pe.Node(interface=CreateIndexFile(), name='indexnode')
        flow.connect([
            (extract_grad_mrtrix, indexnode, [
             ("out_grad_mrtrix", "in_grad_mrtrix")])
        ])

        fs_mriconvert = pe.Node(
            interface=fs.MRIConvert(
                out_type='niigz', out_file='diffusion_preproc_resampled.nii.gz'),
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
            interface=fs.MRIConvert(
                out_type='niigz', out_file='anat_masked_resampled.nii.gz'),
            name="anat_masked_resample")
        fs_mriconvert_brain.inputs.vox_size = self.config.resampling
        fs_mriconvert_brain.inputs.resample_type = self.config.interpolation

        flow.connect([
            (mr_convert_brain, fs_mriconvert_brain,
             [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_brain,[('converted','reslice_like')]),
            (fs_mriconvert_brain, outputnode, [('out_file', 'brain')])
        ])

        fs_mriconvert_brainmask = pe.Node(
            interface=fs.MRIConvert(
                out_type='niigz', resample_type='nearest', out_file='brain_mask_resampled.nii.gz'),
            name="brain_mask_resample")
        fs_mriconvert_brainmask.inputs.vox_size = self.config.resampling
        flow.connect([
            (mr_threshold_brainmask, fs_mriconvert_brainmask,
             [('thresholded', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_brainmask,[('converted','reslice_like')]),
            (fs_mriconvert_brainmask, outputnode, [('out_file', 'brain_mask')])
        ])

        fs_mriconvert_brainmaskfull = pe.Node(
            interface=fs.MRIConvert(
                out_type='niigz', out_file='brain_mask_full_resampled.nii.gz'),
            name="brain_mask_full_resample")
        fs_mriconvert_brainmaskfull.inputs.vox_size = self.config.resampling
        fs_mriconvert_brainmaskfull.inputs.resample_type = self.config.interpolation
        flow.connect([
            (mr_convert_brainmask, fs_mriconvert_brainmaskfull,
             [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_brainmaskfull,[('converted','reslice_like')]),
            (fs_mriconvert_brainmaskfull, outputnode,
             [('out_file', 'brain_mask_full')])
        ])

        fs_mriconvert_wm_mask = pe.Node(
            interface=fs.MRIConvert(
                out_type='niigz', resample_type='nearest', out_file='wm_mask_resampled.nii.gz'),
            name="wm_mask_resample")
        fs_mriconvert_wm_mask.inputs.vox_size = self.config.resampling
        flow.connect([
            (mr_convert_wm_mask_file, fs_mriconvert_wm_mask,
             [('converted', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_wm_mask,[('converted','reslice_like')]),
            (fs_mriconvert_wm_mask, outputnode, [('out_file', 'wm_mask_file')])
        ])

        fs_mriconvert_ROIs = pe.MapNode(interface=fs.MRIConvert(out_type='niigz', resample_type='nearest'),
                                        iterfield=['in_file'], name="ROIs_resample")
        fs_mriconvert_ROIs.inputs.vox_size = self.config.resampling
        flow.connect([
            (mr_convert_roi_volumes, fs_mriconvert_ROIs,
             [('converted_files', 'in_file')]),
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
            (mr_convert_b0_resample, fs_mriconvert_dwimask,
             [('converted', 'reslice_like')]),
            (fs_mriconvert_dwimask, outputnode,
             [('out_file', 'dwi_brain_mask')])
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
                        interface=fsl.MCFLIRT(
                            out_file='motion_corrected.nii.gz', ref_vol=0, save_mats=True),
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
                        (mr_convert_b, eddy_correct,
                         [("converted", "in_file")])
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
                    (eddy_correct, fs_mriconvert, [
                     ('eddy_corrected', 'in_file')]),
                    (fs_mriconvert, outputnode, [
                     ("out_file", "diffusion_preproc")])
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
                    (eddy_correct, outputnode, [
                     ("bvecs_rotated", "bvecs_rot")])
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
                    (eddy_correct, fs_mriconvert, [
                     ('eddy_corrected', 'in_file')]),
                    (fs_mriconvert, outputnode, [
                     ("out_file", "diffusion_preproc")])
                ])
        else:
            # resampling diffusion image and setting output type to short
            flow.connect([
                (mr_convert_b, fs_mriconvert, [("converted", "in_file")]),
                (fs_mriconvert, outputnode, [
                 ("out_file", "diffusion_preproc")]),
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

        mrtrix_5tt = pe.Node(interface=Generate5tt(
            out_file='mrtrix_5tt.nii.gz'), name='mrtrix_5tt')
        mrtrix_5tt.inputs.algorithm = 'freesurfer'
        # mrtrix_5tt.inputs.algorithm = 'hsvs'

        flow.connect([
            (processing_input, mrtrix_5tt, [('aparc_aseg', 'in_file')]),
            (mrtrix_5tt, fs_mriconvert_5tt, [('out_file', 'in_file')]),
            (fs_mriconvert_5tt, outputnode, [('out_file', 'act_5TT')]),
        ])

        # if self.config.partial_volume_estimation:
        pve_extractor_from_5tt = pe.Node(
            interface=ExtractPVEsFrom5TT(), name='pve_extractor_from_5tt')
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
            (pve_extractor_from_5tt, fs_mriconvert_PVEs,
             [('partial_volume_files', 'in_file')]),
            # (mr_convert_b0_resample,fs_mriconvert_ROIs,[('converted','reslice_like')]),
            (fs_mriconvert_PVEs, outputnode, [
             ("out_file", "partial_volume_files")])
        ])

        fs_mriconvert_gmwmi = pe.Node(interface=fs.MRIConvert(out_type='niigz', out_file='gmwmi_resampled.nii.gz'),
                                      name="gmwmi_resample")
        fs_mriconvert_gmwmi.inputs.vox_size = self.config.resampling
        fs_mriconvert_gmwmi.inputs.resample_type = self.config.interpolation

        mrtrix_gmwmi = pe.Node(interface=GenerateGMWMInterface(
            out_file='gmwmi.nii.gz'), name='mrtrix_gmwmi')

        update_gmwmi = pe.Node(
            interface=UpdateGMWMInterfaceSeeding(), name='update_gmwmi')
        update_gmwmi.inputs.out_gmwmi_file = 'gmwmi_proc.nii.gz'

        flow.connect([
            (mrtrix_5tt, mrtrix_gmwmi, [('out_file', 'in_file')]),
            (mrtrix_gmwmi, update_gmwmi, [('out_file', 'in_gmwmi_file')]),
            (processing_input, update_gmwmi, [
             ('roi_volumes', 'in_roi_volumes')]),
            (update_gmwmi, fs_mriconvert_gmwmi,
             [('out_gmwmi_file', 'in_file')]),
            (fs_mriconvert_gmwmi, outputnode, [('out_file', 'gmwmi')]),
        ])

    def define_inspect_outputs(self):
        # print "stage_dir : %s" % self.stage_dir

        if self.config.denoising:

            dwi_denoise_dir = os.path.join(self.stage_dir, 'dwi_denoise')
            denoise = os.path.join(dwi_denoise_dir, 'diffusion_denoised.mif')

            if os.path.exists(denoise):
                self.inspect_outputs_dict['DWI denoised image'] = ['mrview', denoise]
                if self.config.denoising_algo == "MRtrix (MP-PCA)":

                    noise = os.path.join(dwi_denoise_dir, 'diffusion_noisemap.mif')

                    if os.path.exists(denoise):

                        self.inspect_outputs_dict['Noise map'] = ['mrview', noise]

        if self.config.bias_field_correction:

            dwi_biascorrect_dir = os.path.join(self.stage_dir, 'dwi_biascorrect')

            bcorr = ""
            files = glob.glob(os.path.join(dwi_biascorrect_dir, '*_biascorr.mif'))
            if len(files) > 0:
                bcorr = files[0]

            bias = ""
            files = glob.glob(os.path.join(dwi_biascorrect_dir, '*_biasfield.mif'))
            if len(files) > 0:
                bias = files[0]

            if os.path.exists(bcorr):
                self.inspect_outputs_dict['Bias field corrected image'] = ['mrview', bcorr]

            if os.path.exists(bias):
                self.inspect_outputs_dict['Bias field'] = ['mrview', bias]

        if self.config.eddy_current_and_motion_correction:

            if self.config.eddy_correction_algo == 'FSL eddy_correct':
                eddy_dir = os.path.join(self.stage_dir, 'eddy_correct')
            else:
                eddy_dir = os.path.join(self.stage_dir, 'eddy')

            # Might need extra if/else for eddy_correct/eddy
            edcorr = os.path.join(eddy_dir, 'eddy_corrected.nii.gz')

            if os.path.exists(edcorr):
                self.inspect_outputs_dict['Eddy current corrected image'] = ['mrview', edcorr]

        self.inspect_outputs = sorted([key for key in list(self.inspect_outputs_dict.keys())],
                                      key=str.lower)

    def has_run(self):
        if not self.config.eddy_current_and_motion_correction:
            if not self.config.denoising and not self.config.bias_field_correction:
                return True
            else:
                return os.path.exists(os.path.join(self.stage_dir, "mr_convert_b", "result_mr_convert_b.pklz"))
        else:
            return os.path.exists(os.path.join(self.stage_dir, "eddy", "result_eddy.pklz"))
