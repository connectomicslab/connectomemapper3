# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP segmentation stage
"""

# General imports
import os
from traits.api import *
import pickle
import gzip
import shutil
import pkg_resources
import multiprocessing as mp

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
from nipype.interfaces.io import FreeSurferSource
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.freesurfer import copyBrainMaskToFreesurfer, copyFileToFreesurfer


class SegmentationConfig(HasTraits):
    seg_tool = Enum(["Freesurfer", "Custom segmentation"])
    make_isotropic = Bool(False)
    isotropic_vox_size = Float(1.2, desc='specify the size (mm)')
    isotropic_interpolation = Enum('cubic', 'weighted', 'nearest', 'sinc', 'interpolate',
                                   desc='<interpolate|weighted|nearest|sinc|cubic> (default is cubic)')
    brain_mask_extraction_tool = Enum("Freesurfer", ["Freesurfer", "BET", "ANTs", "Custom"])
    ants_templatefile = File(desc="Anatomical template")
    ants_probmaskfile = File(desc="Brain probability mask")
    ants_regmaskfile = File(
        desc="Mask (defined in the template space) used during registration for brain extraction.To limit the metric computation to a specific region.")
    
    use_fsl_brain_mask = Bool(False)
    brain_mask_path = File
    use_existing_freesurfer_data = Bool(False)
    freesurfer_subjects_dir = Directory
    freesurfer_subject_id_trait = List
    freesurfer_subject_id = Str
    freesurfer_args = Str
    
    white_matter_mask = File(exist=True)
    
    def _freesurfer_subjects_dir_changed(self, old, new):
        dirnames = [name for name in os.listdir(self.freesurfer_subjects_dir) if
                    os.path.isdir(os.path.join(self.freesurfer_subjects_dir, name))]
        self.freesurfer_subject_id_trait = dirnames
    
    def _use_existing_freesurfer_data_changed(self, new):
        if new == True:
            self.custom_segmentation = False


def extract_base_directory(file):
    # print "Extract reconall base dir : %s" % file[:-17]
    return file[:-17]


class SegmentationStage(Stage):
    # General and UI members
    def __init__(self):
        self.name = 'segmentation_stage'
        self.config = SegmentationConfig()
        self.config.ants_templatefile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation',
                                                                                                'ants_template_IXI',
                                                                                                'T_template2_BrainCerebellum.nii.gz'))
        self.config.ants_probmaskfile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation',
                                                                                                'ants_template_IXI',
                                                                                                'T_template_BrainCerebellumProbabilityMask.nii.gz'))
        self.config.ants_regmaskfile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation',
                                                                                               'ants_template_IXI',
                                                                                               'T_template_BrainCerebellumMask.nii.gz'))
        self.inputs = ["T1", "brain_mask"]
        self.outputs = ["subjects_dir", "subject_id", "custom_wm_mask", "brain_mask", "brain"]
    
    def create_workflow(self, flow, inputnode, outputnode):
        if self.config.seg_tool == "Freesurfer":
            if self.config.use_existing_freesurfer_data == False:
                # Converting to .mgz format
                fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type="mgz", out_file="T1.mgz"), name="mgz_convert")
                
                if self.config.make_isotropic:
                    fs_mriconvert.inputs.vox_size = (
                    self.config.isotropic_vox_size, self.config.isotropic_vox_size, self.config.isotropic_vox_size)
                    fs_mriconvert.inputs.resample_type = self.config.isotropic_interpolation
                
                rename = pe.Node(util.Rename(), name="copy_orig")
                orig_dir = os.path.join(self.config.freesurfer_subject_id, "mri", "orig")
                if not os.path.exists(orig_dir):
                    os.makedirs(orig_dir)
                    print("INFO : Folder not existing; %s created!" % orig_dir)
                rename.inputs.format_string = os.path.join(orig_dir, "001.mgz")
                
                if self.config.brain_mask_extraction_tool == "Freesurfer":
                    # ReconAll => named outputnode as we don't want to select a specific output....
                    fs_reconall = pe.Node(interface=fs.ReconAll(flags='-no-isrunning'), name="reconall")
                    fs_reconall.inputs.directive = 'all'
                    fs_reconall.inputs.args = self.config.freesurfer_args
                    
                    # fs_reconall.inputs.subjects_dir and fs_reconall.inputs.subject_id set in cmp/pipelines/diffusion/diffusion.py
                    fs_reconall.inputs.subjects_dir = self.config.freesurfer_subjects_dir
                    
                    # fs_reconall.inputs.hippocampal_subfields_T1 = self.config.segment_hippocampal_subfields
                    # fs_reconall.inputs.brainstem = self.config.segment_brainstem
                    
                    def isavailable(file):
                        # print "T1 is available"
                        return file
                    
                    flow.connect([
                        (inputnode, fs_mriconvert, [(('T1', isavailable), 'in_file')]),
                        (fs_mriconvert, rename, [('out_file', 'in_file')]),
                        (rename, fs_reconall, [(("out_file", extract_base_directory), "subject_id")]),
                        (fs_reconall, outputnode, [('subjects_dir', 'subjects_dir'), ('subject_id', 'subject_id')]),
                    ])
                else:
                    # ReconAll => named outputnode as we don't want to select a specific output....
                    fs_autorecon1 = pe.Node(interface=fs.ReconAll(flags='-no-isrunning'), name="autorecon1")
                    fs_autorecon1.inputs.directive = 'autorecon1'
                    if self.config.brain_mask_extraction_tool == "Custom" or self.config.brain_mask_extraction_tool == "ANTs":
                        fs_autorecon1.inputs.flags = '-noskullstrip'
                    fs_autorecon1.inputs.args = self.config.freesurfer_args
                    
                    # fs_reconall.inputs.subjects_dir and fs_reconall.inputs.subject_id set in cmp/pipelines/diffusion/diffusion.py
                    fs_autorecon1.inputs.subjects_dir = self.config.freesurfer_subjects_dir
                    
                    def isavailable(file):
                        # print "Is available"
                        return file
                    
                    flow.connect([
                        (inputnode, fs_mriconvert, [(('T1', isavailable), 'in_file')]),
                        (fs_mriconvert, rename, [('out_file', 'in_file')]),
                        (rename, fs_autorecon1, [(("out_file", extract_base_directory), "subject_id")])
                    ])
                    
                    fs_source = pe.Node(interface=FreeSurferSource(), name='fs_source')
                    
                    fs_mriconvert_nu = pe.Node(interface=fs.MRIConvert(out_type="niigz", out_file="nu.nii.gz"),
                                               name="niigz_convert")
                    
                    flow.connect([
                        (fs_autorecon1, fs_source, [('subjects_dir', 'subjects_dir'), ('subject_id', 'subject_id')]),
                        (fs_source, fs_mriconvert_nu, [('nu', 'in_file')])
                    ])
                    
                    fs_mriconvert_brainmask = pe.Node(interface=fs.MRIConvert(out_type="mgz", out_file="brainmask.mgz"),
                                                      name='fs_mriconvert_bet_brainmask')
                    
                    if self.config.brain_mask_extraction_tool == "BET":
                        fsl_bet = pe.Node(
                            interface=fsl.BET(out_file='brain.nii.gz', mask=True, skull=True, robust=True),
                            name='fsl_bet')
                        
                        flow.connect([
                            (fs_mriconvert_nu, fsl_bet, [('out_file', 'in_file')]),
                            (fsl_bet, fs_mriconvert_brainmask, [('out_file', 'in_file')])
                        ])
                    
                    elif self.config.brain_mask_extraction_tool == "ANTs":
                        # templatefile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'ants_template_IXI', 'T_template2_BrainCerebellum.nii.gz'))
                        # probmaskfile = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'ants_template_IXI', 'T_template_BrainCerebellumProbabilityMask.nii.gz'))
                        
                        ants_bet = pe.Node(interface=ants.BrainExtraction(out_prefix='ants_bet_'), name='ants_bet')
                        ants_bet.inputs.brain_template = self.config.ants_templatefile
                        ants_bet.inputs.brain_probability_mask = self.config.ants_probmaskfile
                        ants_bet.inputs.extraction_registration_mask = self.config.ants_regmaskfile
                        ants_bet.inputs.num_threads = mp.cpu_count()
                        
                        flow.connect([
                            (fs_mriconvert_nu, ants_bet, [('out_file', 'anatomical_image')]),
                            (ants_bet, fs_mriconvert_brainmask, [('BrainExtractionBrain', 'in_file')])
                        ])
                    elif self.config.brain_mask_extraction_tool == "Custom":
                        fs_mriconvert_brainmask.inputs.in_file = os.path.abspath(self.config.brain_mask_path)
                    
                    # copy_brainmask_to_fs = pe.Node(interface=copyFileToFreesurfer(),name='copy_brainmask_to_fs')
                    # copy_brainmask_to_fs.inputs.out_file = os.path.join(self.config.freesurfer_subject_id,"mri","brainmask.mgz")
                    
                    # copy_brainmaskauto_to_fs = pe.Node(interface=copyFileToFreesurfer(),name='copy_brainmaskauto_to_fs')
                    # copy_brainmaskauto_to_fs.inputs.out_file = os.path.join(self.config.freesurfer_subject_id,"mri","brainmask.auto.mgz")
                    
                    # flow.connect([
                    #             (fs_mriconvert_brainmask,copy_brainmask_to_fs,[('out_file','in_file')]),
                    #             (fs_mriconvert_brainmask,copy_brainmaskauto_to_fs,[('out_file','in_file')])
                    #             ])
                    
                    copy_brainmask_to_fs = pe.Node(interface=copyBrainMaskToFreesurfer(), name='copy_brainmask_to_fs')
                    
                    flow.connect([
                        (rename, copy_brainmask_to_fs, [(("out_file", extract_base_directory), "subject_dir")]),
                        (fs_mriconvert_brainmask, copy_brainmask_to_fs, [('out_file', 'in_file')])
                    ])
                    
                    # flow.connect([
                    #             (fs_source,fs_mriconvert_nu,[('nu','in_file')])
                    #             ])
                    
                    def get_freesurfer_subject_id(file):
                        # print "Extract reconall base dir : %s" % file[:-18]
                        return file[:-18]
                    
                    fs_reconall23 = pe.Node(interface=fs.ReconAll(flags='-no-isrunning'), name="reconall23")
                    fs_reconall23.inputs.directive = 'autorecon2'
                    fs_reconall23.inputs.args = self.config.freesurfer_args
                    fs_reconall23.inputs.flags = '-autorecon3'
                    
                    # fs_reconall.inputs.subjects_dir and fs_reconall.inputs.subject_id set in cmp/pipelines/diffusion/diffusion.py
                    fs_reconall23.inputs.subjects_dir = self.config.freesurfer_subjects_dir
                    
                    # fs_reconall.inputs.hippocampal_subfields_T1 = self.config.segment_hippocampal_subfields
                    # fs_reconall.inputs.brainstem = self.config.segment_brainstem
                    
                    flow.connect([
                        (copy_brainmask_to_fs, fs_reconall23,
                         [(("out_brainmask_file", get_freesurfer_subject_id), "subject_id")]),
                        (fs_reconall23, outputnode, [('subjects_dir', 'subjects_dir'), ('subject_id', 'subject_id')])
                    ])
            
            else:
                outputnode.inputs.subjects_dir = self.config.freesurfer_subjects_dir
                outputnode.inputs.subject_id = self.config.freesurfer_subject_id
        
        elif self.config.seg_tool == "Custom segmentation":
            
            apply_mask = pe.Node(interface=fsl.ApplyMask(), name='apply_mask')
            apply_mask.inputs.mask_file = self.config.brain_mask_path
            apply_mask.inputs.out_file = 'brain.nii.gz'
            
            flow.connect([
                (inputnode, apply_mask, [("T1", "in_file")]),
                (apply_mask, outputnode, [("out_file", "brain")]),
            ])
            
            outputnode.inputs.brain_mask = self.config.brain_mask_path
            outputnode.inputs.custom_wm_mask = self.config.white_matter_mask
    
    def define_inspect_outputs(self):
        # print "stage_dir : %s" % self.stage_dir
        if self.config.seg_tool == "Freesurfer":
            fs_path = ''
            if self.config.use_existing_freesurfer_data == False:
                reconall_results_path = os.path.join(self.stage_dir, "reconall", "result_reconall.pklz")
                fs_path = self.config.freesurfer_subject_id
                if (os.path.exists(reconall_results_path)):
                    reconall_results = pickle.load(gzip.open(reconall_results_path))
                    fs_path = reconall_results.outputs.subject_id
            else:
                fs_path = os.path.join(self.config.freesurfer_subjects_dir, self.config.freesurfer_subject_id)
            print ("fs_path : %s" % fs_path)
            
            if 'FREESURFER_HOME' not in os.environ:
                colorLUT_file = pkg_resources.resource_filename('cmtklib',
                                                                os.path.join('data', 'segmentation', 'freesurfer',
                                                                             'FreeSurferColorLUT.txt'))
            else:
                colorLUT_file = os.path.join(os.environ['FREESURFER_HOME'], 'FreeSurferColorLUT.txt')
            
            self.inspect_outputs_dict['brainmask/T1'] = ['tkmedit', '-f', os.path.join(fs_path, 'mri', 'brainmask.mgz'),
                                                         '-surface', os.path.join(fs_path, 'surf', 'lh.white'), '-aux',
                                                         os.path.join(fs_path, 'mri', 'T1.mgz'), '-aux-surface',
                                                         os.path.join(fs_path, 'surf', 'rh.white')]
            self.inspect_outputs_dict['norm/aseg'] = ['tkmedit', '-f', os.path.join(fs_path, 'mri', 'norm.mgz'),
                                                      '-segmentation', os.path.join(fs_path, 'mri', 'aseg.mgz'),
                                                      colorLUT_file]
            self.inspect_outputs_dict['norm/aseg/surf'] = ['tkmedit', '-f', os.path.join(fs_path, 'mri', 'norm.mgz'),
                                                           '-surface', os.path.join(fs_path, 'surf', 'lh.white'),
                                                           '-aux-surface', os.path.join(fs_path, 'surf', 'rh.white'),
                                                           '-segmentation', os.path.join(fs_path, 'mri', 'aseg.mgz'),
                                                           colorLUT_file]
        
        elif self.config.seg_tool == "Custom segmentation":
            self.inspect_outputs_dict['WM mask'] = ['fsleyes', self.config.white_matter_mask]
        
        self.inspect_outputs = sorted([key.encode('ascii', 'ignore') for key in self.inspect_outputs_dict.keys()],
                                      key=str.lower)
    
    def has_run(self):
        if self.config.use_existing_freesurfer_data or self.config.seg_tool == "Custom segmentation":
            return True
        else:
            return os.path.exists(os.path.join(self.stage_dir, "reconall", "result_reconall.pklz"))
