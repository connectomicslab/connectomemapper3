# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""The FSL module provides Nipype interfaces for FSL functions missing in Nipype or modified."""

import os
from glob import glob
import warnings

from nipype.interfaces.fsl.base import FSLCommand, FSLCommandInputSpec
from nipype.interfaces.base import (traits, BaseInterface, BaseInterfaceInputSpec,
                                    TraitedSpec, CommandLineInputSpec, CommandLine,
                                    InputMultiPath, OutputMultiPath, File,
                                    isdefined)
import nipype.interfaces.fsl as fsl
from traits.trait_types import Float, Enum

warn = warnings.warn
warnings.filterwarnings('always', category=UserWarning)


class BinaryThresholdInputSpec(FSLCommandInputSpec):
    in_file = File(position=2, argstr="%s", exists=True, mandatory=True,
                   desc="image to operate on")

    thresh = traits.Float(mandatory=True, position=3, argstr="-thr %s",
                          desc="threshold value")

    binarize = traits.Bool(True, position=4, argstr='-bin')

    out_file = File(genfile=True, mandatory=True, position=5,
                    argstr="%s", desc="image to write", hash_files=False)


class BinaryThresholdOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="image written after calculations")


class BinaryThreshold(FSLCommand):
    """Use `fslmaths` to apply a threshold to an image in a variety of ways.

    Examples
    --------
    >>> from cmtklib.interfaces.fsl import BinaryThreshold
    >>> thresh = BinaryThreshold()
    >>> thresh.inputs.in_file = '/path/to/probseg.nii.gz'
    >>> thresh.inputs.thresh = 0.5
    >>> thresh.inputs.out_file = '/path/to/output_binseg.nii.gz'
    >>> thresh.run()  # doctest: +SKIP

    """

    _cmd = "fslmaths"
    input_spec = BinaryThresholdInputSpec
    output_spec = BinaryThresholdOutputSpec
    _suffix = "_thresh"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(
                self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


class MathsInput(FSLCommandInputSpec):
    in_file = File(position=2, argstr="%s", exists=True, mandatory=True,
                   desc="image to operate on")

    out_file = File(genfile=True, position=-2, argstr="%s",
                    desc="image to write", hash_files=False)

    _dtypes = ["float", "char", "int", "short", "double", "input"]

    internal_datatype = traits.Enum(*_dtypes, position=1, argstr="-dt %s",
                                    desc="datatype to use for calculations (default is float)")

    output_datatype = traits.Enum(*_dtypes,
                                  position=-1, argstr="-odt %s",
                                  desc="datatype to use for output (default uses input type)")

    nan2zeros = traits.Bool(position=3, argstr='-nan',
                            desc='change NaNs to zeros before doing anything')


class MathsOutput(TraitedSpec):
    out_file = File(exists=True, desc="image written after calculations")


class MathsCommand(FSLCommand):
    """Calls the `fslmaths` command in a variety of ways.

    Examples
    --------
    >>> from cmtklib.interfaces.fsl import MathsCommand
    >>> fsl_maths = MathsCommand()
    >>> fsl_maths.inputs.in_file = '/path/to/image_with_nans.nii.gz'
    >>> fsl_maths.inputs.nan2zeros = True
    >>> fsl_maths.inputs.out_file = '/path/to/image_with_no_nans.nii.gz'
    >>> fsl_maths.run()  # doctest: +SKIP

    """

    _cmd = "fslmaths"
    input_spec = MathsInput
    output_spec = MathsOutput
    _suffix = "_maths"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(
                self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


class FSLCreateHDInputSpec(CommandLineInputSpec):
    im_size = traits.List(traits.Int, argstr='%s', mandatory=True, position=1, minlen=4, maxlen=4,
                          desc='Image size : xsize , ysize, zsize, tsize ')

    vox_size = traits.List(traits.Int, argstr='%s', mandatory=True, position=2, minlen=3, maxlen=3,
                           desc='Voxel size : xvoxsize, yvoxsize, zvoxsize')

    tr = traits.Int(argstr='%s', mandatory=True, position=3, desc='<tr>')

    origin = traits.List(traits.Int, argstr='%s', mandatory=True, position=4, minlen=3, maxlen=3,
                         desc='Origin coordinates : xorig, yorig, zorig')

    datatype = traits.Enum('2', '4', '8', '16', '32', '64', argstr='%s', mandatory=True, position=5,
                           desc='Datatype values: 2=char, 4=short, 8=int, 16=float, 64=double')

    out_filename = File(gen=True, mandatory=True, position=6, argstr='%s',
                        desc=' the output temp reference image created.')


class FSLCreateHDOutputSpec(TraitedSpec):
    out_file = File(
        exists=True, desc='Path/name of the output reference image created.')


class FSLCreateHD(CommandLine):
    """Calls the `fslcreatehd` command to create an image for space / dimension reference.

    Examples
    --------
    >>> from cmtklib.interfaces.fsl import FSLCreateHD
    >>> fsl_create = FSLCreateHD()
    >>> fsl_create.inputs.im_size = [256, 256, 256, 1]
    >>> fsl_create.inputs.vox_size = [1, 1, 1]
    >>> fsl_create.inputs.tr = 0
    >>> fsl_create.inputs.origin = [0, 0, 0]
    >>> fsl_create.inputs.datatype = '16' # 16: float
    >>> fsl_create.inputs.out_filename = '/path/to/generated_image.nii.gz'
    >>> fsl_create.run()  # doctest: +SKIP

    """

    _cmd = 'fslcreatehd'
    input_spec = FSLCreateHDInputSpec
    output_spec = FSLCreateHDOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(self.inputs.out_filename)
        return outputs


class OrientInputSpec(FSLCommandInputSpec):
    in_file = File(exists=True, mandatory=True, argstr="%s", position="2",
                   desc="input image")

    _options_xor = ['get_orient', 'get_sform', 'get_qform', 'set_sform', 'set_qform', 'get_sformcode', 'get_qformcode',
                    'set_sformcode', 'set_qformcode', 'copy_sform2qform', 'copy_qform2sform', 'delete_orient',
                    'force_radiological', 'force_neurological', 'swap_orient']

    get_orient = traits.Bool(argstr="-getorient", position="1", xor=_options_xor,
                             desc="gets FSL left-right orientation")

    get_sform = traits.Bool(argstr="-getsform", position="1", xor=_options_xor,
                            desc="gets the 16 elements of the sform matrix")

    get_qform = traits.Bool(argstr="-getqform", position="1", xor=_options_xor,
                            desc="gets the 16 elements of the qform matrix")

    set_sform = traits.List(traits.Float(), minlen=16, maxlen=16, position="1", argstr="-setsform %f",
                            xor=_options_xor, desc="<m11 m12 ... m44> sets the 16 elements of the sform matrix")

    set_qform = traits.List(traits.Float(), minlen=16, maxlen=16, position="1", argstr="-setqform %f",
                            xor=_options_xor, desc="<m11 m12 ... m44> sets the 16 elements of the qform matrix")

    get_sformcode = traits.Bool(argstr="-getsformcode", position="1", xor=_options_xor,
                                desc="gets the sform integer code")

    get_qformcode = traits.Bool(argstr="-getqformcode", position="1", xor=_options_xor,
                                desc="gets the qform integer code")

    set_sformcode = traits.Int(argstr="-setformcode %d", position="1", xor=_options_xor,
                               desc="<code> sets sform integer code")

    set_qformcode = traits.Int(argstr="-setqormcode %d", position="1", xor=_options_xor,
                               desc="<code> sets qform integer code")

    copy_sform2qform = traits.Bool(argstr="-copysform2qform", position="1", xor=_options_xor,
                                   desc="sets the qform equal to the sform - code and matrix")

    copy_qform2sform = traits.Bool(argstr="-copyqform2sform", position="1", xor=_options_xor,
                                   desc="sets the sform equal to the qform - code and matrix")

    delete_orient = traits.Bool(argstr="-deleteorient", position="1", xor=_options_xor,
                                desc="removes orient info from header")

    force_radiological = traits.Bool(argstr="-forceradiological", position="1", xor=_options_xor,
                                     desc="makes FSL radiological header")

    force_neurological = traits.Bool(argstr="-forceneurological", position="1", xor=_options_xor,
                                     desc="makes FSL neurological header - not Analyze")

    swap_orient = traits.Bool(argstr="-swaporient", position="1", xor=_options_xor,
                              desc="swaps FSL radiological and FSL neurological")


class OrientOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="image with modified orientation")

    orient = traits.Str(desc="FSL left-right orientation")

    sform = traits.List(traits.Float(), minlen=16, maxlen=16,
                        desc="the 16 elements of the sform matrix")

    qform = traits.List(traits.Float(), minlen=16, maxlen=16,
                        desc="the 16 elements of the qform matrix")

    sformcode = traits.Int(desc="sform integer code")

    qformcode = traits.Int(desc="qform integer code")


class Orient(FSLCommand):
    """Use fslorient to get/set orientation information from an image's header.

    Advanced tool that reports or sets the orientation information in a file.
    Note that only in NIfTI files can the orientation be changed -
    Analyze files are always treated as "radiological" (meaning that they could be
    simply rotated into the same alignment as the MNI152 standard images - equivalent
    to the appropriate sform or qform in a NIfTI file having a negative determinant).

    Examples
    --------
    >>> from cmtklib.interfaces.fsl import Orient
    >>> fsl_orient = Orient()
    >>> fsl_orient.inputs.in_file = 'input_image.nii.gz'
    >>> fsl_orient.inputs.force_radiological = True
    >>> fsl_orient.inputs.out_file = 'output_image.nii.gz'
    >>> fsl_orient.run()  # doctest: +SKIP

    """

    _cmd = "fslorient"
    input_spec = OrientInputSpec
    output_spec = OrientOutputSpec

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()
        info = runtime.stdout

        # Modified file
        if isdefined(self.inputs.copy_sform2qform) or isdefined(self.inputs.copy_qform2sform) or isdefined(
                self.inputs.delete_orient) or isdefined(self.inputs.force_radiological) or isdefined(
                self.inputs.force_neurological) or isdefined(self.inputs.swap_orient):
            outputs.out_file = self.inputs.in_file
            # outputs['out_file'] = self.inputs.in_file

        # Get information
        if isdefined(self.inputs.get_orient):
            outputs.orient = info
        if isdefined(self.inputs.get_sform):
            outputs.sform = info
        if isdefined(self.inputs.get_qform):
            outputs.qform = info
        if isdefined(self.inputs.get_sformcode):
            outputs.sformcode = info
        if isdefined(self.inputs.get_qformcode):
            outputs.qformcode = info

        return outputs


class EddyInputSpec(FSLCommandInputSpec):
    in_file = File(exists=True, desc='File containing all the images to estimate distortions for', argstr='--imain=%s',
                   position=0, mandatory=True)

    mask = File(exists=True, desc='Mask to indicate brain',
                argstr='--mask=%s', position=1, mandatory=True)

    index = File(exists=True, desc='File containing indices for all volumes in --imain into --acqp and --topup',
                 argstr='--index=%s', position=2, mandatory=True)

    acqp = File(exists=True, desc='File containing acquisition parameters', argstr='--acqp=%s', position=3,
                mandatory=True)

    bvecs = File(exists=True, desc='File containing the b-vectors for all volumes in --imain', argstr='--bvecs=%s',
                 position=4, mandatory=True)

    bvals = File(exists=True, desc='File containing the b-values for all volumes in --imain', argstr='--bvals=%s',
                 position=5, mandatory=True)

    out_file = File(desc='Basename for output', argstr='--out=%s',
                    position=6, genfile=True, hash_files=False)

    verbose = traits.Bool(argstr='--verbose', position=7,
                          desc="Display debugging messages.")


class EddyOutputSpec(TraitedSpec):
    eddy_corrected = File(
        exists=True, desc='path/name of 4D eddy corrected DWI file')

    bvecs_rotated = File(
        exists=True, desc='path/name of rotated DWI gradient bvecs file')


class Eddy(FSLCommand):
    """Performs eddy current distorsion correction using FSL `eddy`.

    Example
    -------
    >>> from cmtklib.interfaces import fsl
    >>> eddyc = fsl.Eddy(in_file='diffusion.nii',
    >>>                  bvecs='diffusion.bvecs',
    >>>                  bvals='diffusion.bvals',
    >>>                  out_file="diffusion_eddyc.nii")
    >>> eddyc.run()  # doctest: +SKIP

    """

    _cmd = 'eddy'
    input_spec = EddyInputSpec
    output_spec = EddyOutputSpec

    def __init__(self, **inputs):
        return super(Eddy, self).__init__(**inputs)

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(
                self.inputs.in_file, suffix='_edc')
        runtime = super(Eddy, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['eddy_corrected'] = self.inputs.out_file
        if not isdefined(outputs['eddy_corrected']):
            outputs['eddy_corrected'] = self._gen_fname(
                self.inputs.in_file, suffix='_edc')
        outputs['eddy_corrected'] = os.path.abspath(outputs['eddy_corrected'])
        outputs['bvecs_rotated'] = self._gen_fname(
            self.inputs.out_file, suffix='', ext='.nii.gz.eddy_rotated_bvecs')
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._list_outputs()['eddy_corrected']
        else:
            return None


class EddyOpenMP(FSLCommand):
    """Performs eddy current distorsion correction using FSL `eddy_openmp`.

    Example
    -------
    >>> from cmtklib.interfaces import fsl
    >>> eddyc = fsl.EddyOpenMP(in_file='diffusion.nii',
    >>>                        bvecs='diffusion.bvecs',
    >>>                        bvals='diffusion.bvals',
    >>>                        out_file="diffusion_eddyc.nii")
    >>> eddyc.run()  # doctest: +SKIP

    """

    _cmd = 'eddy_openmp'
    input_spec = EddyInputSpec
    output_spec = EddyOutputSpec

    def __init__(self, **inputs):
        return super(EddyOpenMP, self).__init__(**inputs)

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(
                self.inputs.in_file, suffix='_edc')
        runtime = super(EddyOpenMP, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['eddy_corrected'] = self.inputs.out_file
        if not isdefined(outputs['eddy_corrected']):
            outputs['eddy_corrected'] = self._gen_fname(
                self.inputs.in_file, suffix='_edc')
        outputs['eddy_corrected'] = os.path.abspath(outputs['eddy_corrected'])
        outputs['bvecs_rotated'] = self._gen_fname(
            self.inputs.out_file, suffix='', ext='.nii.gz.eddy_rotated_bvecs')
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._list_outputs()['eddy_corrected']
        else:
            return None


class ApplymultipleXfmInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(
        File(mandatory=True, exists=True), desc="Files to be registered")

    xfm_file = File(desc="Transform file", mandatory=True, exists=True)

    reference = File(desc="Reference image used for target space",
                     mandatory=True, exists=True)

    interp = Enum('nearestneighbour', 'spline',
                  desc='Interpolation used')


class ApplymultipleXfmOutputSpec(TraitedSpec):
    out_files = OutputMultiPath(File(), desc="Transformed files")


class ApplymultipleXfm(BaseInterface):
    """Apply an XFM transform estimated by FSL `flirt` to a list of images.

    Example
    -------
    >>> from cmtklib.interfaces import fsl
    >>> apply_xfm = fsl.ApplymultipleXfm
    >>> apply_xfm.inputs.in_files = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                              '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                              '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                              '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                              '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> apply_xfm.inputs.xfm_file = '/path/to/flirt_transform.xfm'
    >>> apply_xfm.inputs.reference = '/path/to/sub-01_meanBOLD.nii.gz'
    >>> apply_xfm.run()  # doctest: +SKIP

    """

    input_spec = ApplymultipleXfmInputSpec
    output_spec = ApplymultipleXfmOutputSpec

    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            ax = fsl.ApplyXFM(
                in_file=in_file,
                in_matrix_file=self.inputs.xfm_file,
                apply_xfm=True,
                interp=self.inputs.interp,
                reference=self.inputs.reference)
            ax.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_files'] = glob(os.path.abspath("*.nii.gz"))
        return outputs


class ApplymultipleWarpInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(
        File(mandatory=True, exists=True), desc="Files to be registered")

    field_file = File(desc="Deformation field", mandatory=True, exists=True)

    ref_file = File(desc="Reference image used for target space", mandatory=True, exists=True)

    interp = traits.Enum(
        'nn', 'trilinear', 'sinc', 'spline', argstr='--interp=%s', position=-2,
        desc="Interpolation method")


class ApplymultipleWarpOutputSpec(TraitedSpec):
    out_files = OutputMultiPath(File(), desc="Warped files")


class ApplymultipleWarp(BaseInterface):
    """Apply a deformation field estimated by FSL `fnirt` to a list of images.

    Example
    -------
    >>> from cmtklib.interfaces import fsl
    >>> apply_warp = fsl.ApplymultipleWarp()
    >>> apply_warp.inputs.in_files = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                               '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                               '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                               '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                               '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> apply_warp.inputs.field_file = '/path/to/fnirt_deformation.nii.gz'
    >>> apply_warp.inputs.ref_file = '/path/to/sub-01_meanBOLD.nii.gz'
    >>> apply_warp.run()  # doctest: +SKIP

    """

    input_spec = ApplymultipleWarpInputSpec
    output_spec = ApplymultipleWarpOutputSpec

    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            ax = fsl.ApplyWarp(
                in_file=in_file,
                interp=self.inputs.interp,
                field_file=self.inputs.field_file,
                ref_file=self.inputs.ref_file
            )
            ax.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_files'] = glob(os.path.abspath("*.nii.gz"))
        return outputs


class CreateAcqpFileInputSpec(BaseInterfaceInputSpec):
    total_readout = Float(0.0)


class CreateAcqpFileOutputSpec(TraitedSpec):
    acqp = File(exists=True)


class CreateAcqpFile(BaseInterface):
    """Create an acquisition `Acqp` file for FSL `eddy`.

    .. note::
        This value can be extracted from dMRI data acquired on Siemens scanner

    Examples
    --------
    >>> from cmtklib.interfaces.fsl import CreateAcqpFile
    >>> create_acqp = CreateAcqpFile()
    >>> create_acqp.inputs.total_readout  = 0.28
    >>> create_acqp.run()  # doctest: +SKIP

    """

    input_spec = CreateAcqpFileInputSpec
    output_spec = CreateAcqpFileOutputSpec

    def _run_interface(self, runtime):
        import numpy as np

        # Matrix giving phase-encoding direction (3 first columns) and total read out time (4th column)
        # For phase encoding A << P <=> y-direction
        # Total readout time = Echo spacing x EPI factor x 0.001 [s]
        mat = np.array([['0', '1', '0', str(self.inputs.total_readout)],
                        ['0', '-1', '0', str(self.inputs.total_readout)]])

        with open(os.path.abspath('acqp.txt'), 'a') as out_f:
            np.savetxt(out_f, mat, fmt="%s", delimiter=' ')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["acqp"] = os.path.abspath('acqp.txt')
        return outputs


class CreateIndexFileInputSpec(BaseInterfaceInputSpec):
    in_grad_mrtrix = File(exists=True, mandatory=True,
                          desc='Input DWI gradient table in MRTrix format')


class CreateIndexFileOutputSpec(TraitedSpec):
    index = File(exists=True)


class CreateIndexFile(BaseInterface):
    """Create an index file for FSL `eddy` from a `mrtrix` diffusion gradient table.

    Examples
    --------
    >>> from cmtklib.interfaces.fsl import CreateIndexFile
    >>> create_index = CreateIndexFile()
    >>> create_index.inputs.in_grad_mrtrix  = 'grad.txt'
    >>> create_index.run()  # doctest: +SKIP

    """

    input_spec = CreateIndexFileInputSpec
    output_spec = CreateIndexFileOutputSpec

    def _run_interface(self, runtime):
        import numpy as np

        with open(self.inputs.in_grad_mrtrix, 'r') as f:
            for i, _ in enumerate(f):
                pass

        lines = i + 1

        mat = np.ones((1, lines))

        with open(os.path.abspath('index.txt'), 'a') as out_f:
            np.savetxt(out_f, mat, delimiter=' ', fmt="%1.0g")

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["index"] = os.path.abspath('index.txt')
        return outputs
