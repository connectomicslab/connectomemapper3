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

# Own imports
from cmp.bidsappmanager.stages.common import Stage


class RegistrationConfig(HasTraits):
    # Pipeline mode
    pipeline = Enum(["Diffusion","fMRI"])

    # Registration selection
    registration_mode = Str('ANTs')#Str('FSL')
    registration_mode_trait = List(['FSL','ANTs']) #,'BBregister (FS)'])
    diffusion_imaging_model = Str

    # ANTS
    ants_interpolation = Enum('Linear',['Linear', 'NearestNeighbor', 'CosineWindowedSinc', 'WelchWindowedSinc','HammingWindowedSinc', 'LanczosWindowedSinc', 'BSpline', 'MultiLabel', 'Gaussian'])
    ants_bspline_interpolation_parameters = Tuple(Int(3))
    ants_gauss_interpolation_parameters = Tuple(Float(5),Float(5))
    ants_multilab_interpolation_parameters = Tuple(Float(5),Float(5))
    ants_lower_quantile = Float(0.005)
    ants_upper_quantile = Float(0.995)
    ants_convergence_thresh = Float(1e-06)
    ants_convergence_winsize = Int(10)

    ants_linear_gradient_step = Float(0.1)
    ants_linear_cost = Enum('MI',['CC', 'MeanSquares', 'Demons', 'GC', 'MI', 'Mattes'])
    ants_linear_sampling_perc = Float(0.25)
    ants_linear_sampling_strategy = Enum('Regular',['None', 'Regular', 'Random'])

    ants_perform_syn = Bool(True)
    ants_nonlinear_gradient_step = Float(0.1)
    ants_nonlinear_cost = Enum('CC',['CC', 'MeanSquares', 'Demons', 'GC', 'MI', 'Mattes'])
    ants_nonlinear_update_field_variance = Float(3.0)
    ants_nonlinear_total_field_variance = Float(0.0)

    # FLIRT
    flirt_args = Str
    uses_qform = Bool(True)
    dof = Int(6)
    fsl_cost = Enum('normmi',['mutualinfo','corratio','normcorr','normmi','leastsq','labeldiff'])
    no_search = Bool(True)

    # BBRegister
    init = Enum('header',['spm','fsl','header'])
    contrast_type = Enum('dti',['t1','t2','dti'])

    # Apply transform
    apply_to_eroded_wm = Bool(True)
    apply_to_eroded_csf = Bool(True)
    apply_to_eroded_brain = Bool(False)

    traits_view = View(
                        Item('registration_mode',editor=EnumEditor(name='registration_mode_trait')),
                        Group(Item('uses_qform'),
                              Item('dof'),
                              Item('fsl_cost',label="FLIRT metric"),
                              Item('no_search'),
                              Item('flirt_args'),
                            label='FSL registration settings', show_border=True,visible_when='registration_mode=="FSL"'),
                        Group(Item('uses_qform'),
                              Item('dof'),
                              Item('fsl_cost',label="FLIRT metric"),
                              Item('no_search'),
                              Item('flirt_args'),
                            label='FSL registration settings', show_border=True,visible_when='registration_mode=="Linear (FSL))"'),
                        Group(
                            Group(
                                HGroup(
                                    Item('ants_interpolation',label="Interpolation"),
                                    Item('ants_bspline_interpolation_parameters', label="Parameters", visible_when='ants_interpolation=="BSpline"'),
                                    Item('ants_gauss_interpolation_parameters', label="Parameters", visible_when='ants_interpolation=="Gaussian"'),
                                    Item('ants_multilab_interpolation_parameters', label="Parameters", visible_when='ants_interpolation=="MultiLabel"')
                                ),
                                HGroup(
                                    Item('ants_lower_quantile',label='winsorize lower quantile'),
                                    Item('ants_upper_quantile',label='winsorize upper quantile')
                                ),
                                HGroup(
                                    Item('ants_convergence_thresh',label='Convergence threshold'),
                                    Item('ants_convergence_winsize',label='Convergence window size')
                                ),
                                label="General",show_border=False
                                ),
                            Group(
                                Item('ants_linear_cost', label="Metric"),
                                Item('ants_linear_gradient_step', label="Gradient step size"),
                                HGroup(
                                    Item('ants_linear_sampling_strategy', label="Sampling strategy"),
                                    Item('ants_linear_sampling_perc', label="Sampling percentage", visible_when='ants_linear_sampling_strategy!="None"' )
                                    ),
                                Item('ants_linear_gradient_step', label="Gradient step size"),
                                label="Rigid + Affine",show_border=False
                                ),
                            Item('ants_perform_syn',label='Symmetric diffeomorphic SyN registration'),
                            Group(
                                Item('ants_nonlinear_cost', label="Metric"),
                                Item('ants_nonlinear_gradient_step', label="Gradient step size"),
                                Item('ants_nonlinear_update_field_variance', label="Update field variance in voxel space"),
                                Item('ants_nonlinear_total_field_variance', label="Total field variance in voxel space"),
                                label="SyN (symmetric diffeomorphic registration)",show_border=False, visible_when='ants_perform_syn'
                                ),
                            label='ANTs registration settings',show_border=True,visible_when='registration_mode=="ANTs"'
                            ),
                        Group('init','contrast_type',
                              label='BBregister registration settings', show_border=True,visible_when='registration_mode=="BBregister (FS)"'),
                       kind='live',
                       )


class RegistrationStage(Stage):

    def __init__(self,pipeline_mode):
        self.name = 'registration_stage'
        self.config = RegistrationConfig()
        self.config.pipeline = pipeline_mode
        self.inputs = ["T1","act_5TT","gmwmi","target","T2","subjects_dir","subject_id","wm_mask","partial_volume_files","roi_volumes","brain","brain_mask","brain_mask_full","target_mask","bvecs","bvals"]
        self.outputs = ["T1_registered_crop", "act_5tt_registered_crop", "gmwmi_registered_crop", "brain_registered_crop", "brain_mask_registered_crop", "wm_mask_registered_crop","partial_volumes_registered_crop","roi_volumes_registered_crop","target_epicorrected","grad","bvecs","bvals"]
        if self.config.pipeline == "fMRI":
            self.inputs = self.inputs + ["eroded_csf","eroded_wm","eroded_brain"]
            self.outputs = self.outputs + ["eroded_wm_registered_crop","eroded_csf_registered_crop","eroded_brain_registered_crop"]

    def define_inspect_outputs(self):
        print "stage_dir : %s" % self.stage_dir
        if self.config.pipeline == "Diffusion":
            target_path = os.path.join(self.stage_dir,"target_resample","result_target_resample.pklz")
            reg_results_path = os.path.join(self.stage_dir,"linear_registration","result_linear_registration.pklz")
            warpedROIVs_results_path = os.path.join(self.stage_dir,"apply_warp_roivs","result_apply_warp_roivs.pklz")
            warped5TT_results_path = os.path.join(self.stage_dir,"apply_warp_5tt","result_apply_warp_5tt.pklz")
            warpedPVEs_results_path = os.path.join(self.stage_dir,"apply_warp_pves","result_apply_warp_pves.pklz")
            warpedWM_results_path = os.path.join(self.stage_dir,"apply_warp_wm","result_apply_warp_wm.pklz")
            warpedT1_results_path = os.path.join(self.stage_dir,"apply_warp_T1","result_apply_warp_T1.pklz")
            if self.config.registration_mode == 'FSL':
                fnirt_results_path = os.path.join(self.stage_dir,"fsl_fnirt_crop","result_fsl_fnirt_crop.pklz")
            elif self.config.registration_mode == 'ANTs':
                if self.config.ants_perform_syn:
                    syn_results_path = os.path.join(self.stage_dir,"SyN_registration","result_SyN_registration.pklz")

        else:
            target_path = os.path.join(self.stage_dir,"fMRI_skullstrip","result_fMRI_skullstrip.pklz")
            reg_results_path = os.path.join(self.stage_dir,"linear_registration","result_linear_registration.pklz")
            warpedROIVs_results_path = os.path.join(self.stage_dir,"apply_registration_roivs","result_apply_registration_roivs.pklz")

        if self.config.pipeline == "Diffusion":
                if(os.path.exists(target_path) and os.path.exists(reg_results_path) and os.path.exists(warpedROIVs_results_path) and os.path.exists(warped5TT_results_path) and os.path.exists(warpedPVEs_results_path) and os.path.exists(warpedWM_results_path) and os.path.exists(warpedT1_results_path)):

                    target = pickle.load(gzip.open(target_path))
                    reg_results = pickle.load(gzip.open(reg_results_path))
                    rois_results = pickle.load(gzip.open(warpedROIVs_results_path))
                    mrtrix_5tt_results = pickle.load(gzip.open(warped5TT_results_path))
                    pves_results = pickle.load(gzip.open(warpedPVEs_results_path))
                    wm_results = pickle.load(gzip.open(warpedWM_results_path))
                    T1_results = pickle.load(gzip.open(warpedT1_results_path))

                    if self.config.registration_mode == 'FSL':
                        if(os.path.exists(fnirt_results_path)):
                                fnirt_results = pickle.load(gzip.open(fnirt_results_path))
                                self.inspect_outputs_dict['Linear T1-to-b0'] = ['fslview',reg_results.inputs['reference'],reg_results.outputs.out_file,'-l',"Copper",'-t','0.5']
                                self.inspect_outputs_dict['Wrapped T1-to-b0'] = ['fslview',fnirt_results.inputs['ref_file'],T1_results.outputs.out_file,'-l',"Copper",'-t','0.5']
                                self.inspect_outputs_dict['Wrapped 5TT-to-b0'] = ['fslview',fnirt_results.inputs['ref_file'],mrtrix_5tt_results.outputs.output_image,'-l',"Copper",'-t','0.5']
                                self.inspect_outputs_dict['Deformation field'] = ['fslview',fnirt_results.outputs.fieldcoeff_file]#['mrview',fa_results.inputs['ref_file'],'-vector.load',fnirt_results.outputs.fieldcoeff_file]#

                                if type(rois_results.outputs.out_files) == str:
                                        self.inspect_outputs_dict['%s-to-b0' % os.path.basename(rois_results.outputs.out_files)] = ['fslview',fnirt_results.inputs['ref_file'],rois_results.outputs.out_files,'-l','Random-Rainbow','-t','0.5']
                                else:
                                    for roi_output in rois_results.outputs.out_files:
                                            self.inspect_outputs_dict['%s-to-b0' % os.path.basename(roi_output)] = ['fslview',fnirt_results.inputs['ref_file'],roi_output,'-l','Random-Rainbow','-t','0.5']

                                if type(pves_results.outputs.out_files) == str:
                                        self.inspect_outputs_dict['%s-to-b0' % os.path.basename(pves_results.outputs.out_files)] = ['fslview',fnirt_results.inputs['ref_file'],pves_results.outputs.out_files,'-l','Random-Rainbow','-t','0.5']
                                else:
                                    for pve_output in pves_results.outputs.out_files:
                                            self.inspect_outputs_dict['%s-to-b0' % os.path.basename(pve_output)] = ['fslview',fnirt_results.inputs['ref_file'],pve_output,'-l','Random-Rainbow','-t','0.5']

                    elif self.config.registration_mode == 'ANTs':

                            print("reg_results.inputs['fixed_image']: %s"%reg_results.inputs['fixed_image'][0])
                            print("reg_results.outputs.warped_image: %s"%reg_results.outputs.warped_image)

                            print("T1_results.outputs.output_image: %s"%T1_results.outputs.output_image)
                            self.inspect_outputs_dict['Linear T1-to-b0'] = ['fslview',reg_results.inputs['fixed_image'][0],reg_results.outputs.warped_image,'-l',"Copper",'-t','0.5']

                            if self.config.ants_perform_syn:
                                if(os.path.exists(syn_results_path)):
                                    syn_results = pickle.load(gzip.open(syn_results_path))
                                    print("syn_results.inputs['fixed_image']: %s"%syn_results.inputs['fixed_image'][0])
                                    self.inspect_outputs_dict['Wrapped T1-to-b0'] = ['fslview',syn_results.inputs['fixed_image'][0],T1_results.outputs.output_image,'-l',"Copper",'-t','0.5']
                                    #self.inspect_outputs_dict['Deformation field'] = ['fslview',fnirt_results.outputs.fieldcoeff_file]#['mrview',fa_results.inputs['ref_file'],'-vector.load',fnirt_results.outputs.fieldcoeff_file]#
                            print("rois_results.outputs.output_images: %s"%rois_results.outputs.output_images)
                            print("pves_results.outputs.output_images: %s"%pves_results.outputs.output_images)

                            self.inspect_outputs_dict['Wrapped 5TT-to-b0'] = ['fslview',reg_results.inputs['fixed_image'][0],mrtrix_5tt_results.outputs.output_image,'-l',"Copper",'-t','0.5']

                            if type(rois_results.outputs.output_images) == str:
                                if self.config.ants_perform_syn:
                                    if(os.path.exists(syn_results_path)):
                                        self.inspect_outputs_dict['%s-to-b0' % os.path.basename(rois_results.outputs.output_images)] = ['fslview',syn_results.inputs['fixed_image'][0],rois_results.outputs.output_images,'-l','Random-Rainbow','-t','0.5']
                                else:
                                    self.inspect_outputs_dict['%s-to-b0' % os.path.basename(rois_results.outputs.output_images)] = ['fslview',reg_results.inputs['fixed_image'][0],rois_results.outputs.output_images,'-l','Random-Rainbow','-t','0.5']
                            else:
                                for roi_output in rois_results.outputs.output_images:
                                    if self.config.ants_perform_syn:
                                        if(os.path.exists(syn_results_path)):
                                            self.inspect_outputs_dict['%s-to-b0' % os.path.basename(roi_output)] = ['fslview',syn_results.inputs['fixed_image'][0],roi_output,'-l','Random-Rainbow','-t','0.5']
                                    else:
                                        self.inspect_outputs_dict['%s-to-b0' % os.path.basename(roi_output)] = ['fslview',reg_results.inputs['fixed_image'][0],roi_output,'-l','Random-Rainbow','-t','0.5']

                            if type(pves_results.outputs.output_images) == str:
                                if self.config.ants_perform_syn:
                                    if(os.path.exists(syn_results_path)):
                                        self.inspect_outputs_dict['%s-to-b0' % os.path.basename(pves_results.outputs.output_images)] = ['fslview',syn_results.inputs['fixed_image'][0],pves_results.outputs.output_images,'-l','Random-Rainbow','-t','0.5']
                                else:
                                    self.inspect_outputs_dict['%s-to-b0' % os.path.basename(pves_results.outputs.output_images)] = ['fslview',reg_results.inputs['fixed_image'][0],pves_results.outputs.output_images,'-l','Random-Rainbow','-t','0.5']
                            else:
                                for pve_output in pves_results.outputs.output_images:
                                    if self.config.ants_perform_syn:
                                        if(os.path.exists(syn_results_path)):
                                            self.inspect_outputs_dict['%s-to-b0' % os.path.basename(pve_output)] = ['fslview',syn_results.inputs['fixed_image'][0],pve_output,'-l','Random-Rainbow','-t','0.5']
                                    else:
                                        self.inspect_outputs_dict['%s-to-b0' % os.path.basename(pve_output)] = ['fslview',reg_results.inputs['fixed_image'][0],pve_output,'-l','Random-Rainbow','-t','0.5']
        else:
            if (os.path.exists(target_path)) and (os.path.exists(reg_results_path)) and (os.path.exists(warpedROIVs_results_path)):
                target = pickle.load(gzip.open(target_path))
                reg_results = pickle.load(gzip.open(reg_results_path))
                rois_results = pickle.load(gzip.open(warpedROIVs_results_path))

                self.inspect_outputs_dict['Mean-fMRI/T1-to-fMRI'] = ['fslview',target.inputs['in_file'],reg_results.outputs.out_file,'-l',"Copper",'-t','0.5']

                if type(rois_results.outputs.out_files) == str:
                        self.inspect_outputs_dict['Mean-fMRI/%s' % os.path.basename(rois_results.outputs.out_files)] = ['fslview',target.outputs.out_file,rois_results.outputs.out_files,'-l','Random-Rainbow','-t','0.5']
                else:
                    for roi_output in rois_results.outputs.out_files:
                            self.inspect_outputs_dict['Mean-fMRI/%s' % os.path.basename(roi_output)] = ['fslview',target.outputs.out_file,roi_output,'-l','Random-Rainbow','-t','0.5']

                    # elif self.config.registration_mode == 'Nonlinear (FSL)':
                    #     if type(rois_results.outputs.warped_files) == str:
                    #         if self.config.pipeline == "Diffusion":
                    #             self.inspect_outputs_dict['B0/%s' % os.path.basename(rois_results.outputs.warped_files)] = ['fslview',target.outputs.out_file,rois_results.outputs.warped_files,'-l','Random-Rainbow','-t','0.5']
                    #         else:
                    #             self.inspect_outputs_dict['Mean-fMRI/%s' % os.path.basename(rois_results.outputs.warped_files)] = ['fslview',target.outputs.out_file,rois_results.outputs.warped_files,'-l','Random-Rainbow','-t','0.5']
                    #     elif type(rois_results.outputs.warped_files) == TraitListObject:
                    #         for roi_output in rois_results.outputs.warped_files:
                    #             if self.config.pipeline == "Diffusion":
                    #                 self.inspect_outputs_dict['B0/%s' % os.path.basename(roi_output)] = ['fslview',target.outputs.out_file,roi_output,'-l','Random-Rainbow','-t','0.5']
                    #             else:
                    #                 self.inspect_outputs_dict['Mean-fMRI/%s' % os.path.basename(roi_output)] = ['fslview',target.outputs.out_file,roi_output,'-l','Random-Rainbow','-t','0.5']


        self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)

    def has_run(self):

        if self.config.registration_mode == 'ANTs':
            if self.config.ants_perform_syn:
                return os.path.exists(os.path.join(self.stage_dir,"SyN_registration","result_SyN_registration.pklz"))
            else:
                return os.path.exists(os.path.join(self.stage_dir,"linear_registration","result_linear_registration.pklz"))

        elif self.config.registration_mode != 'Nonlinear (FSL)':
            return os.path.exists(os.path.join(self.stage_dir,"linear_registration","result_linear_registration.pklz"))

        elif self.config.registration_mode == 'Nonlinear (FSL)':
            return os.path.exists(os.path.join(self.stage_dir,"nonlinear_registration","result_nonlinear_registration.pklz"))
