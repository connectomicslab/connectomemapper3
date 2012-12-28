# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Tracking methods and workflows of the diffusion stage
""" 

from traits.api import *
from traitsui.api import *

from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, File, TraitedSpec, BaseInterface, BaseInterfaceInputSpec, isdefined

import glob
import os
import pkg_resources
from nipype.utils.filemanip import split_filename

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.diffusion_toolkit as dtk

from cmtklib.diffusion import filter_fibers

class DTB_tracking_config(HasTraits):
    imaging_model = Str
    flip_input = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    angle = Int(60)
    seeds = Int(32)
    
    traits_view = View(Item('flip_input',style='custom'),'angle','seeds')
    
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
        
class CMTK_filterfibersInputSpec(BaseInterfaceInputSpec):
    track_file = File(desc='Input trk file', mandatory=True, exists=True)
    fiber_cutoff_lower = traits.Int(20, desc='Lower length threshold of the fibers', usedefault=True)
    fiber_cutoff_upper = traits.Int(500, desc='Upper length threshold of the fibers', usedefault=True)
    filtered_track_file = File(desc='Filtered trk file')
    
class CMTK_filterfibersOutputSpec(TraitedSpec):
    filtered_track_file= File(desc='Filtered trk file', exists=True)
    lengths_file= File(desc='Streamline lengths file', exists=True)
    
class CMTK_filterfibers(BaseInterface):
    input_spec = CMTK_filterfibersInputSpec
    output_spec = CMTK_filterfibersOutputSpec
    
    def _run_interface(self, runtime):
        if isdefined(self.inputs.filtered_track_file):
            filter_fibers(intrk=self.inputs.track_file, outtrk=self.filtered_track_file,
                          fiber_cutoff_lower=self.inputs.fiber_cutoff_lower,
                          fiber_cutoff_upper=self.inputs.fiber_cutoff_upper)
        else:
            filter_fibers(intrk=self.inputs.track_file,
                          fiber_cutoff_lower=self.inputs.fiber_cutoff_lower,
                          fiber_cutoff_upper=self.inputs.fiber_cutoff_upper)
        return runtime
        
    def _list_outputs(self):
        outputs = self._outputs().get()
        if not isdefined(self.inputs.filtered_track_file):
            _, base, ext = split_filename(self.inputs.track_file)
            outputs["filtered_track_file"] = os.path.abspath(base + '_cutfiltered' + ext)
        else:
            outputs["filtered_track_file"] = os.path.abspath(self.inputs.filtered_track_file)
        outputs["lengths_file"] = os.path.abspath("lengths.npy")
        return outputs
        
class StreamlineAndFilterInputSpect(BaseInterfaceInputSpec):
    # streamline input specs
    dir_file = File(desc='DIR path/filename (e.g. "data/dsi_DIR.nii")', position=1,
                    mandatory=True, exists=True, argstr="--dir %s")
    wm_mask = File(desc='WM MASK path/filename (e.g. "data/mask.nii")")',position=2,
                   mandatory=True, exists=True, argstr="--wm %s")
    angle = traits.Int(desc='ANGLE threshold [degree]', argstr="--angle %d")
    seeds = traits.Int(desc='number of random seed points per voxel', argstr='--seeds %d')
    out_file = File(desc='OUTPUT path/filename (e.g. "data/fibers.trk")', mandatory=True, argstr='--out %s')
    # spline filter specs
    spline_filter = Bool(True,usedefault=True)
    spline_filter_step_length = traits.Int(1,usedefault=True)
    # fiberlenght filtering specs
    fiberlength_filter = Bool(True,usedefault=True)
    
class StreamlineAndFilterOutputSpect(TraitedSpec):
    out_file = File(desc='Resulting trk file', exists = True)

class StreamlineAndFilter(BaseInterface):
    input_spec = StreamlineAndFilterInputSpect
    output_spec = StreamlineAndFilterOutputSpect
    
    def _run_interface(self, runtime):
        # run streamline
        dtb_streamline = DTB_streamline(out_file=self.inputs.out_file)
        dtb_streamline.inputs.dir_file = self.inputs.dir_file
        dtb_streamline.inputs.wm_mask = self.inputs.wm_mask
        dtb_streamline.inputs.angle = self.inputs.angle
        dtb_streamline.inputs.seeds = self.inputs.seeds
        dtb_streamline.inputs.out_file = self.inputs.out_file
        res_stream = dtb_streamline.run()
        
        if self.inputs.spline_filter:
            dtk_splinefilter = dtk.SplineFilter(step_length=1)
            dtk_splinefilter.inputs.step_length = self.inputs.spline_filter_step_length
            dtk_splinefilter.inputs.track_file = res_stream.outputs.out_file
            res_splinefilter = dtk_splinefilter.run()
            out_track_file = res_splinefilter.outputs.smoothed_track_file
        else:
            out_track_file = res_stream.outputs.out_file
            
        if self.inputs.fiberlength_filter:
            cmtk_filterfibers = CMTK_filterfibers()
            cmtk_filterfibers.inputs.track_file = out_track_file
            cmtk_filterfibers.run()

        return runtime
        

    def _list_outputs(self):
        outputs = self._outputs().get()
        if self.inputs.fiberlength_filter:
            out_trk = '*cutfiltered*trk'
        else:
            if self.inputs.spline_filter:
                out_trk = 'spline*trk'
            else:
                out_trk = self.inputs.out_file
            
        outputs["out_file"] = os.path.abspath(glob.glob(out_trk)[0])
        return outputs
        
class DTK_tracking_config(HasTraits):
    angle_threshold = Int(60)
    mask1_threshold_auto = Bool(True)
    mask1_threshold = List([0.0,1.0])
    mask1_input = Enum('DWI',['B0','DWI'])
    
    traits_view = View('mask1_input','angle_threshold','mask1_threshold_auto',
                        Item('mask1_threshold',enabled_when='mask1_threshold_auto==False'))
        
def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')
    
def create_dtb_tracking_flow(config):
    flow = pe.Workflow(name="tracking")
    
    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","wm_mask_registered"]),name="inputnode")
    
    # outputnode
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["track_file"]),name="outputnode")
    
    # Prepare data for tractography algorithm
    dtb_dtk2dir = pe.Node(interface=DTB_dtk2dir(), name="dtb_dtk2dir")
    if config.imaging_model == 'DSI':
        dtb_dtk2dir.inputs.diffusion_type = 'dsi'
        dtb_dtk2dir.inputs.dirlist = pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','odf_directions','181_vecs.dat'))
        prefix = 'dsi'
    if config.imaging_model == 'DTI':
        dtb_dtk2dir.inputs.diffusion_type = 'dti'
        prefix = 'dti'
    if config.imaging_model == 'HARDI':
        dtb_dtk2dir.inputs.diffusion_type = 'dsi'
        dtb_dtk2dir.inputs.dirlist = pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','odf_directions','181_vecs.dat'))
        prefix = 'hardi'
    if 'x' in config.flip_input:
        dtb_dtk2dir.inputs.invert_x = True
    if 'y' in config.flip_input:
        dtb_dtk2dir.inputs.invert_y = True
    if 'z' in config.flip_input:
        dtb_dtk2dir.inputs.invert_z = True
   
    fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii', vox_size=(1,1,1), 
                            out_datatype='uchar', out_file='fsmask_1mm.nii'), name="fs_mriconvert")

    # Streamline AND filtering (to avoid temp files)
    streamline_filter = pe.Node(interface=StreamlineAndFilter(out_file='streamline.trk'), name="dtb_streamline")
    streamline_filter.inputs.angle = config.angle
    streamline_filter.inputs.seeds = config.seeds
    
    # Workflow connections
    flow.connect([
                 (inputnode,dtb_dtk2dir, [(('DWI',strip_suffix,prefix),'prefix')]),
                 (inputnode,fs_mriconvert, [('wm_mask_registered','in_file')]),
                 (dtb_dtk2dir,streamline_filter, [('out_file','dir_file')]),
                 (fs_mriconvert,streamline_filter, [('out_file','wm_mask')]),
                 (streamline_filter,outputnode, [('out_file','track_file')]),
                 ])
        
    return flow

