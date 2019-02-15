# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license ModifFied BSD.

""" CMP Stage for Diffusion reconstruction and tractography
"""

# General imports
import os
import gzip
import pickle

from traits.api import *
from traitsui.api import *

# Own imports
from cmp.bidsappmanager.stages.common import Stage


class FunctionalMRIConfig(HasTraits):
    smoothing = Float(0.0)
    discard_n_volumes = Int(5)
    # Nuisance factors
    global_nuisance = Bool(False)
    csf = Bool(True)
    wm = Bool(True)
    motion = Bool(True)

    detrending = Bool(True)
    detrending_mode = Enum("linear","quadratic")

    lowpass_filter = Float(0.01)
    highpass_filter = Float(0.1)

    scrubbing = Bool(True)

    traits_view = View( #Item('smoothing'),
                        #Item('discard_n_volumes'),
                        HGroup(
                            Item('detrending'),Item('detrending_mode',visible_when='detrending'),
                            label='Detrending',show_border=True
                            ),
                        HGroup(
                            Item('global_nuisance',label="Global"),
                            Item('csf'),
                            Item('wm'),
                            Item('motion'),
                            label='Nuisance factors',show_border=True
                            ),
                        HGroup(
                            Item('lowpass_filter',label='Low cutoff (volumes)'),
                            Item('highpass_filter',label='High cutoff (volumes)'),
                            label="Bandpass filtering",show_border=True
                            )
                       )

class FunctionalMRIStage(Stage):

    def __init__(self):
        self.name = 'functional_stage'
        self.config = FunctionalMRIConfig()
        self.inputs = ["preproc_file","motion_par_file","registered_roi_volumes","registered_wm","eroded_wm","eroded_csf","eroded_brain"]
        self.outputs = ["func_file","FD","DVARS"]

    def define_inspect_outputs(self):
        if self.config.smoothing > 0.0:
            res_path = os.path.join(self.stage_dir,"smoothing","result_smoothing.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Smoothed image'] = ['fslview',results.outputs.out_file]
        if self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            res_path = os.path.join(self.stage_dir,"nuisance_regression","result_nuisance_regression.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Regression output'] = ['fslview',results.outputs.out_file]
        if self.config.detrending:
            res_path = os.path.join(self.stage_dir,"detrending","result_detrending.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Detrending output'] = ['fslview',results.outputs.out_file]
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            res_path = os.path.join(self.stage_dir,"converter","result_converter.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Filter output'] = ['fslview',results.outputs.out_file]

        self.inspect_outputs = self.inspect_outputs_dict.keys()


    def has_run(self):
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            return os.path.exists(os.path.join(self.stage_dir,"temporal_filter","result_temporal_filter.pklz"))
        elif self.config.detrending:
            return os.path.exists(os.path.join(self.stage_dir,"detrending","result_detrending.pklz"))
        elif self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            return os.path.exists(os.path.join(self.stage_dir,"nuisance_regression","result_nuisance_regression.pklz"))
        elif self.config.smoothing > 0.0:
            return os.path.exists(os.path.join(self.stage_dir,"smoothing","result_smoothing.pklz"))
        else:
            return True
