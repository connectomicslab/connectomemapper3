# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""The MRTrix3 module provides Nipype interfaces for MRTrix3 tools missing in Nipype or modified."""

import os
import os.path as op
import glob

import nipype.interfaces.base as nibase
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, CommandLineInputSpec, \
    CommandLine, traits, TraitedSpec, File, Directory, InputMultiPath, OutputMultiPath, isdefined
from nipype.utils import logger
from nipype.utils.filemanip import split_filename, fname_presuffix


class MRtrix_mul_InputSpec(CommandLineInputSpec):
    input1 = nibase.File(desc='Input1 file', position=1,
                         mandatory=True, exists=True, argstr="%s")

    input2 = nibase.File(desc='Input2 file', position=2,
                         mandatory=True, exists=True, argstr="%s")

    out_filename = traits.Str(
        desc='out filename', position=3, mandatory=True, argstr="-mult %s")


class MRtrix_mul_OutputSpec(TraitedSpec):
    out_file = nibase.File(desc='Multiplication result file')


class MRtrix_mul(CommandLine):
    """Multiply two images together using `mrcalc` tool.

    Examples
    --------
    >>> from cmtklib.interfaces.mrtrix3 import MRtrix_mul
    >>> multiply = MRtrix_mul()
    >>> multiply.inputs.input1  = 'image1.nii.gz'
    >>> multiply.inputs.input2  = 'image2.nii.gz'
    >>> multiply.inputs.out_filename = 'result.nii.gz'
    >>> multiply.run()  # doctest: +SKIP

    """

    _cmd = 'mrcalc'
    input_spec = MRtrix_mul_InputSpec
    output_spec = MRtrix_mul_OutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(self.inputs.out_filename)
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.input1)
        return name + '_masked.mif'


class ErodeInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-3,
                   desc='Input mask image to be eroded')

    out_filename = File(genfile=True, argstr='%s',
                        position=-1, desc='Output image filename')

    number_of_passes = traits.Int(
        argstr='-npass %s', desc='the number of passes (default: 1)')

    filtertype = traits.Enum('clean', 'connect', 'dilate', 'erode', 'median', argstr='%s', position=-2,
                             desc='the type of filter to be applied (clean, connect, dilate, erode, median)')

    dilate = traits.Bool(argstr='-dilate', position=1,
                         desc="Perform dilation rather than erosion")

    quiet = traits.Bool(argstr='-quiet', position=1,
                        desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=1,
                        desc="Display debugging messages.")


class ErodeOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='the output image')


class Erode(CommandLine):
    """Erode (or dilates) a mask (i.e. binary) image using the `maskfilter` tool.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> erode = mrt.Erode()
    >>> erode.inputs.in_file = 'mask.mif'
    >>> erode.run()  # doctest: +SKIP

    """

    _cmd = 'maskfilter'
    input_spec = ErodeInputSpec
    output_spec = ErodeOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        if isdefined(self.inputs.out_filename):
            outfilename = self.inputs.out_filename
        else:
            _, name, _ = split_filename(self.inputs.in_file)
            outfilename = name + '_erode.mif'

        return outfilename


class DWIDenoiseInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                   desc='Input diffusion-weighted image filename')

    out_file = File(genfile=True, argstr='%s', position=-1,
                    desc='Output denoised DWI image filename.')

    mask = File(argstr="-mask %s", position=1, mandatory=False,
                desc="Only perform computation within the specified binary brain mask image. (optional)")

    extent_window = traits.List(traits.Float, argstr='-extent %s', sep=',', position=2, minlen=3, maxlen=3,
                                desc='Three comma-separated numbers giving the window size of the denoising filter.')

    out_noisemap = File(argstr='-noise %s', position=3,
                        desc='Output noise map filename.')

    force_writing = traits.Bool(
        argstr='-force', position=4, desc="Force file overwriting.")
    # quiet = traits.Bool(argstr='-quiet', position=1, desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=5,
                        desc="Display debugging messages.")


class DWIDenoiseOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='Output denoised DWI image.')
    out_noisemap = File(exists=True, desc='Output noise map (if generated).')


class DWIDenoise(CommandLine):
    """Denoise diffusion MRI data using the `dwidenoise` tool.

    Example
    -------
    >>> from cmtklib.interfaces.mrtrix3 import DWIDenoise
    >>> dwi_denoise = DWIDenoise()
    >>> dwi_denoise.inputs.in_file = 'sub-01_dwi.nii.gz'
    >>> dwi_denoise.inputs.out_file = 'sub-01_desc-denoised_dwi.nii.gz'
    >>> dwi_denoise.inputs.out_noisemap = 'sub-01_mod-dwi_noisemap.nii.gz'
    >>> dwi_denoise.run()  # doctest: +SKIP

    """

    _cmd = 'dwidenoise'
    input_spec = DWIDenoiseInputSpec
    output_spec = DWIDenoiseOutputSpec

    # def _run_interface(self, runtime):
    #     # The returncode is meaningless in DWIDenoise.  So check the output
    #     # in stderr and if it's set, then update the returncode
    #     # accordingly.
    #     runtime = super(DWIDenoise, self)._run_interface(runtime)
    #     if runtime.stderr:
    #         self.raise_exception(runtime)
    #     return runtime

    def _gen_fname(self, basename, cwd=None, suffix=None, change_ext=True,
                   ext='.mif'):
        """Generate a filename based on the given parameters.

        The filename will take the form: cwd/basename<suffix><ext>.
        If change_ext is True, it will use the extentions specified in
        <instance>intputs.output_type.

        Parameters
        ----------
        basename : str
            Filename to base the new filename on.
        cwd : str
            Path to prefix to the new filename. (default is os.getcwd())
        suffix : str
            Suffix to add to the `basename`.  (defaults is '' )
        change_ext : bool
            Flag to change the filename extension to the FSL output type.
            (default True)

        Returns
        -------
        fname : str
            New filename based on given parameters.
        """

        if basename == '':
            msg = 'Unable to generate filename for command %s. ' % self.cmd
            msg += 'basename is not set!'
            raise ValueError(msg)
        if cwd is None:
            cwd = os.getcwd()
        if change_ext:
            if suffix:
                suffix = ''.join((suffix, ext))
            else:
                suffix = ext
        if suffix is None:
            suffix = ''
        fname = fname_presuffix(basename, suffix=suffix,
                                use_ext=False, newpath=cwd)
        return fname

    def _gen_outfilename(self):
        out_file = self.inputs.out_file
        if not isdefined(out_file) and isdefined(self.inputs.in_file):
            out_file = self._gen_fname(self.inputs.in_file, suffix='_denoised')
        return os.path.abspath(out_file)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename()
        if isdefined(self.inputs.out_noisemap) and self.inputs.out_noisemap:
            outputs['out_noisemap'] = self._gen_fname(
                self.inputs.in_file, suffix='_noisemap')
        return outputs

    def _gen_filename(self, name):
        if name == 'out_file':
            return self._gen_outfilename()
        return None


class DWIBiasCorrectInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                   desc='The input image series to be corrected')

    out_file = File(genfile=True, argstr='%s', position=-1,
                    desc='The output corrected image series')

    mask = File(argstr="-mask %s", position=2, mandatory=False,
                desc="Manually provide a mask image for bias field estimation (optional)")

    out_bias = File(genfile=True, argstr='-bias %s', position=3,
                    desc='Output the estimated bias field')

    _xor_inputs = ('use_ants', 'use_fsl')

    use_ants = traits.Bool(argstr='ants', position=1, desc="Use ANTS N4 to estimate the inhomogeneity field",
                           xor=_xor_inputs)

    use_fsl = traits.Bool(argstr='fsl', position=1, desc="Use FSL FAST to estimate the inhomogeneity field",
                          xor=_xor_inputs)

    force_writing = traits.Bool(argstr='-force', position=4,
                                desc="Force file overwriting.")
    # quiet = traits.Bool(argstr='-quiet', position=1, desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=5,
                        desc="Display debugging messages.")


class DWIBiasCorrectOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='Output corrected DWI image')

    out_bias = File(exists=True, desc='Output estimated bias field')


class DWIBiasCorrect(CommandLine):
    """Correct for bias field in diffusion MRI data using the `dwibiascorrect` tool.

    Example
    -------
    >>> from cmtklib.interfaces.mrtrix3 import DWIBiasCorrect
    >>> dwi_biascorr = DWIBiasCorrect()
    >>> dwi_biascorr.inputs.in_file = 'sub-01_dwi.nii.gz'
    >>> dwi_biascorr.inputs.use_ants = True
    >>> dwi_biascorr.run() # doctest: +SKIP

    """

    _cmd = 'dwibiascorrect'
    input_spec = DWIBiasCorrectInputSpec
    output_spec = DWIBiasCorrectOutputSpec

    def _gen_fname(self, basename, cwd=None, suffix=None, change_ext=True,
                   ext='.mif'):
        """Generate a filename based on the given parameters.

        The filename will take the form: cwd/basename<suffix><ext>.
        If change_ext is True, it will use the extensions specified in
        <instance> inputs.output_type.

        Parameters
        ----------
        basename : str
            Filename to base the new filename on.
        cwd : str
            Path to prefix to the new filename. (default is os.getcwd())
        suffix : str
            Suffix to add to the `basename`.  (defaults is '' )
        change_ext : bool
            Flag to change the filename extension to the FSL output type.
            (default True)

        Returns
        -------
        fname : str
            New filename based on given parameters.

        """

        if basename == '':
            msg = 'Unable to generate filename for command %s. ' % self.cmd
            msg += 'basename is not set!'
            raise ValueError(msg)
        if cwd is None:
            cwd = os.getcwd()
        if change_ext:
            if suffix:
                suffix = ''.join((suffix, ext))
            else:
                suffix = ext
        if suffix is None:
            suffix = ''
        fname = fname_presuffix(basename, suffix=suffix,
                                use_ext=False, newpath=cwd)
        return fname

    def _gen_outfilename(self):
        out_file = self.inputs.out_file
        if not isdefined(out_file) and isdefined(self.inputs.in_file):
            out_file = self._gen_fname(self.inputs.in_file, suffix='_biascorr')
        return os.path.abspath(out_file)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename()
        if isdefined(self.inputs.out_bias) and self.inputs.out_bias:
            outputs['out_bias'] = self._gen_fname(
                self.inputs.in_file, suffix='_biasfield')
        return outputs

    def _gen_filename(self, name):
        if name == 'out_file':
            return self._gen_outfilename()
        return None


class MRConvertInputSpec(CommandLineInputSpec):
    _xor_inputs = ('in_file', 'in_dir')

    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2, xor=_xor_inputs,
                   desc='voxel-order data filename')

    in_dir = Directory(exists=True, argstr='%s', mandatory=True, position=-2, xor=_xor_inputs,
                       desc='directory containing DICOM files')

    out_filename = File(genfile=True, argstr='%s',
                        position=-1, desc='Output filename')

    extract_at_axis = traits.Enum(1, 2, 3, argstr='-coord %s', position=1,
                                  desc='Extract data only at the coordinates specified.'
                                  'This option specifies the Axis. Must be used in conjunction with extract_at_coordinate. ')

    extract_at_coordinate = traits.List(traits.Int, argstr='%s', sep=',', position=2, minlen=1, maxlen=3,
                                        desc='Extract data only at the coordinates specified. This option specifies the coordinates. '
                                        'Must be used in conjunction with extract_at_axis. '
                                        'Three comma-separated numbers giving the size of each voxel in mm.')

    voxel_dims = traits.List(traits.Float, argstr='-vox %s', sep=',',
                             position=3, minlen=3, maxlen=3,
                             desc='Three comma-separated numbers giving the size of each voxel in mm.')

    stride = traits.List(traits.Int, argstr='-stride %s', sep=',',
                         position=3, minlen=3, maxlen=4,
                         desc='Three to four comma-separated numbers specifying the strides of the output data in memory. '
                         'The actual strides produced will depend on whether the output image format can support it..')

    output_datatype = traits.Enum("float32", "float32le", "float32be", "float64", "float64le", "float64be", "int64",
                                  "uint64", "int64le", "uint64le", "int64be", "uint64be", "int32", "uint32", "int32le",
                                  "uint32le", "int32be", "uint32be", "int16", "uint16", "int16le", "uint16le",
                                  "int16be", "uint16be", "cfloat32", "cfloat32le", "cfloat32be", "cfloat64",
                                  "cfloat64le", "cfloat64be", "int8", "uint8", "bit", argstr='-datatype %s', position=2,
                                  desc='specify output image data type. Valid choices are: '
                                  'float32, float32le, float32be, float64, float64le, float64be, '
                                  'int64, uint64, int64le, uint64le, int64be, uint64be, int32, uint32, '
                                  'int32le, uint32le, int32be, uint32be, int16, uint16, int16le, '
                                  'uint16le, int16be, uint16be, cfloat32, cfloat32le, cfloat32be, '
                                  'cfloat64, cfloat64le, cfloat64be, int8, uint8, bit."')  # , usedefault=True)

    extension = traits.Enum("mif", "nii", "float", "char", "short", "int", "long", "double", position=4,
                            desc='"i.e. Bfloat". Can be "char", "short", "int", "long", "float" or "double"',
                            usedefault=True)

    layout = traits.Enum("nii", "float", "char", "short", "int", "long", "double", argstr='-output %s', position=5,
                         desc='specify the layout of the data in memory. '
                         'The actual layout produced will depend on whether the output image format can support it.')

    resample = traits.Float(argstr='-scale %d', position=6,
                            units='mm', desc='Apply scaling to the intensity values.')

    offset_bias = traits.Float(argstr='-scale %d', position=7,
                               units='mm', desc='Apply offset to the intensity values.')

    replace_nan_with_zero = traits.Bool(
        argstr='-zero', position=8, desc="Replace all NaN values with zero.")

    prs = traits.Bool(argstr='-prs', position=3,
                      desc="Assume that the DW gradients are specified in the PRS frame (Siemens DICOM only).")

    grad = File(exists=True, argstr='-grad %s', position=9,
                desc='Gradient encoding, supplied as a 4xN text file with each line is in the format [ X Y Z b ], '
                'where [ X Y Z ] describe the direction of the applied gradient, and b gives the b-value in units (1000 s/mm^2). '
                'See FSL2MRTrix')

    grad_fsl = traits.Tuple(File(exists=True), File(exists=True), argstr='-fslgrad %s %s',
                            desc='[bvecs, bvals] DW gradient scheme (FSL format)')

    force_writing = traits.Bool(
        argstr='-force', desc="Force file overwriting.")

    quiet = traits.Bool(
        argstr='-quiet', desc="Do not display information messages or progress status.")


class MRConvertOutputSpec(TraitedSpec):
    converted = File(exists=True, desc='path/name of 4D volume in voxel order')


class MRConvert(CommandLine):
    """Perform conversion with `mrconvert` between different file types and optionally extract a subset of the input image.

    If used correctly, this program can be a very useful workhorse.
    In addition to converting images between different formats, it can
    be used to extract specific studies from a data set, extract a specific
    region of interest, flip the images, or to scale the intensity of the images.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> mrconvert = mrt.MRConvert()
    >>> mrconvert.inputs.in_file = 'dwi_FA.mif'
    >>> mrconvert.inputs.out_filename = 'dwi_FA.nii'
    >>> mrconvert.run()  # doctest: +SKIP

    """

    _cmd = 'mrconvert'
    input_spec = MRConvertInputSpec
    output_spec = MRConvertOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['converted'] = op.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        if isdefined(self.inputs.out_filename):
            outname = self.inputs.out_filename
        else:
            outname = name + '_mrconvert.' + self.inputs.extension
        return outname


class ApplymultipleMRConvertInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(
        File(mandatory=True, exists=True), desc='Files to be registered')

    stride = traits.List(traits.Int, argstr='-stride %s', sep=',',
                         position=3, minlen=3, maxlen=4,
                         desc='Three to four comma-separated numbers specifying the strides of the output data in memory. '
                              'The actual strides produced will depend on whether the output image format can support it..')

    output_datatype = traits.Enum("float32", "float32le", "float32be", "float64", "float64le", "float64be", "int64",
                                  "uint64", "int64le", "uint64le", "int64be", "uint64be", "int32", "uint32", "int32le",
                                  "uint32le", "int32be", "uint32be", "int16", "uint16", "int16le", "uint16le",
                                  "int16be", "uint16be", "cfloat32", "cfloat32le", "cfloat32be", "cfloat64",
                                  "cfloat64le", "cfloat64be", "int8", "uint8", "bit", argstr='-datatype %s', position=2,
                                  desc='specify output image data type. Valid choices are: float32, float32le, float32be, '
                                  'float64, float64le, float64be, int64, uint64, int64le, uint64le, int64be, uint64be, int32, '
                                  'uint32, int32le, uint32le, int32be, uint32be, int16, uint16, int16le, uint16le, int16be, '
                                  'uint16be, cfloat32, cfloat32le, cfloat32be, cfloat64, cfloat64le, cfloat64be, int8, uint8, '
                                  'bit.')  # , usedefault=True)

    extension = traits.Enum("mif", "nii", "float", "char", "short", "int", "long", "double", position=4,
                            desc='"i.e. Bfloat". Can be "char", "short", "int", "long", "float" or "double"',
                            usedefault=True)


class ApplymultipleMRConvertOutputSpec(TraitedSpec):
    converted_files = OutputMultiPath(File(), desc='Output files')


class ApplymultipleMRConvert(BaseInterface):
    """Apply `mrconvert` tool to multiple images.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> mrconvert = mrt.ApplymultipleMRConvert()
    >>> mrconvert.inputs.in_files = ['dwi_FA.mif','dwi_MD.mif']
    >>> mrconvert.inputs.extension = 'nii'
    >>> mrconvert.run()  # doctest: +SKIP

    """

    input_spec = ApplymultipleMRConvertInputSpec
    output_spec = ApplymultipleMRConvertOutputSpec

    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            # Extract image filename (only) and create output image filename (no renaming)
            out_filename = in_file.split('/')[-1]
            ax = MRConvert(in_file=in_file, stride=self.inputs.stride, out_filename=out_filename,
                           output_datatype=self.inputs.output_datatype, extension=self.inputs.extension)
            ax.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['converted_files'] = glob.glob(os.path.abspath("*.nii.gz"))
        return outputs


class MRCropInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                   desc='Input image')

    in_mask_file = File(exists=True, argstr='-mask %s', position=-3,
                        desc='Input mask')

    out_filename = File(genfile=True, argstr='%s',
                        position=-1, desc='Output cropped image')

    quiet = traits.Bool(argstr='-quiet', position=1,
                        desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=1,
                        desc="Display debugging messages.")


class MRCropOutputSpec(TraitedSpec):
    cropped = File(exists=True, desc='the output cropped image.')


class MRCrop(CommandLine):
    """Crops a NIFTI image using the `mrcrop` tool.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> mrcrop = mrt.MRCrop()
    >>> mrcrop.inputs.in_file = 'sub-01_dwi.nii.gz'
    >>> mrcrop.inputs.in_mask_file = 'sub-01_mod-dwi_desc-brain_mask.nii.gz'
    >>> mrcrop.inputs.out_filename = 'sub-01_desc-cropped_dwi.nii.gz'
    >>> mrcrop.run()  # doctest: +SKIP

    """

    _cmd = 'mrcrop'
    input_spec = MRCropInputSpec
    output_spec = MRCropOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['cropped'] = os.path.abspath(self.inputs.out_filename)
        if not isdefined(outputs['cropped']):
            outputs['cropped'] = os.path.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        return name + '_crop.nii.gz'


class MRThresholdInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, mandatory=True, position=-3,
                   argstr='%s', desc='the input image to be thresholded.')

    out_file = File(mandatory=True, position=-2, argstr='%s',
                    desc=' the output binary image mask.')

    abs_value = traits.Float(argstr='-abs %s', position=-1,
                             desc='specify threshold value as absolute intensity.')

    force_writing = traits.Bool(
        argstr='-force', desc="Force file overwriting.")

    quiet = traits.Bool(
        argstr='-quiet', desc="Do not display information messages or progress status.")


class MRThresholdOutputSpec(TraitedSpec):
    thresholded = File(
        exists=True, desc='Path/name of the output binary image mask.')


class MRThreshold(CommandLine):
    """Threshold an image using the `mrthreshold` tool.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> mrthresh = mrt.MRCrop()
    >>> mrthresh.inputs.in_file = 'sub-01_dwi.nii.gz'
    >>> mrthresh.inputs.out_file = 'sub-01_desc-thresholded_dwi.nii.gz'
    >>> mrthresh.run()  # doctest: +SKIP

    """

    _cmd = 'mrthreshold'
    input_spec = MRThresholdInputSpec
    output_spec = MRThresholdOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['thresholded'] = os.path.abspath(self.inputs.out_file)
        return outputs


class MRTransformInputSpec(CommandLineInputSpec):
    in_files = InputMultiPath(exists=True, argstr='%s', mandatory=True, position=-2,
                              desc='Input images to be transformed')

    out_filename = File(genfile=True, argstr='%s',
                        position=-1, desc='Output image')

    invert = traits.Bool(argstr='-inverse', position=1,
                         desc="Invert the specified transform before using it")

    replace_transform = traits.Bool(argstr='-replace', position=1,
                                    desc="replace the current transform by that specified, rather than applying it to the current transform")

    transformation_file = File(exists=True, argstr='-transform %s', position=1,
                               desc='The transform to apply, in the form of a 4x4 ascii file.')

    template_image = File(exists=True, argstr='-template %s', position=1,
                          desc='Reslice the input image to match the specified template image.')

    reference_image = File(exists=True, argstr='-reference %s', position=1,
                           desc='in case the transform supplied maps from the input image onto a reference image, use this option to specify the reference. '
                           'Note that this implicitly sets the -replace option.')

    flip_x = traits.Bool(argstr='-flipx', position=1,
                         desc="assume the transform is supplied assuming a coordinate system with the x-axis reversed relative to the MRtrix convention "
                              "(i.e. x increases from right to left). This is required to handle transform matrices produced by FSL's FLIRT command. "
                              "This is only used in conjunction with the -reference option.")

    interp = traits.Enum('nearest', 'linear', 'cubic', 'sinc',
                         argstr='-interp %s',
                         desc='set the interpolation method to use when reslicing (choices: nearest,linear, cubic, sinc. Default: cubic).')

    quiet = traits.Bool(argstr='-quiet', position=1,
                        desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=1,
                        desc="Display debugging messages.")


class MRTransformOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='the output image of the transformation')


class MRTransform(CommandLine):
    """Apply spatial transformations or reslice images using the `mrtransform` tool.

    Example
    -------
    >>> from cmtklib.interfaces.mrtrix3 import MRTransform
    >>> MRxform = MRTransform()
    >>> MRxform.inputs.in_files = 'anat_coreg.mif'
    >>> MRxform.inputs.interp = 'cubic'
    >>> MRxform.run()  # doctest: +SKIP

    """

    _cmd = 'mrtransform'
    input_spec = MRTransformInputSpec
    output_spec = MRTransformOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_filename):
            outputs['out_file'] = os.path.abspath(self._gen_outfilename())
        else:
            outputs['out_file'] = os.path.abspath(self.inputs.out_filename)
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_files[0])
        return name + '_crop.nii.gz'


class ApplymultipleMRCropInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(File(mandatory=True, exists=True),
                              desc='Files to be cropped')

    template_image = File(mandatory=True, exists=True, desc='Template image')


class ApplymultipleMRCropOutputSpec(TraitedSpec):
    out_files = OutputMultiPath(File(), desc='Cropped files')


class ApplymultipleMRCrop(BaseInterface):
    """Apply MRCrop to a list of images.

    Example
    -------
    >>> from cmtklib.interfaces.mrtrix3 import ApplymultipleMRCrop
    >>> multi_crop = ApplymultipleMRCrop()
    >>> multi_crop.inputs.in_files = ['/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                               'sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                               'sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                               'sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                               'sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> multi_crop.inputs.template_image = 'sub-01_T1w.nii.gz'
    >>> multi_crop.run()  # doctest: +SKIP


    See Also
    --------
    cmtklib.interfaces.mrtrix3.MRCrop
    """

    input_spec = ApplymultipleMRCropInputSpec
    output_spec = ApplymultipleMRCropOutputSpec

    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            ax = MRCrop(in_file=in_file,
                        template_image=self.inputs.template_image)
            ax.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_files'] = glob.glob(os.path.abspath("*.nii.gz"))
        return outputs


class ApplymultipleMRTransformsInputSpec(BaseInterfaceInputSpec):
    in_files = InputMultiPath(
        File(mandatory=True, exists=True), desc='Files to be transformed')

    template_image = File(mandatory=True, exists=True, desc='Template image')


class ApplymultipleMRTransformsOutputSpec(TraitedSpec):
    out_files = OutputMultiPath(File(), desc='Transformed files')


class ApplymultipleMRTransforms(BaseInterface):
    """Apply MRTransform to a list of images.

    Example
    -------
    >>> from cmtklib.interfaces.mrtrix3 import ApplymultipleMRTransforms
    >>> multi_transform = ApplymultipleMRTransforms()
    >>> multi_transform.inputs.in_files = ['/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                    'sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                    'sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                    'sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                    'sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> multi_transform.inputs.template_image = 'sub-01_T1w.nii.gz'
    >>> multi_transform.run()  # doctest: +SKIP


    See Also
    --------
    cmtklib.interfaces.mrtrix3.MRTransform
    """

    input_spec = ApplymultipleMRTransformsInputSpec
    output_spec = ApplymultipleMRTransformsOutputSpec

    def _run_interface(self, runtime):
        for in_file in self.inputs.in_files:
            mt = MRTransform(in_files=in_file,
                             template_image=self.inputs.template_image)
            mt.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_files'] = glob.glob(os.path.abspath("*.nii.gz"))
        return outputs


class ExtractFSLGradInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                   desc='Input images to be read')

    out_grad_fsl = traits.Tuple(File(), File(), argstr='-export_grad_fsl %s %s',
                                desc='export the DWI gradient table to files in FSL (bvecs / bvals) format')


class ExtractFSLGradOutputSpec(TraitedSpec):
    out_grad_fsl = traits.Tuple(File(exists=True), File(exists=True),
                                desc='Outputs [bvecs, bvals] DW gradient scheme (FSL format) if set')


class ExtractFSLGrad(CommandLine):
    """Use `mrinfo` to extract FSL gradient.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> fsl_grad = mrt.ExtractFSLGrad()
    >>> fsl_grad.inputs.in_file = 'sub-01_dwi.mif'
    >>> fsl_grad.inputs.out_grad_fsl = ['sub-01_dwi.bvecs', 'sub-01_dwi.bvals']
    >>> fsl_grad.run()  # doctest: +SKIP

    """

    _cmd = 'mrinfo'
    input_spec = ExtractFSLGradInputSpec
    output_spec = ExtractFSLGradOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_grad_fsl'] = os.path.abspath(self.inputs.out_grad_fsl)
        if not isdefined(outputs['out_grad_fsl']):
            outputs['out_grad_fsl'] = (os.path.abspath(
                'diffusion.bvec'), os.path.abspath('diffusion.bval'))
        return outputs


class ExtractMRTrixGradInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                   desc='Input images to be read')

    out_grad_mrtrix = File(argstr='-export_grad_mrtrix %s',
                           desc='export the DWI gradient table to file in MRtrix format')


class ExtractMRTrixGradOutputSpec(TraitedSpec):
    out_grad_mrtrix = File(
        exits=True, desc='Output MRtrix gradient text file if set')


class ExtractMRTrixGrad(CommandLine):
    """Use `mrinfo` to extract mrtrix gradient text file.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> mrtrix_grad = mrt.ExtractMRTrixGrad()
    >>> mrtrix_grad.inputs.in_file = 'sub-01_dwi.mif'
    >>> mrtrix_grad.inputs.out_grad_mrtrix = 'sub-01_gradient.txt'
    >>> mrtrix_grad.run()  # doctest: +SKIP

    """

    _cmd = 'mrinfo'
    input_spec = ExtractMRTrixGradInputSpec
    output_spec = ExtractMRTrixGradOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_grad_mrtrix'] = os.path.abspath(
            self.inputs.out_grad_mrtrix)
        if not isdefined(outputs['out_grad_mrtrix']):
            outputs['out_grad_mrtrix'] = os.path.abspath('grad.txt')
        return outputs


class DWI2TensorInputSpec(CommandLineInputSpec):
    in_file = InputMultiPath(exists=True, argstr='%s', mandatory=True, position=-2,
                             desc='Diffusion-weighted images')

    out_filename = File(genfile=True, argstr='%s',
                        position=-1, desc='Output tensor filename')

    in_mask_file = File(exists=True, argstr='-mask %s',
                        position=-3, desc='Input DWI mask')

    encoding_file = File(argstr='-grad %s', position=2,
                         desc='Encoding file, , supplied as a 4xN text file with each line is in the format [ X Y Z b ], '
                         'where [ X Y Z ] describe the direction of the applied gradient, and b gives the b-value in units (1000 s/mm^2). '
                         'See FSL2MRTrix()')

    ignore_slice_by_volume = traits.List(traits.Int, argstr='-ignoreslices %s', sep=' ', position=2, minlen=2, maxlen=2,
                                         desc='Requires two values (i.e. [34 1] for [Slice Volume] Ignores the image slices '
                                         'specified when computing the tensor. Slice here means the z coordinate of the slice to be ignored.')

    ignore_volumes = traits.List(traits.Int, argstr='-ignorevolumes %s', sep=' ', position=2, minlen=1,
                                 desc='Requires two values (i.e. [2 5 6] for [Volumes] Ignores the image volumes specified when computing the tensor.')

    quiet = traits.Bool(argstr='-quiet', position=1,
                        desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=1,
                        desc="Display debugging messages.")


class DWI2TensorOutputSpec(TraitedSpec):
    tensor = File(
        exists=True, desc='path/name of output diffusion tensor image')


class DWI2Tensor(CommandLine):
    """Converts diffusion-weighted images to tensor images using `dwi2tensor`.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> dwi2tensor = mrt.DWI2Tensor()
    >>> dwi2tensor.inputs.in_file = 'dwi.mif'
    >>> dwi2tensor.inputs.encoding_file = 'encoding.txt'
    >>> dwi2tensor.run()  # doctest: +SKIP

    """

    _cmd = 'dwi2tensor'
    input_spec = DWI2TensorInputSpec
    output_spec = DWI2TensorOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_filename):
            outputs['tensor'] = op.abspath(self._gen_outfilename())
        else:
            outputs['tensor'] = op.abspath(self.inputs.out_filename)
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file[0])
        return name + '_tensor.mif'


class Tensor2VectorInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                   desc='Diffusion tensor image')

    out_filename = File(genfile=True, argstr='-vector %s',
                        position=-1, desc='Output vector filename')

    quiet = traits.Bool(argstr='-quiet', position=1,
                        desc="Do not display information messages or progress status.")

    debug = traits.Bool(argstr='-debug', position=1,
                        desc="Display debugging messages.")


class Tensor2VectorOutputSpec(TraitedSpec):
    vector = File(
        exists=True, desc='the output image of the major eigenvectors of the diffusion tensor image.')


class Tensor2Vector(CommandLine):
    """Generates a map of the major eigenvectors of the tensors in each voxel using `tensor2metric`.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> tensor2vector = mrt.Tensor2Vector()
    >>> tensor2vector.inputs.in_file = 'dwi_tensor.mif'
    >>> tensor2vector.run()  # doctest: +SKIP

    """

    _cmd = 'tensor2metric'
    input_spec = Tensor2VectorInputSpec
    output_spec = Tensor2VectorOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['vector'] = op.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        return name + '_vector.mif'


class EstimateResponseForSHInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True,
                   position=2, desc='Diffusion-weighted images')

    algorithm = traits.Enum('dhollander', 'fa', 'manual', 'msmt_5tt', 'tax', 'tournier', argstr='%s', position=1,
                            desc='Select the algorithm to be used to derive the response function; '
                            'additional details and options become available once an algorithm is nominated. '
                            'Options are: dhollander, fa, manual, msmt_5tt, tax, tournier')

    mask_image = File(exists=True, mandatory=True, argstr='-mask %s', position=-1,
                      desc='only perform computation within the specified binary brain mask image')

    out_filename = File(genfile=True, argstr='%s',
                        position=3, desc='Output filename')

    encoding_file = File(exists=True, argstr='-grad %s', mandatory=True, position=-2,
                         desc='Gradient encoding, supplied as a 4xN text file with each line is in the format [ X Y Z b ], '
                         'where [ X Y Z ] describe the direction of the applied gradient, and b gives the b-value in units (1000 s/mm^2). '
                         'See FSL2MRTrix')
    maximum_harmonic_order = traits.Int(argstr='-lmax %s', position=-3,
                                        desc='set the maximum harmonic order for the output series. '
                                        'By default, the program will use the highest possible lmax given the number of diffusion-weighted images.')
    # normalise = traits.Bool(argstr='-normalise', desc='normalise the DW signal to the b=0 image')

    quiet = traits.Bool(
        argstr='-quiet', desc='Do not display information messages or progress status.')

    debug = traits.Bool(argstr='-debug', desc='Display debugging messages.')


class EstimateResponseForSHOutputSpec(TraitedSpec):
    response = File(exists=True, desc='Spherical harmonics image')


class EstimateResponseForSH(CommandLine):
    """Estimates the fibre response function for use in spherical deconvolution using `dwi2response`.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> estresp = mrt.EstimateResponseForSH()
    >>> estresp.inputs.in_file = 'dwi.mif'
    >>> estresp.inputs.mask_image = 'dwi_WMProb.mif'
    >>> estresp.inputs.encoding_file = 'encoding.txt'
    >>> estresp.run()  # doctest: +SKIP

    """

    _cmd = 'dwi2response'
    input_spec = EstimateResponseForSHInputSpec
    output_spec = EstimateResponseForSHOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['response'] = op.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        return name + '_ER.mif'


class ConstrainedSphericalDeconvolutionInputSpec(CommandLineInputSpec):
    algorithm = traits.Enum('csd', argstr='%s', mandatory=True, position=-4,
                            desc='use CSD algorithm for FOD estimation')

    in_file = File(exists=True, argstr='%s', mandatory=True,
                   position=-3, desc='diffusion-weighted image')

    response_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
                         desc='the diffusion-weighted signal response function for a single fibre population (see EstimateResponse)')

    out_filename = File(genfile=True, argstr='%s',
                        position=-1, desc='Output filename')

    mask_image = File(exists=True, argstr='-mask %s', position=2,
                      desc='only perform computation within the specified binary brain mask image')

    encoding_file = File(exists=True, argstr='-grad %s', position=1,
                         desc='Gradient encoding, supplied as a 4xN text file with each line is in the format [ X Y Z b ], '
                         'where [ X Y Z ] describe the direction of the applied gradient, and b gives the b-value in units (1000 s/mm^2). '
                         'See FSL2MRTrix')

    filter_file = File(exists=True, argstr='-filter %s', position=-2,
                       desc='a text file containing the filtering coefficients for each even harmonic order.'
                            'the linear frequency filtering parameters used for the initial linear spherical deconvolution step (default = [ 1 1 1 0 0 ]).')

    lambda_value = traits.Float(argstr='-norm_lambda %s',
                                desc='the regularisation parameter lambda that controls the strength of the constraint (default = 1.0).')

    maximum_harmonic_order = traits.Int(argstr='-lmax %s',
                                        desc='set the maximum harmonic order for the output series. '
                                        'By default, the program will use the highest possible lmax given the number of diffusion-weighted images.')

    threshold_value = traits.Float(argstr='-threshold %s',
                                   desc='the threshold below which the amplitude of the FOD is assumed to be zero, '
                                   'expressed as a fraction of the mean value of the initial FOD (default = 0.1)')

    iterations = traits.Int(argstr='-niter %s',
                            desc='the maximum number of iterations to perform for each voxel (default = 50)')

    directions_file = File(exists=True, argstr='-directions %s', position=-2,
                           desc='a text file containing the [ el az ] pairs for the directions: '
                           'Specify the directions over which to apply the non-negativity constraint '
                           '(by default, the built-in 300 direction set is used)')

    # normalise = traits.Bool(argstr='-normalise', position=3, desc="normalise the DW signal to the b=0 image")


class ConstrainedSphericalDeconvolutionOutputSpec(TraitedSpec):
    spherical_harmonics_image = File(
        exists=True, desc='Spherical harmonics image')


class ConstrainedSphericalDeconvolution(CommandLine):
    """Perform non-negativity constrained spherical deconvolution using `dwi2fod`.

    Note that this program makes use of implied symmetries in the diffusion profile.
    First, the fact the signal attenuation profile is real implies that it has conjugate symmetry,
    i.e. Y(l,-m) = Y(l,m)* (where * denotes the complex conjugate). Second, the diffusion profile should be
    antipodally symmetric (i.e. S(x) = S(-x)), implying that all odd l components should be zero.
    Therefore, this program only computes the even elements. 	Note that the spherical harmonics equations used here
    differ slightly from those conventionally used, in that the (-1)^m factor has been omitted. This should be taken
    into account in all subsequent calculations. Each volume in the output image corresponds to a different spherical
    harmonic component, according to the following convention:

    * [0] Y(0,0)
    * [1] Im {Y(2,2)}
    * [2] Im {Y(2,1)}
    * [3] Y(2,0)
    * [4] Re {Y(2,1)}
    * [5] Re {Y(2,2)}
    * [6] Im {Y(4,4)}
    * [7] Im {Y(4,3)}


    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> csdeconv = mrt.ConstrainedSphericalDeconvolution()
    >>> csdeconv.inputs.in_file = 'dwi.mif'
    >>> csdeconv.inputs.encoding_file = 'encoding.txt'
    >>> csdeconv.run()                                          # doctest: +SKIP
    """

    _cmd = 'dwi2fod'
    input_spec = ConstrainedSphericalDeconvolutionInputSpec
    output_spec = ConstrainedSphericalDeconvolutionOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['spherical_harmonics_image'] = op.abspath(
            self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        return name + '_CSD.mif'


class Generate5ttInputSpec(CommandLineInputSpec):
    algorithm = traits.Enum(
        'fsl',
        'gif',
        'freesurfer',
        'hsvs',
        argstr='%s',
        position=-3,
        mandatory=True,
        desc='tissue segmentation algorithm')

    in_file = File(
        exists=True,
        argstr='-nocrop -sgm_amyg_hipp %s',
        mandatory=True,
        position=-2,
        desc='input image')

    out_file = File(
        argstr='%s', mandatory=True, position=-1, desc='output image')


class Generate5ttOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output image')


class Generate5tt(CommandLine):
    """Generate a 5TT image suitable for ACT using the selected algorithm using `5ttgen`.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> gen5tt = mrt.Generate5tt()
    >>> gen5tt.inputs.in_file = 'T1.nii.gz'
    >>> gen5tt.inputs.algorithm = 'fsl'
    >>> gen5tt.inputs.out_file = '5tt.mif'
    >>> gen5tt.cmdline                             # doctest: +ELLIPSIS
    '5ttgen fsl T1.nii.gz 5tt.mif'
    >>> gen5tt.run()                               # doctest: +SKIP

    """

    _cmd = '5ttgen'
    input_spec = Generate5ttInputSpec
    output_spec = Generate5ttOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputs


class GenerateGMWMInterfaceInputSpec(CommandLineInputSpec):
    in_file = File(
        exists=True,
        argstr='%s',
        mandatory=True,
        position=-2,
        desc='input 5TT image')

    out_file = File(
        argstr='%s', mandatory=True, position=-1, desc='output GW/WM interface image')


class GenerateGMWMInterfaceOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output image')


class GenerateGMWMInterface(CommandLine):
    """Generate a grey matter-white matter interface mask from the 5TT image using `5tt2gmwmi`.

    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as cmp_mrt
    >>> genWMGMI = cmp_mrt.Generate5tt()
    >>> genWMGMI.inputs.in_file = '5tt.mif'
    >>> genWMGMI.inputs.out_file = 'gmwmi.mif'
    >>> genGMWMI.run()  # doctest: +SKIP

    """

    _cmd = '5tt2gmwmi'
    input_spec = GenerateGMWMInterfaceInputSpec
    output_spec = GenerateGMWMInterfaceOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputs


class StreamlineTrackInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=2,
                   desc='the image containing the source data.'
                        'The type of data required depends on the type of tracking as set in the preceeding argument.'
                        'For DT methods, the base DWI are needed.'
                        'For SD methods, the SH harmonic coefficients of the FOD are needed.')

    seed_file = File(exists=True, argstr='-seed_image %s', desc='seed file')

    seed_spec = traits.List(traits.Int, desc='seed specification in voxels and radius (x y z r)',
                            argstr='-seed_sphere %s', minlen=4, maxlen=4, sep=',', units='voxels')
    # include_file = File(exists=True, argstr='-include %s', mandatory=False, desc='inclusion file')
    # include_spec = traits.List(traits.Int, desc='inclusion specification in voxels and radius (x y z r)',
    #     argstr='-seed %s', minlen=4, maxlen=4, sep=',', units='voxels')
    # exclude_file = File(exists=True, argstr='-exclude %s', mandatory=False, desc='exclusion file')
    # exclude_spec = traits.List(traits.Int, desc='exclusion specification in voxels and radius (x y z r)',
    #     argstr='-exclude %s', minlen=4, maxlen=4, sep=',', units='voxels')

    mask_file = File(exists=True, argstr='-mask %s', mandatory=False,
                     desc='mask file. Only tracks within mask.')
    # mask_spec = traits.List(traits.Int, desc='Mask specification in voxels and radius (x y z r).'
    #                                          'Tracks will be terminated when they leave the ROI.',
    #     argstr='-mask %s', minlen=4, maxlen=4, sep=',', units='voxels')

    gradient_encoding_file = File(exists=True, argstr='-grad %s', mandatory=False,
                                  desc='Gradient encoding, supplied as a 4xN text file with each line is in the format [ X Y Z b ]'
                                  'where [ X Y Z ] describe the direction of the applied gradient, and b gives the b-value'
                                  'in units (1000 s/mm^2). See FSL2MRTrix')

    inputmodel = traits.Enum('FACT', 'iFOD1', 'iFOD2', 'Nulldist1', 'Nulldist2', 'SD_Stream', 'Seedtest', 'Tensor_Det',
                             'Tensor_Prob',
                             argstr='-algorithm %s',
                             desc='specify the tractography algorithm to use. Valid choices are:'
                             'FACT, iFOD1, iFOD2, Nulldist1, Nulldist2, SD_Stream, Seedtest, Tensor_Det, Tensor_Prob (default: iFOD2).',
                             usedefault=True, position=-3)

    stop = traits.Bool(
        argstr='-stop', desc="stop track as soon as it enters any of the include regions.")

    do_not_precompute = traits.Bool(argstr='-noprecomputed',
                                    desc="Turns off precomputation of the legendre polynomial values."
                                    "Warning: this will slow down the algorithm by a factor of approximately 4.")

    unidirectional = traits.Bool(argstr='-seed_unidirectional',
                                 desc="Track from the seed point in one direction only (default is to track in both directions).")
    # no_mask_interpolation = traits.Bool(argstr='-nomaskinterp', desc="Turns off trilinear interpolation of mask images.")

    step_size = traits.Float(argstr='-step %s', units='mm',
                             desc="Set the step size of the algorithm in mm (default is 0.5).")
    # minimum_radius_of_curvature = traits.Float(argstr='-curvature %s', units='mm',
    #     desc="Set the minimum radius of curvature (default is 2 mm for DT_STREAM, 0 for SD_STREAM, 1 mm for SD_PROB and DT_PROB)")

    desired_number_of_tracks = traits.Int(argstr='-select %d',
                                          desc='Sets the desired number of tracks.'
                                          'The program will continue to generate tracks until this number of tracks have been selected'
                                          'and written to the output file (default is 100 for *_STREAM methods, 1000 for *_PROB methods).')

    maximum_number_of_seeds = traits.Int(argstr='-seeds %d',
                                         desc='Sets the maximum number of tracks to generate.'
                                         'The program will not generate more tracks than this number,'
                                         "even if the desired number of tracks hasn't yet been reached"
                                         '(default is 1000 x number of streamlines).')

    rk4 = traits.Bool(argstr='-rk4',
                      desc='use 4th-order Runge-Kutta integration (slower, but eliminates curvature overshoot in 1st-order deterministic methods)')

    minimum_tract_length = traits.Float(argstr='-minlength %s', units='mm',
                                        desc="Sets the minimum length of any track in millimeters (default is 5 mm).")

    maximum_tract_length = traits.Float(argstr='-maxlength %s', units='mm',
                                        desc="Sets the maximum length of any track in millimeters (default is 500 mm).")

    angle = traits.Float(argstr='-angle %s', units='degrees',
                         desc="Set the maximum angle between successive steps (default is 90deg x stepsize / voxelsize).")

    cutoff_value = traits.Float(argstr='-cutoff %s', units='NA',
                                desc="Set the FA or FOD amplitude cutoff for terminating tracks (default is 0.5).")

    initial_cutoff_value = traits.Float(argstr='-seed_cutoff %s', units='NA',
                                        desc="Sets the minimum FA or FOD amplitude for initiating tracks (default is twice the normal cutoff).")

    initial_direction = traits.List(traits.Int, desc='Specify the initial tracking direction as a vector',
                                    argstr='-seed_direction %s', minlen=2, maxlen=2, units='voxels')

    # Anatomically-Constrained Tractography options
    act_file = File(
        exists=True,
        argstr='-act %s',
        desc=('use the Anatomically-Constrained Tractography framework during'
              ' tracking; provided image must be in the 5TT '
              '(five - tissue - type) format'))

    backtrack = traits.Bool(
        argstr='-backtrack', desc='allow tracks to be truncated')

    crop_at_gmwmi = traits.Bool(
        argstr='-crop_at_gmwmi',
        desc='crop streamline endpoints more precisely as they cross the GM-WM interface')

    seed_gmwmi = File(
        exists=True,
        argstr='-seed_gmwmi %s',
        requires=['act_file'],
        desc='seed from the grey matter - white matter interface (only valid if using ACT framework)')

    out_file = File(argstr='%s', position=-1,
                    genfile=True, desc='output data file')


class StreamlineTrackOutputSpec(TraitedSpec):
    tracked = File(
        exists=True, desc='output file containing reconstructed tracts')


class StreamlineTrack(CommandLine):
    """Performs tractography using `tckgen`.

    It can use one of the following models::

        'dt_prob', 'dt_stream', 'sd_prob', 'sd_stream'

    where 'dt' stands for diffusion tensor,
    'sd' stands for spherical deconvolution, and
    'prob' stands for probabilistic.


    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as mrt
    >>> strack = mrt.StreamlineTrack()
    >>> strack.inputs.inputmodel = 'SD_PROB'
    >>> strack.inputs.in_file = 'data.Bfloat'
    >>> strack.inputs.seed_file = 'seed_mask.nii'
    >>> strack.run()  # doctest: +SKIP

    """

    _cmd = 'tckgen'
    input_spec = StreamlineTrackInputSpec
    output_spec = StreamlineTrackOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            outputs['tracked'] = os.path.abspath(self._gen_outfilename())
        else:
            outputs['tracked'] = os.path.abspath(self.inputs.out_file)
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        return name + '_tracked.tck'


class MRTrix3Base(CommandLine):
    """"MRtrix3Base base class inherited by FilterTractogram class."""

    def _format_arg(self, name, trait_spec, value):
        if name == 'nthreads' and value == 0:
            value = 1
            try:
                from multiprocessing import cpu_count
                value = cpu_count()
            except Exception:
                logger.warn('Number of threads could not be computed')
                # pass
            return trait_spec.argstr % value

        if name == 'in_bvec':
            return trait_spec.argstr % (value, self.inputs.in_bval)

        return super(MRTrix3Base, self)._format_arg(name, trait_spec, value)

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        try:
            if (isdefined(self.inputs.grad_file) or
                    isdefined(self.inputs.grad_fsl)):
                skip += ['in_bvec', 'in_bval']

            is_bvec = isdefined(self.inputs.in_bvec)
            is_bval = isdefined(self.inputs.in_bval)
            if is_bvec or is_bval:
                if not is_bvec or not is_bval:
                    raise RuntimeError('If using bvecs and bvals inputs, both'
                                       'should be defined')
                skip += ['in_bval']
        except AttributeError:
            pass

        return super(MRTrix3Base, self)._parse_inputs(skip=skip)


class FilterTractogramInputSpec(CommandLineInputSpec):
    in_tracks = File(exists=True, mandatory=True, argstr='%s',
                     position=-3, desc='Input track file in TCK format')
    in_fod = File(exists=True, mandatory=True, argstr='%s', position=-2,
                  desc='Input image containing the spherical harmonics of the fibre orientation distributions')
    act_file = File(exists=True, argstr='-act %s',
                    position=-4, desc='ACT 5TT image file')
    out_file = File(argstr='%s', position=-1,
                    desc='Output filtered tractogram')


class FilterTractogramOutputSpec(TraitedSpec):
    out_tracks = File(
        exists=True, desc='Output filtered tractogram')


class FilterTractogram(MRTrix3Base):
    """Spherical-deconvolution informed filtering of tractograms using `tcksift` [Smith2013SIFT]_.

    References
    ----------
    .. [Smith2013SIFT] R.E. Smith et al., NeuroImage 67 (2013), pp. 298–312, <https://www.ncbi.nlm.nih.gov/pubmed/23238430>.


    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as cmp_mrt
    >>> mrtrix_sift = cmp_mrt.FilterTractogram()
    >>> mrtrix_sift.inputs.in_tracks = 'tractogram.tck'
    >>> mrtrix_sift.inputs.in_fod = 'spherical_harmonics_image.nii.gz'
    >>> mrtrix_sift.inputs.out_file = 'sift_tractogram.tck'
    >>> mrtrix_sift.run()   # doctest: +SKIP

    """

    _cmd = 'tcksift'
    input_spec = FilterTractogramInputSpec
    output_spec = FilterTractogramOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.out_file):
            outputs['out_tracks'] = op.abspath('SIFT-filtered_tractogram.tck')
        else:
            outputs['out_tracks'] = op.abspath(self.inputs.out_file)

        return outputs


class SIFT2InputSpec(CommandLineInputSpec):
    in_tracks = File(exists=True, mandatory=True, argstr='%s',
                     position=-3, desc='Input track file in TCK format')
    in_fod = File(exists=True, mandatory=True, argstr='%s', position=-2,
                  desc='Input image containing the spherical harmonics of the fibre orientation distributions')
    act_file = File(exists=True, argstr='-act %s',
                    position=-4, desc='ACT 5TT image file')
    out_file = File(argstr='%s', position=-1,
                    desc='Output text file containing the weighting factor for each streamline')


class SIFT2OutputSpec(TraitedSpec):
    out_weights = File(
            exists=True, desc='Output text file containing the weighting factor for each streamline')


class SIFT2(MRTrix3Base):
    """Determine an appropriate cross-sectional area multiplier for each streamline using `tcksift2` [Smith2015SIFT2]_.

    References
    ----------
    .. [Smith2015SIFT2] Smith RE et al., Neuroimage, 2015, 119:338-51. <https://doi.org/10.1016/j.neuroimage.2015.06.092>.


    Example
    -------
    >>> import cmtklib.interfaces.mrtrix3 as cmp_mrt
    >>> mrtrix_sift2 = cmp_mrt.SIFT2()
    >>> mrtrix_sift2.inputs.in_tracks = 'tractogram.tck'
    >>> mrtrix_sift2.inputs.in_fod = 'spherical_harmonics_image.nii.gz'
    >>> mrtrix_sift2.inputs.out_file = 'sift2_fiber_weights.txt'
    >>> mrtrix_sift2.run()  # doctest: +SKIP

    """

    _cmd = 'tcksift2'
    input_spec = FilterTractogramInputSpec
    output_spec = FilterTractogramOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.out_file):
            outputs['out_weights'] = op.abspath('streamlines_weights.txt')
        else:
            outputs['out_weights'] = op.abspath(self.inputs.out_file)

        return outputs

# class MRTrixInfoInputSpec(CommandLineInputSpec):
#     in_file = File(exists=True, argstr='%s', mandatory=True, position=-2,
#         desc='Input images to be read')
#     _xor_inputs = ('out_grad_mrtrix','out_grad_fsl')
#     out_grad_mrtrix = File(argstr='-export_grad_mrtrix %s',
#                            desc='export the DWI gradient table to file in MRtrix format',
#                            xor=_xor_inputs)
#     out_grad_fsl =  traits.Tuple(File(),File(), argstr='-export_grad_fsl %s %s',
#                                                 desc='export the DWI gradient table to files in FSL (bvecs / bvals) format',
#                                                 xor=_xor_inputs)

# class MRTrixInfoOutputSpec(TraitedSpec):
#     out_grad_mrtrix = traits.Tuple(File(exists=True),File(exists=True),
#                                    desc='Outputs [bvecs, bvals] DW gradient scheme (FSL format) if set')
#     out_grad_fsl = File(exits=True,desc='Output MRtrix gradient text file if set')

# class MRTrixInfo(CommandLine):
#     """
#     Prints out relevant header information found in the image specified.

#     Example
#     -------

#     >>> import nipype.interfaces.mrtrix as mrt
#     >>> MRinfo = mrt.MRTrixInfo()
#     >>> MRinfo.inputs.in_file = 'dwi.mif'
#     >>> MRinfo.run()                                    # doctest: +SKIP
#     """

#     _cmd = 'mrinfo'
#     input_spec=MRTrixInfoInputSpec
#     output_spec=MRTrixInfoOutputSpec

#     def _list_outputs(self):
#         outputs = self.output_spec().get()
#         outputs['out_grad_mrtrix'] = op.abspath(self.inputs.out_grad_mrtrix)
#         if isdefined(self.inputs.out_grad_mrtrix):
#             outputs['out_grad_mrtrix'] = op.abspath(self.inputs.out_grad_mrtrix)
#         if isdefined(self.inputs.out_grad_fsl):
#             outputs['out_grad_fsl'] =
#                 (op.abspath(self.inputs.out_grad_fsl[0]),op.abspath(self.inputs.out_grad_mrtrix[1]))
#         return outputs
