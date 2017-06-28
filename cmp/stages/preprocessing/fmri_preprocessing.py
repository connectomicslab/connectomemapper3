# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
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



class PreprocessingConfig(HasTraits):
    slice_timing = Enum("none", ["none", "bottom-top interleaved", "top-bottom interleaved", "bottom-top", "top-bottom"])
    repetition_time = Float(3.0)
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
            mo_corr = pe.Node(interface=fsl.MCFLIRT(stats_imgs = True, save_mats = False, save_plots = True),name="motion_correction")
        
        if self.config.slice_timing != "none":
            flow.connect([
                        (inputnode,slc_timing,[("functional","in_file")])
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
                            (inputnode,mo_corr,[("functional","in_file")]),
                            (mo_corr,outputnode,[("out_file","functional_preproc")]),
                            (mo_corr,outputnode,[("par_file","par_file")]),
                            (mo_corr,outputnode,[("mean_img","mean_vol")]),
                            ])
            else:
                mean = pe.Node(interface=fsl.MeanImage(),name="mean")
                flow.connect([
                            (inputnode,outputnode,[("functional","functional_preproc")]),
                            (inputnode,mean,[("functional","in_file")]),
                            (mean,outputnode,[("out_file","mean_vol")])
                            ])
        

    def define_inspect_outputs(self):                
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
        else:
            return True

