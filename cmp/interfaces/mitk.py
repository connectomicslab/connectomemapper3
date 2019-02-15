# Copyright (C) 2017-2019, Brain Communication Pathways Sinergia Consortium, Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" The MITK module provides functions for interfacing with MITK functions missing in nipype or modified
"""
from traits.api import *

import os
import glob

from nipype.interfaces.base import traits, isdefined, CommandLine, CommandLineInputSpec,\
    TraitedSpec, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec

class MITKqball_commandInputSpec(CommandLineInputSpec):
    in_file = File(argstr="-i %s",position = 1,mandatory=True,exists=True,desc="input raw dwi (.dwi or .fsl/.fslgz)")
    out_file_name = String(argstr="-o %s",position=2,desc='output fiber name (.dti)')
    sh_order = Int(argstr="-sh %d", position=3,des='spherical harmonics order (optional), (default: 4)')
    reg_lambda = Float(argstr="-r %0.4f", position=4, desc='ragularization factor lambda (optional), (default: 0.006)')
    csa = Bool(argstr="-csa", position=5, desc='use constant solid angle consideration (optional)')

class MITKqball_commandOutputSpec(TraitedSpec):
    out_file = File(exists=True,desc='output tensor file')

class MITKqball(CommandLine):
    _cmd = 'MitkQballReconstruction.sh'
    input_spec = MITKqball_commandInputSpec
    output_spec = MITKqball_commandOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = self.inputs.out_file_name
        return outputs

class MITKtensor_commandInputSpec(CommandLineInputSpec):
    in_file = File(argstr="-i %s",position = 1,mandatory=True,exists=True,desc="input raw dwi (.dwi or .fsl/.fslgz)")
    out_file_name = String(argstr="-o %s",position=2,desc='output fiber name (.dti)')

class MITKtensor_commandOutputSpec(TraitedSpec):
    out_file = File(exists=True,desc='output tensor file')

class MITKtensor(CommandLine):
    _cmd = 'MitkTensorReconstruction.sh'
    input_spec = MITKtensor_commandInputSpec
    output_spec = MITKtensor_commandOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = self.inputs.out_file_name
        return outputs


class gibbs_reconInputSpec(BaseInterfaceInputSpec):

    dwi = File(exists=True)
    bvals = File(exists=True)
    bvecs = File(exists=True)
    recon_model = Enum(['Tensor','CSD'])
    sh_order = Int(argstr="-sh %d", position=3,des='spherical harmonics order (optional), (default: 4)')
    reg_lambda = Float(argstr="-t %0.4f", position=4, desc='ragularization factor lambda (optional), (default: 0.006)')
    csa = Bool(argstr="-csa", position=5, desc='use constant solid angle consideration (optional)')

class gibbs_reconOutputSpec(TraitedSpec):
    recon_file = File(exists=True)

class gibbs_recon(BaseInterface):
    input_spec = gibbs_reconInputSpec
    output_spec = gibbs_reconOutputSpec

    def _run_interface(self,runtime):
        # change DWI and gradient table names
        mitk_dwi = os.path.abspath(os.path.basename(self.inputs.dwi)+'.fsl')
        shutil.copyfile(self.inputs.dwi,mitk_dwi)
        mitk_bvec = os.path.abspath(os.path.basename(self.inputs.dwi)+'.fsl.bvecs')
        shutil.copyfile(self.inputs.bvecs,mitk_bvec)
        mitk_bval = os.path.abspath(os.path.basename(self.inputs.dwi)+'.fsl.bvals')
        shutil.copyfile(self.inputs.bvals,mitk_bval)
        if self.inputs.recon_model == 'Tensor':
            tensor = pe.Node(interface=MITKtensor(in_file = mitk_dwi, out_file_name = os.path.abspath('mitk_tensor.dti')),name="mitk_tensor")
            res = tensor.run()
        elif self.inputs.recon_model == 'CSD':
            csd = pe.Node(interface=MITKqball(),name='mitk_CSD')
            csd.inputs.in_file = mitk_dwi
            csd.inputs.out_file_name = os.path.abspath('mitk_qball.qbi')
            csd.inputs.sh_order = self.inputs.sh_order
            csd.inputs.reg_lambda = self.inputs.reg_lambda
            csd.inputs.csa = self.inputs.csa
            res = csd.run()

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        if self.inputs.recon_model == 'Tensor':
            outputs["recon_file"] = os.path.abspath('mitk_tensor.dti')
        elif self.inputs.recon_model == 'CSD':
            outputs["recon_file"] = os.path.abspath('mitk_qball.qbi')
        return outputs
