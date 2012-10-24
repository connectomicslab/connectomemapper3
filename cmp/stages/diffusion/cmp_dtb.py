# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP sub-stage of diffusion Stage for DTB-tracking
""" 

try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, File, TraitedSpec

import os
import pkg_resources
from nipype.utils.filemanip import split_filename

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl

class DTB_tracking_config(HasTraits):
    imaging_model = Str
    flip_input = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    angle = Int(60)
    seeds = Int(32)
    
    traits_view = View(Item('flip_input',style='custom'),'angle','seeds')

# Nipype interfaces for DTB commands

class DTB_P0InputSpec(CommandLineInputSpec):
    dsi_basepath = traits.Str(desc='DSI path/basename (e.g. \"data/dsi_\")',position=1,mandatory=True,argstr = "--dsi %s")
    dwi_file = File(desc='DWI file',position=2,mandatory=True,exists=True,argstr = "--dwi %s")

class DTB_P0OutputSpec(TraitedSpec):
    out_file = File(desc='Resulting P0 file')

class DTB_P0(CommandLine):
    _cmd = 'DTB_P0'
    input_spec = DTB_P0InputSpec
    output_spec = DTB_P0OutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        path, base, _ = split_filename(self.inputs.dsi_basepath)
        outputs["out_file"]  = os.path.join(path,base+'P0.nii')
        return outputs

class DTB_gfaInputSpec(CommandLineInputSpec):
    dsi_basepath = traits.Str(desc='DSI path/basename (e.g. \"data/dsi_\")',position=1,mandatory=True,argstr = "--dsi %s")
    moment = traits.Enum((2, 3, 4),desc='Moment to calculate (2 = gfa, 3 = skewness, 4 = curtosis)',position=2,mandatory=True,argstr = "--m %s")

class DTB_gfaOutputSpec(TraitedSpec):
    out_file = File(desc='Resulting file')

class DTB_gfa(CommandLine):
    _cmd = 'DTB_gfa'
    input_spec = DTB_gfaInputSpec
    output_spec = DTB_gfaOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        path, base, _ = split_filename(self.inputs.dsi_basepath)

        if self.inputs.moment == 2:
            outputs["out_file"]  = os.path.join(path,base+'gfa.nii')
        if self.inputs.moment == 3:
            outputs["out_file"]  = os.path.join(path,base+'skewness.nii')
        if self.inputs.moment == 4:
            outputs["out_file"]  = os.path.join(path,base+'kurtosis.nii')

        return outputs
        
class DTB_dtk2dirInputSpec(CommandLineInputSpec):
    diffusion_type = traits.Enum(['dti','dsi'], desc='type of diffusion data [dti|dsi]', position=1,
                                 mandatory=True, argstr="--type %s")
    prefix = Str(desc='DATA path/prefix (e.g. "data/dsi_")',position=2, mandatory=True, argstr="--prefix %s")
    dirlist = File(desc='filename of the file containing ODF sampling directions [only for dsi]', position=3,
                   exists=True, argstr="--dirlist %s")
    invert_x = Bool(desc='invert x axis', argstr='--ix')
    invert_y = Bool(desc='invert y axis', argstr='--iy')
    invert_z = Bool(desc='invert z axis', argstr='--iz')

class DTB_dtk2dirOutputSpec(TraitedSpec):
    out_file = File(desc='Resulting dir file')

class DTB_dtk2dir(CommandLine):
    _cmd = 'DTB_dtk2dir'
    input_spec = DTB_dtk2dirInputSpec
    output_spec = DTB_dtk2dirOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = self.inputs.prefix+'dir.nii'
        return outputs
        
class DTB_streamlineInputSpec(CommandLineInputSpec):
    dir_file = File(desc='DIR path/filename (e.g. "data/dsi_DIR.nii")', position=1,
                    mandatory=True, exists=True, argstr="--dir %s")
    wm_mask = File(desc='WM MASK path/filename (e.g. "data/mask.nii")")',position=2,
                   mandatory=True, exists=True, argstr="--wm %s")
    angle = traits.Int(desc='ANGLE threshold [degree]', argstr="--angle %d")
    seeds = traits.Int(desc='number of random seed points per voxel', argstr='--seeds %d')
    out_file = File(desc='OUTPUT path/filename (e.g. "data/fibers.trk")', mandatory=True, argstr='--out %s')

class DTB_streamlineOutputSpec(TraitedSpec):
    out_file = File(desc='Resulting trk file', exists = True)

class DTB_streamline(CommandLine):
    _cmd = 'DTB_streamline'
    input_spec = DTB_streamlineInputSpec
    output_spec = DTB_streamlineOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs
        
def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')
    
def create_dtb_tracking_flow(config):
    flow = pe.Workflow(name="DTB_tracking_substage")
    
    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","wm_mask","T1-TO-B0_mat"]),name="inputnode")
    
    # outputnode
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["track_file"]),name="outputnode")
    
    # Prepare data for tractography algorithm
    dtb_dtk2dir = pe.Node(interface=DTB_dtk2dir(), name="dtb_dtk2dir")
    if config.imaging_model == 'DSI':
        dtb_dtk2dir.inputs.diffusion_type = 'dsi'
        dtb_dtk2dir.inputs.dirlist = pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','odf_directions','181_vecs.dat'))
        prefix = 'dsi'
    else:
        dtb_dtk2dir.inputs.diffusion_type = 'dti'
    if 'x' in config.flip_input:
        dtb_dtk2dir.inputs.invert_x = True
    if 'y' in config.flip_input:
        dtb_dtk2dir.inputs.invert_y = True
    if 'z' in config.flip_input:
        dtb_dtk2dir.inputs.invert_z = True
        prefix = 'dti'
        
        
    # Apply transformation to WM-mask
    fsl_applyxfm = pe.Node(interface=fsl.ApplyXfm(apply_xfm=True), name="fsl_applyxfm")
   
    fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii', vox_size=(1,1,1), 
                            out_datatype='uchar', out_file='fsmask_1mm.nii'), name="fs_mriconvert")

    # Streamline
    dtb_streamline = pe.Node(interface=DTB_streamline(out_file='streamline.trk'), name="dtb_streamline")
    dtb_streamline.inputs.angle = config.angle
    dtb_streamline.inputs.seeds = config.seeds
    
    # Workflow connections
    flow.connect([
                 (inputnode,dtb_dtk2dir, [(('DWI',strip_suffix,prefix),'prefix')]),
                 (inputnode,fsl_applyxfm, [('wm_mask','in_file'),('DWI','reference'),('T1-TO-B0_mat','in_matrix_file')]),
                 (fsl_applyxfm,fs_mriconvert, [('out_file','in_file')]),
                 (dtb_dtk2dir,dtb_streamline, [('out_file','dir_file')]),
                 (fs_mriconvert,dtb_streamline, [('out_file','wm_mask')]),
                 (dtb_streamline,outputnode, [('out_file','track_file')]),
                 ])
        
    return flow

