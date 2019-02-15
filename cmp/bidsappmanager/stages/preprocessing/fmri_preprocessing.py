# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
"""

import os
import pickle
import gzip

from traits.api import *
from traitsui.api import *

from cmp.bidsappmanager.stages.common import Stage


class PreprocessingConfig(HasTraits):
    discard_n_volumes = Int('5')
    despiking = Bool(True)
    slice_timing = Enum("none", ["bottom-top interleaved", "bottom-top interleaved", "top-bottom interleaved", "bottom-top", "top-bottom"])
    repetition_time = Float(1.92)
    motion_correction = Bool(True)

    traits_view = View('discard_n_volumes','despiking','slice_timing',Item('repetition_time',visible_when='slice_timing!="none"'),'motion_correction')


class PreprocessingStage(Stage):
    # General and UI members
    def __init__(self):
        self.name = 'preprocessing_stage'
        self.config = PreprocessingConfig()
        self.inputs = ["functional"]
        self.outputs = ["functional_preproc","par_file","mean_vol"]


    def define_inspect_outputs(self):
        if self.config.despiking:
            despike_path = os.path.join(self.stage_dir,"converter","result_converter.pklz")
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
            return os.path.exists(os.path.join(self.stage_dir,"converter","result_converter.pklz"))
        else:
            return True
