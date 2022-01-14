# Copyright (C) 2017-2020, Brain Communication Pathways Sinergia Consortium, Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""The AFNI module provides Nipype interfaces for the AFNI toolbox missing in nipype or modified."""

import os

from nipype import logging
from nipype.utils.filemanip import split_filename
from nipype.interfaces.base import (
    traits, isdefined, File, InputMultiPath)
# from nipype.external.due import BibTeX

from nipype.interfaces.afni.base import (AFNICommand,
                                         AFNICommandInputSpec,
                                         AFNICommandOutputSpec)

# Use nipype's logging system
IFLOGGER = logging.getLogger('interface')


class BandpassInputSpec(AFNICommandInputSpec):
    in_file = File(
        desc='input file to 3dBandpass',
        argstr='%s',
        position=-1,
        mandatory=True,
        exists=True,
        copyfile=False)
    out_file = File(
        name_template='%s_bp',
        desc='output file from 3dBandpass',
        argstr='-prefix %s',
        position=1,
        name_source='in_file',
        genfile=True)
    lowpass = traits.Float(
        desc='lowpass',
        argstr='%f',
        position=-2,
        mandatory=True)
    highpass = traits.Float(
        desc='highpass',
        argstr='%f',
        position=-3,
        mandatory=True)
    mask = File(
        desc='mask file',
        position=2,
        argstr='-mask %s',
        exists=True)
    despike = traits.Bool(
        argstr='-despike',
        desc="Despike each time series before other processing. "
             "Hopefully, you don't actually need to do this, "
             "which is why it is optional."
    )
    orthogonalize_file = InputMultiPath(
        File(exists=True),
        argstr="-ort %s",
        desc="Also orthogonalize input to columns in f.1D "
             "Multiple '-ort' options are allowed.")
    orthogonalize_dset = File(
        exists=True,
        argstr="-dsort %s",
        desc="Orthogonalize each voxel to the corresponding "
             "voxel time series in dataset 'fset', which must "
             "have the same spatial and temporal grid structure "
             "as the main input dataset. "
             "At present, only one '-dsort' option is allowed."
    )
    no_detrend = traits.Bool(
        argstr='-nodetrend',
        desc="Skip the quadratic detrending of the input that "
             "occurs before the FFT-based bandpassing. "
             "++ You would only want to do this if the dataset "
             "had been detrended already in some other program."
    )
    tr = traits.Float(
        argstr="-dt %f",
        desc="set time step (TR) in sec [default=from dataset header]")
    nfft = traits.Int(
        argstr='-nfft %d',
        desc="set the FFT length [must be a legal value]")
    normalize = traits.Bool(
        argstr='-norm',
        desc="Make all output time series have L2 norm = 1 "
             "++ i.e., sum of squares = 1"
    )
    automask = traits.Bool(
        argstr='-automask',
        desc="Create a mask from the input dataset")
    blur = traits.Float(
        argstr='-blur %f',
        desc="Blur (inside the mask only) with a filter "
             "width (FWHM) of 'fff' millimeters."
    )
    localPV = traits.Float(
        argstr='-localPV %f',
        desc="Replace each vector by the local Principal Vector "
             "(AKA first singular vector) from a neighborhood "
             "of radius 'rrr' millimiters. "
             "Note that the PV time series is L2 normalized. "
             "This option is mostly for Bob Cox to have fun with.")
    notrans = traits.Bool(
        argstr='-notrans',
        desc="Don't check for initial positive transients in the data: "
             "The test is a little slow, so skipping it is OK, "
             "if you KNOW the data time series are transient-free."
    )


class Bandpass(AFNICommand):
    """Program to lowpass and/or highpass each voxel time series in a dataset.

    Calls the `3dBandpass` tool from AFNI, offering more/different options than Fourier.

    For complete details, see the `3dBandpass Documentation.
    <http://afni.nimh.nih.gov/pub/dist/doc/program_help/3dbandpass.html>`_

    Examples
    --------
    >>> from nipype.interfaces import afni as afni
    >>> from nipype.testing import  example_data
    >>> bandpass = afni.Bandpass()
    >>> bandpass.inputs.in_file = example_data('functional.nii')
    >>> bandpass.inputs.highpass = 0.005
    >>> bandpass.inputs.lowpass = 0.1
    >>> res = bandpass.run()  # doctest: +SKIP

    """

    _cmd = '3dBandpass'
    input_spec = BandpassInputSpec
    output_spec = AFNICommandOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        name = 'out_file'
        if isdefined(self.inputs.out_file):
            if outputs[name]:
                print('out_file: {}'.format(outputs[name]))
                _, _, ext = split_filename(outputs[name])
                if ext == "":
                    outputs[name] = outputs[name] + "+orig.BRIK"
        else:
            from glob import glob
            files = sorted(glob("*.BRIK"))
            print("files: {}".format(files))
            if len(files) > 0:
                outputs[name] = os.path.abspath(files[0])
        return outputs


class DespikeInputSpec(AFNICommandInputSpec):
    in_file = File(
        desc="input file to 3dDespike",
        argstr="%s",
        position=-1,
        mandatory=True,
        exists=True,
        copyfile=False,
    )
    out_file = File(
        name_template="%s_despike",
        desc="output image file name",
        argstr="-prefix %s",
        name_source="in_file",
    )


class Despike(AFNICommand):
    """Removes 'spikes' from the 3D+time input dataset.

    It calls the `3dDespike` tool from AFNI.

    For complete details, see the `3dDespike Documentation.
    <https://afni.nimh.nih.gov/pub/dist/doc/program_help/3dDespike.html>`_

    Examples
    --------
    >>> from nipype.interfaces import afni
    >>> despike = afni.Despike()
    >>> despike.inputs.in_file = 'functional.nii'
    >>> res = despike.run()  # doctest: +SKIP

    """

    _cmd = "3dDespike"
    input_spec = DespikeInputSpec
    output_spec = AFNICommandOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        name = 'out_file'
        if isdefined(self.inputs.out_file):
            if outputs[name]:
                print('out_file: {}'.format(outputs[name]))
                _, base, ext = split_filename(outputs[name])
                if ext == "":
                    outputs[name] = outputs[name] + "+orig.BRIK"
        else:
            from glob import glob
            files = sorted(glob("*.BRIK"))
            print("files: {}".format(files))
            if len(files) > 0:
                outputs[name] = os.path.abspath(files[0])
        return outputs
