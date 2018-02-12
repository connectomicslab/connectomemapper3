# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" The FreeSurfer module provides functions for interfacing with Freesurfer functions missing in nipype or modified
"""

import os
import os.path as op
from glob import glob
#import itertools
import numpy as np

from nibabel import load
from nipype.utils.filemanip import fname_presuffix, copyfile
from nipype.interfaces.io import FreeSurferSource, IOBase

from nipype.interfaces.freesurfer.base import FSCommand, FSTraitedSpec
from nipype.interfaces.base import (TraitedSpec, File, traits,
                                    Directory, InputMultiPath,
                                    OutputMultiPath, CommandLine,
                                    CommandLineInputSpec, isdefined, BaseInterface, BaseInterfaceInputSpec)

class copyFileToFreesurfer_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True)
    out_file = File(exists=False)

class copyFileToFreesurfer_OutputSpec(TraitedSpec):
    out_file = File(exists=True)

class copyFileToFreesurfer(IOBase):
    input_spec = copyFileToFreesurfer_InputSpec
    output_spec = copyFileToFreesurfer_OutputSpec

    # def _run_interface(self,runtime):
    #     copyfile(self.inputs.in_file,self.inputs.out_file, copy=True)
    #     return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        copyfile(self.inputs.in_file,self.inputs.out_file, copy=True)
        outputs["out_file"] = self.inputs.out_file
        return outputs


class copyBrainMaskToFreesurfer_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True)
    subject_dir = Directory(exists=True)

class copyBrainMaskToFreesurfer_OutputSpec(TraitedSpec):
    out_brainmask_file = File(exists=True)
    out_brainmaskauto_file = File(exists=True)

class copyBrainMaskToFreesurfer(IOBase):
    input_spec = copyBrainMaskToFreesurfer_InputSpec
    output_spec = copyBrainMaskToFreesurfer_OutputSpec

    # def _run_interface(self,runtime):
    #     copyfile(self.inputs.in_file,self.inputs.out_file, copy=True)
    #     return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        brainmask_file = op.join(self.inputs.subject_dir,'mri','brainmask.mgz')
        if op.isfile(brainmask_file):
            copyfile(brainmask_file, op.join(self.inputs.subject_dir,'mri','brainmask.old.mgz'), copy=True)
        copyfile(self.inputs.in_file, brainmask_file, copy=True)

        brainmaskauto_file = op.join(self.inputs.subject_dir,'mri','brainmask.auto.mgz')
        if op.isfile(brainmaskauto_file):
            copyfile(brainmaskauto_file, op.join(self.inputs.subject_dir,'mri','brainmask.auto.old.mgz'), copy=True)
        copyfile(self.inputs.in_file, brainmaskauto_file, copy=True)

        outputs["out_brainmask_file"] = brainmask_file
        outputs["out_brainmaskauto_file"] = brainmaskauto_file

        return outputs


class BBRegisterInputSpec(FSTraitedSpec):
    subject_id = traits.Str(argstr='--s %s',
                            desc='freesurfer subject id',
                            mandatory=True)
    source_file = File(argstr='--mov %s',
                       desc='source file to be registered',
                       mandatory=True, copyfile=False)
    init = traits.Enum('spm', 'fsl', 'header', argstr='--init-%s',
                       mandatory=True, xor=['init_reg_file'],
                       desc='initialize registration spm, fsl, header')
    init_reg_file = File(exists=True,
                         desc='existing registration file',
                         xor=['init'], mandatory=True)
    contrast_type = traits.Enum('t1', 't2', 'dti', argstr='--%s',
                                desc='contrast type of image',
                                mandatory=True)
    intermediate_file = File(exists=True, argstr="--int %s",
                             desc="Intermediate image, e.g. in case of partial FOV")
    reg_frame = traits.Int(argstr="--frame %d", xor=["reg_middle_frame"],
                           desc="0-based frame index for 4D source file")
    reg_middle_frame = traits.Bool(argstr="--mid-frame", xor=["reg_frame"],
                                   desc="Register middle frame of 4D source file")
    out_reg_file = File(argstr='--reg %s',
                        desc='output registration file',
                        genfile=True)
    spm_nifti = traits.Bool(argstr="--spm-nii",
                            desc="force use of nifti rather than analyze with SPM")
    epi_mask = traits.Bool(argstr="--epi-mask",
                           desc="mask out B0 regions in stages 1 and 2")
    out_fsl_file = traits.Either(traits.Bool, File, argstr="--fslmat %s",
                   desc="write the transformation matrix in FSL FLIRT format")
    registered_file = traits.Either(traits.Bool, File, argstr='--o %s',
                      desc='output warped sourcefile either True or filename')


class BBRegisterOutputSpec(TraitedSpec):
    out_reg_file = File(exists=True, desc='Output registration file')
    out_fsl_file = File(desc='Output FLIRT-style registration file')
    min_cost_file = File(exists=True, desc='Output registration minimum cost file')
    registered_file = File(desc='Registered and resampled source file')


class BBRegister(FSCommand):
    """Use FreeSurfer bbregister to register a volume to the Freesurfer anatomical.

    This program performs within-subject, cross-modal registration using a
    boundary-based cost function. The registration is constrained to be 6
    DOF (rigid). It is required that you have an anatomical scan of the
    subject that has already been recon-all-ed using freesurfer.

    Examples
    --------

    >>> from nipype.interfaces.freesurfer import BBRegister
    >>> bbreg = BBRegister(subject_id='me', source_file='structural.nii', init='header', contrast_type='t2')
    >>> bbreg.cmdline
    'bbregister --t2 --init-header --reg structural_bbreg_me.dat --mov structural.nii --s me'

    """

    _cmd = 'bbregister'
    input_spec = BBRegisterInputSpec
    output_spec = BBRegisterOutputSpec

    def _list_outputs(self):

        outputs = self.output_spec().get()
        _in = self.inputs

        if isdefined(_in.out_reg_file):
            outputs['out_reg_file'] = op.abspath(_in.out_reg_file)
        elif _in.source_file:
            suffix = '_bbreg_%s.dat' % _in.subject_id
            outputs['out_reg_file'] = fname_presuffix(_in.source_file,
                                                      suffix=suffix,
                                                      use_ext=False)

        if isdefined(_in.registered_file):
            if isinstance(_in.registered_file, bool):
                outputs['registered_file'] = fname_presuffix(_in.source_file,
                                                             suffix='_bbreg')
            else:
                outputs['registered_file'] = op.abspath(_in.registered_file)

        if isdefined(_in.out_fsl_file):
            if isinstance(_in.out_fsl_file, bool):
                suffix='_bbreg_%s.mat' % _in.subject_id
                out_fsl_file = fname_presuffix(_in.source_file,
                                               suffix=suffix,
                                               use_ext=False)
                outputs['out_fsl_file'] = out_fsl_file
            else:
                outputs['out_fsl_file'] = op.abspath(_in.out_fsl_file)

        outputs['min_cost_file'] = outputs['out_reg_file'] + '.mincost'
        return outputs

    def _format_arg(self, name, spec, value):

        if name in ['registered_file', 'out_fsl_file']:
            if isinstance(value, bool):
                fname = self._list_outputs()[name]
            else:
                fname = value
            return spec.argstr % fname
        return super(BBRegister, self)._format_arg(name, spec, value)

    def _gen_filename(self, name):

        if name == 'out_reg_file':
            return self._list_outputs()[name]
        return None
