# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license ModifFied BSD.

""" CMP second functional preprocessing stage
"""

# General imports
from traits.api import *
import gzip
import pickle
import os

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
from nipype.interfaces import afni

# Own imports
from cmp.stages.common import Stage
from cmtklib.functionalMRI import Scrubbing, Detrending, nuisance_regression

# Imports for processing
import nibabel as nib
import numpy as np


class FunctionalMRIConfig(HasTraits):
    smoothing = Float(0.0)
    discard_n_volumes = Int(5)
    # Nuisance factors
    global_nuisance = Bool(False)
    csf = Bool(True)
    wm = Bool(True)
    motion = Bool(True)

    detrending = Bool(True)
    detrending_mode = Enum("linear", "quadratic")

    lowpass_filter = Float(0.01)
    highpass_filter = Float(0.1)

    scrubbing = Bool(True)


class FunctionalMRIStage(Stage):

    def __init__(self):
        self.name = 'functional_stage'
        self.config = FunctionalMRIConfig()
        self.inputs = ["preproc_file", "motion_par_file", "registered_roi_volumes", "registered_wm", "eroded_wm",
                       "eroded_csf", "eroded_brain"]
        self.outputs = ["func_file", "FD", "DVARS"]

    def create_workflow(self, flow, inputnode, outputnode):

        # smoothing_output = pe.Node(interface=util.IdentityInterface(fields=["smoothing_output"]),name="smoothing_output")
        # if self.config.smoothing > 0.0:
        #     smoothing = pe.Node(interface=fsl.SpatialFilter(operation='mean',kernel_shape = 'gauss'),name="smoothing")
        #     smoothing.inputs.kernel_size = self.config.smoothing
        #     flow.connect([
        #                 (inputnode,smoothing,[("preproc_file","in_file")]),
        #                 (smoothing,smoothing_output,[("out_file","smoothing_output")])
        #                 ])
        # else:
        #     flow.connect([
        #                 (inputnode,smoothing_output,[("preproc_file","smoothing_output")])
        #                 ])
        #
        # discard_output = pe.Node(interface=util.IdentityInterface(fields=["discard_output"]),name="discard_output")
        # if self.config.discard_n_volumes > 0:
        #     discard = pe.Node(interface=discard_tp(n_discard=self.config.discard_n_volumes),name='discard_volumes')
        #     flow.connect([
        #                 (smoothing_output,discard,[("smoothing_output","in_file")]),
        #                 (discard,discard_output,[("out_file","discard_output")])
        #                 ])
        # else:
        #     flow.connect([
        #                 (smoothing_output,discard_output,[("smoothing_output","discard_output")])
        #                 ])
        # scrubbing_output = pe.Node(interface=util.IdentityInterface(fields=["scrubbing_output"]),name="scrubbing_output")
        if self.config.scrubbing:
            scrubbing = pe.Node(interface=Scrubbing(), name='scrubbing')
            flow.connect([
                (inputnode, scrubbing, [("preproc_file", "in_file")]),
                (inputnode, scrubbing, [("registered_wm", "wm_mask")]),
                (inputnode, scrubbing, [
                 ("registered_roi_volumes", "gm_file")]),
                (inputnode, scrubbing, [
                 ("motion_par_file", "motion_parameters")]),
                (scrubbing, outputnode, [("fd_npy", "FD")]),
                (scrubbing, outputnode, [("dvars_npy", "DVARS")])
            ])

        detrending_output = pe.Node(interface=util.IdentityInterface(fields=["detrending_output"]),
                                    name="detrending_output")
        if self.config.detrending:
            detrending = pe.Node(interface=Detrending(), name='detrending')
            detrending.inputs.mode = self.config.detrending_mode
            flow.connect([
                (inputnode, detrending, [("preproc_file", "in_file")]),
                (inputnode, detrending, [
                 ("registered_roi_volumes", "gm_file")]),
                (detrending, detrending_output, [
                 ("out_file", "detrending_output")])
            ])
        else:
            flow.connect([
                (inputnode, detrending_output, [
                 ("preproc_file", "detrending_output")])
            ])

        nuisance_output = pe.Node(interface=util.IdentityInterface(
            fields=["nuisance_output"]), name="nuisance_output")
        if self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            nuisance = pe.Node(interface=nuisance_regression(),
                               name="nuisance_regression")
            nuisance.inputs.global_nuisance = self.config.global_nuisance
            nuisance.inputs.csf_nuisance = self.config.csf
            nuisance.inputs.wm_nuisance = self.config.wm
            nuisance.inputs.motion_nuisance = self.config.motion
            nuisance.inputs.n_discard = self.config.discard_n_volumes
            flow.connect([
                (detrending_output, nuisance, [
                 ("detrending_output", "in_file")]),
                (inputnode, nuisance, [("eroded_brain", "brainfile")]),
                (inputnode, nuisance, [("eroded_csf", "csf_file")]),
                (inputnode, nuisance, [("registered_wm", "wm_file")]),
                (inputnode, nuisance, [("motion_par_file", "motion_file")]),
                (inputnode, nuisance, [("registered_roi_volumes", "gm_file")]),
                (nuisance, nuisance_output, [("out_file", "nuisance_output")])
            ])
        else:
            flow.connect([
                (detrending_output, nuisance_output, [
                 ("detrending_output", "nuisance_output")])
            ])

        filter_output = pe.Node(interface=util.IdentityInterface(
            fields=["filter_output"]), name="filter_output")
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            from cmtklib.interfaces.afni import Bandpass
            filtering = pe.Node(interface=Bandpass(), name='temporal_filter')
            # filtering = pe.Node(interface=afni.Bandpass(),name='temporal_filter')
            converter = pe.Node(interface=afni.AFNItoNIFTI(
                out_file='fMRI_bandpass.nii.gz'), name='converter')
            # FIXME: Seems that lowpass and highpass inputs of the nipype 3DBandPass interface swaped low and high frequencies
            filtering.inputs.lowpass = self.config.highpass_filter
            filtering.inputs.highpass = self.config.lowpass_filter

            # if self.config.detrending:
            #    filtering.inputs.no_detrend = True

            filtering.inputs.no_detrend = True

            flow.connect([
                (nuisance_output, filtering, [("nuisance_output", "in_file")]),
                # (filtering,filter_output,[("out_file","filter_output")])
                (filtering, converter, [("out_file", "in_file")]),
                (converter, filter_output, [("out_file", "filter_output")])
            ])
        else:
            flow.connect([
                (nuisance_output, filter_output, [
                 ("nuisance_output", "filter_output")])
            ])

        # OLD version using FSL
        # filter_output = pe.Node(interface=util.IdentityInterface(fields=["filter_output"]),name="filter_output")
        # if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
        #     filtering = pe.Node(interface=fsl.TemporalFilter(),name='temporal_filter')
        #     filtering.inputs.lowpass_sigma = self.config.lowpass_filter
        #     filtering.inputs.highpass_sigma = self.config.highpass_filter
        #     flow.connect([
        #                 (detrending_output,filtering,[("detrending_output","in_file")]),
        #                 (filtering,filter_output,[("out_file","filter_output")])
        #                 ])
        # else:
        #     flow.connect([
        #                 (detrending_output,filter_output,[("detrending_output","filter_output")])
        #                 ])

        # if self.config.scrubbing:
        #     scrubbing = pe.Node(interface=Scrubbing(),name='scrubbing')
        #     flow.connect([
        #                 (filter_output,scrubbing,[("filter_output","in_file")]),
        #                 (inputnode,scrubbing,[("registered_wm","wm_mask")]),
        #                 (inputnode,scrubbing,[("registered_roi_volumes","gm_file")]),
        #                 (inputnode,scrubbing,[("motion_par_file","motion_parameters")]),
        #                 (scrubbing,outputnode,[("fd_npy","FD")]),
        #                 (scrubbing,outputnode,[("dvars_npy","DVARS")])
        #                 ])

        flow.connect([
            (filter_output, outputnode, [("filter_output", "func_file")])
        ])

    def define_inspect_outputs(self):
        if self.config.smoothing > 0.0:
            res_path = os.path.join(
                self.stage_dir, "smoothing", "result_smoothing.pklz")
            if (os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Smoothed image'] = ['fsleyes', '-sdefault', results.outputs.out_file, '-cm',
                                                               'brain_colours_blackbdy_iso']
        if self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            res_path = os.path.join(
                self.stage_dir, "nuisance_regression", "result_nuisance_regression.pklz")
            if (os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Regression output'] = [
                    'fsleyes', '-sdefault', results.outputs.out_file]
        if self.config.detrending:
            res_path = os.path.join(
                self.stage_dir, "detrending", "result_detrending.pklz")
            if (os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Detrending output'] = ['fsleyes', '-sdefault', results.outputs.out_file,
                                                                  '-cm', 'brain_colours_blackbdy_iso']
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            res_path = os.path.join(
                self.stage_dir, "converter", "result_converter.pklz")
            if (os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Filter output'] = ['fsleyes', '-sdefault', results.outputs.out_file, '-cm',
                                                              'brain_colours_blackbdy_iso']

        self.inspect_outputs = sorted([key.encode('ascii', 'ignore') for key in list(self.inspect_outputs_dict.keys())],
                                      key=str.lower)

    def has_run(self):
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            return os.path.exists(os.path.join(self.stage_dir, "temporal_filter", "result_temporal_filter.pklz"))
        elif self.config.detrending:
            return os.path.exists(os.path.join(self.stage_dir, "detrending", "result_detrending.pklz"))
        elif self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            return os.path.exists(
                os.path.join(self.stage_dir, "nuisance_regression", "result_nuisance_regression.pklz"))
        elif self.config.smoothing > 0.0:
            return os.path.exists(os.path.join(self.stage_dir, "smoothing", "result_smoothing.pklz"))
        else:
            return True
