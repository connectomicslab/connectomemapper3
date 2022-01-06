# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""The Diffusion Toolkit module provides Nipype interfaces for the Diffusion Toolkit missing in nipype or modified.

.. note:

    Module not used anymore by CMP3.

"""

import re
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
import os
import glob

__docformat__ = 'restructuredtext'

from nipype.interfaces.base import (TraitedSpec, File, traits, CommandLine,
                                    CommandLineInputSpec, isdefined, OutputMultiPath)


class HARDIMatInputSpec(CommandLineInputSpec):
    bvecs = File(exists=True, desc='b vectors file',
                 argstr='%s', position=1)
    bvals = File(exists=True, desc='b values file')
    gradient_table = File(
        exists=True, desc='Input gradient table', position=1, argstr='%s')
    out_file = File("recon_mat.dat", desc='output matrix file',
                    argstr='%s', usedefault=True, position=2)
    order = traits.Int(argsstr='-order %s',
                       desc="""maximum order of spherical harmonics. must be even number. default
                            is 4""")
    odf_file = File(exists=True, argstr='-odf %s',
                    desc="""filename that contains the reconstruction points on a HEMI-sphere.
                    use the pre-set 181 points by default""")
    reference_file = File(exists=True, argstr='-ref %s',
                          desc="""provide a dicom or nifti image as the reference for the program to
                          figure out the image orientation information. if no such info was
                          found in the given image header, the next 5 options -info, etc.,
                          will be used if provided. if image orientation info can be found
                          in the given reference, all other 5 image orientation options will
                          be IGNORED""")
    image_info = File(exists=True, argstr='-info %s',
                      desc="""specify image information file. the image info file is generated
                      from original dicom image by diff_unpack program and contains image
                      orientation and other information needed for reconstruction and
                      tracking. by default will look into the image folder for .info file""")
    image_orientation_vectors = traits.List(traits.Float(), minlen=6, maxlen=6,
                                            desc="""specify image orientation vectors. if just one argument given,
                                            will treat it as filename and read the orientation vectors from
                                            the file. if 6 arguments are given, will treat them as 6 float
                                            numbers and construct the 1st and 2nd vector and calculate the 3rd
                                            one automatically. This information will be used to determine image orientation,
                                            as well as to adjust gradient vectors with oblique angle when""", argstr="-iop %f")
    oblique_correction = traits.Bool(desc="""when oblique angle(s) applied, some SIEMENS dti
        protocols do not adjust gradient accordingly, thus it requires adjustment for correct
        diffusion tensor calculation""", argstr="-oc")


class HARDIMatOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='output matrix file')


class HARDIMat(CommandLine):
    """Use hardi_mat to calculate a reconstruction matrix from a gradient table.

    Examples
    --------
    >>> hardi_mat = HARDIMat()
    >>> hardi_mat.inputs.bvecs = 'sub-01_dwi.bvec'
    >>> hardi_mat.inputs.bvals = 'sub-01_dwi.bval'
    >>> hardi_mat.inputs.gradient_table = 'sub-01_grad.txt'
    >>> hardi_mat.inputs.out_file = 'recon_mat.dat'
    >>> hardi_mat.inputs.order = 8
    >>> hardi_mat.inputs.reference_file = 'sub-01_dwi.nii.gz'
    >>> hardi_mat.run()  # doctest: +SKIP

    """

    input_spec = HARDIMatInputSpec
    output_spec = HARDIMatOutputSpec

    _cmd = 'hardi_mat'

    def _create_gradient_matrix(self, bvecs_file, bvals_file):
        _gradient_matrix_file = 'gradient_matrix.txt'
        bvals = [val for val in re.split(
             r'\s+', open(bvals_file).readline().strip())]
        bvecs_f = open(bvecs_file)
        bvecs_x = [val for val in re.split(r'\s+', bvecs_f.readline().strip())]
        bvecs_y = [val for val in re.split(r'\s+', bvecs_f.readline().strip())]
        bvecs_z = [val for val in re.split(r'\s+', bvecs_f.readline().strip())]
        bvecs_f.close()
        gradient_matrix_f = open(_gradient_matrix_file, 'w')
        for i in range(len(bvals)):
            if int(bvals[i]) == 0:
                continue
            gradient_matrix_f.write("%s %s %s\n" % (
                bvecs_x[i], bvecs_y[i], bvecs_z[i]))
        gradient_matrix_f.close()
        return _gradient_matrix_file

    def _format_arg(self, name, spec, value):
        if name == "bvecs":
            new_val = self._create_gradient_matrix(
                self.inputs.bvecs, self.inputs.bvals)
            return super(HARDIMat, self)._format_arg("bvecs", spec, new_val)
        return super(HARDIMat, self)._format_arg(name, spec, value)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(self.inputs.out_file)
        return outputs


class DiffUnpackInputSpec(CommandLineInputSpec):
    input_dicom = File(exists=True, mandatory=True,
                       desc='input dicom file', argstr='%s', position=1)
    out_prefix = traits.Str(
        'output', desc='Output file prefix', argstr='%s', usedefault=True, position=2)
    output_type = traits.Enum('nii', 'analyze', 'ni1', 'nii.gz', argstr='-ot %s', desc='output file type',
                              usedefault=True)
    split = traits.Bool(desc="""instead of saving everything in one big multi-timepoint 4D image,
          split it into seperate files, one timepoint per file""", argstr='-split')


class DiffUnpackOutputSpec(TraitedSpec):
    converted_files = OutputMultiPath(desc='converted files')


class DiffUnpack(CommandLine):
    """Use `diff_unpack` to convert dicom files to multiple formats.

    Examples
    --------
    >>> convert = DiffUnpack()
    >>> convert.inputs.input_dicom = '/path/to/sub-01_dwi.dcm'
    >>> convert.inputs.out_prefix = 'output'
    >>> convert.inputs.output_type = 'nii.gz'
    >>> convert.run()  # doctest: +SKIP

    """

    input_spec = DiffUnpackInputSpec
    output_spec = DiffUnpackOutputSpec

    _cmd = "diff_unpack"

    def _list_outputs(self):
        outputs = self.output_spec().get()

        outputs['converted_files'] = glob.glob(
            os.path.abspath(self.inputs.out_prefix + '*'))
        return outputs


class DTIReconInputSpec(CommandLineInputSpec):
    DWI = File(desc='Input diffusion volume', argstr='%s',
               exists=True, mandatory=True, position=1)
    out_prefix = traits.Str("dti", desc='Output file prefix',
                            argstr='%s', usedefault=True, position=2)
    output_type = traits.Enum('nii', 'analyze', 'ni1', 'nii.gz', argstr='-ot %s', desc='output file type',
                              usedefault=True)
    gradient_matrix = File(desc="""specify gradient matrix to use. required.""", argstr='-gm %s', exists=True,
                           mandatory=True, position=3)
    multiple_b_values = traits.Bool(desc="""if 'MultiBvalue' is 'true'
          or 1, it will either use the bvalues specified as the 4th component
          of each gradient vector, or use max b value scaled by the magnitude
          of the vector.""", argstr='%d', position=4)
    b_value = traits.Int(desc="""set b value or maximum b value for multi-bvalue data. default is 1000""",
                         argstr='-b %d')
    number_of_b0 = traits.Int(desc="""number of repeated b0 images on top. default is 1. the program
          assumes b0 images are on top""", argstr='-b0 %d')
    n_averages = traits.Int(desc='Number of averages', argstr='-nex %s')
    image_orientation_vectors = traits.List(traits.Float(), minlen=6, maxlen=6, desc="""specify image orientation vectors. if just one argument given,
        will treat it as filename and read the orientation vectors from
        the file. if 6 arguments are given, will treat them as 6 float
        numbers and construct the 1st and 2nd vector and calculate the 3rd
        one automatically.
        this information will be used to determine image orientation,
        as well as to adjust gradient vectors with oblique angle when""", argstr="-iop %f")
    oblique_correction = traits.Bool(desc="""when oblique angle(s) applied, some SIEMENS dti protocols do not
        adjust gradient accordingly, thus it requires adjustment for correct
        diffusion tensor calculation""", argstr="-oc")
    b0_threshold = traits.Float(desc="""program will use b0 image with the given threshold to mask out high
        background of fa/adc maps. by default it will calculate threshold
        automatically. but if it failed, you need to set it manually.""", argstr="-b0_th")


class DTIReconOutputSpec(TraitedSpec):
    ADC = File(exists=True)
    B0 = File(exists=True)
    DWI = File(exists=True)
    L1 = File(exists=True)
    L2 = File(exists=True)
    L3 = File(exists=True)
    exp = File(exists=True)
    FA = File(exists=True)
    FA_color = File(exists=True)
    tensor = File(exists=True)
    V1 = File(exists=True)
    V2 = File(exists=True)
    V3 = File(exists=True)


class DTIRecon(CommandLine):
    """Use dti_recon to generate tensors and other maps.

    .. note::

        Not used anymore by CMP3

    """

    input_spec = DTIReconInputSpec
    output_spec = DTIReconOutputSpec

    _cmd = 'dti_recon'

    def _list_outputs(self):
        out_prefix = self.inputs.out_prefix
        output_type = self.inputs.output_type

        outputs = self.output_spec().get()
        outputs['ADC'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_adc.' + output_type))
        outputs['B0'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_b0.' + output_type))
        outputs['DWI'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_dwi.' + output_type))
        outputs['L1'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_e1.' + output_type))
        outputs['L2'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_e2.' + output_type))
        outputs['L3'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_e3.' + output_type))
        outputs['exp'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_exp.' + output_type))
        outputs['FA'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_fa.' + output_type))
        outputs['FA_color'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_fa_color.' + output_type))
        outputs['tensor'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_tensor.' + output_type))
        outputs['V1'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_v1.' + output_type))
        outputs['V2'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_v2.' + output_type))
        outputs['V3'] = os.path.abspath(fname_presuffix(
            "", prefix=out_prefix, suffix='_v3.' + output_type))

        return outputs
