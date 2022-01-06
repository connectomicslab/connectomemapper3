# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""The ANTs module provides Nipype interfaces for the ANTs registration toolbox missing in nipype or modified."""
import os
import glob

from traits.api import *

from nipype.interfaces.base import traits, \
    TraitedSpec, InputMultiPath, OutputMultiPath, \
    BaseInterface, BaseInterfaceInputSpec

from nipype.interfaces.ants.resampling import ApplyTransforms


# class RegistrationSyNInputSpec(BaseInterfaceInputSpec):
#     input_image = File(desc='image to be registered')
#     target_image = File(desc='Fixed (target) image')
#     transform_type = Str('s')
#     number_of_cores = Int(mp.cpu_count())
#
# class RegitrationSyNOutputSpec(TraitedSpec):
#
# class RegistrationSyN(BaseInterface):
#     input_spec = RegistrationSyNInputSpec
#     output_spec = RegistrationSyNOutputSpec
#
#     def _run_interface(self, runtime):
#
#         return runtime
#
#     def _list_outputs(self):
#         outputs = self._outputs().get()
#         outputs['output_images'] = glob.glob(os.path.abspath("*.nii.gz"))
#         return outputs


class MultipleANTsApplyTransformsInputSpec(BaseInterfaceInputSpec):
    input_images = InputMultiPath(
        File(desc='files to be registered', mandatory=True, exists=True))

    transforms = InputMultiPath(File(exists=True), mandatory=True,
                                desc='transform files: will be applied in reverse order. For '
                                     'example, the last specified transform will be applied first.')

    reference_image = File(mandatory=True, exists=True)

    interpolation = traits.Enum('Linear',
                                'NearestNeighbor',
                                'CosineWindowedSinc',
                                'WelchWindowedSinc',
                                'HammingWindowedSinc',
                                'LanczosWindowedSinc',
                                'MultiLabel',
                                'Gaussian',
                                'BSpline',
                                usedefault=True)

    default_value = traits.Float(0)

    out_postfix = traits.Str("_transformed", usedefault=True)


class MultipleANTsApplyTransformsOutputSpec(TraitedSpec):
    output_images = OutputMultiPath(File())


class MultipleANTsApplyTransforms(BaseInterface):
    """Apply linear and deformable transforms estimated by ANTS to a list of images.

    It calls the `antsApplyTransform` on a series of images.

    Examples
    --------
    >>> apply_tf = MultipleANTsApplyTransforms()
    >>> apply_tf.inputs.input_images = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                 '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                 '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                 '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                 '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> apply_tf.inputs.transforms = ['/path/to/final1Warp.nii.gz',
    >>>                               '/path/to/final0GenericAffine.mat']
    >>> apply_tf.inputs.reference_image = File(mandatory=True, exists=True)
    >>> apply_tf.inputs.interpolation = 'NearestNeighbor'
    >>> apply_tf.inputs.default_value = 0.0
    >>> apply_tf.inputs.out_postfix = "_transformed"
    >>> apply_tf.run() # doctest: +SKIP

    """

    input_spec = MultipleANTsApplyTransformsInputSpec
    output_spec = MultipleANTsApplyTransformsOutputSpec

    def _run_interface(self, runtime):
        for input_image in self.inputs.input_images:
            ax = ApplyTransforms(input_image=input_image, reference_image=self.inputs.reference_image,
                                 interpolation=self.inputs.interpolation, transforms=self.inputs.transforms,
                                 out_postfix=self.inputs.out_postfix, default_value=self.inputs.default_value)
            ax.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_images'] = glob.glob(os.path.abspath("*.nii.gz"))
        return outputs
