# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

import os

import numpy as np
import nibabel as nib
from traits.api import *

from nipype.utils.filemanip import copyfile
from nipype.interfaces.base import traits, TraitedSpec, File, BaseInterface, BaseInterfaceInputSpec
from nipype.interfaces.utility.base import Rename

class ExtractHeaderVoxel2WorldMatrixInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc='Input image file')


class ExtractHeaderVoxel2WorldMatrixOutputSpec(TraitedSpec):
    out_matrix = File(
        exists=true, desc='Output voxel to world affine transform file')


class ExtractHeaderVoxel2WorldMatrix(BaseInterface):
    """Write in a text file the voxel-to-world transform matrix from the heaer of a Nifti image.

    Examples
    --------
    >>> from cmtklib.interfaces.misc import ExtractHeaderVoxel2WorldMatrix
    >>> extract_mat = ExtractHeaderVoxel2WorldMatrix()
    >>> extract_mat.inputs.in_file = 'sub-01_T1w.nii.gz'
    >>> extract_mat.run()  # doctest: +SKIP

    """

    input_spec = ExtractHeaderVoxel2WorldMatrixInputSpec
    output_spec = ExtractHeaderVoxel2WorldMatrixOutputSpec

    def _run_interface(self, runtime):
        im = nib.load(self.inputs.in_file)
        transform = np.array(im.get_affine())

        with open(os.path.abspath('voxel2world.txt'), 'a') as out_f:
            np.savetxt(out_f, transform, delimiter=' ', fmt="%6.6g")

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_matrix"] = os.path.abspath('voxel2world.txt')
        return outputs


class ExtractImageVoxelSizesInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)


class ExtractImageVoxelSizesOutputSpec(TraitedSpec):
    voxel_sizes = traits.List((traits.Int(), traits.Int(), traits.Int()))


class ExtractImageVoxelSizes(BaseInterface):
    """Returns a list of voxel sizes from an image.

    Examples
    --------
    >>> from cmtklib.interfaces.misc import ExtractImageVoxelSizes
    >>> extract_voxel_sizes = ExtractImageVoxelSizes()
    >>> extract_voxel_sizes.inputs.in_file = 'sub-01_T1w.nii.gz'
    >>> extract_voxel_sizes.run()  # doctest: +SKIP

    """

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


class ConcatOutputsAsTupleInputSpec(BaseInterfaceInputSpec):
    input1 = File(exists=True)

    input2 = File(exists=True)


class ConcatOutputsAsTupleOutputSpec(TraitedSpec):
    out_tuple = traits.Tuple(File(exists=True), File(exists=True))


class ConcatOutputsAsTuple(BaseInterface):
    """Concatenate 2 different output file as a Tuple of 2 files.

    Examples
    --------
    >>> from cmtklib.interfaces.misc import ConcatOutputsAsTuple
    >>> concat_outputs = ConcatOutputsAsTuple()
    >>> concat_outputs.inputs.input1  = 'output_interface1.nii.gz'
    >>> concat_outputs.inputs.input2  = 'output_interface2.nii.gz'
    >>> concat_outputs.run()  # doctest: +SKIP

    """

    input_spec = ConcatOutputsAsTupleInputSpec
    output_spec = ConcatOutputsAsTupleOutputSpec

    def _run_interface(self, runtime):
        self._outputs().out_tuple = (self.inputs.input1, self.inputs.input2)
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_tuple"] = (self.inputs.input1, self.inputs.input2)
        return outputs


class Rename001(Rename):
    """Change the name of a file based on a mapped format string.

    To use additional inputs that will be defined at run-time, the class
    constructor must be called with the format template, and the fields
    identified will become inputs to the interface.
    Additionally, you may set the parse_string input, which will be run
    over the input filename with a regular expressions search, and will
    fill in additional input fields from matched groups. Fields set with
    inputs have precedence over fields filled in with the regexp match.

    It corresponds to the `nipype.interfaces.utility.base.Rename` interface
    that has been modified to force hard link during copy

    Examples
    --------
    >>> from nipype.interfaces.utility import Rename
    >>> rename1 = Rename()
    >>> rename1.inputs.in_file = os.path.join(datadir, "zstat1.nii.gz") # datadir is a directory with exemplary files, defined in conftest.py
    >>> rename1.inputs.format_string = "Faces-Scenes.nii.gz"
    >>> res = rename1.run()          # doctest: +SKIP
    >>> res.outputs.out_file         # doctest: +SKIP
    'Faces-Scenes.nii.gz"            # doctest: +SKIP

    >>> rename2 = Rename(format_string="%(subject_id)s_func_run%(run)02d")
    >>> rename2.inputs.in_file = os.path.join(datadir, "functional.nii")
    >>> rename2.inputs.keep_ext = True
    >>> rename2.inputs.subject_id = "subj_201"
    >>> rename2.inputs.run = 2
    >>> res = rename2.run()          # doctest: +SKIP
    >>> res.outputs.out_file         # doctest: +SKIP
    'subj_201_func_run02.nii'        # doctest: +SKIP

    >>> rename3 = Rename(format_string="%(subject_id)s_%(seq)s_run%(run)02d.nii")
    >>> rename3.inputs.in_file = os.path.join(datadir, "func_epi_1_1.nii")
    >>> rename3.inputs.parse_string = r"func_(?P<seq>\w*)_.*"
    >>> rename3.inputs.subject_id = "subj_201"
    >>> rename3.inputs.run = 2
    >>> res = rename3.run()          # doctest: +SKIP
    >>> res.outputs.out_file         # doctest: +SKIP
    'subj_201_epi_run02.nii'         # doctest: +SKIP

    References
    ----------
    Adapted from https://github.com/nipy/nipype/blob/cd4c34d935a43812d1756482fdc4034844e485b8/nipype/interfaces/utility/base.py#L232-L272

    """

    def _run_interface(self, runtime):
        runtime.returncode = 0
        out_file = os.path.join(runtime.cwd, self._rename())
        copyfile(self.inputs.in_file, out_file, use_hardlink=True)
        self._results["out_file"] = out_file
        return runtime
