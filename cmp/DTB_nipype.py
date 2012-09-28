#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      abirbaum
#
# Created:     22.05.2012
# Copyright:   (c) abirbaum 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from nipype.interfaces.base import CommandLine, \
    CommandLineInputSpec, traits, File, TraitedSpec
    
import os
from nipype.utils.filemanip import split_filename

class DTB_P0InputSpec(CommandLineInputSpec):
	dsi_basepath = traits.Str(desc='DSI path/basename (e.g. \"data/dsi_\")',position=1,mandatory=True,argstr = "--dsi %s")
	dwi_file = traits.File(desc='DWI file',position=2,mandatory=True,exists=True,argstr = "--dwi %s")

class DTB_P0OutputSpec(TraitedSpec):
	p0_file = traits.File(desc='Resulting P0 file')

class DTB_P0(CommandLine):
	_cmd = 'DTB_P0'
	input_spec = DTB_P0InputSpec
	output_spec = DTB_P0OutputSpec

	def _list_outputs(self):
		outputs = self._outputs().get()
		path, base, _ = split_filename(self.inputs.dsi_basepath)
		outputs["p0_file"]  = os.path.join(path,base+'P0.nii')
		return outputs
		
class DTB_gfaInputSpec(CommandLineInputSpec):
	dsi_basepath = traits.Str(desc='DSI path/basename (e.g. \"data/dsi_\")',position=1,mandatory=True,argstr = "--dsi %s")
	moment = traits.Enum((2, 3, 4),desc='Moment to calculate (2 = gfa, 3 = skewness, 4 = curtosis)',position=2,mandatory=True,argstr = "--m %s")

class DTB_gfaOutputSpec(TraitedSpec):
	out_file = traits.File(desc='Resulting file')

class DTB_gfa(CommandLine):
	_cmd = 'DTB_gfa'
	input_spec = DTB_gfaInputSpec
	output_spec = DTB_gfaOutputSpec

	def _list_outputs(self):
		outputs = self._outputs().get()
		path, base, _ = split_filename(self.inputs.dsi_basepath)
		
		if self.inputs.moment == 2:
			outputs["out_file"]  = os.path.join(path,base+'gfa.nii')
		if self.inputs.moment == 3:
			outputs["out_file"]  = os.path.join(path,base+'skewness.nii')
		if self.inputs.moment == 4:
			outputs["out_file"]  = os.path.join(path,base+'curtosis.nii')
		
		return outputs


