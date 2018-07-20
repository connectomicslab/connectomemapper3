# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
"""

from traits.api import *
from traitsui.api import *

from cmp.stages.common import Stage

import os
import pickle
import gzip

import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
from nipype.interfaces import afni

class discard_tp_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True,mandatory=True)
    n_discard = Int(mandatory=True)

class discard_tp_OutputSpec(TraitedSpec):
    out_file = File(exists = True)

class discard_tp(BaseInterface):
    input_spec = discard_tp_InputSpec
    output_spec = discard_tp_OutputSpec

    def _run_interface(self,runtime):
        dataimg = nib.load( self.inputs.in_file )
        data = dataimg.get_data()

        n_discard = int(self.inputs.n_discard) - 1

        new_data = data.copy()
        new_data = new_data[:,:,:,n_discard:-1]

        hd = dataimg.get_header()
        hd.set_data_shape([hd.get_data_shape()[0],hd.get_data_shape()[1],hd.get_data_shape()[2],hd.get_data_shape()[3]-n_discard-1])
        img = nib.Nifti1Image(new_data, dataimg.get_affine(), hd)
        nib.save(img, os.path.abspath('fMRI_discard.nii.gz'))
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_discard.nii.gz")
        return outputs


class PreprocessingConfig(HasTraits):
    discard_n_volumes = Int('5')
    despiking = Bool(True)
    slice_timing = Enum("none", ["bottom-top interleaved", "bottom-top interleaved", "top-bottom interleaved", "bottom-top", "top-bottom"])
    repetition_time = Float(1.92)
    motion_correction = Bool(True)

    traits_view = View('slice_timing',Item('repetition_time',visible_when='slice_timing!="none"'),'motion_correction')


class PreprocessingStage(Stage):
    # General and UI members
    def __init__(self):
        self.name = 'preprocessing_stage'
        self.config = PreprocessingConfig()
        self.inputs = ["functional"]
        self.outputs = ["functional_preproc","par_file","mean_vol"]

    def create_workflow(self, flow, inputnode, outputnode):
        discard_output = pe.Node(interface=util.IdentityInterface(fields=["discard_output"]),name="discard_output")
        if self.config.discard_n_volumes > 0:
            discard = pe.Node(interface=discard_tp(n_discard=self.config.discard_n_volumes),name='discard_volumes')
            flow.connect([
                        (inputnode,discard,[("functional","in_file")]),
                        (discard,discard_output,[("out_file","discard_output")])
                        ])
        else:
            flow.connect([
                        (inputnode,discard,[("functional","discard_output")])
                        ])

        despiking_output = pe.Node(interface=util.IdentityInterface(fields=["despiking_output"]),name="despkiking_output")
        if self.config.despiking:
            despike = pe.Node(interface=Despike(),name='afni_despike')
            flow.connect([
                        (discard_output,despike,[("discard_output","in_file")]),
                        (despike,despiking_output,[("out_file","despiking_output")])
                        ])
        else:
            flow.connect([
                        (discard_output,despiking_output,[("discard_output","despiking_output")])
                        ])

        if self.config.slice_timing != "none":
            slc_timing = pe.Node(interface=fsl.SliceTimer(),name = 'slice_timing')
            slc_timing.inputs.time_repetition = self.config.repetition_time
            if self.config.slice_timing == "bottom-top interleaved":
                slc_timing.inputs.interleaved = True
                slc_timing.inputs.index_dir = False
            elif self.config.slice_timing == "top-bottom interleaved":
                slc_timing.inputs.interleaved = True
                slc_timing.inputs.index_dir = True
            elif self.config.slice_timing == "bottom-top":
                slc_timing.inputs.interleaved = False
                slc_timing.inputs.index_dir = False
            elif self.config.slice_timing == "top-bottom":
                slc_timing.inputs.interleaved = False
                slc_timing.inputs.index_dir = True

        if self.config.motion_correction:
            mo_corr = pe.Node(interface=fsl.MCFLIRT(stats_imgs = True, save_mats = False, save_plots = True, mean_vol=True),name="motion_correction")

        if self.config.slice_timing != "none":
            flow.connect([
                        (despiking_output,slc_timing,[("despiking_output","in_file")])
                        ])
            if self.config.motion_correction:
                flow.connect([
                            (slc_timing,mo_corr,[("slice_time_corrected_file","in_file")]),
                            (mo_corr,outputnode,[("out_file","functional_preproc")]),
                            (mo_corr,outputnode,[("par_file","par_file")]),
                            (mo_corr,outputnode,[("mean_img","mean_vol")]),
                            ])
            else:
                mean = pe.Node(interface=fsl.MeanImage(),name="mean")
                flow.connect([
                            (slc_timing,outputnode,[("slice_time_corrected_file","functional_preproc")]),
                            (slc_timing,mean,[("slice_time_corrected_file","in_file")]),
                            (mean,outputnode,[("out_file","mean_vol")])
                            ])
        else:
            if self.config.motion_correction:
                flow.connect([
                            (despiking_output,mo_corr,[("despiking_output","in_file")]),
                            (mo_corr,outputnode,[("out_file","functional_preproc")]),
                            (mo_corr,outputnode,[("par_file","par_file")]),
                            (mo_corr,outputnode,[("mean_img","mean_vol")]),
                            ])
            else:
                mean = pe.Node(interface=fsl.MeanImage(),name="mean")
                flow.connect([
                            (despiking_output,outputnode,[("despiking_output","functional_preproc")]),
                            (inputnode,mean,[("functional","in_file")]),
                            (mean,outputnode,[("out_file","mean_vol")])
                            ])


    def define_inspect_outputs(self):
        if self.config.despiking:
            despike_path = os.path.join(self.stage_dir,"despike","result_despike.pklz")
            if(os.path.exists(despike_path)):
                despike_results = pickle.load(gzip.open(despike_path))
                self.inspect_outputs_dict['Spike corrected image'] = ['fslview',despike_results.outputs.out_file]

        if self.config.slice_timing:
            slc_timing_path = os.path.join(self.stage_dir,"slice_timing","result_slice_timing.pklz")
            if(os.path.exists(slc_timing_path)):
                slice_results = pickle.load(gzip.open(slc_timing_path))
                self.inspect_outputs_dict['Slice time corrected image'] = ['fslview',slice_results.outputs.slice_time_corrected_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()
            if self.config.motion_correction:
                motion_results_path = os.path.join(self.stage_dir,"motion_correction","result_motion_correction.pklz")
                if(os.path.exists(motion_results_path)):
                    motion_results = pickle.load(gzip.open(motion_results_path))
                    self.inspect_outputs_dict['Slice time and motion corrected image'] = ['fslview',motion_results.outputs.out_file]
                    self.inspect_outputs = self.inspect_outputs_dict.keys()

        elif self.config.motion_correction:
            motion_results_path = os.path.join(self.stage_dir,"motion_correction","result_motion_correction.pklz")
            if(os.path.exists(motion_results_path)):
                motion_results = pickle.load(gzip.open(motion_results_path))
                self.inspect_outputs_dict['Motion corrected image'] = ['fslview',motion_results.outputs.out_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()


    def has_run(self):
        if self.config.motion_correction:
            return os.path.exists(os.path.join(self.stage_dir,"motion_correction","result_motion_correction.pklz"))
        elif self.config.slice_timing:
            return os.path.exists(os.path.join(self.stage_dir,"slice_timing","result_slice_timing.pklz"))
        elif self.config.despiking:
            return os.path.exists(os.path.join(self.stage_dir,"despike","result_despike.pklz"))
        else:
            return True
