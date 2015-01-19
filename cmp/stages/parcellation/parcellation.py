# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
from traits.trait_handlers import TraitListObject

# Nipype imports
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.cmtk as cmtk
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage

class ParcellationConfig(HasTraits):
    pipeline_mode = Enum(["Diffusion","fMRI"])
    parcellation_scheme = Str('Lausanne2008')
    parcellation_scheme_editor = List(['NativeFreesurfer','Lausanne2008','Custom'])
    pre_custom = Str('Lausanne2008')
    #atlas_name = Str()
    number_of_regions = Int()
    atlas_nifti_file = File(exists=True)
    csf_file = File(exists=True)
    brain_file = File(exists=True)
    graphml_file = File(exists=True)
    atlas_info = Dict()
    traits_view = View(Item('parcellation_scheme',editor=EnumEditor(name='parcellation_scheme_editor')),
                       Group(
                             'number_of_regions',
                             'atlas_nifti_file',
                             'graphml_file',
                             Group(
                                   "csf_file","brain_file",
                                   show_border=True,
                                   label="Files for nuisance regression (optional)",
                                   visible_when="pipeline_mode=='fMRI'"
                                   ),
                             visible_when='parcellation_scheme=="Custom"'
                             )
                       )
    
    def update_atlas_info(self):
        atlas_name = os.path.basename(self.atlas_nifti_file)
        atlas_name = os.path.splitext(os.path.splitext(atlas_name)[0])[0].encode('ascii')
        self.atlas_info = {atlas_name : {'number_of_regions':self.number_of_regions,'node_information_graphml':self.graphml_file}}
    
    def _atlas_nifti_file_changed(self,new):
        self.update_atlas_info()
        
    def _number_of_regions_changed(self,new):
        self.update_atlas_info()
        
    def _graphml_file_changed(self,new):
        self.update_atlas_info()
        
    def _parcellation_scheme_changed(self,old,new):
        if new == 'Custom':
            self.pre_custom = old
          
class ParcellationStage(Stage):
    
    def __init__(self,pipeline_mode):
        self.name = 'parcellation_stage'
        self.config = ParcellationConfig()
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["subjects_dir","subject_id","custom_wm_mask"]
        self.outputs = [#"aseg_file",
    		"wm_mask_file",
            "wm_eroded",
            "csf_eroded",
            "brain_eroded",
    	       #"cc_unknown_file","ribbon_file","roi_files",
            "roi_volumes","parcellation_scheme","atlas_info"]
    
    def create_workflow(self, flow, inputnode, outputnode):
        outputnode.inputs.parcellation_scheme = self.config.parcellation_scheme
        
        if self.config.parcellation_scheme != "Custom":
            parc_node = pe.Node(interface=cmtk.Parcellate(),name="%s_parcellation" % self.config.parcellation_scheme)
            parc_node.inputs.parcellation_scheme = self.config.parcellation_scheme
            
            flow.connect([
                         (inputnode,parc_node,[("subjects_dir","subjects_dir"),(("subject_id",os.path.basename),"subject_id")]),
                         (parc_node,outputnode,[#("aseg_file","aseg_file"),("cc_unknown_file","cc_unknown_file"),
                                                #("ribbon_file","ribbon_file"),("roi_files","roi_files"),
    					     ("white_matter_mask_file","wm_mask_file"),
                             ("roi_files_in_structural_space","roi_volumes"),
                             ("wm_eroded","wm_eroded"),("csf_eroded","csf_eroded"),("brain_eroded","brain_eroded")])
                        ])
        else:
            temp_node = pe.Node(interface=util.IdentityInterface(fields=["roi_volumes","atlas_info"]),name="custom_parcellation")
            temp_node.inputs.roi_volumes = self.config.atlas_nifti_file
            temp_node.inputs.atlas_info = self.config.atlas_info
            flow.connect([
                        (temp_node,outputnode,[("roi_volumes","roi_volumes")]),
                        (temp_node,outputnode,[("atlas_info","atlas_info")]),
                        (inputnode,outputnode,[("custom_wm_mask","wm_mask_file")])
                        ])
            if self.config.pipeline_mode == "fMRI":
                erode_wm = pe.Node(interface=cmtk.Erode(),name="erode_wm")
                flow.connect([
                            (inputnode,erode_wm,[("custom_wm_mask","in_file")]),
                            (erode_wm,outputnode,[("out_file","wm_eroded")]),
                            ])
                if os.path.exists(self.config.csf_file):
                    erode_csf = pe.Node(interface=cmtk.Erode(in_file = self.config.csf_file),name="erode_csf")
                    flow.connect([
                                (erode_csf,outputnode,[("out_file","csf_eroded")])
                                ])
                if os.path.exists(self.config.brain_file):
                    erode_brain = pe.Node(interface=cmtk.Erode(in_file = self.config.brain_file),name="erode_brain")
                    flow.connect([
                                (erode_brain,outputnode,[("out_file","brain_eroded")])
                                ])

    def define_inspect_outputs(self):
        if self.config.parcellation_scheme != "Custom":
            parc_results_path = os.path.join(self.stage_dir,"%s_parcellation" % self.config.parcellation_scheme,"result_%s_parcellation.pklz" % self.config.parcellation_scheme)
            if(os.path.exists(parc_results_path)):
                parc_results = pickle.load(gzip.open(parc_results_path))
                white_matter_file = parc_results.outputs.white_matter_mask_file
                if type(parc_results.outputs.roi_files_in_structural_space) == str:
                    lut_file = pkg_resources.resource_filename('cmtklib',os.path.join('data','parcellation','nativefreesurfer','freesurferaparc','FreeSurferColorLUT_adapted.txt'))
                    roi_v = parc_results.outputs.roi_files_in_structural_space
                    self.inspect_outputs_dict[os.path.basename(roi_v)] = ['freeview','-v',
                                                                           white_matter_file+':colormap=GEColor',
                                                                           roi_v+":colormap=lut:lut="+lut_file]
                elif type(parc_results.outputs.roi_files_in_structural_space) == TraitListObject:
                    resolution = {'33':'resolution83','60':'resolution150','125':'resolution258','250':'resolution500','500':'resolution1015'}
                    for roi_v in parc_results.outputs.roi_files_in_structural_space:
                        roi_basename = os.path.basename(roi_v)
                        scale = roi_basename[16:-7]
                        lut_file = pkg_resources.resource_filename('cmtklib',os.path.join('data','parcellation','lausanne2008',resolution[scale],resolution[scale] + '_LUT.txt'))
                        self.inspect_outputs_dict[roi_basename] = ['freeview','-v',
                                                                           white_matter_file+':colormap=GEColor',
                                                                           roi_v+":colormap=lut:lut="+lut_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()
        else:
            self.inspect_outputs_dict["Custom atlas"] = ['fslview',self.config.atlas_nifti_file,"-l","Random-Rainbow"]
            self.inspect_outputs = self.inspect_outputs_dict.keys()
            
    def has_run(self):
        if self.config.parcellation_scheme != "Custom":
            return os.path.exists(os.path.join(self.stage_dir,"%s_parcellation" % self.config.parcellation_scheme,"result_%s_parcellation.pklz" % self.config.parcellation_scheme))
        else:
            return os.path.exists(self.config.atlas_nifti_file)

