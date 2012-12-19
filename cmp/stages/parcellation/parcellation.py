# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Parcellation
""" 

# General imports
from traits.api import *
from traitsui.api import *
import pkg_resources
import os
import pickle
import gzip

# Nipype imports
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.cmtk as cmtk

# Own imports
from cmp.stages.common import Stage

class ParcellationConfig(HasTraits):
    parcellation_scheme = Enum('Lausanne2008',['NativeFreesurfer','Lausanne2008'])

    traits_view = View('parcellation_scheme')

class ParcellationStage(Stage):
    name = 'parcellation_stage'
    config = ParcellationConfig()
    inputs = ["subjects_dir","subject_id"]
    outputs = ["aseg_file","wm_mask_file","cc_unknown_file",
               "ribbon_file","roi_files","roi_volumes","parcellation_scheme"]
    
    def create_workflow(self, flow, inputnode, outputnode):
        outputnode.inputs.parcellation_scheme = self.config.parcellation_scheme
        
        parc_node = pe.Node(interface=cmtk.Parcellate(),name="parcellation")
        parc_node.inputs.parcellation_scheme = self.config.parcellation_scheme
        
        flow.connect([
                     (inputnode,parc_node,[("subjects_dir","subjects_dir"),("subject_id","subject_id")]),
                     (parc_node,outputnode,[("aseg_file","aseg_file"),("cc_unknown_file","cc_unknown_file"),
                                            ("ribbon_file","ribbon_file"),("white_matter_mask_file","wm_mask_file"),
                                            ("roi_files","roi_files"),("roi_files_in_structural_space","roi_volumes")])
                    ])

    def define_inspect_outputs(self):
        parc_results_path = os.path.join(self.stage_dir,"parcellation","result_parcellation.pklz")
        if(os.path.exists(parc_results_path)):
            parc_results = pickle.load(gzip.open(parc_results_path))
            for roi_v in parc_results.outputs.roi_files_in_structural_space:
                self.inspect_outputs_dict[os.path.basename(roi_v)] = ['freeview','-v',
                 parc_results.outputs.white_matter_mask_file+':colormap=GEColor',
                    roi_v+":colormap=lut:lut="+pkg_resources.resource_filename('cmtklib',os.path.join('data','parcellation','nativefreesurfer','freesurferaparc','FreeSurferColorLUT_adapted.txt'))]
            self.inspect_outputs = self.inspect_outputs_dict.keys()
            
    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"parcellation","result_parcellation.pklz"))

