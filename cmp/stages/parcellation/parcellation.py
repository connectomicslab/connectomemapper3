# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Parcellation
""" 

# General imports
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

# Nipype imports
import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.cmtk as cmtk

# Own imports
from cmp.stages.common import CMP_Stage

class CMP_Parcellation_Config(HasTraits):
    parcellation_scheme = Enum('Lausanne2008',['NativeFreesurfer','Lausanne2008'])

    traits_view = View('parcellation_scheme')

class Parcellation(CMP_Stage):
    name = 'Parcellation'
    display_color = 'lightyellow'
    position_x = 70
    position_y = 330
    config = CMP_Parcellation_Config()
    
    def create_workflow(self):
        flow = pe.Workflow(name="Parcellation_stage")
        
        inputnode = pe.Node(interface=util.IdentityInterface(fields=["subjects_dir","subject_id"]),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=["aseg_file","wm_mask_file","cc_unknown_file",
                            "ribbon_file","roi_files","roi_volumes","parcellation_scheme"]),name="outputnode")
        flow.add_nodes([inputnode,outputnode])
        
        outputnode.inputs.parcellation_scheme = self.config.parcellation_scheme
        
        parc_node = pe.Node(interface=cmtk.Parcellate(),name="cmtk_parcellation")
        parc_node.inputs.parcellation_scheme = self.config.parcellation_scheme
        
        flow.connect([
                     (inputnode,parc_node,[("subjects_dir","subjects_dir"),("subject_id","subject_id")]),
                     (parc_node,outputnode,[("aseg_file","aseg_file"),("cc_unknown_file","cc_unknown_file"),
                                            ("ribbon_file","ribbon_file"),("white_matter_mask_file","wm_mask_file"),
                                            ("roi_files","roi_files"),("roi_files_in_structural_space","roi_volumes")])
                    ])

        return flow

