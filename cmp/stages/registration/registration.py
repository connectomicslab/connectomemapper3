# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP registration stage
"""

# General imports
import os
from traits.api import *
import pickle
import gzip
import glob

# Nipype imports
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.mrtrix as mrt
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
from nipype.interfaces.base import traits, isdefined, CommandLine, CommandLineInputSpec, \
    TraitedSpec, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec
from nipype.interfaces.mrtrix3.reconst import FitTensor
from nipype.interfaces.mrtrix3.utils import TensorMetrics
import nipype.interfaces.ants as ants
# from nipype.interfaces.ants.registration import ANTS
# from nipype.interfaces.ants.resampling import ApplyTransforms, WarpImageMultiTransform

import nibabel as nib

# Own imports
from cmp.stages.common import Stage

# from cmp.pipelines.common import MRThreshold, MRCrop, ExtractMRTrixGrad, FSLCreateHD
from cmtklib.interfaces.mrtrix3 import DWI2Tensor, MRConvert, MRTransform, \
    MRThreshold, MRCrop, ExtractMRTrixGrad, ApplymultipleMRTransforms, ApplymultipleMRCrop
from cmtklib.interfaces.fsl import FSLCreateHD, ApplymultipleXfm, ApplymultipleWarp, \
    Applynlinmultiplewarps
import cmtklib.interfaces.freesurfer as cmp_fs
import cmtklib.interfaces.fsl as cmp_fsl
from cmtklib.interfaces.ants import MultipleANTsApplyTransforms
from cmtklib.util import get_pipeline_dictionary_outputs


class RegistrationConfig(HasTraits):
    # Pipeline mode
    pipeline = Enum(["Diffusion", "fMRI"])

    # Registration selection
    registration_mode = Str('ANTs')  # Str('FSL')
    registration_mode_trait = List(['FSL', 'ANTs'])  # ,'BBregister (FS)'])
    diffusion_imaging_model = Str

    use_float_precision = Bool(False)

    # ANTS
    ants_interpolation = Enum('Linear', ['Linear', 'NearestNeighbor', 'CosineWindowedSinc', 'WelchWindowedSinc',
                                         'HammingWindowedSinc', 'LanczosWindowedSinc', 'BSpline', 'MultiLabel',
                                         'Gaussian'])
    ants_bspline_interpolation_parameters = Tuple(Int(3))
    ants_gauss_interpolation_parameters = Tuple(Float(5), Float(5))
    ants_multilab_interpolation_parameters = Tuple(Float(5), Float(5))
    ants_lower_quantile = Float(0.005)
    ants_upper_quantile = Float(0.995)
    ants_convergence_thresh = Float(1e-06)
    ants_convergence_winsize = Int(10)

    ants_linear_gradient_step = Float(0.1)
    ants_linear_cost = Enum(
        'MI', ['CC', 'MeanSquares', 'Demons', 'GC', 'MI', 'Mattes'])
    ants_linear_sampling_perc = Float(0.25)
    ants_linear_sampling_strategy = Enum(
        'Regular', ['None', 'Regular', 'Random'])

    ants_perform_syn = Bool(True)
    ants_nonlinear_gradient_step = Float(0.1)
    ants_nonlinear_cost = Enum(
        'CC', ['CC', 'MeanSquares', 'Demons', 'GC', 'MI', 'Mattes'])
    ants_nonlinear_update_field_variance = Float(3.0)
    ants_nonlinear_total_field_variance = Float(0.0)

    # FLIRT
    flirt_args = Str
    uses_qform = Bool(True)
    dof = Int(6)
    fsl_cost = Enum('normmi', ['mutualinfo', 'corratio',
                               'normcorr', 'normmi', 'leastsq', 'labeldiff'])
    no_search = Bool(True)

    # BBRegister
    init = Enum('header', ['spm', 'fsl', 'header'])
    contrast_type = Enum('dti', ['t1', 't2', 'dti'])

    # Apply transform
    apply_to_eroded_wm = Bool(True)
    apply_to_eroded_csf = Bool(True)
    apply_to_eroded_brain = Bool(False)


def unicode2str(text):
    return str(text)


class RegistrationStage(Stage):

    # Freesurfer informations (for BBregister)
    fs_subjects_dir = Directory(exists=False, resolve=False, mandatory=False)
    fs_subject_id = Str(mandatory=False)

    def __init__(self, pipeline_mode, fs_subjects_dir=None, fs_subject_id=None, bids_dir="", output_dir=""):
        self.name = 'registration_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = RegistrationConfig()
        self.config.pipeline = pipeline_mode

        if pipeline_mode == 'fMRI':
            self.config.registration_mode = 'FSL (Linear)'
            self.config.registration_mode_trait = [
                'FSL (Linear)', 'BBregister (FS)']

        if fs_subjects_dir is not None: self.fs_subjects_dir = fs_subjects_dir
        if fs_subject_id is not None: self.fs_subject_id = fs_subject_id

        self.inputs = ["T1", "act_5TT", "gmwmi", "target", "T2", "subjects_dir", "subject_id", "wm_mask",
                       "partial_volume_files", "roi_volumes", "brain", "brain_mask", "brain_mask_full", "target_mask",
                       "bvecs", "bvals"]
        self.outputs = ["T1_registered_crop", "act_5tt_registered_crop", "affine_transform", "warp_field",
                        "gmwmi_registered_crop", "brain_registered_crop", "brain_mask_registered_crop",
                        "wm_mask_registered_crop", "partial_volumes_registered_crop", "roi_volumes_registered_crop",
                        "target_epicorrected", "grad", "bvecs", "bvals"]
        if self.config.pipeline == "fMRI":
            self.inputs = self.inputs + \
                ["eroded_csf", "eroded_wm", "eroded_brain"]
            self.outputs = self.outputs + ["eroded_wm_registered_crop", "eroded_csf_registered_crop",
                                           "eroded_brain_registered_crop"]

    def create_workflow(self, flow, inputnode, outputnode):
        # Extract first volume and resample it to 1x1x1mm3
        if self.config.pipeline == "Diffusion":
            extract_first = pe.Node(interface=fsl.ExtractROI(t_min=0, t_size=1, roi_file='first.nii.gz'),
                                    name='extract_first')
            flow.connect([
                (inputnode, extract_first, [("target", "in_file")])
            ])
            fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_file="target_first.nii.gz", vox_size=(1, 1, 1)),
                                    name="target_resample")
            flow.connect(
                [(extract_first, fs_mriconvert, [('roi_file', 'in_file')])])

        elif self.config.pipeline == "fMRI":
            fmri_bet = pe.Node(interface=fsl.BET(), name="fMRI_skullstrip")
            T1_bet = pe.Node(interface=fsl.BET(), name="T1_skullstrip")
            flow.connect([
                (inputnode, fmri_bet, [("target", "in_file")]),
                (inputnode, T1_bet, [("T1", "in_file")])
            ])

        if self.config.registration_mode == 'FSL':
            # [SUB-STEP 1] Linear register "T1" onto"Target_FA_resampled"
            # [1.1] Convert diffusion data to mrtrix format using rotated bvecs
            mr_convert = pe.Node(interface=MRConvert(out_filename='diffusion.mif', stride=[+1, +2, +3, +4]),
                                 name='mr_convert')
            mr_convert.inputs.quiet = True
            mr_convert.inputs.force_writing = True

            concatnode = pe.Node(interface=util.Merge(2), name='concatnode')

            def convertList2Tuple(lists):
                return tuple(lists)

            flow.connect([
                (inputnode, concatnode, [('bvecs', 'in1')]),
                (inputnode, concatnode, [('bvals', 'in2')]),
                (concatnode, mr_convert, [
                 (('out', convertList2Tuple), 'grad_fsl')]),
                (inputnode, mr_convert, [('target', 'in_file')])
            ])
            grad_mrtrix = pe.Node(ExtractMRTrixGrad(
                out_grad_mrtrix='grad.txt'), name='extract_grad')
            flow.connect([
                (mr_convert, grad_mrtrix, [("converted", "in_file")]),
                (grad_mrtrix, outputnode, [("out_grad_mrtrix", "grad")])
            ])

            flow.connect([
                (inputnode, outputnode, [("bvals", "bvals")]),
                (inputnode, outputnode, [("bvecs", "bvecs")])
            ])

            mr_convert_b0 = pe.Node(interface=MRConvert(out_filename='b0.nii.gz', stride=[+1, +2, +3]),
                                    name='mr_convert_b0')
            mr_convert_b0.inputs.extract_at_axis = 3
            mr_convert_b0.inputs.extract_at_coordinate = [0]

            flow.connect([
                (inputnode, mr_convert_b0, [('target', 'in_file')])
            ])

            dwi2tensor = pe.Node(interface=DWI2Tensor(
                out_filename='dt_corrected.mif'), name='dwi2tensor')
            dwi2tensor_unmasked = pe.Node(interface=DWI2Tensor(out_filename='dt_corrected_unmasked.mif'),
                                          name='dwi2tensor_unmasked')

            tensor2FA = pe.Node(interface=TensorMetrics(
                out_fa='fa_corrected.mif'), name='tensor2FA')
            tensor2FA_unmasked = pe.Node(interface=TensorMetrics(out_fa='fa_corrected_unmasked.mif'),
                                         name='tensor2FA_unmasked')

            mr_convert_FA = pe.Node(interface=MRConvert(out_filename='fa_corrected.nii.gz', stride=[+1, +2, +3]),
                                    name='mr_convert_FA')
            mr_convert_FA_unmasked = pe.Node(
                interface=MRConvert(
                    out_filename='fa_corrected_unmasked.nii.gz', stride=[+1, +2, +3]),
                name='mr_convert_FA_unmasked')

            FA_noNaN = pe.Node(interface=cmp_fsl.MathsCommand(out_file='fa_corrected_nonan.nii.gz', nan2zeros=True),
                               name='FA_noNaN')
            FA_noNaN_unmasked = pe.Node(
                interface=cmp_fsl.MathsCommand(
                    out_file='fa_corrected_unmasked_nonan.nii.gz', nan2zeros=True),
                name='FA_noNaN_unmasked')

            flow.connect([
                (mr_convert, dwi2tensor, [('converted', 'in_file')]),
                (inputnode, dwi2tensor, [('target_mask', 'in_mask_file')]),
                (dwi2tensor, tensor2FA, [('tensor', 'in_file')]),
                (inputnode, tensor2FA, [('target_mask', 'in_mask')]),
                (tensor2FA, mr_convert_FA, [('out_fa', 'in_file')]),
                (mr_convert_FA, FA_noNaN, [('converted', 'in_file')])
            ])

            flow.connect([
                (mr_convert, dwi2tensor_unmasked, [('converted', 'in_file')]),
                (dwi2tensor_unmasked, tensor2FA_unmasked,
                 [('tensor', 'in_file')]),
                (tensor2FA_unmasked, mr_convert_FA_unmasked,
                 [('out_fa', 'in_file')]),
                (mr_convert_FA_unmasked, FA_noNaN_unmasked,
                 [('converted', 'in_file')])
            ])

            # [1.2] Linear registration of the DW data to the T1 data
            fsl_flirt = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-B0.nii.gz', out_matrix_file='T12DWIaff.mat'),
                                name="linear_registration")
            fsl_flirt.inputs.dof = self.config.dof
            fsl_flirt.inputs.cost = self.config.fsl_cost
            fsl_flirt.inputs.cost_func = self.config.fsl_cost
            fsl_flirt.inputs.no_search = self.config.no_search
            fsl_flirt.inputs.verbose = False

            flow.connect([
                (inputnode, fsl_flirt, [('brain', 'in_file')]),
                (mr_convert_b0, fsl_flirt, [('converted', 'reference')])
            ])

            # [1.3] Transforming T1-space images to avoid rotation of bvecs
            T12DWIaff = pe.Node(interface=fsl.ConvertXFM(
                invert_xfm=False), name='T12DWIaff')
            flow.connect([
                (fsl_flirt, T12DWIaff, [('out_matrix_file', 'in_file')]),
                (T12DWIaff, outputnode, [('out_file', 'affine_transform')])
            ])

            fsl_applyxfm_wm = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="nearestneighbour", out_file="wm_mask_registered.nii.gz"),
                name="apply_registration_wm")
            fsl_applyxfm_rois = pe.Node(
                interface=ApplymultipleXfm(), name="apply_registration_roivs")
            fsl_applyxfm_brain_mask = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="spline", out_file="brain_mask_registered_temp.nii.gz"),
                name="apply_registration_brain_mask")
            fsl_applyxfm_brain_mask_full = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, interp="spline",
                                                                          out_file="brain_mask_full_registered_temp.nii.gz"),
                                                   name="apply_registration_brain_mask_full")
            fsl_applyxfm_brain = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="spline", out_file="brain_registered.nii.gz"),
                name="apply_registration_brain")
            fsl_applyxfm_T1 = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="spline", out_file="T1_registered.nii.gz"),
                name="apply_registration_T1")

            mr_threshold_brain_mask = pe.Node(
                interface=MRThreshold(abs_value=0.5, out_file='brain_mask2_registered.nii.gz', quiet=True,
                                      force_writing=True), name="mr_threshold_brain_mask")
            mr_threshold_brain_mask_full = pe.Node(
                interface=MRThreshold(abs_value=1, out_file='brain_mask_registered.nii.gz', quiet=True,
                                      force_writing=True), name="mr_threshold_brain_mask_full")
            mr_threshold_T1 = pe.Node(
                interface=MRThreshold(
                    abs_value=10, out_file='T1_registered_th.nii.gz', quiet=True, force_writing=True),
                name="mr_threshold_T1")

            fsl_applyxfm_5tt = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="spline", out_file="5tt_registered.nii.gz"),
                name="apply_registration_5tt")
            fsl_applyxfm_gmwmi = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="spline", out_file="gmwmi_registered.nii.gz"),
                name="apply_registration_5tt")
            # fsl_create_HD = pe.Node(interface=FSLCreateHD(im_size=[256,256,256,1],vox_size=[1,1,1],origin=[0,0,0],tr=1,datatype='16',out_filename='tempref.nii.gz'),name='fsl_create_HD')

            flow.connect([
                (inputnode, fsl_applyxfm_wm, [('wm_mask', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_wm, [('out_file', 'in_matrix_file')]),
                # (fsl_create_HD, fsl_applyxfm_wm, [('out_file','reference')]),
                (mr_convert_b0, fsl_applyxfm_wm, [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_rois, [('roi_volumes', 'in_files')]),
                (T12DWIaff, fsl_applyxfm_rois, [('out_file', 'xfm_file')]),
                # (fsl_create_HD, fsl_applyxfm_rois, [('out_file','reference')]),
                (mr_convert_b0, fsl_applyxfm_rois,
                 [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_brain_mask,
                 [('brain_mask', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_brain_mask,
                 [('out_file', 'in_matrix_file')]),
                # (fsl_create_HD, fsl_applyxfm_brain_mask, [('out_file','reference')]),
                (mr_convert_b0, fsl_applyxfm_brain_mask,
                 [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_brain_mask_full,
                 [('brain_mask_full', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_brain_mask_full,
                 [('out_file', 'in_matrix_file')]),
                # (fsl_create_HD, fsl_applyxfm_brain_mask_full, [('out_file','reference')]),
                (mr_convert_b0, fsl_applyxfm_brain_mask_full,
                 [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_brain, [('brain', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_brain, [
                 ('out_file', 'in_matrix_file')]),
                # (fsl_create_HD, fsl_applyxfm_brain, [('out_file','reference')]),
                (mr_convert_b0, fsl_applyxfm_brain,
                 [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_T1, [('T1', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_T1, [('out_file', 'in_matrix_file')]),
                # (fsl_create_HD, fsl_applyxfm_T1, [('out_file','reference')]),
                (mr_convert_b0, fsl_applyxfm_T1, [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_5tt, [('act_5TT', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_5tt, [
                 ('out_file', 'in_matrix_file')]),
                (mr_convert_b0, fsl_applyxfm_5tt,
                 [('converted', 'reference')]),
                (inputnode, fsl_applyxfm_gmwmi, [('gmwmi', 'in_file')]),
                (T12DWIaff, fsl_applyxfm_gmwmi, [
                 ('out_file', 'in_matrix_file')]),
                (mr_convert_b0, fsl_applyxfm_gmwmi,
                 [('converted', 'reference')]),
            ])

            flow.connect([
                (fsl_applyxfm_brain_mask, outputnode, [
                 ('out_file', 'brain_mask_registered_crop')]),
            ])

            fsl_fnirt_crop = pe.Node(interface=fsl.FNIRT(
                fieldcoeff_file=True), name='fsl_fnirt_crop')

            flow.connect([
                (mr_convert_b0, fsl_fnirt_crop, [('converted', 'ref_file')]),
                (inputnode, fsl_fnirt_crop, [('brain', 'in_file')]),
                (fsl_flirt, fsl_fnirt_crop, [
                 ('out_matrix_file', 'affine_file')]),
                (fsl_fnirt_crop, outputnode, [
                 ('fieldcoeff_file', 'warp_field')]),
                # (inputnode, fsl_fnirt_crop, [('target_mask','refmask_file')])
            ])

            fsl_applywarp_T1 = pe.Node(interface=fsl.ApplyWarp(interp="spline", out_file="T1_warped.nii.gz"),
                                       name="apply_warp_T1")
            fsl_applywarp_5tt = pe.Node(interface=fsl.ApplyWarp(interp="spline", out_file="5tt_warped.nii.gz"),
                                        name="apply_warp_5tt")
            fsl_applywarp_gmwmi = pe.Node(interface=fsl.ApplyWarp(interp="spline", out_file="gmwmi_warped.nii.gz"),
                                          name="apply_warp_gmwmi")
            fsl_applywarp_brain = pe.Node(interface=fsl.ApplyWarp(interp="spline", out_file="brain_warped.nii.gz"),
                                          name="apply_warp_brain")
            fsl_applywarp_wm = pe.Node(interface=fsl.ApplyWarp(interp='nn', out_file="wm_mask_warped.nii.gz"),
                                       name="apply_warp_wm")
            fsl_applywarp_rois = pe.Node(interface=ApplymultipleWarp(
                interp='nn'), name="apply_warp_roivs")

            flow.connect([
                (inputnode, fsl_applywarp_T1, [('T1', 'in_file')]),
                (inputnode, fsl_applywarp_T1, [('target', 'ref_file')]),
                (fsl_fnirt_crop, fsl_applywarp_T1, [
                 ('fieldcoeff_file', 'field_file')]),
                (fsl_applywarp_T1, outputnode, [
                 ('out_file', 'T1_registered_crop')]),
            ])

            flow.connect([
                (inputnode, fsl_applywarp_5tt, [('act_5TT', 'in_file')]),
                (inputnode, fsl_applywarp_5tt, [('target', 'ref_file')]),
                (fsl_fnirt_crop, fsl_applywarp_5tt, [
                 ('fieldcoeff_file', 'field_file')]),
                (fsl_applywarp_5tt, outputnode, [
                 ('out_file', 'act_5tt_registered_crop')]),
            ])

            flow.connect([
                (inputnode, fsl_applywarp_gmwmi, [('gmwmi', 'in_file')]),
                (inputnode, fsl_applywarp_gmwmi, [('target', 'ref_file')]),
                (fsl_fnirt_crop, fsl_applywarp_gmwmi,
                 [('fieldcoeff_file', 'field_file')]),
                (fsl_applywarp_gmwmi, outputnode, [
                 ('out_file', 'gmwmi_registered_crop')]),
            ])

            flow.connect([
                (inputnode, fsl_applywarp_brain, [('brain', 'in_file')]),
                (inputnode, fsl_applywarp_brain, [('target', 'ref_file')]),
                (fsl_fnirt_crop, fsl_applywarp_brain,
                 [('fieldcoeff_file', 'field_file')]),
                (fsl_applywarp_brain, outputnode, [
                 ('out_file', 'brain_registered_crop')]),
            ])

            flow.connect([
                (inputnode, fsl_applywarp_wm, [('wm_mask', 'in_file')]),
                (inputnode, fsl_applywarp_wm, [('target', 'ref_file')]),
                (fsl_fnirt_crop, fsl_applywarp_wm, [
                 ('fieldcoeff_file', 'field_file')]),
                (fsl_applywarp_wm, outputnode, [
                 ('out_file', 'wm_mask_registered_crop')]),
            ])

            flow.connect([
                (inputnode, fsl_applywarp_rois, [('roi_volumes', 'in_files')]),
                (inputnode, fsl_applywarp_rois, [('target', 'ref_file')]),
                (fsl_fnirt_crop, fsl_applywarp_rois, [
                 ('fieldcoeff_file', 'field_file')]),
                (fsl_applywarp_rois, outputnode, [
                 ('out_files', 'roi_volumes_registered_crop')]),
            ])

            flow.connect([
                (inputnode, outputnode, [('target', 'target_epicorrected')]),
            ])

        elif self.config.registration_mode == 'ANTs':
            # [SUB-STEP 1] Linear register "T1" onto"Target_FA_resampled"
            # [1.1] Convert diffusion data to mrtrix format using rotated bvecs
            mr_convert = pe.Node(interface=MRConvert(out_filename='diffusion.mif', stride=[+1, +2, +3, +4]),
                                 name='mr_convert')
            mr_convert.inputs.quiet = True
            mr_convert.inputs.force_writing = True

            concatnode = pe.Node(interface=util.Merge(2), name='concatnode')

            def convertList2Tuple(lists):
                # print "******************************************",tuple(lists)
                return tuple(lists)

            flow.connect([
                (inputnode, concatnode, [('bvecs', 'in1')]),
                (inputnode, concatnode, [('bvals', 'in2')]),
                (concatnode, mr_convert, [
                 (('out', convertList2Tuple), 'grad_fsl')]),
                (inputnode, mr_convert, [('target', 'in_file')])
            ])
            grad_mrtrix = pe.Node(ExtractMRTrixGrad(
                out_grad_mrtrix='grad.txt'), name='extract_grad')
            flow.connect([
                (mr_convert, grad_mrtrix, [("converted", "in_file")]),
                (grad_mrtrix, outputnode, [("out_grad_mrtrix", "grad")])
            ])

            flow.connect([
                (inputnode, outputnode, [("bvals", "bvals")]),
                (inputnode, outputnode, [("bvecs", "bvecs")])
            ])

            mr_convert_b0 = pe.Node(interface=MRConvert(out_filename='b0.nii.gz', stride=[+1, +2, +3]),
                                    name='mr_convert_b0')
            mr_convert_b0.inputs.extract_at_axis = 3
            mr_convert_b0.inputs.extract_at_coordinate = [0]

            flow.connect([
                (inputnode, mr_convert_b0, [('target', 'in_file')])
            ])

            dwi2tensor = pe.Node(interface=DWI2Tensor(
                out_filename='dt_corrected.mif'), name='dwi2tensor')
            dwi2tensor_unmasked = pe.Node(interface=DWI2Tensor(out_filename='dt_corrected_unmasked.mif'),
                                          name='dwi2tensor_unmasked')

            tensor2FA = pe.Node(interface=TensorMetrics(
                out_fa='fa_corrected.mif'), name='tensor2FA')
            tensor2FA_unmasked = pe.Node(interface=TensorMetrics(out_fa='fa_corrected_unmasked.mif'),
                                         name='tensor2FA_unmasked')

            mr_convert_FA = pe.Node(interface=MRConvert(out_filename='fa_corrected.nii.gz', stride=[+1, +2, +3]),
                                    name='mr_convert_FA')
            mr_convert_FA_unmasked = pe.Node(
                interface=MRConvert(
                    out_filename='fa_corrected_unmasked.nii.gz', stride=[+1, +2, +3]),
                name='mr_convert_FA_unmasked')

            FA_noNaN = pe.Node(interface=cmp_fsl.MathsCommand(out_file='fa_corrected_nonan.nii.gz', nan2zeros=True),
                               name='FA_noNaN')
            FA_noNaN_unmasked = pe.Node(
                interface=cmp_fsl.MathsCommand(
                    out_file='fa_corrected_unmasked_nonan.nii.gz', nan2zeros=True),
                name='FA_noNaN_unmasked')

            flow.connect([
                (mr_convert, dwi2tensor, [('converted', 'in_file')]),
                (inputnode, dwi2tensor, [('target_mask', 'in_mask_file')]),
                (dwi2tensor, tensor2FA, [('tensor', 'in_file')]),
                (inputnode, tensor2FA, [('target_mask', 'in_mask')]),
                (tensor2FA, mr_convert_FA, [('out_fa', 'in_file')]),
                (mr_convert_FA, FA_noNaN, [('converted', 'in_file')])
            ])

            flow.connect([
                (mr_convert, dwi2tensor_unmasked, [('converted', 'in_file')]),
                (dwi2tensor_unmasked, tensor2FA_unmasked,
                 [('tensor', 'in_file')]),
                (tensor2FA_unmasked, mr_convert_FA_unmasked,
                 [('out_fa', 'in_file')]),
                (mr_convert_FA_unmasked, FA_noNaN_unmasked,
                 [('converted', 'in_file')])
            ])

            from nipype.interfaces.fsl.maths import ApplyMask
            b0_masking = pe.Node(interface=ApplyMask(
                out_file='b0_masked.nii.gz'), name='b0_masking')

            flow.connect([
                (mr_convert_b0, b0_masking, [('converted', 'in_file')]),
                (inputnode, b0_masking, [('target_mask', 'mask_file')])
            ])

            # [1.2] Linear registration of the DW data to the T1 data
            affine_registration = pe.Node(
                interface=ants.Registration(), name='linear_registration')
            affine_registration.inputs.collapse_output_transforms = True
            # affine_registration.inputs.initialize_transforms_per_stage=True
            affine_registration.inputs.initial_moving_transform_com = True
            affine_registration.inputs.output_transform_prefix = 'initial'
            affine_registration.inputs.num_threads = 8
            affine_registration.inputs.output_inverse_warped_image = True
            affine_registration.inputs.output_warped_image = 'linear_warped_image.nii.gz'
            affine_registration.inputs.sigma_units = ['vox'] * 2
            affine_registration.inputs.transforms = ['Rigid', 'Affine']

            affine_registration.inputs.interpolation = self.config.ants_interpolation
            if self.config.ants_interpolation == "BSpline":
                # (3,)
                affine_registration.inputs.interpolation_parameters = self.config.ants_bspline_interpolation_parameters
            elif self.config.ants_interpolation == "Gaussian":
                # (5,5,)
                affine_registration.inputs.interpolation_parameters = self.config.ants_gauss_interpolation_parameters
            elif self.config.ants_interpolation == "MultiLabel":
                # (5,5,)
                affine_registration.inputs.interpolation_parameters = self.config.ants_multilab_interpolation_parameters

            # affine_registration.inputs.terminal_output='file'
            affine_registration.inputs.winsorize_lower_quantile = self.config.ants_lower_quantile  # 0.005
            affine_registration.inputs.winsorize_upper_quantile = self.config.ants_upper_quantile  # 0.995
            affine_registration.inputs.convergence_threshold = [
                self.config.ants_convergence_thresh] * 2  # [1e-06]*2
            affine_registration.inputs.convergence_window_size = [
                self.config.ants_convergence_winsize] * 2  # [10]*2
            affine_registration.inputs.metric = [self.config.ants_linear_cost,
                                                 self.config.ants_linear_cost]  # ['MI','MI']
            affine_registration.inputs.metric_weight = [1.0] * 2
            affine_registration.inputs.number_of_iterations = [[1000, 500, 250, 100],
                                                               [1000, 500, 250, 100]]
            affine_registration.inputs.radius_or_number_of_bins = [32, 32]
            affine_registration.inputs.sampling_percentage = [self.config.ants_linear_sampling_perc,
                                                              self.config.ants_linear_sampling_perc]  # [0.25, 0.25]
            affine_registration.inputs.sampling_strategy = [self.config.ants_linear_sampling_strategy,
                                                            self.config.ants_linear_sampling_strategy]  # ['Regular','Regular']
            affine_registration.inputs.shrink_factors = [[8, 4, 2, 1]] * 2
            affine_registration.inputs.smoothing_sigmas = [[3, 2, 1, 0]] * 2
            affine_registration.inputs.transform_parameters = [(self.config.ants_linear_gradient_step,), (
                self.config.ants_linear_gradient_step,)]  # [(0.1,),(0.1,)]
            affine_registration.inputs.use_histogram_matching = True
            if self.config.ants_perform_syn:
                affine_registration.inputs.write_composite_transform = True
            affine_registration.inputs.verbose = True

            affine_registration.inputs.float = self.config.use_float_precision

            flow.connect([
                (b0_masking, affine_registration,
                 [('out_file', 'fixed_image')]),
                (inputnode, affine_registration, [('brain', 'moving_image')]),
                # (inputnode, affine_registration, [('T1','moving_image')]),
                # (mr_convert_b0, affine_registration, [('converted','fixed_image')]),
                # (inputnode, affine_registration, [('brain_mask','moving_image_mask')]),
                # (inputnode, affine_registration, [('target_mask','fixed_image_mask')])
            ])

            SyN_registration = pe.Node(
                interface=ants.Registration(), name='SyN_registration')

            if self.config.ants_perform_syn:

                SyN_registration.inputs.collapse_output_transforms = True
                SyN_registration.inputs.write_composite_transform = False
                SyN_registration.inputs.output_transform_prefix = 'final'
                # SyN_registration.inputs.initial_moving_transform_com=True
                SyN_registration.inputs.num_threads = 8
                SyN_registration.inputs.output_inverse_warped_image = True
                SyN_registration.inputs.output_warped_image = 'Syn_warped_image.nii.gz'
                SyN_registration.inputs.sigma_units = ['vox'] * 1
                SyN_registration.inputs.transforms = ['SyN']
                SyN_registration.inputs.restrict_deformation = [[0, 1, 0]]

                SyN_registration.inputs.interpolation = self.config.ants_interpolation  # 'BSpline'
                if self.config.ants_interpolation == "BSpline":
                    # (3,)
                    SyN_registration.inputs.interpolation_parameters = self.config.ants_bspline_interpolation_parameters
                elif self.config.ants_interpolation == "Gaussian":
                    # (5,5,)
                    SyN_registration.inputs.interpolation_parameters = self.config.ants_gauss_interpolation_parameters
                elif self.config.ants_interpolation == "MultiLabel":
                    # (5,5,)
                    SyN_registration.inputs.interpolation_parameters = self.config.ants_multilab_interpolation_parameters

                # SyN_registration.inputs.terminal_output='file'
                SyN_registration.inputs.winsorize_lower_quantile = self.config.ants_lower_quantile  # 0.005
                SyN_registration.inputs.winsorize_upper_quantile = self.config.ants_upper_quantile  # 0.995
                SyN_registration.inputs.convergence_threshold = [
                    self.config.ants_convergence_thresh] * 1  # [1e-06]*1
                SyN_registration.inputs.convergence_window_size = [
                    self.config.ants_convergence_winsize] * 1  # [10]*1
                SyN_registration.inputs.metric = [
                    self.config.ants_nonlinear_cost]  # ['CC']
                SyN_registration.inputs.metric_weight = [1.0] * 1
                SyN_registration.inputs.number_of_iterations = [[20]]
                SyN_registration.inputs.radius_or_number_of_bins = [4]
                SyN_registration.inputs.sampling_percentage = [1]
                SyN_registration.inputs.sampling_strategy = ['None']
                SyN_registration.inputs.shrink_factors = [[1]] * 1
                SyN_registration.inputs.smoothing_sigmas = [[0]] * 1
                SyN_registration.inputs.transform_parameters = [(self.config.ants_nonlinear_gradient_step,
                                                                 self.config.ants_nonlinear_update_field_variance,
                                                                 self.config.ants_nonlinear_total_field_variance)]  # [(0.1, 3.0, 0.0)]
                SyN_registration.inputs.use_histogram_matching = True
                SyN_registration.inputs.verbose = True

                SyN_registration.inputs.float = self.config.use_float_precision

                # SyN_registration = pe.Node(interface=ants.Registration(),name='SyN_registration')
                # SyN_registration.inputs.collapse_output_transforms=True
                # SyN_registration.inputs.write_composite_transform=False
                # SyN_registration.inputs.output_transform_prefix = 'final'
                # #SyN_registration.inputs.initial_moving_transform_com=True
                # SyN_registration.inputs.num_threads=8
                # SyN_registration.inputs.output_inverse_warped_image=True
                # SyN_registration.inputs.output_warped_image='Syn_warped_image.nii.gz'
                # SyN_registration.inputs.sigma_units=['vox']*1
                # SyN_registration.inputs.transforms=['SyN']
                # SyN_registration.inputs.restrict_deformation=[[1,1,0]]
                # SyN_registration.inputs.interpolation='BSpline'
                # SyN_registration.inputs.interpolation_parameters=(3,)
                # SyN_registration.inputs.terminal_output='file'
                # SyN_registration.inputs.winsorize_lower_quantile=0.005
                # SyN_registration.inputs.winsorize_upper_quantile=0.995
                # SyN_registration.inputs.convergence_threshold=[1e-06]*1
                # SyN_registration.inputs.convergence_window_size=[10]*1
                # SyN_registration.inputs.metric=['CC']
                # SyN_registration.inputs.metric_weight=[1.0]*1
                # SyN_registration.inputs.number_of_iterations=[[100, 70, 50, 20]]
                # SyN_registration.inputs.radius_or_number_of_bins=[4]
                # SyN_registration.inputs.sampling_percentage=[1]
                # SyN_registration.inputs.sampling_strategy=['None']
                # SyN_registration.inputs.shrink_factors=[[8, 4, 2, 1]]*1
                # SyN_registration.inputs.smoothing_sigmas=[[3, 2, 1, 0]]*1
                # SyN_registration.inputs.transform_parameters=[(0.1, 3.0, 0.0)]
                # SyN_registration.inputs.use_histogram_matching=True
                # SyN_registration.inputs.verbose = True

                # BSplineSyN_registration = pe.Node(interface=ants.Registration(),name='BSplineSyN_registration')
                # BSplineSyN_registration.inputs.collapse_output_transforms=True
                # BSplineSyN_registration.inputs.write_composite_transform=False
                # BSplineSyN_registration.inputs.output_transform_prefix = 'final'
                # #BSplineSyN_registration.inputs.initial_moving_transform_com=True
                # BSplineSyN_registration.inputs.num_threads=8
                # BSplineSyN_registration.inputs.output_inverse_warped_image=True
                # BSplineSyN_registration.inputs.output_warped_image='Syn_warped_image.nii.gz'
                # BSplineSyN_registration.inputs.sigma_units=['vox']*1
                # BSplineSyN_registration.inputs.transforms=['BSplineSyN']
                # BSplineSyN_registration.inputs.interpolation='BSpline'
                # BSplineSyN_registration.inputs.interpolation_parameters=(3,)
                # BSplineSyN_registration.inputs.terminal_output='file'
                # BSplineSyN_registration.inputs.winsorize_lower_quantile=0.005
                # BSplineSyN_registration.inputs.winsorize_upper_quantile=0.995
                # BSplineSyN_registration.inputs.convergence_threshold=[1e-06]*1
                # BSplineSyN_registration.inputs.convergence_window_size=[10]*1
                # BSplineSyN_registration.inputs.metric=['CC']
                # BSplineSyN_registration.inputs.metric_weight=[1.0]*1
                # BSplineSyN_registration.inputs.number_of_iterations=[[100, 70, 50, 20]]
                # BSplineSyN_registration.inputs.radius_or_number_of_bins=[4]
                # BSplineSyN_registration.inputs.sampling_percentage=[1]
                # BSplineSyN_registration.inputs.sampling_strategy=['None']
                # BSplineSyN_registration.inputs.shrink_factors=[[8, 4, 2, 1]]*1
                # BSplineSyN_registration.inputs.smoothing_sigmas=[[3, 2, 1, 0]]*1
                # BSplineSyN_registration.inputs.transform_parameters=[(0.25, 26, 0, 3)]
                # BSplineSyN_registration.inputs.use_histogram_matching=True
                # BSplineSyN_registration.inputs.verbose = True

                flow.connect([
                    (affine_registration, SyN_registration, [
                     ('composite_transform', 'initial_moving_transform')]),
                    (b0_masking, SyN_registration, [
                     ('out_file', 'fixed_image')]),
                    (inputnode, SyN_registration, [('brain', 'moving_image')])
                    # (inputnode, SyN_registration, [('T1','moving_image')]),
                    # (mr_convert_b0, SyN_registration, [('converted','fixed_image')]),
                    # (inputnode, SyN_registration, [('brain_mask','moving_image_mask')]),
                    # (inputnode, SyN_registration, [('target_mask','fixed_image_mask')])
                ])

            # multitransforms = pe.Node(interface=util.Merge(2),name='multitransforms')
            #
            # def convertList2Tuple(lists):
            #     print "******************************************",tuple(lists)
            #     return tuple(lists)
            #
            # flow.connect([
            #     (ants_registration,multitransforms,[('warp_transform','in1')]),
            #     (ants_registration,multitransforms,[('affine_transform','in2')])
            #     #(concatnode,mr_convert,[(('out',convertList2Tuple),'grad_fsl')])
            #     ])

            ants_applywarp_T1 = pe.Node(
                interface=ants.ApplyTransforms(
                    default_value=0, interpolation="Gaussian", out_postfix="_warped"),
                name="apply_warp_T1")
            ants_applywarp_brain = pe.Node(
                interface=ants.ApplyTransforms(
                    default_value=0, interpolation="Gaussian", out_postfix="_warped"),
                name="apply_warp_brain")
            ants_applywarp_brainmask = pe.Node(
                interface=ants.ApplyTransforms(
                    default_value=0, interpolation="NearestNeighbor", out_postfix="_warped"),
                name="apply_warp_brainmask")
            ants_applywarp_wm = pe.Node(
                interface=ants.ApplyTransforms(
                    default_value=0, interpolation="NearestNeighbor", out_postfix="_warped"),
                name="apply_warp_wm")
            ants_applywarp_rois = pe.Node(
                interface=MultipleANTsApplyTransforms(interpolation="NearestNeighbor", default_value=0,
                                                      out_postfix="_warped"), name="apply_warp_roivs")
            ants_applywarp_pves = pe.Node(
                interface=MultipleANTsApplyTransforms(
                    interpolation="Gaussian", default_value=0, out_postfix="_warped"),
                name="apply_warp_pves")

            ants_applywarp_5tt = pe.Node(
                interface=ants.ApplyTransforms(
                    default_value=0, interpolation="Gaussian", out_postfix="_warped"),
                name="apply_warp_5tt")
            ants_applywarp_5tt.inputs.dimension = 3
            ants_applywarp_5tt.inputs.input_image_type = 3
            ants_applywarp_5tt.inputs.float = True

            ants_applywarp_gmwmi = pe.Node(
                interface=ants.ApplyTransforms(
                    default_value=0, interpolation="Gaussian", out_postfix="_warped"),
                name="apply_warp_gmwmi")
            ants_applywarp_gmwmi.inputs.dimension = 3
            ants_applywarp_gmwmi.inputs.input_image_type = 3
            ants_applywarp_gmwmi.inputs.float = True

            def reverse_order_transforms(transforms):
                return transforms[::-1]

            def extract_affine_transform(transforms):
                for t in transforms:
                    if 'Affine' in t:
                        return t

            def extract_warp_field(transforms):
                for t in transforms:
                    if 'Warp' in t:
                        return t

            if self.config.ants_perform_syn:
                flow.connect([
                    (SyN_registration, ants_applywarp_T1,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_5tt,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_gmwmi,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_brain,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_brainmask,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_wm,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_rois,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, ants_applywarp_pves,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (SyN_registration, outputnode,
                     [(('forward_transforms', extract_affine_transform), 'affine_transform')]),
                    (SyN_registration, outputnode, [
                     (('forward_transforms', extract_warp_field), 'warp_field')]),
                ])
            else:
                flow.connect([
                    (affine_registration, ants_applywarp_T1,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_5tt,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_gmwmi,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_brain,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_brainmask,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_wm,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_rois,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, ants_applywarp_pves,
                     [(('forward_transforms', reverse_order_transforms), 'transforms')]),
                    (affine_registration, outputnode,
                     [(('forward_transforms', extract_affine_transform), 'affine_transform')]),
                ])

            flow.connect([
                (inputnode, ants_applywarp_T1, [('T1', 'input_image')]),
                (mr_convert_b0, ants_applywarp_T1, [
                 ('converted', 'reference_image')]),
                # (multitransforms, ants_applywarp_T1, [('out','transforms')]),
                (ants_applywarp_T1, outputnode, [
                 ('output_image', 'T1_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_5tt, [('act_5TT', 'input_image')]),
                (mr_convert_b0, ants_applywarp_5tt, [
                 ('converted', 'reference_image')]),
                # (multitransforms, ants_applywarp_T1, [('out','transforms')]),
                (ants_applywarp_5tt, outputnode, [
                 ('output_image', 'act_5tt_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_gmwmi, [('gmwmi', 'input_image')]),
                (mr_convert_b0, ants_applywarp_gmwmi,
                 [('converted', 'reference_image')]),
                # (multitransforms, ants_applywarp_T1, [('out','transforms')]),
                (ants_applywarp_gmwmi, outputnode, [
                 ('output_image', 'gmwmi_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_brain, [('brain', 'input_image')]),
                (mr_convert_b0, ants_applywarp_brain,
                 [('converted', 'reference_image')]),
                # (multitransforms, ants_applywarp_brain, [('out','transforms')]),
                (ants_applywarp_brain, outputnode, [
                 ('output_image', 'brain_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_brainmask,
                 [('brain_mask', 'input_image')]),
                (mr_convert_b0, ants_applywarp_brainmask,
                 [('converted', 'reference_image')]),
                # (multitransforms, ants_applywarp_brainmask, [('out','transforms')]),
                (ants_applywarp_brainmask, outputnode, [
                 ('output_image', 'brain_mask_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_wm, [('wm_mask', 'input_image')]),
                (mr_convert_b0, ants_applywarp_wm, [
                 ('converted', 'reference_image')]),
                # (multitransforms, ants_applywarp_wm, [('out','transforms')]),
                (ants_applywarp_wm, outputnode, [
                 ('output_image', 'wm_mask_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_rois, [
                 ('roi_volumes', 'input_images')]),
                (mr_convert_b0, ants_applywarp_rois,
                 [('converted', 'reference_image')]),
                (ants_applywarp_rois, outputnode, [
                 ('output_images', 'roi_volumes_registered_crop')]),
            ])

            flow.connect([
                (inputnode, ants_applywarp_pves, [
                 ('partial_volume_files', 'input_images')]),
                (mr_convert_b0, ants_applywarp_pves,
                 [('converted', 'reference_image')]),
                (ants_applywarp_pves, outputnode, [
                 ('output_images', 'partial_volumes_registered_crop')]),
            ])

            flow.connect([
                # (inputnode, outputnode, [('roi_volumes','roi_volumes_registered_crop')]),
                (inputnode, outputnode, [('target', 'target_epicorrected')]),
            ])

        if self.config.registration_mode == 'FSL (Linear)':
            fsl_flirt = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-TARGET.nii.gz', out_matrix_file='T1-TO-TARGET.mat'),
                                name="linear_registration")
            fsl_flirt.inputs.uses_qform = self.config.uses_qform
            fsl_flirt.inputs.dof = self.config.dof
            fsl_flirt.inputs.cost = self.config.fsl_cost
            fsl_flirt.inputs.no_search = self.config.no_search
            fsl_flirt.inputs.args = self.config.flirt_args

            fsl_applyxfm_wm = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="nearestneighbour", out_file="wm_mask_registered.nii.gz"),
                name="apply_registration_wm")
            fsl_applyxfm_rois = pe.Node(
                interface=ApplymultipleXfm(), name="apply_registration_roivs")

            # TODO apply xfm to gmwmi / 5tt and pves

            flow.connect([
                (inputnode, fsl_applyxfm_wm, [('wm_mask', 'in_file')]),
                (fsl_flirt, outputnode, [("out_file", "T1_registered_crop")]),
                (fsl_flirt, fsl_applyxfm_wm, [
                 ('out_matrix_file', 'in_matrix_file')]),
                (fsl_applyxfm_wm, outputnode, [
                 ('out_file', 'wm_mask_registered_crop')]),
                (inputnode, fsl_applyxfm_rois, [('roi_volumes', 'in_files')]),
                (fsl_flirt, fsl_applyxfm_rois, [
                 ('out_matrix_file', 'xfm_file')]),
                (fsl_flirt, outputnode, [
                 ('out_matrix_file', 'affine_transform')]),
                (fsl_applyxfm_rois, outputnode, [
                 ('out_files', 'roi_volumes_registered_crop')])
            ])

            if self.config.pipeline == "fMRI":
                flow.connect([
                    (T1_bet, fsl_flirt, [('out_file', 'in_file')]),
                    (fmri_bet, fsl_flirt, [('out_file', 'reference')]),
                    (fmri_bet, fsl_applyxfm_wm, [('out_file', 'reference')]),
                    (fmri_bet, fsl_applyxfm_rois, [('out_file', 'reference')])
                ])
                fsl_applyxfm_eroded_wm = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, interp="nearestneighbour",
                                                                        out_file="eroded_wm_registered.nii.gz"),
                                                 name="apply_registration_wm_eroded")
                if self.config.apply_to_eroded_csf:
                    fsl_applyxfm_eroded_csf = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, interp="nearestneighbour",
                                                                             out_file="eroded_csf_registered.nii.gz"),
                                                      name="apply_registration_csf_eroded")
                    flow.connect([
                        (inputnode, fsl_applyxfm_eroded_csf,
                         [('eroded_csf', 'in_file')]),
                        (fmri_bet, fsl_applyxfm_eroded_csf,
                         [('out_file', 'reference')]),
                        (fsl_flirt, fsl_applyxfm_eroded_csf, [
                         ('out_matrix_file', 'in_matrix_file')]),
                        (fsl_applyxfm_eroded_csf, outputnode, [
                         ('out_file', 'eroded_csf_registered_crop')])
                    ])
                if self.config.apply_to_eroded_brain:
                    fsl_applyxfm_eroded_brain = pe.Node(
                        interface=fsl.ApplyXFM(apply_xfm=True, interp="nearestneighbour",
                                               out_file="eroded_brain_registered.nii.gz"),
                        name="apply_registration_brain_eroded")
                    flow.connect([
                        (inputnode, fsl_applyxfm_eroded_brain,
                         [('eroded_brain', 'in_file')]),
                        (fmri_bet, fsl_applyxfm_eroded_brain,
                         [('out_file', 'reference')]),
                        (fsl_flirt, fsl_applyxfm_eroded_brain, [
                         ('out_matrix_file', 'in_matrix_file')]),
                        (fsl_applyxfm_eroded_brain, outputnode, [
                         ('out_file', 'eroded_brain_registered_crop')])
                    ])
                flow.connect([
                    (inputnode, fsl_applyxfm_eroded_wm,
                     [('eroded_wm', 'in_file')]),
                    (fmri_bet, fsl_applyxfm_eroded_wm,
                     [('out_file', 'reference')]),
                    (fsl_flirt, fsl_applyxfm_eroded_wm, [
                     ('out_matrix_file', 'in_matrix_file')]),
                    (fsl_applyxfm_eroded_wm, outputnode, [
                     ('out_file', 'eroded_wm_registered_crop')])
                ])
            else:
                flow.connect([
                    (inputnode, fsl_flirt, [('T1', 'in_file')]),
                    (fs_mriconvert, fsl_flirt, [('out_file', 'reference')]),
                    (fs_mriconvert, fsl_applyxfm_wm,
                     [('out_file', 'reference')]),
                    (fs_mriconvert, fsl_applyxfm_rois,
                     [('out_file', 'reference')]),
                ])

        if self.config.pipeline == "fMRI" and self.config.registration_mode == 'BBregister (FS)':

            fs_bbregister = pe.Node(interface=cmp_fs.BBRegister(
                out_fsl_file="target-TO-orig.mat"), name="bbregister")
            fs_bbregister.inputs.init = self.config.init
            fs_bbregister.inputs.contrast_type = self.config.contrast_type
            fs_bbregister.inputs.subjects_dir = self.fs_subjects_dir
            fs_bbregister.inputs.subject_id = self.fs_subject_id

            fsl_invertxfm = pe.Node(interface=fsl.ConvertXFM(
                invert_xfm=True), name="fsl_invertxfm")

            fs_source = pe.Node(
                interface=fs.preprocess.FreeSurferSource(), name="get_fs_files")
            fs_source.inputs.subjects_dir = self.fs_subjects_dir
            fs_source.inputs.subject_id = self.fs_subject_id

            fs_tkregister2 = pe.Node(interface=cmp_fs.Tkregister2(
                regheader=True, noedit=True), name="fs_tkregister2")
            fs_tkregister2.inputs.reg_out = 'T1-TO-orig.dat'
            fs_tkregister2.inputs.fslreg_out = 'T1-TO-orig.mat'
            fs_tkregister2.inputs.subjects_dir = self.fs_subjects_dir
            fs_tkregister2.inputs.subject_id = self.fs_subject_id

            fsl_concatxfm = pe.Node(interface=fsl.ConvertXFM(
                concat_xfm=True), name="fsl_concatxfm")

            fsl_applyxfm = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, out_file="T1-TO-TARGET.nii.gz"),
                                   name="linear_registration")
            fsl_applyxfm_wm = pe.Node(
                interface=fsl.ApplyXFM(
                    apply_xfm=True, interp="nearestneighbour", out_file="wm_mask_registered.nii.gz"),
                name="apply_registration_wm")
            fsl_applyxfm_rois = pe.Node(
                interface=ApplymultipleXfm(), name="apply_registration_roivs")

            flow.connect([
                (fs_bbregister, fsl_invertxfm, [('out_fsl_file', 'in_file')]),
                (fsl_invertxfm, fsl_concatxfm, [('out_file', 'in_file2')]),
                (fs_source, fs_tkregister2, [
                 ("orig", "target_file"), ("rawavg", "in_file")]),
                (fs_tkregister2, fsl_concatxfm, [
                 ('fslregout_file', 'in_file')]),
                # (inputnode, fsl_applyxfm, [('T1', 'in_file')]),
                (T1_bet, fsl_applyxfm, [('out_file', 'in_file')]),
                (fsl_concatxfm, fsl_applyxfm, [
                 ('out_file', 'in_matrix_file')]),
                (fsl_applyxfm, outputnode, [
                 ("out_file", "T1_registered_crop")]),
                (inputnode, fsl_applyxfm_wm, [('wm_mask', 'in_file')]),
                (fsl_concatxfm, fsl_applyxfm_wm, [
                 ('out_file', 'in_matrix_file')]),
                (fsl_applyxfm_wm, outputnode, [
                 ('out_file', 'wm_mask_registered_crop')]),
                (inputnode, fsl_applyxfm_rois, [('roi_volumes', 'in_files')]),
                (fsl_concatxfm, fsl_applyxfm_rois, [('out_file', 'xfm_file')]),
                (fsl_applyxfm_rois, outputnode, [
                 ('out_files', 'roi_volumes_registered_crop')])
            ])

            flow.connect([
                #(inputnode, fs_bbregister, [('target', 'source_file')]),
                (fmri_bet, fs_bbregister, [('out_file', 'source_file')]),
                (inputnode, fsl_applyxfm, [('target', 'reference')]),
                (inputnode, fsl_applyxfm_wm, [('target', 'reference')]),
                (inputnode, fsl_applyxfm_rois, [('target', 'reference')]),
            ])
            fsl_applyxfm_eroded_wm = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, interp="nearestneighbour",
                                                                    out_file="eroded_wm_registered.nii.gz"),
                                             name="apply_registration_wm_eroded")
            if self.config.apply_to_eroded_csf:
                fsl_applyxfm_eroded_csf = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, interp="nearestneighbour",
                                                                         out_file="eroded_csf_registered.nii.gz"),
                                                  name="apply_registration_csf_eroded")
                flow.connect([
                    (inputnode, fsl_applyxfm_eroded_csf,
                     [('eroded_csf', 'in_file')]),
                    (inputnode, fsl_applyxfm_eroded_csf,
                     [('target', 'reference')]),
                    (fsl_concatxfm, fsl_applyxfm_eroded_csf,
                     [('out_file', 'in_matrix_file')]),
                    (fsl_applyxfm_eroded_csf, outputnode, [
                     ('out_file', 'eroded_csf_registered_crop')])
                ])
            if self.config.apply_to_eroded_brain:
                fsl_applyxfm_eroded_brain = pe.Node(
                    interface=fsl.ApplyXFM(apply_xfm=True, interp="nearestneighbour",
                                           out_file="eroded_brain_registered.nii.gz"),
                    name="apply_registration_brain_eroded")
                flow.connect([
                    (inputnode, fsl_applyxfm_eroded_brain,
                     [('eroded_brain', 'in_file')]),
                    (inputnode, fsl_applyxfm_eroded_brain,
                     [('target', 'reference')]),
                    (fsl_concatxfm, fsl_applyxfm_eroded_brain,
                     [('out_file', 'in_matrix_file')]),
                    (fsl_applyxfm_eroded_brain, outputnode, [
                     ('out_file', 'eroded_brain_registered_crop')])
                ])
            flow.connect([
                (inputnode, fsl_applyxfm_eroded_wm,
                 [('eroded_wm', 'in_file')]),
                (inputnode, fsl_applyxfm_eroded_wm, [('target', 'reference')]),
                (fsl_concatxfm, fsl_applyxfm_eroded_wm,
                 [('out_file', 'in_matrix_file')]),
                (fsl_applyxfm_eroded_wm, outputnode, [
                 ('out_file', 'eroded_wm_registered_crop')])
            ])

        # if self.config.registration_mode == 'FSL (Nonlinear)':
        #     # [SUB-STEP 1] LINEAR register "T2" onto "Target_resampled
        #     # [1.1] linear register "T1" onto "T2"
        #     fsl_flirt_1 = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-T2.nii.gz',out_matrix_file='T1-TO-T2.mat'),name="t1tot2_lin_registration")
        #     fsl_flirt_1.inputs.dof = 6
        #     fsl_flirt_1.inputs.cost = "mutualinfo"
        #     fsl_flirt_1.inputs.no_search = True
        #     #[1.2] -> linear register "T2" onto "target_resampled"
        #     fsl_flirt_2 = pe.Node(interface=fsl.FLIRT(out_file='T2-TO-TARGET.nii.gz',out_matrix_file='T2-TO-TARGET.mat'),name="t2totarget_lin_registration")
        #     fsl_flirt_2.inputs.dof = 12
        #     fsl_flirt_2.inputs.cost = "normmi"
        #     fsl_flirt_2.inputs.no_search = True
        #     #[1.3] -> apply the linear registration "T1" --> "target" (for comparison)
        #     fsl_concatxfm = pe.Node(interface=fsl.ConvertXFM(concat_xfm=True),name="fsl_concatxfm")
        #     fsl_applyxfm = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True, interp="sinc",out_file='T1-TO-target.nii.gz',out_matrix_file='T1-TO-TARGET.mat'),name="linear_registration")
        #     #"[SUB-STEP 2] Create BINARY MASKS for nonlinear registration"
        #     # [2.1] -> create a T2 brain mask
        #     fsl_bet_1 = pe.Node(interface=fsl.BET(out_file='T2-brain',mask=True,no_output=True,robust=True),name="t2_brain_mask")
        #     fsl_bet_1.inputs.frac = 0.35
        #     fsl_bet_1.inputs.vertical_gradient = 0.15
        #     #[2.2] -> create a DSI_target brain mask
        #     fsl_bet_2 = pe.Node(interface=fsl.BET(out_file='target-brain',mask=True,no_output=True,robust=True),name="target_brain_mask")
        #     fsl_bet_2.inputs.frac = 0.2
        #     fsl_bet_2.inputs.vertical_gradient = 0.2
        #     # [SUB-STEP 3] NONLINEAR register "T2" onto "target_resampled"
        #     # [3.1] 'Started FNIRT to find 'T2 --> target' nonlinear transformation at
        #     fsl_fnirt = pe.Node(interface=fsl.FNIRT(field_file='T2-TO-target_warp.nii.gz'),name="t2totarget_nlin_registration")
        #     fsl_fnirt.inputs.subsampling_scheme = [8,4,2,2]
        #     fsl_fnirt.inputs.max_nonlin_iter = [5,5,5,5]
        #     fsl_fnirt.inputs.regularization_lambda = [240,120,90,30]
        #     fsl_fnirt.inputs.spline_order = 3
        #     fsl_fnirt.inputs.apply_inmask = [0,0,1,1]
        #     fsl_fnirt.inputs.apply_refmask = [0,0,1,1]
        #     #[3.2] -> apply the warp found for "T2" also onto "T1"
        #     fsl_applywarp = pe.Node(interface=fsl.ApplyWarp(out_file='T1_warped.nii.gz'),name="nonlinear_registration")
        #     fsl_applywarp_wm = pe.Node(interface=fsl.ApplyWarp(interp="nn",out_file="wm_mask_registered.nii.gz"),name="apply_registration_wm")
        #     fsl_applywarp_rois = pe.Node(interface=Applynlinmultiplewarps(),name="apply_registration_roivs") # TO FIX: Applynlinmultiplewarps() done because applying MapNode to fsl.ApplyWarp crashes
        #     #fsl_applywarp_rois = pe.MapNode(interface=fsl.ApplyWarp(interp="nn"),name="apply_registration_roivs",iterfield=["in_file"])
        #
        #     flow.connect([
        #             (inputnode,fsl_flirt_1,[('T1','in_file'),('T2','reference')]),
        #             (inputnode,fsl_flirt_2,[('T2','in_file')]),
        #             (fsl_flirt_1,fsl_concatxfm,[('out_matrix_file','in_file')]),
        #             (fsl_flirt_2,fsl_concatxfm,[('out_matrix_file','in_file2')]),
        #             (inputnode,fsl_applyxfm,[('T1','in_file')]),
        #             (fsl_concatxfm,fsl_applyxfm,[('out_file','in_matrix_file')]),
        #             (inputnode,fsl_bet_1,[('T2','in_file')]),
        #             (inputnode,fsl_fnirt,[('T2','in_file')]),
        #             (fsl_flirt_2,fsl_fnirt,[('out_matrix_file','affine_file')]),
        #             (fsl_bet_1,fsl_fnirt,[('mask_file','inmask_file')]),
        #             (fsl_bet_2,fsl_fnirt,[('mask_file','refmask_file')]),
        #             (inputnode,fsl_applywarp,[('T1','in_file')]),
        #             (fsl_flirt_1,fsl_applywarp,[('out_matrix_file','premat')]),
        #             (fsl_fnirt,fsl_applywarp,[('field_file','field_file')]),
        #             (inputnode, fsl_applywarp_wm, [('wm_mask','in_file')]),
        #             (fsl_flirt_1, fsl_applywarp_wm, [('out_matrix_file','premat')]),
        #             (fsl_fnirt,fsl_applywarp_wm,[('field_file','field_file')]),
        #             (fsl_applywarp_wm, outputnode, [('out_file','wm_mask_registered_crop')]),
        #             (inputnode, fsl_applywarp_rois, [('roi_volumes','in_files')]),
        #             (fsl_flirt_1, fsl_applywarp_rois, [('out_matrix_file','premat_file')]),
        #             (fsl_fnirt,fsl_applywarp_rois,[('field_file','field_file')]),
        #             (fsl_applywarp_rois, outputnode, [('warped_files','roi_volumes_registered_crop')])
        #             ])
        #     if self.config.pipeline == "fMRI":
        #         flow.connect([
        #                     (inputnode,fsl_flirt_2,[('target','reference')]),
        #                     (inputnode,fsl_applyxfm,[('target','reference')]),
        #                     (inputnode,fsl_bet_2,[('target','in_file')]),
        #                     (inputnode,fsl_fnirt,[('target','ref_file')]),
        #                     (inputnode,fsl_applywarp,[('target','ref_file')]),
        #                     (inputnode, fsl_applywarp_wm, [('target','ref_file')]),
        #                     (inputnode, fsl_applywarp_rois, [('target','ref_file')]),
        #                     ])
        #         fsl_applywarp_eroded_wm = pe.Node(interface=fsl.ApplyWarp(interp="nn",out_file="eroded_wm_registered.nii.gz"),name="apply_registration_eroded_wm")
        #         if self.config.apply_to_eroded_csf:
        #             fsl_applywarp_eroded_csf = pe.Node(interface=fsl.ApplyWarp(interp="nn",out_file="eroded_csf_registered.nii.gz"),name="apply_registration_eroded_csf")
        #             flow.connect([
        #                           (inputnode, fsl_applywarp_eroded_csf, [('eroded_csf','in_file')]),
        #                           (inputnode, fsl_applywarp_eroded_csf, [('target','ref_file')]),
        #                           (fsl_flirt_1, fsl_applywarp_eroded_csf, [('out_matrix_file','premat')]),
        #                           (fsl_fnirt,fsl_applywarp_eroded_csf,[('field_file','field_file')]),
        #                           (fsl_applywarp_eroded_csf, outputnode, [('out_file','eroded_csf_registered_crop')])
        #                         ])
        #         if self.config.apply_to_eroded_brain:
        #             fsl_applywarp_eroded_brain = pe.Node(interface=fsl.ApplyWarp(interp="nn",out_file="eroded_brain_registered.nii.gz"),name="apply_registration_eroded_brain")
        #             flow.connect([
        #                           (inputnode, fsl_applywarp_eroded_brain, [('eroded_brain','in_file')]),
        #                           (inputnode, fsl_applywarp_eroded_brain, [('target','ref_file')]),
        #                           (fsl_flirt_1, fsl_applywarp_eroded_brain, [('out_matrix_file','premat')]),
        #                           (fsl_fnirt,fsl_applywarp_eroded_brain,[('field_file','field_file')]),
        #                           (fsl_applywarp_eroded_brain, outputnode, [('out_file','eroded_brain_registered_crop')])
        #                         ])
        #         flow.connect([
        #                     (inputnode, fsl_applywarp_eroded_wm, [('eroded_wm','in_file')]),
        #                     (inputnode, fsl_applywarp_eroded_wm, [('target','ref_file')]),
        #                     (fsl_flirt_1, fsl_applywarp_eroded_wm, [('out_matrix_file','premat')]),
        #                     (fsl_fnirt,fsl_applywarp_eroded_wm,[('field_file','field_file')]),
        #                     (fsl_applywarp_eroded_wm, outputnode, [('out_file','eroded_wm_registered_crop')])
        #                     ])
        #     else:
        #         flow.connect([
        #                     (fs_mriconvert,fsl_flirt_2,[('out_file','reference')]),
        #                     (fs_mriconvert,fsl_applyxfm,[('out_file','reference')]),
        #                     (fs_mriconvert,fsl_bet_2,[('out_file','in_file')]),
        #                     (fs_mriconvert,fsl_fnirt,[('out_file','ref_file')]),
        #                     (fs_mriconvert,fsl_applywarp,[('out_file','ref_file')]),
        #                     (fs_mriconvert, fsl_applywarp_wm, [('out_file','ref_file')]),
        #                     (fs_mriconvert, fsl_applywarp_rois, [('out_file','ref_file')]),
        #                     ])

    def define_inspect_outputs(self):
        # print("stage_dir : %s" % self.stage_dir)
        if self.config.pipeline == "Diffusion":
            dwi_sinker_dir = os.path.join(os.path.dirname(self.stage_dir), 'diffusion_sinker')
            dwi_sinker_report = os.path.join(dwi_sinker_dir, '_report', 'report.rst')

            if os.path.exists(dwi_sinker_report):
                print(self.output_dir)
                dwi_outputs = get_pipeline_dictionary_outputs(dwi_sinker_report, self.output_dir)

                tool= self.config.registration_mode
                ref = dwi_outputs['dwi.@bdiffusion_reg_crop']
                out = dwi_outputs['anat.@brain_reg_crop']

                print(ref)
                print(out)

                if (os.path.exists(ref) and os.path.exists(out)):
                    print('reg 1')
                    self.inspect_outputs_dict['Linear T1-to-b0 (%s)' % tool] = ['fsleyes', '-sdefault',
                                                                    ref,
                                                                    out, '-cm', "copper",
                                                                    '-a', '50']

                out = dwi_outputs['anat.@act_5tt_reg_crop']
                if (os.path.exists(ref) and os.path.exists(out)):
                    self.inspect_outputs_dict['Wrapped 5TT-to-b0 (%s)' % tool] = ['fsleyes', '-sdefault',
                                                                      ref,
                                                                      out,
                                                                      '-cm', "hot", '-a', '50']

                out = dwi_outputs['anat.@gmwmi_reg_crop']
                if (os.path.exists(ref) and os.path.exists(out)):
                    self.inspect_outputs_dict['Wrapped GMWMi-to-b0 (%s)' % tool] = ['fsleyes', '-sdefault',
                                                                      ref,
                                                                      out,
                                                                      '-cm', "hot", '-a', '50']

                field = dwi_outputs['xfm.@warp_field']
                if os.path.exists(field):
                    self.inspect_outputs_dict['Deformation field (%s)' % tool] = ['fsleyes', '-sdefault',
                                                                      field]

                if (isinstance(dwi_outputs['anat.@roivs_reg_crop'], str) and os.path.exists(dwi_outputs['anat.@roivs_reg_crop'])):
                    roiv = dwi_outputs['anat.@roivs_reg_crop']
                    if os.path.exists(roiv):
                        self.inspect_outputs_dict['%s-to-b0 (%s)' % (os.path.basename(roiv), tool)] = [
                            'fsleyes', '-sdefault', ref, roiv, '-cm', 'random', '-a', '50']
                else:
                    for roi_output in dwi_outputs['anat.@roivs_reg_crop']:
                        roiv = roi_output
                        if os.path.exists(roiv):
                            self.inspect_outputs_dict['%s-to-b0 (%s)' % (os.path.basename(roiv), tool)] = [
                            'fsleyes', '-sdefault', ref, roiv, '-cm', 'random', '-a', '50']

                if isinstance(dwi_outputs['anat.@pves_reg_crop'], str):
                    pves = dwi_outputs['anat.@pves_reg_crop']
                    if os.path.exists(pves):
                        self.inspect_outputs_dict['%s-to-b0 (%s)' % (os.path.basename(pves), tool)] = [
                            'fsleyes', '-sdefault', ref, pves, '-cm', 'hot', '-a', '50']
                else:
                    for pve_output in dwi_outputs['anat.@pves_reg_crop']:
                        pves = pve_output
                        if os.path.exists(pves):
                            self.inspect_outputs_dict['%s-to-b0 (%s)' % (os.path.basename(pves), tool)] = [
                                'fsleyes', '-sdefault', ref, pves, '-cm', 'hot', '-a', '50']

        else:
            func_sinker_dir = os.path.join(os.path.dirname(self.stage_dir), 'bold_sinker')
            func_sinker_report = os.path.join(func_sinker_dir, '_report', 'report.rst')

            print('fMRI registration (tool %s)' % self.config.registration_mode)

            if os.path.exists(func_sinker_report):

                func_outputs = get_pipeline_dictionary_outputs(func_sinker_report, self.output_dir)

                tool= self.config.registration_mode

                if isinstance(func_outputs['anat.@registered_roi_volumes'], str):
                    ref = func_outputs['func.@mean_vol']
                    out = func_outputs['anat.@registered_roi_volumes']
                    if (os.path.exists(ref) and os.path.exists(out)):
                        self.inspect_outputs_dict['Mean-fMRI/%s (%s)' % (os.path.basename(out), tool)] = [
                            'fsleyes', '-sdefault', ref, out, '-cm', 'random', '-a', '50']
                else:
                    for roi_output in func_outputs['anat.@registered_roi_volumes']:
                        ref = func_outputs['func.@mean_vol']
                        out = roi_output
                        if (os.path.exists(ref) and os.path.exists(out)):
                            self.inspect_outputs_dict['Mean-fMRI/%s (%s)' % (os.path.basename(out), tool)] = [
                            'fsleyes', '-sdefault', ref, out, '-cm', 'random', '-a', '50']

        self.inspect_outputs = sorted([key for key in list(self.inspect_outputs_dict.keys())],
                                      key=str.lower)
        print(self.inspect_outputs)

    def has_run(self):

        if self.config.registration_mode == 'ANTs':
            if self.config.ants_perform_syn:
                return os.path.exists(os.path.join(self.stage_dir, "SyN_registration", "result_SyN_registration.pklz"))
            else:
                return os.path.exists(
                    os.path.join(self.stage_dir, "linear_registration", "result_linear_registration.pklz"))

        elif self.config.registration_mode != 'Nonlinear (FSL)':
            return os.path.exists(
                os.path.join(self.stage_dir, "linear_registration", "result_linear_registration.pklz"))

        elif self.config.registration_mode == 'Nonlinear (FSL)':
            return os.path.exists(
                os.path.join(self.stage_dir, "nonlinear_registration", "result_nonlinear_registration.pklz"))
