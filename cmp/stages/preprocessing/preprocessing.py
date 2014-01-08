# Copyright (C) 2009-2014, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
    description = Str('description')
    eddy_current_correction = Bool(False)
    motion_correction = Bool(False)
    
    traits_view = View('motion_correction','eddy_current_correction')

class PreprocessingStage(Stage):
    # General and UI members
    name = 'preprocessing_stage'
    config = PreprocessingConfig()
    inputs = ["diffusion"]
    outputs = ["diffusion_preproc"]
    
    def create_workflow(self, flow, inputnode, outputnode):
        if self.config.motion_correction:
            mc_flirt = pe.Node(interface=fsl.MCFLIRT(out_file='motion_corrected.nii.gz'),name='motion_correction')
            flow.connect([
			    (inputnode,mc_flirt,[("diffusion","in_file")]),
			    ])
            if self.config.eddy_current_correction:
                eddy_correct = pe.Node(interface=fsl.EddyCorrect(ref_num=0,out_file='eddy_corrected.nii.gz'),name='eddy_correct')
                flow.connect([
				    (mc_flirt,eddy_correct,[("out_file","in_file")]),
				    (eddy_correct,outputnode,[("eddy_corrected","diffusion_preproc")]),
				    ])
            else:
                flow.connect([
				    (mc_flirt,outputnode,[("out_file","diffusion_preproc")]),
				    ])
        else:
            if self.config.eddy_current_correction:
                eddy_correct = pe.Node(interface=fsl.EddyCorrect(ref_num=0,out_file="eddy_corrected.nii.gz"),name='eddy_correct')
                flow.connect([
				    (inputnode,eddy_correct,[("diffusion","in_file")]),
				    (eddy_correct,outputnode,[("eddy_corrected","diffusion_preproc")]),
				    ])
            else:
                flow.connect([
				    (inputnode,outputnode,[("diffusion","diffusion_preproc")]),
				    ])

    def define_inspect_outputs(self):

        if self.config.motion_correction:
            motion_results_path = os.path.join(self.stage_dir,"motion_correction","result_motion_correction.pklz")
            if(os.path.exists(motion_results_path)):
                motion_results = pickle.load(gzip.open(motion_results_path))
                self.inspect_outputs_dict['Motion corrected image'] = ['fslview',motion_results.outputs.out_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()
            if self.config.eddy_current_correction:
                eddy_results_path = os.path.join(self.stage_dir,"eddy_correct","result_eddy_correct.pklz")
                if(os.path.exists(eddy_results_path)):
                    eddy_results = pickle.load(gzip.open(eddy_results_path))
                    self.inspect_outputs_dict['Motion and eddy corrected image'] = ['fslview',eddy_results.outputs.eddy_corrected]
                    self.inspect_outputs = self.inspect_outputs_dict.keys()
                
        elif self.config.eddy_current_correction:
            eddy_results_path = os.path.join(self.stage_dir,"eddy_correct","result_eddy_correct.pklz")
            if(os.path.exists(eddy_results_path)):
                eddy_results = pickle.load(gzip.open(eddy_results_path))
                self.inspect_outputs_dict['Eddy current corrected image'] = ['fslview',eddy_results.outputs.eddy_corrected]
                self.inspect_outputs = self.inspect_outputs_dict.keys()           

            
    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"result_preprocessing_stage.pklz"))
