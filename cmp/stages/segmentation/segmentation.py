# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP segmentation stage
""" 

# General imports
import os
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.freesurfer as fs

# Own imports
from cmp.stages.common import CMP_Stage

class Segmentation_Config(HasTraits):
    use_existing_freesurfer_data = Bool(False)
    freesurfer_subjects_dir = Directory
    freesurfer_subject_id_trait = List
    freesurfer_subject_id = Str
    traits_view = View('use_existing_freesurfer_data',
                        Item('freesurfer_subjects_dir', enabled_when='use_existing_freesurfer_data == True'),
                        Item('freesurfer_subject_id',editor=EnumEditor(name='freesurfer_subject_id_trait'), enabled_when='use_existing_freesurfer_data == True')
                        )
    
    def _freesurfer_subjects_dir_changed(self, old, new):
        dirnames = [name for name in os.listdir(self.freesurfer_subjects_dir) if
             os.path.isdir(os.path.join(self.freesurfer_subjects_dir, name))]
        self.freesurfer_subject_id_trait = dirnames
        

class Segmentation(CMP_Stage):
    # General and UI members
    name = 'Segmentation'
    display_color = 'lightyellow'
    position_x = 70
    position_y = 420
    config = Segmentation_Config()

    
    def create_workflow(self):
        flow = pe.Workflow(name="Segmentation_stage")
        
        if self.config.use_existing_freesurfer_data == False:
            inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1"]),name="inputnode")
            
            # Converting to .mgz format
            fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type="mgz",out_file="T1.mgz"),name="fs_mriconvert")
            
            # ReconAll => named outputnode as we don't want to select a specific output....
            fs_reconall = pe.Node(interface=fs.ReconAll(),name="outputnode")
            fs_reconall.inputs.subjects_dir = self.config.freesurfer_subjects_dir
            if self.config.use_existing_freesurfer_data == True:
                fs_reconall.inputs.subject_id = self.config.freesurfer_subject_id
            
            flow.connect([
                        (inputnode,fs_mriconvert,[('T1','in_file')]),
                        (fs_mriconvert,fs_reconall,[('out_file','T1_files')]),
                        ])
            
        else:
            inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1"]),name="inputnode")
            outputnode = pe.Node(interface=util.IdentityInterface(fields=["subjects_dir","subject_id"]),name="outputnode")
            outputnode.inputs.subjects_dir = self.config.freesurfer_subjects_dir
            outputnode.inputs.subject_id = self.config.freesurfer_subject_id
            flow.add_nodes([inputnode,outputnode])
        
        return flow

	
