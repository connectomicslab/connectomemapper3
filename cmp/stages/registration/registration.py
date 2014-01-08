# Copyright (C) 2009-2014, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP registration stage
""" 

# General imports
from traits.api import *
from traitsui.api import *
import os
import pickle
import gzip
import glob

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, File, TraitedSpec, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec

# Own imports
from cmp.stages.common import Stage

class RegistrationConfig(HasTraits):
    # Registration selection
    registration_mode = Str('Linear (FSL)')
    registration_mode_trait = List(['Linear (FSL)','BBregister (FS)'])
    imaging_model = Str
    
    # FLIRT
    flirt_args = Str
    uses_qform = Bool(True)
    dof = Int(6)
    cost = Enum('mutualinfo',['mutualinfo','corratio','normcorr','normmi','leastsq','labeldiff'])
    no_search = Bool(True)
    
    # BBRegister
    init = Enum('header',['spm','fsl','header'])
    contrast_type = Enum('t2',['t1','t2'])
                
    traits_view = View(Item('registration_mode',editor=EnumEditor(name='registration_mode_trait')),
                        Group('uses_qform','dof','cost','no_search','flirt_args',label='FLIRT',
                              show_border=True,visible_when='registration_mode=="Linear (FSL)"'),
                        Group('init','contrast_type',
                              show_border=True,visible_when='registration_mode=="BBregister (FS)"'),
                       kind='live',
                       )
                       

class Tkregister2InputSpec(CommandLineInputSpec):
    subjects_dir = Directory(desc='Use dir as SUBJECTS_DIR',exists=True,argstr="--sd %s")
    subject_id = traits.Str(desc='Set subject id',argstr="--s %s")
    regheader = traits.Bool(desc='Compute registration from headers',argstr="--regheader")
    in_file = File(desc='Movable volume',mandatory=True,exists=True,argstr="--mov %s")
    target_file = File(desc='Target volume',mandatory=True,exists=True,argstr="--targ %s")
    reg_out = traits.Str(desc='Input/output registration file',mandatory=True,argstr="--reg %s")
    fslreg_out = traits.Str(desc='FSL-Style registration output matrix',mandatory=True,argstr="--fslregout %s")
    noedit = traits.Bool(desc='Do not open edit window (exit) - for conversions',argstr="--noedit")


class Tkregister2OutputSpec(TraitedSpec):
    regout_file = File(desc='Resulting registration file')
    fslregout_file = File(desc='Resulting FSL-Style registration matrix')

class Tkregister2(CommandLine):
    _cmd = 'tkregister2'
    input_spec = Tkregister2InputSpec
    output_spec = Tkregister2OutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["regout_file"]  = os.path.abspath(self.inputs.reg_out)
        outputs["fslregout_file"]  = os.path.abspath(self.inputs.fslregout_out)
        return outputs
        
class ApplynlinmultiplewarpsInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(File(desc='files to be registered', mandatory=True, exists=True))
    ref_file = File(mandatory=True, exists=True)
    premat_file = File(mandatory=True, exists=True)
    field_file = File(mandatory=True, exists=True)
    
class ApplynlinmultiplewarpsOutputSpec(TraitedSpec):
    warped_files = OutputMultiPath(File())
    
class Applynlinmultiplewarps(BaseInterface):
    input_spec = ApplynlinmultiplewarpsInputSpec
    output_spec = ApplynlinmultiplewarpsOutputSpec
    
    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            aw = fsl.ApplyWarp(interp="nn",in_file=in_file,ref_file=self.inputs.ref_file,premat=self.inputs.premat_file,field_file=self.inputs.field_file)
            aw.run()
        return runtime
        
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["warped_files"] = glob.glob(os.path.abspath("*.nii.gz"))
        return outputs

class RegistrationStage(Stage):
    name = 'registration_stage'
    config = RegistrationConfig()
    inputs = ["T1","diffusion","T2","subjects_dir","subject_id","wm_mask","roi_volumes"]
    outputs = ["T1_registered", "wm_mask_registered","roi_volumes_registered"]

    def create_workflow(self, flow, inputnode, outputnode):
        # Extract B0 and resample it to 1x1x1mm3
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(frame=0,out_file="diffusion_first.nii.gz",vox_size=(1,1,1)),name="diffusion_resample")
        
        flow.connect([(inputnode, fs_mriconvert,[('diffusion','in_file')])])
        
        if self.config.registration_mode == 'Linear (FSL)':
            fsl_flirt = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-B0.nii.gz',out_matrix_file='T1-TO-B0.mat'),name="linear_registration")
            fsl_flirt.inputs.uses_qform = self.config.uses_qform
            fsl_flirt.inputs.dof = self.config.dof
            fsl_flirt.inputs.cost = self.config.cost
            fsl_flirt.inputs.no_search = self.config.no_search
            fsl_flirt.inputs.args = self.config.flirt_args
            
            fsl_applyxfm_wm = pe.Node(interface=fsl.ApplyXfm(apply_xfm=True,interp="nearestneighbour",out_file="wm_mask_registered.nii.gz"),name="apply_registration_wm")
            fsl_applyxfm_rois = pe.MapNode(interface=fsl.ApplyXfm(apply_xfm=True,interp="nearestneighbour"),name="apply_registration_roivs",iterfield=["in_file"])
            
            flow.connect([
                        (inputnode, fsl_flirt, [('T1','in_file')]),
                        (fs_mriconvert, fsl_flirt, [('out_file','reference')]),
                        (inputnode, fsl_applyxfm_wm, [('wm_mask','in_file')]),
                        (fs_mriconvert, fsl_applyxfm_wm, [('out_file','reference')]),
                        (fsl_flirt,outputnode,[("out_file","T1_registered")]),
                        (fsl_flirt, fsl_applyxfm_wm, [('out_matrix_file','in_matrix_file')]),
                        (fsl_applyxfm_wm, outputnode, [('out_file','wm_mask_registered')]),
                        (inputnode, fsl_applyxfm_rois, [('roi_volumes','in_file')]),
                        (fs_mriconvert, fsl_applyxfm_rois, [('out_file','reference')]),
                        (fsl_flirt, fsl_applyxfm_rois, [('out_matrix_file','in_matrix_file')]),
                        (fsl_applyxfm_rois, outputnode, [('out_file','roi_volumes_registered')]),
                        ])
        if self.config.registration_mode == 'BBregister (FS)':
            fs_bbregister = pe.Node(interface=fs.BBRegister(out_fsl_file="b0-TO-orig.mat"),name="bbregister")
            fs_bbregister.inputs.init = self.config.init
            fs_bbregister.inputs.contrast_type = self.config.contrast_type
            
            fsl_invertxfm = pe.Node(interface=fsl.ConvertXFM(invert_xfm=True),name="fsl_invertxfm")
            
            fs_tkregister2 = pe.Node(interface=Tkregister2(regheader=True,noedit=True),name="fs_tkregister2")
            fs_tkregister2.inputs.reg_out = 'T1-TO-orig.dat'
            fs_tkregister2.inputs.fslreg_out = 'T1-TO-orig.mat'
            fs_tkregister2.inputs.in_file = 'rawavg.mgz'
            fs_tkregister2.inputs.target_file = 'orig.mgz'
            
            fsl_concatxfm = pe.Node(interface=fsl.ConvertXFM(concat_xfm=True),name="fsl_concatxfm")
            
            fsl_applyxfm = pe.Node(interface=fsl.ApplyXfm(apply_xfm=True),name="linear_registration")
            fsl_applyxfm_wm = pe.Node(interface=fsl.ApplyXfm(apply_xfm=True,interp="nearestneighbour",out_file="wm_mask_registered.nii.gz"),name="apply_registration_wm")
            fsl_applyxfm_rois = pe.MapNode(interface=fsl.ApplyXfm(apply_xfm=True,interp="nearestneighbour"),name="apply_registration_roivs",iterfield=["in_file"])
            
            
            flow.connect([
                        (inputnode, fs_bbregister, [('subjects_dir','subjects_dir'),('subject_id','subject_id')]),
                        (fs_mriconvert, fs_bbregister, [('out_file','source_file')]),
                        (fs_bbregister, fsl_invertxfm, [('out_fsl_file','in_file')]),
                        (fsl_invertxfm, fsl_concatxfm, [('out_file','in_file')]),
                        (inputnode, fs_tkregister2, [(('subjects_dir','subjects_dir'),('subject_id','subject_id'))]),
                        (fs_tkregister2, fsl_concatxfm, [('fslregout_file','in_file2')]),
                        (fsl_concatxfm, fsl_applyxfm, [('out_file','in_matrix_file')]),
                        (inputnode, fsl_applyxfm_wm, [('T1','in_file')]),
                        (fs_mriconvert, fsl_applyxfm_wm, [('out_file','reference')]),
                        (fsl_flirt, fsl_applyxfm_wm, [('out_matrix_file','in_matrix_file')]),
                        (fsl_applyxfm_wm, outputnode, [('out_file','wm_mask_registered')]),
                        (inputnode, fsl_applyxfm_rois, [('roi_volumes','in_file')]),
                        (fs_mriconvert, fsl_applyxfm_rois, [('out_file','reference')]),
                        (fsl_flirt, fsl_applyxfm_rois, [('out_matrix_file','in_matrix_file')]),
                        (fsl_applyxfm_rois, outputnode, [('out_file','roi_volumes_registered')]),
                        ])
        if self.config.registration_mode == 'Nonlinear (FSL)':
            # [SUB-STEP 1] LINEAR register "T2" onto "b0_resampled
            # [1.1] linear register "T1" onto "T2"
            fsl_flirt_1 = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-T2.nii.gz',out_matrix_file='T1-TO-T2.mat'),name="t1tot2_lin_registration")
            fsl_flirt_1.inputs.dof = 6
            fsl_flirt_1.inputs.cost = "mutualinfo"
            fsl_flirt_1.inputs.no_search = True
            #[1.2] -> linear register "T2" onto "b0_resampled"
            fsl_flirt_2 = pe.Node(interface=fsl.FLIRT(out_file='T2-TO-b0.nii.gz',out_matrix_file='T2-TO-b0.mat'),name="t2tob0_lin_registration")
            fsl_flirt_2.inputs.dof = 12
            fsl_flirt_2.inputs.cost = "normmi"
            fsl_flirt_2.inputs.no_search = True
            #[1.3] -> apply the linear registration "T1" --> "b0" (for comparison)
            fsl_concatxfm = pe.Node(interface=fsl.ConvertXFM(concat_xfm=True),name="fsl_concatxfm")
            fsl_applyxfm = pe.Node(interface=fsl.ApplyXfm(apply_xfm=True, interp="sinc",out_file='T1-TO-b0.nii.gz',out_matrix_file='T1-TO-b0.mat'),name="linear_registration")
            #"[SUB-STEP 2] Create BINARY MASKS for nonlinear registration"
            # [2.1] -> create a T2 brain mask
            fsl_bet_1 = pe.Node(interface=fsl.BET(out_file='T2-brain',mask=True,no_output=True,robust=True),name="t2_brain_mask")
            fsl_bet_1.inputs.frac = 0.35
            fsl_bet_1.inputs.vertical_gradient = 0.15
            #[2.2] -> create a DSI_b0 brain mask
            fsl_bet_2 = pe.Node(interface=fsl.BET(out_file='b0-brain',mask=True,no_output=True,robust=True),name="b0_brain_mask")
            fsl_bet_2.inputs.frac = 0.2
            fsl_bet_2.inputs.vertical_gradient = 0.2
            # [SUB-STEP 3] NONLINEAR register "T2" onto "b0_resampled"
            # [3.1] 'Started FNIRT to find 'T2 --> b0' nonlinear transformation at
            fsl_fnirt = pe.Node(interface=fsl.FNIRT(field_file='T2-TO-b0_warp.nii.gz',warped_file='T2_warped.nii.gz'),name="t2tob0_nlin_registration")
            fsl_fnirt.inputs.subsampling_scheme = [8,4,2,2]
            fsl_fnirt.inputs.max_nonlin_iter = [5,5,5,5]
            fsl_fnirt.inputs.regularization_lambda = [240,120,90,30]
            fsl_fnirt.inputs.spline_order = 3
            fsl_fnirt.inputs.apply_inmask = [0,0,1,1]
            fsl_fnirt.inputs.apply_refmask = [0,0,1,1]
            #[3.2] -> apply the warp found for "T2" also onto "T1"
            fsl_applywarp = pe.Node(interface=fsl.ApplyWarp(out_file='T1_warped.nii.gz'),name="nonlinear_registration")
            fsl_applywarp_wm = pe.Node(interface=fsl.ApplyWarp(interp="nn",out_file="wm_mask_registered.nii.gz"),name="apply_registration_wm")
            fsl_applywarp_rois = pe.Node(interface=Applynlinmultiplewarps(),name="apply_registration_roivs")
            
            flow.connect([
                    (inputnode,fsl_flirt_1,[('T1','in_file'),('T2','reference')]),
                    (inputnode,fsl_flirt_2,[('T2','in_file')]),
                    (fs_mriconvert,fsl_flirt_2,[('out_file','reference')]),
                    (fsl_flirt_1,fsl_concatxfm,[('out_matrix_file','in_file')]),
                    (fsl_flirt_2,fsl_concatxfm,[('out_matrix_file','in_file2')]),
                    (inputnode,fsl_applyxfm,[('T1','in_file')]),
                    (fs_mriconvert,fsl_applyxfm,[('out_file','reference')]),
                    (fsl_concatxfm,fsl_applyxfm,[('out_file','in_matrix_file')]),
                    (inputnode,fsl_bet_1,[('T2','in_file')]),
                    (fs_mriconvert,fsl_bet_2,[('out_file','in_file')]),
                    (inputnode,fsl_fnirt,[('T2','in_file')]),
                    (fsl_flirt_2,fsl_fnirt,[('out_matrix_file','affine_file')]),
                    (fs_mriconvert,fsl_fnirt,[('out_file','ref_file')]),
                    (fsl_bet_1,fsl_fnirt,[('mask_file','inmask_file')]),
                    (fsl_bet_2,fsl_fnirt,[('mask_file','refmask_file')]),
                    (inputnode,fsl_applywarp,[('T1','in_file')]),
                    (fsl_flirt_1,fsl_applywarp,[('out_matrix_file','premat')]),
                    (fs_mriconvert,fsl_applywarp,[('out_file','ref_file')]),
                    (fsl_fnirt,fsl_applywarp,[('field_file','field_file')]),
                    (inputnode, fsl_applywarp_wm, [('wm_mask','in_file')]),
                    (fs_mriconvert, fsl_applywarp_wm, [('out_file','ref_file')]),
                    (fsl_flirt_1, fsl_applywarp_wm, [('out_matrix_file','premat')]),
                    (fsl_fnirt,fsl_applywarp_wm,[('field_file','field_file')]),
                    (fsl_applywarp_wm, outputnode, [('out_file','wm_mask_registered')]),
                    (inputnode, fsl_applywarp_rois, [('roi_volumes','in_files')]),
                    (fs_mriconvert, fsl_applywarp_rois, [('out_file','ref_file')]),
                    (fsl_flirt_1, fsl_applywarp_rois, [('out_matrix_file','premat_file')]),
                    (fsl_fnirt,fsl_applywarp_rois,[('field_file','field_file')]),
                    (fsl_applywarp_rois, outputnode, [('warped_files','roi_volumes_registered')]),
                    ])

    def define_inspect_outputs(self):
        resamp_results_path = os.path.join(self.stage_dir,"diffusion_resample","result_diffusion_resample.pklz")
        
        if self.config.registration_mode != 'Nonlinear (FSL)':
            reg_results_path = os.path.join(self.stage_dir,"linear_registration","result_linear_registration.pklz")
        elif self.config.registration_mode == 'Nonlinear (FSL)':
            reg_results_path = os.path.join(self.stage_dir,"nonlinear_registration","result_nonlinear_registration.pklz")
        
        if(os.path.exists(resamp_results_path) and os.path.exists(reg_results_path)):
                resamp_results = pickle.load(gzip.open(resamp_results_path))
                reg_results = pickle.load(gzip.open(reg_results_path))
                self.inspect_outputs_dict['B0/T1-to-B0'] = ['fslview',resamp_results.outputs.out_file,reg_results.outputs.out_file,'-l "Copper" -t 0.5']
                self.inspect_outputs = self.inspect_outputs_dict.keys()

    def has_run(self):
        if self.config.registration_mode != 'Nonlinear (FSL)':
            return os.path.exists(os.path.join(self.stage_dir,"linear_registration","result_linear_registration.pklz"))
        elif self.config.registration_mode == 'Nonlinear (FSL)':
            return os.path.exists(os.path.join(self.stage_dir,"nonlinear_registration","result_linear_registration.pklz"))


