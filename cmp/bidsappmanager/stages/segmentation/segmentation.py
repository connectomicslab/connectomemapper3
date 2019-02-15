# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP segmentation stage
"""

# General imports
import os
import pickle
import gzip
import pkg_resources

from traits.api import *
from traitsui.api import *

# Own imports
from cmp.bidsappmanager.stages.common import Stage

class SegmentationConfig(HasTraits):
    seg_tool = Enum(["Freesurfer","Custom segmentation"])
    make_isotropic = Bool(False)
    isotropic_vox_size = Float(1.2, desc='specify the size (mm)')
    isotropic_interpolation = Enum('cubic', 'weighted', 'nearest', 'sinc', 'interpolate',
                                desc='<interpolate|weighted|nearest|sinc|cubic> (default is cubic)')
    brain_mask_extraction_tool = Enum("Freesurfer",["Freesurfer","BET","ANTs","Custom"])
    ants_templatefile = File(desc="Anatomical template")
    ants_probmaskfile = File(desc="Brain probability mask")
    ants_regmaskfile = File(desc="Mask (defined in the template space) used during registration for brain extraction.To limit the metric computation to a specific region.")

    use_fsl_brain_mask = Bool(False)
    brain_mask_path = File
    use_existing_freesurfer_data = Bool(False)
    freesurfer_subjects_dir = Directory
    freesurfer_subject_id_trait = List
    freesurfer_subject_id = Str
    freesurfer_args = Str

    white_matter_mask = File(exist=True)

    traits_view = View(Item('seg_tool',label="Segmentation tool"),
                       Group(
                        HGroup('make_isotropic',Item('isotropic_vox_size',label="Voxel size (mm)",visible_when='make_isotropic')),
                        Item('isotropic_interpolation',label='Interpolation',visible_when='make_isotropic'),
                        'brain_mask_extraction_tool',
                        Item('ants_templatefile',label='Template',visible_when='brain_mask_extraction_tool == "ANTs"'),
                        Item('ants_probmaskfile',label='Probability mask',visible_when='brain_mask_extraction_tool == "ANTs"'),
                        Item('ants_regmaskfile',label='Extraction mask',visible_when='brain_mask_extraction_tool == "ANTs"'),
                        Item('brain_mask_path',label='Brain mask path',visible_when='brain_mask_extraction_tool == "Custom"'),
                        'freesurfer_args',
                        'use_existing_freesurfer_data',
                        Item('freesurfer_subjects_dir', enabled_when='use_existing_freesurfer_data == True'),
                        Item('freesurfer_subject_id',editor=EnumEditor(name='freesurfer_subject_id_trait'), enabled_when='use_existing_freesurfer_data == True'),
                        visible_when="seg_tool=='Freesurfer'"),
                       Group(
                        'white_matter_mask',
                        Item('brain_mask_path',label='Brain mask'),
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
    def __init__(self):
        self.name = 'segmentation_stage'
        self.config = SegmentationConfig()


        self.config.ants_templatefile = os.path.join('app','connectomemapper3','cmtklib','data', 'segmentation', 'ants_template_IXI', 'T_template2_BrainCerebellum.nii.gz')
        self.config.ants_probmaskfile = os.path.join('app','connectomemapper3','cmtklib','data', 'segmentation', 'ants_template_IXI', 'T_template_BrainCerebellumProbabilityMask.nii.gz')
        self.config.ants_regmaskfile = os.path.join('app','connectomemapper3','cmtklib','data', 'segmentation', 'ants_template_IXI', 'T_template_BrainCerebellumMask.nii.gz')
        # FIXME
        # self.config.ants_templatefile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'ants_template_IXI', 'T_template2_BrainCerebellum.nii.gz'))
        # self.config.ants_probmaskfile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'ants_template_IXI', 'T_template_BrainCerebellumProbabilityMask.nii.gz'))
        # self.config.ants_regmaskfile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'ants_template_IXI', 'T_template_BrainCerebellumMask.nii.gz'))
        self.inputs = ["T1","brain_mask"]
        self.outputs = ["subjects_dir","subject_id","custom_wm_mask","brain_mask","brain"]

    def define_inspect_outputs(self):
        print "stage_dir : %s" % self.stage_dir
        if self.config.seg_tool == "Freesurfer":
            fs_path = ''
            if self.config.use_existing_freesurfer_data == False:
                reconall_results_path = os.path.join(self.stage_dir,"reconall","result_reconall.pklz")
                fs_path = self.config.freesurfer_subject_id
                if(os.path.exists(reconall_results_path)):
                    reconall_results = pickle.load(gzip.open(reconall_results_path))
            else:
                fs_path = os.path.join(self.config.freesurfer_subjects_dir, self.config.freesurfer_subject_id)
            print "fs_path : %s" % fs_path

            if 'FREESURFER_HOME' not in os.environ:
                colorLUT_file = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'freesurfer', 'FreeSurferColorLUT.txt'))
            else:
                colorLUT_file = os.path.join(os.environ['FREESURFER_HOME'],'FreeSurferColorLUT.txt')
            
            self.inspect_outputs_dict['brainmask/T1'] = ['tkmedit','-f',os.path.join(fs_path,'mri','brainmask.mgz'),'-surface',os.path.join(fs_path,'surf','lh.white'),'-aux',os.path.join(fs_path,'mri','T1.mgz'),'-aux-surface',os.path.join(fs_path,'surf','rh.white')]
            self.inspect_outputs_dict['norm/aseg'] = ['tkmedit','-f',os.path.join(fs_path,'mri','norm.mgz'),'-segmentation',os.path.join(fs_path,'mri','aseg.mgz'),colorLUT_file]
            self.inspect_outputs_dict['norm/aseg/surf'] = ['tkmedit','-f',os.path.join(fs_path,'mri','norm.mgz'),'-surface',os.path.join(fs_path,'surf','lh.white'),'-aux-surface',os.path.join(fs_path,'surf','rh.white'),'-segmentation',os.path.join(fs_path,'mri','aseg.mgz'),colorLUT_file]

        elif self.config.seg_tool == "Custom segmentation":
            self.inspect_outputs_dict['brainmask'] = ['fslview',self.config.white_matter_mask]

        self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)

    def has_run(self):
        if self.config.use_existing_freesurfer_data or self.config.seg_tool == "Custom segmentation":
            return True
        else:
            return os.path.exists(os.path.join(self.stage_dir,"reconall","result_reconall.pklz"))
