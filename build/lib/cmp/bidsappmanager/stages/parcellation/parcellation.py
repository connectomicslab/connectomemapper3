# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Parcellation
"""

# General imports
import os
import pickle
import gzip
import pkg_resources

from traits.api import *
from traits.trait_handlers import TraitListObject

from traitsui.api import *

# Own imports
from cmp.bidsappmanager.stages.common import Stage

class ParcellationConfig(HasTraits):
    pipeline_mode = Enum(["Diffusion","fMRI"])
    parcellation_scheme = Str('Lausanne2008')
    parcellation_scheme_editor = List(['NativeFreesurfer','Lausanne2008','Lausanne2018','Custom'])
    include_thalamic_nuclei_parcellation = Bool(True)
    template_thalamus = File()
    thalamic_nuclei_maps = File()
    segment_hippocampal_subfields = Bool(True)
    segment_brainstem = Bool(True)
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
                             ),
                       Group(
                             'segment_hippocampal_subfields',
                             'segment_brainstem',
                             'include_thalamic_nuclei_parcellation',
                             visible_when='parcellation_scheme=="Lausanne2018"'
                             )
                       )

    def update_atlas_info(self):
        atlas_name = os.path.basename(self.atlas_nifti_file)
        atlas_name = os.path.splitext(os.path.splitext(atlas_name)[0])[0].encode('ascii')
        self.atlas_info = {atlas_name : {'number_of_regions':self.number_of_regions,'node_information_graphml':self.graphml_file}}
        print "Update atlas information"
        print self.atlas_info

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
        self.config.template_thalamus = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'thalamus2018', 'mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz'))
        self.config.thalamic_nuclei_maps = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'thalamus2018', 'Thalamus_Nuclei-HCP-4DSPAMs.nii.gz'))
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["subjects_dir","subject_id","custom_wm_mask"]
        self.outputs = [#"aseg_file",
            "T1","brain","aseg","brain_mask",
    		"wm_mask_file",
            "wm_eroded",
            "csf_eroded",
            "brain_eroded",
            "gm_mask_file",
            "aseg",
    	       #"cc_unknown_file","ribbon_file","roi_files",
            "roi_volumes","roi_colorLUTs","roi_graphMLs","parcellation_scheme","atlas_info"]

    def define_inspect_outputs(self):
        print "stage_dir : %s" % self.stage_dir
        print "parcellation scheme : %s" % self.config.parcellation_scheme
        print "atlas info : "
        print self.config.atlas_info

        if self.config.parcellation_scheme != "Custom":
            parc_results_path = os.path.join(self.stage_dir,"%s_parcellation" % self.config.parcellation_scheme,"result_%s_parcellation.pklz" % self.config.parcellation_scheme)
            print "parc_results_path : %s" % parc_results_path
            if(os.path.exists(parc_results_path)):
                parc_results = pickle.load(gzip.open(parc_results_path))
                print parc_results
                #print parc_results.outputs.roi_files_in_structural_space
                white_matter_file = parc_results.outputs.white_matter_mask_file
                if isinstance(parc_results.outputs.roi_files_in_structural_space, (str,unicode)):
                    print "str: %s" % parc_results.outputs.roi_files_in_structural_space
                    lut_file = pkg_resources.resource_filename('cmtklib',os.path.join('data','parcellation','nativefreesurfer','freesurferaparc','FreeSurferColorLUT_adapted.txt'))
                    roi_v = parc_results.outputs.roi_files_in_structural_space
                    print "roi_v : %s" % os.path.basename(roi_v)
                    self.inspect_outputs_dict[os.path.basename(roi_v)] = ['freeview','-v',
                                                                           white_matter_file+':colormap=GEColor',
                                                                           roi_v+":colormap=lut:lut="+lut_file]
                elif isinstance(parc_results.outputs.roi_files_in_structural_space, TraitListObject):
                    print parc_results.outputs.roi_files_in_structural_space
                    if self.config.parcellation_scheme == 'Lausanne2008':
                        resolution = {'1':'resolution83','2':'resolution150','3':'resolution258','4':'resolution500','5':'resolution1015'}
                        for roi_v in parc_results.outputs.roi_files_in_structural_space:
                            roi_basename = os.path.basename(roi_v)
                            scale = roi_basename[16:-7]
                            print scale
                            lut_file = pkg_resources.resource_filename('cmtklib',os.path.join('data','parcellation','lausanne2008',resolution[scale],resolution[scale] + '_LUT.txt'))
                            self.inspect_outputs_dict[roi_basename] = ['freeview','-v',
                                                                               white_matter_file+':colormap=GEColor',
                                                                               roi_v+":colormap=lut:lut="+lut_file]
                    elif self.config.parcellation_scheme == 'Lausanne2018':
                        # resolution = {'1':'resolution1','2':'resolution2','3':'resolution3','4':'resolution4','5':'resolution5'}
                        parc_results_path = os.path.join(self.stage_dir,"parcCombiner","result_parcCombiner.pklz")
                        print "parc_results_path : %s" % parc_results_path
                        if(os.path.exists(parc_results_path)):
                            parc_results = pickle.load(gzip.open(parc_results_path))

                            for roi_v, lut_file in zip(parc_results.outputs.output_rois,parc_results.outputs.colorLUT_files):
                                roi_basename = os.path.basename(roi_v)
                                self.inspect_outputs_dict[roi_basename] = ['freeview','-v',
                                                                                   white_matter_file+':colormap=GEColor',
                                                                                   roi_v+":colormap=lut:lut="+lut_file]
                        # if self.config.include_thalamic_nuclei_parcellation:
                        results_path = os.path.join(self.stage_dir,"parcThal","result_parcThal.pklz")

                        if(os.path.exists(results_path)):
                            results = pickle.load(gzip.open(results_path))
                            self.inspect_outputs_dict['Thalamic nuclei - Probability maps'] = ['fslview',results.inputs['T1w_image'],results.outputs.prob_maps_registered,'-l',"Copper",'-t','0.5']
                            self.inspect_outputs_dict['Thalamic nuclei - MaxProb labels'] = ['fslview',results.inputs['T1w_image'],results.outputs.max_prob_registered,"-l","Random-Rainbow",'-t','0.5']

                        # if self.config.segment_brainstem:
                        results_path = os.path.join(self.stage_dir,"parcBrainStem","result_parcBrainStem.pklz")

                        if(os.path.exists(results_path)):
                            results = pickle.load(gzip.open(results_path))
                            self.inspect_outputs_dict['Brainstem structures'] = ['fslview',results.outputs.brainstem_structures,"-l","Random-Rainbow"]

                        # if self.config.segment_hippocampal_subfields:
                        results_path = os.path.join(self.stage_dir,"parcHippo","result_parcHippo.pklz")

                        if(os.path.exists(results_path)):
                            results = pickle.load(gzip.open(results_path))
                            self.inspect_outputs_dict['Hippocampal subfields'] = ['fslview',results.outputs.lh_hipposubfields,"-l","Random-Rainbow",results.outputs.rh_hipposubfields,"-l","Random-Rainbow"]

                #self.inspect_outputs = self.inspect_outputs_dict.keys()
        else:
            self.inspect_outputs_dict["Custom atlas"] = ['fslview',self.config.atlas_nifti_file,"-l","Random-Rainbow"]

        self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)

    def has_run(self):
        if self.config.parcellation_scheme != "Custom":
            if self.config.parcellation_scheme == 'Lausanne2018':
                return os.path.exists(os.path.join(self.stage_dir,"parcCombiner","result_parcCombiner.pklz"))
            else:
                return os.path.exists(os.path.join(self.stage_dir,"%s_parcellation" % self.config.parcellation_scheme,"result_%s_parcellation.pklz" % self.config.parcellation_scheme))
        else:
            return os.path.exists(self.config.atlas_nifti_file)
