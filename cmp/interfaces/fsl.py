# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" The FSL module provides functions for interfacing with FSL functions missing in nipype or modified
"""

import os
from glob import glob
import warnings

import numpy as np

from nipype.interfaces.fsl.base import FSLCommand, FSLCommandInputSpec, Info
from nipype.interfaces.base import (traits, TraitedSpec,CommandLineInputSpec, CommandLine, InputMultiPath, OutputMultiPath, File, Directory,
                                    isdefined)
from nipype.utils.filemanip import load_json, save_json, split_filename, fname_presuffix

warn = warnings.warn
warnings.filterwarnings('always', category=UserWarning)

class BinaryThresholdInputSpec(FSLCommandInputSpec):

    in_file = File(position=2, argstr="%s", exists=True, mandatory=True,
                desc="image to operate on")
    thresh = traits.Float(mandatory=True, position=3, argstr="-thr %s",
                          desc="threshold value")

    binarize = traits.Bool(True, position=4, argstr='-bin')

    out_file = File(genfile=True, mandatory=True, position=5, argstr="%s", desc="image to write", hash_files=False)


class BinaryThresholdOutputSpec(TraitedSpec):

    out_file = File(exists=True, desc="image written after calculations")


class BinaryThreshold(FSLCommand):
    """Use fslmaths to apply a threshold to an image in a variety of ways.

    """
    _cmd = "fslmaths"
    input_spec = BinaryThresholdInputSpec
    output_spec = BinaryThresholdOutputSpec
    _suffix = "_thresh"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


class MathsInput(FSLCommandInputSpec):

    in_file = File(position=2, argstr="%s", exists=True, mandatory=True,
                desc="image to operate on")
    out_file = File(genfile=True, position=-2, argstr="%s", desc="image to write", hash_files=False)
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

    _cmd = "fslmaths"
    input_spec = MathsInput
    output_spec = MathsOutput
    _suffix = "_maths"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


class FSLCreateHDInputSpec(CommandLineInputSpec):
    im_size = traits.List(traits.Int,argstr='%s',mandatory=True,position=1,minlen=4,maxlen=4,desc='Image size : xsize , ysize, zsize, tsize ')
    vox_size = traits.List(traits.Int,argstr='%s',mandatory=True,position=2,minlen=3,maxlen=3,desc='Voxel size : xvoxsize, yvoxsize, zvoxsize')
    tr = traits.Int(argstr='%s',mandatory=True,position=3,desc='<tr>')
    origin = traits.List(traits.Int,argstr='%s',mandatory=True,position=4,minlen=3,maxlen=3,desc='Origin coordinates : xorig, yorig, zorig')
    datatype = traits.Enum('2','4','8','16','32','64',argstr='%s',mandatory=True,position=5,desc='Datatype values: 2=char, 4=short, 8=int, 16=float, 64=double')
    out_filename = File(gen=True,mandatory=True,position=6,argstr='%s',desc=' the output temp reference image created.')

class FSLCreateHDOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='Path/name of the output reference image created.')

class FSLCreateHD(CommandLine):

    _cmd = 'fslcreatehd'
    input_spec=FSLCreateHDInputSpec
    output_spec=FSLCreateHDOutputSpec

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

    get_orient = traits.Bool(argstr="-getorient", position="1", xor=_options_xor, desc="gets FSL left-right orientation")
    get_sform = traits.Bool(argstr="-getsform", position="1", xor=_options_xor, desc="gets the 16 elements of the sform matrix")
    get_qform = traits.Bool(argstr="-getqform", position="1", xor=_options_xor, desc="gets the 16 elements of the qform matrix")
    set_sform = traits.List(traits.Float(), minlen=16, maxlen=16, position="1", argstr="-setsform %f",
                            xor=_options_xor, desc="<m11 m12 ... m44> sets the 16 elements of the sform matrix")
    set_qform = traits.List(traits.Float(), minlen=16, maxlen=16, position="1", argstr="-setqform %f",
                            xor=_options_xor, desc="<m11 m12 ... m44> sets the 16 elements of the qform matrix")
    get_sformcode = traits.Bool(argstr="-getsformcode", position="1", xor=_options_xor, desc="gets the sform integer code")
    get_qformcode = traits.Bool(argstr="-getqformcode", position="1", xor=_options_xor, desc="gets the qform integer code")
    set_sformcode = traits.Int(argstr="-setformcode %d", position="1", xor=_options_xor, desc="<code> sets sform integer code")
    set_qformcode = traits.Int(argstr="-setqormcode %d", position="1", xor=_options_xor, desc="<code> sets qform integer code")
    copy_sform2qform = traits.Bool(argstr="-copysform2qform", position="1", xor=_options_xor, desc="sets the qform equal to the sform - code and matrix")
    copy_qform2sform = traits.Bool(argstr="-copyqform2sform", position="1", xor=_options_xor, desc="sets the sform equal to the qform - code and matrix")
    delete_orient = traits.Bool(argstr="-deleteorient", position="1", xor=_options_xor, desc="removes orient info from header")
    force_radiological = traits.Bool(argstr="-forceradiological", position="1", xor=_options_xor, desc="makes FSL radiological header")
    force_neurological = traits.Bool(argstr="-forceneurological", position="1", xor=_options_xor, desc="makes FSL neurological header - not Analyze")
    swap_orient = traits.Bool(argstr="-swaporient", position="1", xor=_options_xor, desc="swaps FSL radiological and FSL neurological")


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


    """
    _cmd = "fslorient"
    input_spec = OrientInputSpec
    output_spec = OrientOutputSpec

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()
        info = runtime.stdout

        # Modified file
        if isdefined(self.inputs.copy_sform2qform) or isdefined(self.inputs.copy_qform2sform) or isdefined(self.inputs.delete_orient) or isdefined(self.inputs.force_radiological) or isdefined(self.inputs.force_neurological) or isdefined(self.inputs.swap_orient):
            outputs.out_file = self.inputs.in_file
            #outputs['out_file'] = self.inputs.in_file

        # Get information
        if isdefined(self.inputs.get_orient):
            outputs.orient = info
        if isdefined(self.inputs.get_sform):
            outputs.sform = info
        if isdefined(self.inputs.get_qform):
            outputs.qform= info
        if isdefined(self.inputs.get_sformcode):
            outputs.sformcode = info
        if isdefined(self.inputs.get_qformcode):
            outputs.qformcode = info

        return outputs


class EddyInputSpec(FSLCommandInputSpec):
    in_file = File(exists=True, desc='File containing all the images to estimate distortions for', argstr='--imain=%s', position=0, mandatory=True)
    mask = File(exists=True, desc='Mask to indicate brain', argstr='--mask=%s', position=1, mandatory=True)
    index = File(exists=True, desc='File containing indices for all volumes in --imain into --acqp and --topup', argstr='--index=%s', position=2, mandatory=True)
    acqp = File(exists=True, desc='File containing acquisition parameters', argstr='--acqp=%s', position=3, mandatory=True)
    bvecs = File(exists=True, desc='File containing the b-vectors for all volumes in --imain', argstr='--bvecs=%s', position=4, mandatory=True)
    bvals = File(exists=True, desc='File containing the b-values for all volumes in --imain', argstr='--bvals=%s', position=5, mandatory=True)
    out_file = File(desc='Basename for output', argstr='--out=%s', position=6, genfile=True, hash_files=False)
    verbose = traits.Bool(argstr='--verbose', position=7, desc="Display debugging messages.")

class EddyOutputSpec(TraitedSpec):
    eddy_corrected = File(exists=True, desc='path/name of 4D eddy corrected DWI file')
    bvecs_rotated = File(exists=True, desc='path/name of rotated DWI gradient bvecs file')


class Eddy(FSLCommand):
    """

    Example
    -------

    >>> from nipype.interfaces import fsl
    >>> eddyc = fsl.EddyCorrect(in_file='diffusion.nii', out_file="diffusion_edc.nii", ref_num=0)
    >>> eddyc.cmdline
    'eddy_correct diffusion.nii diffusion_edc.nii 0'

    """
    _cmd = 'eddy'
    input_spec = EddyInputSpec
    output_spec = EddyOutputSpec

    def __init__(self, **inputs):
        return super(Eddy, self).__init__(**inputs)

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix='_edc')
        runtime = super(Eddy, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['eddy_corrected'] = self.inputs.out_file
        if not isdefined(outputs['eddy_corrected']):
            outputs['eddy_corrected'] = self._gen_fname(self.inputs.in_file, suffix='_edc')
        outputs['eddy_corrected'] = os.path.abspath(outputs['eddy_corrected'])
        outputs['bvecs_rotated'] = self._gen_fname(self.inputs.out_file, suffix='', ext='.nii.gz.eddy_rotated_bvecs')
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._list_outputs()['eddy_corrected']
        else:
            return None


class EddyOpenMP(FSLCommand):
    """

    Example
    -------

    >>> from nipype.interfaces import fsl
    >>> eddyc = fsl.EddyCorrect(in_file='diffusion.nii', out_file="diffusion_edc.nii", ref_num=0)
    >>> eddyc.cmdline
    'eddy_correct diffusion.nii diffusion_edc.nii 0'

    """
    _cmd = 'eddy_openmp'
    input_spec = EddyInputSpec
    output_spec = EddyOutputSpec

    def __init__(self, **inputs):
        return super(EddyOpenMP, self).__init__(**inputs)

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix='_edc')
        runtime = super(EddyOpenMP, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['eddy_corrected'] = self.inputs.out_file
        if not isdefined(outputs['eddy_corrected']):
            outputs['eddy_corrected'] = self._gen_fname(self.inputs.in_file, suffix='_edc')
        outputs['eddy_corrected'] = os.path.abspath(outputs['eddy_corrected'])
        outputs['bvecs_rotated'] = self._gen_fname(self.inputs.out_file, suffix='', ext='.nii.gz.eddy_rotated_bvecs')
        return outputs

    def _gen_filename(self, name):
        if name is 'out_file':
            return self._list_outputs()['eddy_corrected']
        else:
            return None


class ProbTrackXInputSpec(FSLCommandInputSpec):
    thsamples = InputMultiPath(File(exists=True), mandatory=True)
    phsamples = InputMultiPath(File(exists=True), mandatory=True)
    fsamples = InputMultiPath(File(exists=True), mandatory=True)
    samples_base_name = traits.Str("merged", desc='the rootname/base_name for samples files',
                                   argstr='--samples=%s', usedefault=True)
    mask = File(exists=True, desc='bet binary mask file in diffusion space',
                    argstr='-m %s', mandatory=True)
    seed = traits.Either(File(exists=True), traits.List(File(exists=True)),
                         traits.List(traits.List(traits.Int(), minlen=3, maxlen=3)),
                         desc='seed volume(s), or voxel(s)' +
                         'or freesurfer label file',
                         argstr='--seed=%s', mandatory=True)
    mode = traits.Enum("simple", "two_mask_symm", "seedmask",
                       desc='options: simple (single seed voxel), seedmask (mask of seed voxels), '
                            + 'twomask_symm (two bet binary masks) ',
                       argstr='--mode=%s', genfile=True)
    target_masks = InputMultiPath(File(exits=True), desc='list of target masks - ' +
                       'required for seeds_to_targets classification', argstr='--targetmasks=%s')
    mask2 = File(exists=True, desc='second bet binary mask (in diffusion space) in twomask_symm mode',
                 argstr='--mask2=%s')
    waypoints = File(exists=True, desc='waypoint mask or ascii list of waypoint masks - ' +
                     'only keep paths going through ALL the masks', argstr='--waypoints=%s')
    network = traits.Bool(desc='activate network mode - only keep paths going through ' +
                          'at least one seed mask (required if multiple seed masks)',
                          argstr='--network')
    mesh = File(exists=True, desc='Freesurfer-type surface descriptor (in ascii format)',
                argstr='--mesh=%s')
    seed_ref = File(exists=True, desc='reference vol to define seed space in ' +
                   'simple mode - diffusion space assumed if absent',
                   argstr='--seedref=%s')
    out_dir = Directory(exists=True, argstr='--dir=%s',
                       desc='directory to put the final volumes in', genfile=True)
    force_dir = traits.Bool(True, desc='use the actual directory name given - i.e. ' +
                            'do not add + to make a new directory', argstr='--forcedir',
                            usedefault=True)
    opd = traits.Bool(True, desc='outputs path distributions', argstr='--opd', usedefault=True)
    correct_path_distribution = traits.Bool(desc='correct path distribution for the length of the pathways',
                                            argstr='--pd')
    os2t = traits.Bool(desc='Outputs seeds to targets', argstr='--os2t')
    #paths_file = File('nipype_fdtpaths', usedefault=True, argstr='--out=%s',
    #                 desc='produces an output file (default is fdt_paths)')
    avoid_mp = File(exists=True, desc='reject pathways passing through locations given by this mask',
                    argstr='--avoid=%s')
    stop_mask = File(exists=True, argstr='--stop=%s',
                      desc='stop tracking at locations given by this mask file')
    xfm = File(exists=True, argstr='--xfm=%s',
               desc='transformation matrix taking seed space to DTI space ' +
                '(either FLIRT matrix or FNIRT warp_field) - default is identity')
    inv_xfm = File(argstr='--invxfm=%s', desc='transformation matrix taking DTI space to seed' +
                    ' space (compulsory when using a warp_field for seeds_to_dti)')
    n_samples = traits.Int(5000, argstr='--nsamples=%d',
                           desc='number of samples - default=5000', usedefault=True)
    n_steps = traits.Int(argstr='--nsteps=%d', desc='number of steps per sample - default=2000')
    dist_thresh = traits.Float(argstr='--distthresh=%.3f', desc='discards samples shorter than ' +
                              'this threshold (in mm - default=0)')
    c_thresh = traits.Float(argstr='--cthr=%.3f', desc='curvature threshold - default=0.2')
    sample_random_points = traits.Bool(argstr='--sampvox', desc='sample random points within seed voxels')
    step_length = traits.Float(argstr='--steplength=%.3f', desc='step_length in mm - default=0.5')
    loop_check = traits.Bool(argstr='--loopcheck', desc='perform loop_checks on paths -' +
                            ' slower, but allows lower curvature threshold')
    use_anisotropy = traits.Bool(argstr='--usef', desc='use anisotropy to constrain tracking')
    rand_fib = traits.Enum(0, 1, 2, 3, argstr='--randfib %d',
                           desc='options: 0 - default, 1 - to randomly sample' +
                            ' initial fibres (with f > fibthresh), 2 - to sample in ' +
                            'proportion fibres (with f>fibthresh) to f, 3 - to sample ALL ' +
                            'populations at random (even if f<fibthresh)')
    fibst = traits.Int(argstr='--fibst=%d', desc='force a starting fibre for tracking - ' +
                       'default=1, i.e. first fibre orientation. Only works if randfib==0')
    mod_euler = traits.Bool(argstr='--modeuler', desc='use modified euler streamlining')
    random_seed = traits.Bool(argstr='--rseed', desc='random seed')
    s2tastext = traits.Bool(argstr='--s2tastext', desc='output seed-to-target counts as a' +
                            ' text file (useful when seeding from a mesh)')
    verbose = traits.Enum(0, 1, 2, desc="Verbose level, [0-2]." +
                          "Level 2 is required to output particle files.",
                          argstr="--verbose=%d")


class ProbTrackXOutputSpec(TraitedSpec):
    log = File(exists=True, desc='path/name of a text record of the command that was run')
    fdt_paths = OutputMultiPath(File(exists=True), desc='path/name of a 3D image file containing the output ' +
                     'connectivity distribution to the seed mask')
    way_total = File(exists=True, desc='path/name of a text file containing a single number ' +
                    'corresponding to the total number of generated tracts that ' +
                    'have not been rejected by inclusion/exclusion mask criteria')
    targets = traits.List(File, exists=True, desc='a list with all generated seeds_to_target files')
    particle_files = traits.List(File, exists=True, desc='Files describing ' +
                                 'all of the tract samples. Generated only if ' +
                                 'verbose is set to 2')


class ProbTrackX(FSLCommand):
    """ Use FSL  probtrackx for tractography on bedpostx results

    Examples
    --------

    >>> from nipype.interfaces import fsl
    >>> pbx = fsl.ProbTrackX(samples_base_name='merged', mask='mask.nii', \
    seed='MASK_average_thal_right.nii', mode='seedmask', \
    xfm='trans.mat', n_samples=3, n_steps=10, force_dir=True, opd=True, os2t=True, \
    target_masks = ['targets_MASK1.nii', 'targets_MASK2.nii'], \
    thsamples='merged_thsamples.nii', fsamples='merged_fsamples.nii', phsamples='merged_phsamples.nii', \
    out_dir='.')
    >>> pbx.cmdline
    'probtrackx --forcedir -m mask.nii --mode=seedmask --nsamples=3 --nsteps=10 --opd --os2t --dir=. --samples=merged --seed=MASK_average_thal_right.nii --targetmasks=targets.txt --xfm=trans.mat'

    """

    _cmd = 'probtrackx'
    input_spec = ProbTrackXInputSpec
    output_spec = ProbTrackXOutputSpec

    def __init__(self, **inputs):
        warnings.warn("Deprecated: Please use create_bedpostx_pipeline instead", DeprecationWarning)
        return super(ProbTrackX, self).__init__(**inputs)

    def _run_interface(self, runtime):
        for i in range(1, len(self.inputs.thsamples) + 1):
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.thsamples[i - 1],
                     self.inputs.samples_base_name + "_th%dsamples" % i + ext,
                     copy=True)
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.phsamples[i - 1],
                     self.inputs.samples_base_name + "_ph%dsamples" % i + ext,
                     copy=True)
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.fsamples[i - 1],
                     self.inputs.samples_base_name + "_f%dsamples" % i + ext,
                     copy=True)

        if isdefined(self.inputs.target_masks):
            f = open("targets.txt", "w")
            for target in self.inputs.target_masks:
                f.write("%s\n" % target)
            f.close()
        if isinstance(self.inputs.seed, list):
            f = open("seeds.txt", "w")
            for seed in self.inputs.seed:
                if isinstance(seed, list):
                    f.write("%s\n" % (" ".join([str(s) for s in seed])))
                else:
                    f.write("%s\n" % seed)
            f.close()

        runtime = super(ProbTrackX, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _format_arg(self, name, spec, value):
        if name == 'target_masks' and isdefined(value):
            fname = "targets.txt"
            return super(ProbTrackX, self)._format_arg(name, spec, [fname])
        elif name == 'seed' and isinstance(value, list):
            fname = "seeds.txt"
            return super(ProbTrackX, self)._format_arg(name, spec, fname)
        else:
            return super(ProbTrackX, self)._format_arg(name, spec, value)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_dir):
            out_dir = self._gen_filename("out_dir")
        else:
            out_dir = self.inputs.out_dir

        outputs['log'] = os.path.abspath(os.path.join(out_dir, 'probtrackx.log'))
        #utputs['way_total'] = os.path.abspath(os.path.join(out_dir, 'waytotal'))
        if isdefined(self.inputs.opd == True):
            if isinstance(self.inputs.seed, list) and isinstance(self.inputs.seed[0], list):
                outputs['fdt_paths'] = []
                for seed in self.inputs.seed:
                    outputs['fdt_paths'].append(
                            os.path.abspath(
                                self._gen_fname("fdt_paths_%s" % ("_".join([str(s) for s in seed])),
                                                cwd=out_dir, suffix='')))
            else:
                outputs['fdt_paths'] = os.path.abspath(self._gen_fname("fdt_paths",
                                               cwd=out_dir, suffix=''))

        # handle seeds-to-target output files
        if isdefined(self.inputs.target_masks):
            outputs['targets'] = []
            for target in self.inputs.target_masks:
                outputs['targets'].append(os.path.abspath(
                                                self._gen_fname('seeds_to_' + os.path.split(target)[1],
                                                cwd=out_dir,
                                                suffix='')))
        if isdefined(self.inputs.verbose) and self.inputs.verbose == 2:
            outputs['particle_files'] = [os.path.abspath(
                                            os.path.join(out_dir, 'particle%d' % i))
                                            for i in range(self.inputs.n_samples)]
        return outputs

    def _gen_filename(self, name):
        if name == "out_dir":
            return os.getcwd()
        elif name == "mode":
            if isinstance(self.inputs.seed, list) and isinstance(self.inputs.seed[0], list):
                return "simple"
            else:
                return "seedmask"


class mapped_ProbTrackXInputSpec(FSLCommandInputSpec):
    thsamples = InputMultiPath(File(exists=True), mandatory=True)
    phsamples = InputMultiPath(File(exists=True), mandatory=True)
    fsamples = InputMultiPath(File(exists=True), mandatory=True)
    samples_base_name = traits.Str("merged", desc='the rootname/base_name for samples files',
                                   argstr='--samples=%s', usedefault=True)
    mask = File(exists=True, desc='bet binary mask file in diffusion space',
                    argstr='-m %s', mandatory=True)
    seed = traits.File(exists=True,
                         desc='seed volume(s)',
                         argstr='--seed=%s', mandatory=True)
    mode = traits.Enum("simple", "two_mask_symm", "seedmask",
                       desc='options: simple (single seed voxel), seedmask (mask of seed voxels), '
                            + 'twomask_symm (two bet binary masks) ',
                       argstr='--mode=%s', genfile=True)
    target_masks = InputMultiPath(File(exits=True), desc='list of target masks - ' +
                       'required for seeds_to_targets classification', argstr='--targetmasks=%s')
    network = traits.Bool(desc='activate network mode - only keep paths going through ' +
                          'at least one seed mask (required if multiple seed masks)',
                          argstr='--network')
    opd = traits.Bool(True, desc='outputs path distributions', argstr='--opd', usedefault=True)
    os2t = traits.Bool(desc='Outputs seeds to targets', argstr='--os2t')
    n_samples = traits.Int(5000, argstr='--nsamples=%d',
                           desc='number of samples - default=5000', usedefault=True)
    n_steps = traits.Int(argstr='--nsteps=%d', desc='number of steps per sample - default=2000')
    dist_thresh = traits.Float(argstr='--distthresh=%.3f', desc='discards samples shorter than ' +
                              'this threshold (in mm - default=0)')
    c_thresh = traits.Float(argstr='--cthr=%.3f', desc='curvature threshold - default=0.2')
    step_length = traits.Float(argstr='--steplength=%.3f', desc='step_length in mm - default=0.5')
    loop_check = traits.Bool(argstr='--loopcheck', desc='perform loop_checks on paths -' +
                            ' slower, but allows lower curvature threshold')
    fibst = traits.Int(argstr='--fibst=%d', desc='force a starting fibre for tracking - ' +
                       'default=1, i.e. first fibre orientation. Only works if randfib==0')
    s2tastext = traits.Bool(argstr='--s2tastext', desc='output seed-to-target counts as a' +
                            ' text file (useful when seeding from a mesh)')
    out_dir = Directory(exists=True, argstr='--dir=%s',
                       desc='directory to put the final volumes in', genfile=True)
    force_dir = traits.Bool(True, desc='use the actual directory name given - i.e. ' +
                            'do not add + to make a new directory', argstr='--forcedir',
                            usedefault=True)

class mapped_ProbTrackXOutputSpec(TraitedSpec):
    matrix = File(exists=True, desc='matrix_seeds_to_all_targets file')

class mapped_ProbTrackX(FSLCommand):
    input_spec = mapped_ProbTrackXInputSpec
    output_spec = mapped_ProbTrackXOutputSpec

    _cmd = "probtrackx"

    def _run_interface(self, runtime):
        for i in range(1, len(self.inputs.thsamples) + 1):
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.thsamples[i - 1],
                     self.inputs.samples_base_name + "_th%dsamples" % i + ext,
                     copy=True)
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.phsamples[i - 1],
                     self.inputs.samples_base_name + "_ph%dsamples" % i + ext,
                     copy=True)
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.fsamples[i - 1],
                     self.inputs.samples_base_name + "_f%dsamples" % i + ext,
                     copy=True)

        if isdefined(self.inputs.target_masks):
            f = open("targets.txt", "w")
            for target in self.inputs.target_masks:
                f.write("%s\n" % target)
            f.close()

        runtime = super(mapped_ProbTrackX, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _format_arg(self, name, spec, value):
        if name == 'target_masks' and isdefined(value):
            fname = "targets.txt"
            return super(mapped_ProbTrackX, self)._format_arg(name, spec, [fname])
        elif name == 'seed' and isinstance(value, list):
            fname = "seeds.txt"
            return super(mapped_ProbTrackX, self)._format_arg(name, spec, fname)
        else:
            return super(mapped_ProbTrackX, self)._format_arg(name, spec, value)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_dir):
            out_dir = self._gen_filename("out_dir")
        else:
            out_dir = self.inputs.out_dir

        # handle seeds-to-target output files
        if isdefined(self.inputs.target_masks):
            outputs['matrix'] = os.path.abspath('matrix_seeds_to_all_targets')
        return outputs

    def _gen_filename(self, name):
        if name == "out_dir":
            return os.getcwd()
