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

import nibabel as nib

class ComputeSphereRadiusInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)
    dilation_radius = Float(mandatory=True)

class ComputeSphereRadiusOutputSpec(TraitedSpec):
    sphere_radius = Float

class ComputeSphereRadius(BaseInterface):

    input_spec = ComputeSphereRadiusInputSpec
    output_spec = ComputeSphereRadiusOutputSpec

    def _run_interface(self, runtime):
        img = nib.load(self.inputs.in_file)
        voxel_sizes = img.get_header().get_zooms()[:3]
        min_size = 100
        for voxel_size in voxel_sizes:
            if voxel_size < min_size:
                min_size = voxel_size
        self.sphere_radius =  0.5*min_size + self.inputs.dilation_radius * min_size
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['sphere_radius'] = self.sphere_radius
        return outputs

class ExtractImageVoxelSizesInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)


class ExtractImageVoxelSizesOutputSpec(TraitedSpec):
    voxel_sizes = List(Int(),Int(),Int())

class ExtractImageVoxelSizes(BaseInterface):

    input_spec = ExtractImageVoxelSizesInputSpec
    output_spec = ExtractImageVoxelSizesOutputSpec

    def _run_interface(self, runtime):
        img = nib.load(self.inputs.in_file)
        self.voxel_sizes = img.get_header().get_zooms()[:3]
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['voxel_sizes'] = self.voxel_sizes
        return outputs

class Tck2TrkInputSpec(BaseInterfaceInputSpec):
    in_tracks = File(exists=True,mandatory=True,desc='Input track file in MRtrix .tck format')
    in_image = File(exists=True,mandatory=True,desc='Input image used to extract the header')
    out_tracks = File(mandatory=True,desc='Output track file in Trackvis .trk format')

class Tck2TrkOutputSpec(TraitedSpec):
    out_tracks = File(exists=True,desc='Output track file in Trackvis .trk format')

class Tck2Trk(BaseInterface):

    input_spec = Tck2TrkInputSpec
    output_spec = Tck2TrkOutputSpec

    def _run_interface(self, runtime):
        import nibabel
        from nibabel.streamlines import Field
        from nibabel.orientations import aff2axcodes
        print '-> Load nifti and copy header'
        nii = nibabel.load(self.inputs.in_image)

        header = {}
        header[Field.VOXEL_TO_RASMM] = nii.affine.copy()
        header[Field.VOXEL_SIZES] = nii.header.get_zooms()[:3]
        header[Field.DIMENSIONS] = nii.shape[:3]
        header[Field.VOXEL_ORDER] = "".join(aff2axcodes(nii.affine))

        if nibabel.streamlines.detect_format(self.inputs.in_tracks) is not nibabel.streamlines.TckFile:
            print("Skipping non TCK file: '{}'".format(tractogram))
        else:
            tck = nibabel.streamlines.load(self.inputs.in_tracks)
            self.out_tracks = self.inputs.out_tracks
            nibabel.streamlines.save(tck.tractogram, self.out_tracks, header=header)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_tracks'] = os.path.abspath(self.out_tracks)
        return outputs
