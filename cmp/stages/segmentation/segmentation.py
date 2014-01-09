# Copyright (C) 2009-2014, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP segmentation stage
""" 

# General imports
import os
from traits.api import *
from traitsui.api import *
import pickle
import gzip

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
from nipype.interfaces.io import FreeSurferSource
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage

class SegmentationConfig(HasTraits):
    seg_tool = Enum(["Freesurfer","Custom segmentation"])
    use_existing_freesurfer_data = Bool(False)
    freesurfer_subjects_dir = Directory
    freesurfer_subject_id_trait = List
    freesurfer_subject_id = Str
    freesurfer_args = Str
    white_matter_mask = File(exist=True)
    traits_view = View(Item('seg_tool',label="Segmentation tool"),
                       Group('freesurfer_args','use_existing_freesurfer_data',
                        Item('freesurfer_subjects_dir', enabled_when='use_existing_freesurfer_data == True'),
                        Item('freesurfer_subject_id',editor=EnumEditor(name='freesurfer_subject_id_trait'), enabled_when='use_existing_freesurfer_data == True'),
                        visible_when="seg_tool=='Freesurfer'"),
                       Group(
                        'white_matter_mask',
                        visible_when='seg_tool=="Custom segmentation"')
                        )
    
    def _freesurfer_subjects_dir_changed(self, old, new):
        dirnames = [name for name in os.listdir(self.freesurfer_subjects_dir) if
             os.path.isdir(os.path.join(self.freesurfer_subjects_dir, name))]
        self.freesurfer_subject_id_trait = dirnames
        
    def _use_existing_freesurfer_data_changed(self,new):
        if new == True:
            self.custom_segmentation = False

class SegmentationStage(Stage):
    # General and UI members
    name = 'segmentation_stage'
    config = SegmentationConfig()
    inputs = ["T1"]
    outputs = ["subjects_dir","subject_id","custom_wm_mask"]

    def create_workflow(self, flow, inputnode, outputnode):
        if self.config.seg_tool == "Freesurfer":
            if self.config.use_existing_freesurfer_data == False:
                # Converting to .mgz format
                fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type="mgz",out_file="T1.mgz"),name="mgz_convert")
                
                # ReconAll => named outputnode as we don't want to select a specific output....
                fs_reconall = pe.Node(interface=fs.ReconAll(),name="reconall")
                fs_reconall.inputs.subjects_dir = self.config.freesurfer_subjects_dir
                fs_reconall.inputs.args = self.config.freesurfer_args
                
                fs_reconall.inputs.subject_id = self.config.freesurfer_subject_id # DR: inputs seemed to lack from previous version
                
                flow.connect([
                            (inputnode,fs_mriconvert,[('T1','in_file')]),
                            (fs_mriconvert,fs_reconall,[('out_file','T1_files')]),
                            (fs_reconall,outputnode,[('subjects_dir','subjects_dir'),('subject_id','subject_id')]),
                            ])
                
            else:
                outputnode.inputs.subjects_dir = self.config.freesurfer_subjects_dir
                outputnode.inputs.subject_id = self.config.freesurfer_subject_id
            
        elif self.config.seg_tool == "Custom segmentation":
            
            outputnode.inputs.custom_wm_mask = self.config.white_matter_mask

    def define_inspect_outputs(self):
        if self.config.seg_tool == "Freesurfer":
            if self.config.use_existing_freesurfer_data == False:
                reconall_results_path = os.path.join(self.stage_dir,"reconall","result_reconall.pklz")
                if(os.path.exists(reconall_results_path)):
                    reconall_results = pickle.load(gzip.open(reconall_results_path))
                    fs = FreeSurferSource(subjects_dir=reconall_results.outputs.subjects_dir,
                                          subject_id=reconall_results.outputs.subject_id)
                    res = fs.run()
                    self.inspect_outputs_dict['brainmask/T1'] = ['tkmedit','-f',res.outputs.brainmask,'-surface',res.outputs.white[1],'-aux',res.outputs.T1,'-aux-surface',res.outputs.white[2]]
                    self.inspect_outputs_dict['norm/aseg'] = ['tkmedit','-f',res.outputs.norm,'-segmentation',res.outputs.aseg,os.path.join(os.environ['FREESURFER_HOME'],'FreeSurferColorLUT.txt')]
                    self.inspect_outputs_dict['norm/aseg/surf'] = ['tkmedit','-f',res.outputs.norm,'-surface',res.outputs.white[1],'-aux-surface',res.outputs.white[2],'-segmentation',res.outputs.aseg,os.path.join(os.environ['FREESURFER_HOME'],'FreeSurferColorLUT.txt')]
                    self.inspect_outputs = self.inspect_outputs_dict.keys()
            else:
                fs = FreeSurferSource(subjects_dir=self.config.freesurfer_subjects_dir,
                                          subject_id=self.config.freesurfer_subject_id)
                res = fs.run()
                self.inspect_outputs_dict['brainmask/T1'] = ['tkmedit','-f',res.outputs.brainmask,'-surface',res.outputs.white[1],'-aux',res.outputs.T1,'-aux-surface',res.outputs.white[2]]
                self.inspect_outputs_dict['norm/aseg'] = ['tkmedit','-f',res.outputs.norm,'-segmentation',res.outputs.aseg,os.path.join(os.environ['FREESURFER_HOME'],'FreeSurferColorLUT.txt')]
                self.inspect_outputs_dict['norm/aseg/surf'] = ['tkmedit','-f',res.outputs.norm,'-surface',res.outputs.white[1],'-aux-surface',res.outputs.white[2],'-segmentation',res.outputs.aseg,os.path.join(os.environ['FREESURFER_HOME'],'FreeSurferColorLUT.txt')]
                self.inspect_outputs = self.inspect_outputs_dict.keys()
        elif self.config.seg_tool == "Custom segmentation":
            self.inspect_outputs_dict['brainmask'] = ['fslview',self.config.white_matter_mask]
            self.inspect_outputs = self.inspect_outputs_dict.keys()
            
    def has_run(self):
        if self.config.use_existing_freesurfer_data or self.config.seg_tool == "Custom segmentation":
            return True
        else:
            return os.path.exists(os.path.join(self.stage_dir,"reconall","result_reconall.pklz"))

