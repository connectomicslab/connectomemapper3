import os
import glob
import numpy as np
import nibabel as nibabel

try:
    from traitsui.api import *
    from traits.api import *

except ImportError:
    from enthought.traits.api import *
    from enthought.traits.ui.api import *

from nipype.interfaces.base import traits, isdefined, CommandLine, CommandLineInputSpec,\
    TraitedSpec, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec

class ExtractImageVoxelSizesInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)

class ExtractImageVoxelSizesOutputSpec(TraitedSpec):
    voxel_sizes = List(Int(),Int(),Int())

class ExtractImageVoxelSizes(BaseInterface):

    input_spec = ExtractImageVoxelSizesInputSpec
    output_spec = ExtractImageVoxelSizesOutputSpec

    def _run_interface(self, runtime):
        img = nib.load(self.inputs.in_file)
        self.voxel_sizes = img.get_zooms()[:3]
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['voxel_sizes'] = self.voxel_sizes
        return outputs
