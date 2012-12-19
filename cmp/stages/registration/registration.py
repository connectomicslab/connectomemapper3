# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
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

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, File, TraitedSpec

# Own imports
from cmp.stages.common import Stage

class RegistrationConfig(HasTraits):
    # Registration selection
    registration_mode = Enum('Linear (FSL)','Nonlinear (FSL)','BBregister (FS)')
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
                
    traits_view = View('registration_mode',
                        Group('uses_qform','dof','cost','no_search','flirt_args',label='FLIRT',
                              show_border=True,visible_when='registration_mode=="Linear (FSL)"'),
                        Group('init','contrast_type',
                              show_border=True,visible_when='registration_mode=="BBregister (FS)"'),
                       kind='live',
                       )
                       

class Tkregsiter2InputSpec(CommandLineInputSpec):
    subjects_dir = Directory(desc='Use dir as SUBJECTS_DIR',exists=True,argstr="--sd %s")
    subject_id = traits.Str(desc='Set subject id',argstr="--s %s")
    regheader = traits.Bool(desc='Compute registration from headers',argstr="--regheader")
    in_file = File(desc='Movable volume',mandatory=True,exists=True,argstr="--mov %s")
    target_file = File(desc='Target volume',mandatory=True,exists=True,argstr="--targ %s")
    reg_out = traits.Str(desc='Input/output registration file',mandatory=True,argstr="--reg %s")
    fslreg_out = traits.Str(desc='FSL-Style registration output matrix',mandatory=True,argstr="--fslregout %s")
    noedit = traits.Bool(desc='Do not open edit window (exit) - for conversions',argstr="--noedit")


class Tkregsiter2OutputSpec(TraitedSpec):
    regout_file = File(desc='Resulting registration file')
    fslregout_file = File(desc='Resulting FSL-Style registration matrix')

class Tkregsiter2(CommandLine):
    _cmd = 'tkregister2'
    input_spec = Tkregsiter2InputSpec
    output_spec = Tkregsiter2OutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["regout_file"]  = os.path.abspath(self.inputs.reg_out)
        outputs["fslregout_file"]  = os.path.abspath(self.inputs.fslregout_out)
        return outputs

class RegistrationStage(Stage):
    name = 'registration_stage'
    config = RegistrationConfig()
    inputs = ["T1","diffusion","T2","subjects_dir","subject_id"]
    outputs = ["T1-TO-B0","T1-TO-B0_mat","diffusion_b0_resampled"]

    def create_workflow(self, flow, inputnode, outputnode):
        # Extract B0 and resample it to 1x1x1mm3
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(frame=0,out_file="diffusion_first.nii.gz",vox_size=(1,1,1)),name="diffusion_resample")
        
        flow.connect([(inputnode, fs_mriconvert,[('diffusion','in_file')]),
                      (fs_mriconvert, outputnode, [('out_file','diffusion_b0_resampled')])])
        
        if self.config.registration_mode == 'Linear (FSL)':
            fsl_flirt = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-B0.nii.gz',out_matrix_file='T1-TO-B0.mat'),name="registration")
            fsl_flirt.inputs.uses_qform = self.config.uses_qform
            fsl_flirt.inputs.dof = self.config.dof
            fsl_flirt.inputs.cost = self.config.cost
            fsl_flirt.inputs.no_search = self.config.no_search
            fsl_flirt.inputs.args = self.config.flirt_args
            
            flow.connect([
                        (inputnode, fsl_flirt, [('T1','in_file')]),
                        (fs_mriconvert, fsl_flirt, [('out_file','reference')]),
                        (fsl_flirt, outputnode, [('out_file','T1-TO-B0'),('out_matrix_file','T1-TO-B0_mat')]),
                        ])
        if self.config.registration_mode == 'BBregister (FS)':
            fs_bbregister = pe.Node(interface=fs.BBRegister(out_fsl_file="b0-TO-orig.mat"),name="registration")
            fs_bbregister.inputs.init = self.config.init
            fs_bbregister.inputs.contrast_type = self.config.contrast_type
            
            fsl_invertxfm = pe.Node(interface=fsl.ConvertXFM(invert_xfm=True),name="fsl_invertxfm")
            
            fs_tkregister2 = pe.Node(interface=Tkregister2(regheader=True,noedit=True),name="fs_tkregister2")
            fs_tkregister2.inputs.reg_out = 'T1-TO-orig.dat'
            fs_tkregister2.inputs.fslreg_out = 'T1-TO-orig.mat'
            fs_tkregister2.inputs.in_file = 'rawavg.mgz'
            fs_tkregister2.inputs.target_file = 'orig.mgz'
            
            fsl_concatxfm = pe.Node(interface=fsl.ConvertXFM(concat_xfm=True),name="fsl_concatxfm")
            
            fsl_applyxfm = pe.Node(interface=fsl.ApplyXFM(apply_xfm=True),name="fsl_applyxfm")
            
            flow.connect([
                        (inputnode, fs_bbregister, [('subjects_dir','subjects_dir'),('subject_id','subject_id')]),
                        (fs_mriconvert, fs_bbregister, [('out_file','source_file')]),
                        (fs_bbregister, fsl_invertxfm, [('out_fsl_file','in_file')]),
                        (fsl_invertxfm, fsl_concatxfm, [('out_file','in_file')]),
                        (inputnode, fs_tkregister2, [(('subjects_dir','subjects_dir'),('subject_id','subject_id'))]),
                        (fs_tkregister2, fsl_concatxfm, [('fslregout_file','in_file2')]),
                        (fsl_concatxfm, fsl_applyxfm, [('out_file','in_matrix_file')]),
                        (inputnode, fsl_applyxfm, [('T1','in_file')]),
                        (fs_mriconvert, fsl_applyxfm, [('out_file','reference')]),
                        (fsl_applyxfm, outputnode [('out_file','T1-TO-B0')]),
                        (fsl_concatxfm, outputnode, [('out_file','T1-TO-B0_mat')]),
                        ])

    def define_inspect_outputs(self):
        resamp_results_path = os.path.join(self.stage_dir,"diffusion_resample","result_diffusion_resample.pklz")
        reg_results_path = os.path.join(self.stage_dir,"registration","result_registration.pklz")
        if(os.path.exists(resamp_results_path) and os.path.exists(reg_results_path)):
            resamp_results = pickle.load(gzip.open(resamp_results_path))
            reg_results = pickle.load(gzip.open(reg_results_path))
            self.inspect_outputs_dict['B0/T1-to-B0'] = ['fslview',resamp_results.outputs.out_file,reg_results.outputs.out_file]
            self.inspect_outputs = self.inspect_outputs_dict.keys()

    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"registration","result_registration.pklz"))


