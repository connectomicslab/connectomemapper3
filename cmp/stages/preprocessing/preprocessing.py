# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
""" 

from traits.api import *
from traitsui.api import *

from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, OutputMultiPath, TraitedSpec

from cmp.stages.common import Stage

import os
import pickle
import gzip

import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

import nibabel as nib

class PreprocessingConfig(HasTraits):
    description = Str('description')
    eddy_current_correction = Bool(False)
    motion_correction = Bool(False)
    start_vol = Int(0)
    end_vol = Int()
    max_vol = Int()
    max_str = Str
    traits_view = View('motion_correction','eddy_current_correction',HGroup(Item('start_vol',label='Vol'),Item('end_vol',label='to'),Item('max_str',style='readonly',show_label=False)))
    
    def _max_vol_changed(self,new):
        self.max_str = '(max: %d)' % new
        
    def _end_vol_changed(self,new):
        if new > self.max_vol:
            self.end_vol = self.max_vol
            
    def _start_vol_changed(self,new):
        if new < 0:
            self.start_vol = 0

class splitDiffusion_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True)
    start = Int(0)
    end = Int()
    
class splitDiffusion_OutputSpec(TraitedSpec):
    data = File(exists=True)
    padding1 = File(exists=False)
    padding2 = File(exists=False)
    
class splitDiffusion(BaseInterface):
    input_spec = splitDiffusion_InputSpec
    output_spec = splitDiffusion_OutputSpec
    
    def _run_interface(self,runtime):
        diffusion_file = nib.load(self.inputs.in_file)
        diffusion = diffusion_file.get_data()
        affine = diffusion_file.get_affine()
        dim = diffusion.shape
        if self.inputs.start > 0 and self.inputs.end > dim[3]-1:
            error('End volume is set to %d but it should be bellow %d' % (self.inputs.end, dim[3]-1))
        padding_idx1 = range(0,self.inputs.start)
        if len(padding_idx1) > 0:
            temp = diffusion[:,:,:,0:self.inputs.start]
            nib.save(nib.nifti1.Nifti1Image(temp,affine),os.path.abspath('padding1.nii.gz'))
        temp = diffusion[:,:,:,self.inputs.start:self.inputs.end+1]
        nib.save(nib.nifti1.Nifti1Image(temp,affine),os.path.abspath('data.nii.gz'))
        padding_idx2 = range(self.inputs.end,dim[3]-1)
        if len(padding_idx2) > 0:
            temp = diffusion[:,:,:,self.inputs.end+1:dim[3]]
            nib.save(nib.nifti1.Nifti1Image(temp,affine),os.path.abspath('padding2.nii.gz'))        
            
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["data"] = os.path.abspath('data.nii.gz')
        if os.path.exists(os.path.abspath('padding1.nii.gz')):
            outputs["padding1"] = os.path.abspath('padding1.nii.gz')
        if os.path.exists(os.path.abspath('padding2.nii.gz')):
            outputs["padding2"] = os.path.abspath('padding2.nii.gz')
        return outputs

class PreprocessingStage(Stage):
    # General and UI members
    def __init__(self):
        self.name = 'preprocessing_stage'
        self.config = PreprocessingConfig()
        self.inputs = ["diffusion"]
        self.outputs = ["diffusion_preproc"]
    
    def create_workflow(self, flow, inputnode, outputnode):
        processing_input = pe.Node(interface=util.IdentityInterface(fields=['diffusion']),name='processing_input')
        # For DSI acquisition: extract the hemisphere that contains the data
        if self.config.start_vol > 0 or self.config.end_vol < self.config.max_vol:
            split_vol = pe.Node(interface=splitDiffusion(),name='split_vol')
            split_vol.inputs.start = self.config.start_vol
            split_vol.inputs.end = self.config.end_vol
            flow.connect([
                        (inputnode,split_vol,[("diffusion","in_file")]),
                        (split_vol,processing_input,[("data","diffusion")])
                        ])
        else:
            flow.connect([
                        (inputnode,processing_input,[("diffusion","diffusion")])
                        ])
        if self.config.motion_correction:
            mc_flirt = pe.Node(interface=fsl.MCFLIRT(out_file='motion_corrected.nii.gz',ref_vol=0),name='motion_correction')
            flow.connect([
                        (processing_input,mc_flirt,[("diffusion","in_file")])
                        ])
            if self.config.eddy_current_correction:
                eddy_correct = pe.Node(interface=fsl.EddyCorrect(ref_num=0,out_file='eddy_corrected.nii.gz'),name='eddy_correct')
                flow.connect([
                            (mc_flirt,eddy_correct,[("out_file","in_file")])
                            ])
                if self.config.start_vol > 0 and self.config.end_vol == self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                    flow.connect([
                                (split_vol,merge_filenames,[("padding1","in1")]),
                                (eddy_correct,merge_filenames,[("eddy_corrected","in2")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                elif self.config.start_vol > 0 and self.config.end_vol < self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(3),name='merge_files')
                    flow.connect([
                                (split_vol,merge_filenames,[("padding1","in1")]),
                                (eddy_correct,merge_filenames,[("eddy_corrected","in2")]),
                                (split_vol,merge_filenames,[("padding2","in3")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                elif self.config.start_vol == 0 and self.config.end_vol < self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                    flow.connect([
                                (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                                (split_vol,merge_filenames,[("padding2","in2")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                else:
                    flow.connect([
                                (eddy_correct,outputnode,[("eddy_corrected","diffusion_preproc")])
                                ])
            else:
                if self.config.start_vol > 0 and self.config.end_vol == self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                    flow.connect([
                                (split_vol,merge_filenames,[("padding1","in1")]),
                                (mc_flirt,merge_filenames,[("out_file","in2")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                elif self.config.start_vol > 0 and self.config.end_vol < self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(3),name='merge_files')
                    flow.connect([
                                (split_vol,merge_filenames,[("padding1","in1")]),
                                (mc_flirt,merge_filenames,[("out_file","in2")]),
                                (split_vol,merge_filenames,[("padding2","in3")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                elif self.config.start_vol == 0 and self.config.end_vol < self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                    flow.connect([
                                (mc_flirt,merge_filenames,[("out_file","in1")]),
                                (split_vol,merge_filenames,[("padding2","in2")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                else:
                    flow.connect([
                                (mc_flirt,outputnode,[("out_file","diffusion_preproc")])
                                ])
        else:
            if self.config.eddy_current_correction:
                eddy_correct = pe.Node(interface=fsl.EddyCorrect(ref_num=0,out_file="eddy_corrected.nii.gz"),name='eddy_correct')
                flow.connect([
                            (processing_input,eddy_correct,[("diffusion","in_file")])
                            ])
                if self.config.start_vol > 0 and self.config.end_vol == self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                    flow.connect([
                                (split_vol,merge_filenames,[("padding1","in1")]),
                                (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                elif self.config.start_vol > 0 and self.config.end_vol < self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(3),name='merge_files')
                    flow.connect([
                                (split_vol,merge_filenames,[("padding1","in1")]),
                                (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                                (split_vol,merge_filenames,[("padding2","in3")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                elif self.config.start_vol == 0 and self.config.end_vol < self.config.max_vol:
                    merge_filenames = pe.Node(interface=util.Merge(2),name='merge_files')
                    flow.connect([
                                (eddy_correct,merge_filenames,[("eddy_corrected","in1")]),
                                (split_vol,merge_filenames,[("padding2","in2")]),
                                ])
                    merge = pe.Node(interface=fsl.Merge(dimension='t'),name="merge")
                    flow.connect([
                                (merge_filenames,merge,[("out","in_files")]),
                                (merge,outputnode,[("merged_file","diffusion_preproc")])
                                ])
                else:
                    flow.connect([
                                (eddy_correct,outputnode,[("eddy_corrected","diffusion_preproc")])
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
        if not self.config.eddy_current_correction and not self.config.motion_correction:
            return True
        else:
            return os.path.exists(os.path.join(self.stage_dir,"result_preprocessing_stage.pklz"))
