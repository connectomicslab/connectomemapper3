# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Tracking methods and workflows of the diffusion stage
""" 

from traits.api import *
from traitsui.api import *

from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, File, TraitedSpec, BaseInterface, BaseInterfaceInputSpec, isdefined, OutputMultiPath, InputMultiPath
    
from nipype.utils.filemanip import copyfile

import glob
import os
import pkg_resources
from nipype.utils.filemanip import split_filename

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
from nipype.interfaces.fsl.base import FSLCommand, FSLCommandInputSpec
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.mrtrix as mrtrix
import nipype.interfaces.camino as camino
import nipype.interfaces.camino2trackvis as camino2trackvis
from nipype.workflows.misc.utils import get_data_dims, get_vox_dims

import nibabel as nib
import numpy as np

from cmtklib.diffusion import filter_fibers

from nipype import logging
iflogger = logging.getLogger('interface')

class DTB_tracking_config(HasTraits):
    imaging_model = Str
    flip_input = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    angle = Int(60)
    step_size = traits.Float(1.0)
    seeds = Int(32)
    
    traits_view = View(Item('flip_input',style='custom'),'angle','step_size','seeds')

class MRtrix_tracking_config(HasTraits):
    tracking_mode = Str
    SD = Bool
    desired_number_of_tracks = Int(1000)
    max_number_of_tracks = Int(1000)
    curvature = Float(2.0)
    step_size = Float(0.2)
    min_length = Float(10)
    max_length = Float(200)
    
    traits_view = View( HGroup('desired_number_of_tracks','max_number_of_tracks'),
			Item('curvature',label="Curvature radius"),'step_size',
			HGroup('min_length','max_length')
		      )
    
    def _SD_changed(self,new):
        if self.tracking_mode == "Deterministic" and not new:
            self.curvature = 2.0
        elif self.tracking_mode == "Deterministic" and new:
            self.curvature = 0.0
        elif self.tracking_mode == "Probabilistic":
            self.curvature = 1.0
            
    def _tracking_mode_changed(self,new):
        if new == "Deterministic" and not self.SD:
            self.curvature = 2.0
        elif new == "Deterministic" and self.SD:
            self.curvature = 0.0
        elif new == "Probabilistic":
            self.curvature = 1.0
            
    def _curvature_changed(self,new):
        if new <= 0.000001:
            self.curvature = 0.0                

class Camino_tracking_config(HasTraits):
    imaging_model = Str
    tracking_mode = Str
    inversion_index = Int(1) # 1=='dt' which is the default local_model in reconstruction.py
    fallback_index = Int(1) # 1=='dt' which is the default fallback_index in reconstruction.py
    angle = Float(60)
    cross_angle = Float(20)
    trace = Float(0.0000000021)
    units = Enum(["m^2/s","s/mm^2"])
    tracking_model = Str('dt')
    snr = Float(20)
    iterations = Int(50)
    pdf = Enum(['bingham', 'watson', 'acg'])
    traits_view = View( 'angle',
                        Item('snr',visible_when="tracking_mode=='Probabilistic'"),
                        Item('iterations',visible_when="tracking_mode=='Probabilistic'"),
                        Item('pdf',visible_when="tracking_mode=='Probabilistic'"),
                        Item('cross_angle', label="Crossing angle", visible_when='(tracking_mode=="Probabilistic") and (inversion_index > 9)'),
                        HGroup('trace','units')
                        )
    
    def _units_changed(self,new):
        if new == "s/mm^2":
            self.trace = self.trace * 1000000
        elif new == "m^2/s":
            self.trace = self.trace / 1000000

    
class FSL_tracking_config(HasTraits):
    number_of_samples = Int(5000)
    number_of_steps = Int(2000)
    distance_threshold = Float(0)
    curvature_threshold = Float(0.2)
    
    traits_view = View('number_of_samples','number_of_steps','distance_threshold','curvature_threshold')

class Gibbs_tracking_config(HasTraits):
    iterations = Int(100000000)
    particle_length=Float(1.5)
    particle_width=Float(0.5)
    particle_weight=Float(0.0003)
    temp_start=Float(0.1)
    temp_end=Float(0.001)
    inexbalance=Int(-2)
    fiber_length=Float(20)
    curvature_threshold=Float(90)
    
    traits_view = View('iterations','particle_length','particle_width','particle_weight','temp_start','temp_end','inexbalance','fiber_length','curvature_threshold')


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
        import shutil
        outputs = self._outputs().get()
        _, base, _ = split_filename(self.inputs.prefix)
        shutil.move(self.inputs.prefix+'dir.nii',os.path.abspath(base+'dir.nii'))
        outputs["out_file"] = os.path.abspath(base+'dir.nii')
        return outputs
        
class DTB_streamlineInputSpec(CommandLineInputSpec):
    dir_file = File(desc='DIR path/filename (e.g. "data/dsi_DIR.nii")', position=1,
                    mandatory=True, exists=True, argstr="--dir %s")
    wm_mask = File(desc='WM MASK path/filename (e.g. "data/mask.nii")")',position=2,
                   mandatory=True, exists=True, argstr="--wm %s")
    angle = traits.Int(desc='ANGLE threshold [degree]', argstr="--angle %d")
    step_size = traits.Float(desc='Step-size [mm]',  argstr="--stepSize %f")
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
    step_size = traits.Float(desc='Step-size [mm]',  argstr="--stepSize %f")
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
        dtb_streamline.inputs.step_size = self.inputs.step_size
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
    streamline_filter.inputs.step_size = config.step_size
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

class make_seedsInputSpec(BaseInterfaceInputSpec):
    ROI_files = InputMultiPath(File(exists=True),desc='ROI files registered to diffusion space')
    WM_file = File(mandatory=True,desc='WM mask file registered to diffusion space')
    #DWI = File(mandatory=True,desc='Diffusion data file for probabilistic tractography')
    

class make_seedsOutputSpec(TraitedSpec):
    seed_files = OutputMultiPath(File(exists=True),desc='Seed files for probabilistic tractography')

class make_seeds(BaseInterface):
    """ - Creates seeding ROIs by intersecting dilated ROIs with WM mask
    """
    input_spec = make_seedsInputSpec
    output_spec = make_seedsOutputSpec
    ROI_idx = []
    base_name = ''
    def _run_interface(self,runtime):
        iflogger.info("Computing seed files for probabilistic tractography\n===================================================")
        # Load ROI file
        for ROI_file in self.inputs.ROI_files:
            ROI_vol = nib.load(ROI_file)
            ROI_data = ROI_vol.get_data()
            ROI_affine = ROI_vol.get_affine()
            # Load WM mask
            WM_vol = nib.load(self.inputs.WM_file)
            WM_data = WM_vol.get_data()
            # Extract ROI indexes, define number of ROIs, overlap code and start ROI dilation
            iflogger.info("ROI dilation...")
            self.ROI_idx = np.unique(ROI_data[ROI_data!=0]).astype(int)
            # Take overlap between dilated ROIs and WM to define seeding regions
            border = ROI_data * WM_data 
            # Save one nifti file per seeding ROI
            temp = border.copy()
            _,self.base_name,_ = split_filename(ROI_file)
            for i in self.ROI_idx:
                temp[border == i] = 1
                temp[border != i] = 0
                new_image = nib.Nifti1Image(temp,ROI_affine)
                save_as = os.path.abspath(self.base_name+'_seed_'+str(i)+'.nii.gz')
                nib.save(new_image,save_as)
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["seed_files"] = self.gen_outputfilelist()
        return outputs
    
    def gen_outputfilelist(self):
        output_list = []
        for i in self.ROI_idx:
            output_list.append(os.path.abspath(self.base_name+'_seed_'+str(i)+'.nii.gz'))
        return output_list

def create_mrtrix_tracking_flow(config):
    flow = pe.Workflow(name="tracking")
    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=['DWI','wm_mask_resampled','gm_registered','grad']),name='inputnode')
    # outputnode
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["track_file"]),name="outputnode")
    if config.tracking_mode == 'Deterministic':
        mrtrix_tracking = pe.Node(interface=mrtrix.StreamlineTrack(),name="mrtrix_deterministic_tracking")
        mrtrix_tracking.inputs.desired_number_of_tracks = config.desired_number_of_tracks
        mrtrix_tracking.inputs.maximum_number_of_tracks = config.max_number_of_tracks
        mrtrix_tracking.inputs.maximum_tract_length = config.max_length
        mrtrix_tracking.inputs.minimum_tract_length = config.min_length
        mrtrix_tracking.inputs.step_size = config.step_size
        mrtrix_tracking.inputs.args = '2>/dev/null'
        if config.curvature >= 0.000001:
            mrtrix_tracking.inputs.minimum_radius_of_curvature = config.curvature
        if config.SD:
            mrtrix_tracking.inputs.inputmodel = 'SD_STREAM'  
        else:
            mrtrix_tracking.inputs.inputmodel = 'DT_STREAM'
        flow.connect([
                      (inputnode,mrtrix_tracking,[("grad","gradient_encoding_file")])
                    ])
        converter = pe.Node(interface=mrtrix.MRTrix2TrackVis(),name="trackvis")
        flow.connect([
                      (inputnode,mrtrix_tracking,[('DWI','in_file'),('wm_mask_resampled','seed_file'),('wm_mask_resampled','mask_file')]),
                      (mrtrix_tracking,converter,[('tracked','in_file')]),
                      (inputnode,converter,[('wm_mask_resampled','image_file')]),
                      (converter,outputnode,[('out_file','track_file')])
                      ])

    elif config.tracking_mode == 'Probabilistic':
        mrtrix_seeds = pe.Node(interface=make_seeds(),name="mrtrix_seeds")
        mrtrix_tracking = pe.MapNode(interface=mrtrix.StreamlineTrack(desired_number_of_tracks = config.desired_number_of_tracks,maximum_number_of_tracks = config.max_number_of_tracks, maximum_tract_length = config.max_length,minimum_tract_length = config.min_length, step_size = config.step_size),name="mrtrix_probabilistic_tracking",iterfield=['seed_file'])
        mrtrix_tracking.inputs.args = '2>/dev/null'
        if config.curvature >= 0.000001:
            mrtrix_tracking.inputs.minimum_radius_of_curvature = config.curvature
        if config.SD:
            mrtrix_tracking.inputs.inputmodel='SD_PROB'
        else:
            mrtrix_tracking.inputs.inputmodel='DT_PROB'
        converter = pe.MapNode(interface=mrtrix.MRTrix2TrackVis(),iterfield=['in_file'],name='trackvis')
        flow.connect([
		    (inputnode,mrtrix_seeds,[('wm_mask_resampled','WM_file')]),
		    (inputnode,mrtrix_seeds,[('gm_registered','ROI_files')]),
		    ])
        flow.connect([
		    (mrtrix_seeds,mrtrix_tracking,[('seed_files','seed_file')]),
		    (inputnode,mrtrix_tracking,[('DWI','in_file')]),
		    (inputnode,mrtrix_tracking,[('wm_mask_resampled','mask_file')]),
            (mrtrix_tracking,converter,[('tracked','in_file')]),
            (inputnode,converter,[('wm_mask_resampled','image_file')]),
		    (converter,outputnode,[('out_file','track_file')])
		    ])

    return flow

def create_camino_tracking_flow(config):
    flow = pe.Workflow(name="tracking")

    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","wm_mask_resampled","gm_registered", "grad"]),name="inputnode")
    
    # outputnode
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["track_file"]),name="outputnode")
    
    if config.tracking_mode == 'Deterministic':
        
        # Camino tracking
        camino_tracking = pe.Node(interface=camino.Track(),name='camino_tracking')
        camino_tracking.inputs.curvethresh = config.angle
        camino_tracking.inputs.inputmodel = config.tracking_model
        camino_tracking.inputs.anisthresh = 0.5
        if config.inversion_index >= 10:
            camino_tracking.inputs.inputmodel = 'multitensor'
        if config.inversion_index > 100:
            camino_tracking.inputs.maxcomponents = 3
        # Converter
        converter = pe.Node(interface=camino2trackvis.Camino2Trackvis(),name='trackvis')
        converter.inputs.phys_coords = True
    
        flow.connect([
    		(inputnode,camino_tracking,[('DWI','in_file')]),
    		(inputnode,camino_tracking,[('wm_mask_resampled','seed_file')]),
            (inputnode,camino_tracking,[('wm_mask_resampled','anisfile')]),
    		(camino_tracking,converter,[('tracked','in_file')]),
            (inputnode,converter,[('wm_mask_resampled','nifti_file')]),
            (converter,outputnode,[('trackvis','track_file')]),
    		])
        
    elif config.tracking_mode == 'Probabilistic':
        # Make seeds
        camino_seeds = pe.Node(interface=make_seeds(),name="camino_seeds")
        # Generate Lookup table
        dtlutgen = pe.Node(interface=camino.DTLUTGen(),name='dtlutgen')
        flow.connect([
                      (inputnode,dtlutgen,[('grad','scheme_file')])
                    ])
        dtlutgen.inputs.snr = config.snr
        dtlutgen.inputs.inversion = config.inversion_index
        dtlutgen.inputs.trace = config.trace
        if config.pdf == 'bingham':
            dtlutgen.inputs.bingham = True
        if config.pdf == 'watson':
            dtlutgen.inputs.watson = True
        if config.pdf == 'acg':
            dtlutgen.inputs.acg = True
            
        if config.inversion_index >= 10:
            dtlutgen.inputs.cross = config.cross_angle
            dtlutgen2 = pe.Node(interface=camino.DTLUTGen(),name='dtlutgen2')
            flow.connect([
                        (inputnode,dtlutgen2,[("grad","scheme_file")])
                        ])
            dtlutgen2.inputs.snr = config.snr
            dtlutgen2.inputs.inversion = config.fallback_index
            dtlutgen2.inputs.trace = config.trace
            if config.pdf == 'bingham':
                dtlutgen2.inputs.bingham = True
            if config.pdf == 'watson':
                dtlutgen2.inputs.watson = True
            if config.pdf == 'acg':
                dtlutgen2.inputs.acg = True
                
        # Pico PDF generation
        picopdf = pe.Node(interface=camino.PicoPDFs(),name='picopdf')
        picopdf.inputs.pdf = config.pdf
        if config.inversion_index >= 10:
            picopdf.inputs.inputmodel = 'multitensor'
            merge = pe.Node(interface=util.Merge(2),name='merge_LUTs')
            flow.connect([
                        (dtlutgen2,merge,[("dtLUT","in1")]),
                        (dtlutgen,merge,[("dtLUT","in2")]),
                        (merge,picopdf,[("out","luts")]),
                        ])
            
        else:
            picopdf.inputs.inputmodel = 'dt'
            flow.connect([
                        (dtlutgen,picopdf,[("dtLUT","luts")]),
                        ])         
            
        # Camino tracking
        camino_tracking = pe.MapNode(interface=camino.TrackPICo(),iterfield=['seed_file'],name='camino_tracking')
        camino_tracking.inputs.curvethresh = config.angle
        camino_tracking.inputs.inputmodel = config.tracking_model
        camino_tracking.inputs.anisthresh = 0.5
        camino_tracking.inputs.iterations = config.iterations
        camino_tracking.inputs.pdf = config.pdf
        if config.inversion_index >= 10 and config.inversion_index < 100:
            camino_tracking.inputs.numpds = 2
        else:
            camino_tracking.inputs.numpds = 3
        
        # Convert to trk format
        converter = pe.MapNode(interface=camino2trackvis.Camino2Trackvis(),iterfield=['in_file'],name='trackvis')
        converter.inputs.phys_coords = True
        
        flow.connect([
            (inputnode,camino_seeds,[('wm_mask_resampled','WM_file')]),
            (inputnode,camino_seeds,[('gm_registered','ROI_files')]),
            (inputnode,picopdf,[("DWI","in_file")]),
            (picopdf,camino_tracking,[('pdfs','in_file')]),
            (camino_seeds,camino_tracking,[('seed_files','seed_file')]),
            (inputnode,camino_tracking,[('wm_mask_resampled','anisfile')]),
            (camino_tracking,converter,[('tracked','in_file')]),
            (inputnode,converter,[('wm_mask_resampled','nifti_file')]),
            (converter,outputnode,[('trackvis','track_file')]),
            ])
        

    return flow

class mapped_ProbTrackXInputSpec(FSLCommandInputSpec):
    thsamples = InputMultiPath(File(exists=True), mandatory=True)
    phsamples = InputMultiPath(File(exists=True), mandatory=True)
    fsamples = InputMultiPath(File(exists=True), mandatory=True)
    samples_base_name = traits.Str("merged", desc='the rootname/base_name for samples files',
                                   argstr='--samples=%s', usedefault=True)
    mask = File(exists=True, desc='bet binary mask file in diffusion space',
                    argstr='-m %s', mandatory=True)
    seed = traits.File(exists=True,
                         desc='seed volume(s)',
                         argstr='--seed=%s', mandatory=True)
    mode = traits.Enum("simple", "two_mask_symm", "seedmask",
                       desc='options: simple (single seed voxel), seedmask (mask of seed voxels), '
                            + 'twomask_symm (two bet binary masks) ',
                       argstr='--mode=%s', genfile=True)
    target_masks = InputMultiPath(File(exits=True), desc='list of target masks - ' +
                       'required for seeds_to_targets classification', argstr='--targetmasks=%s')
    network = traits.Bool(desc='activate network mode - only keep paths going through ' +
                          'at least one seed mask (required if multiple seed masks)',
                          argstr='--network')
    opd = traits.Bool(True, desc='outputs path distributions', argstr='--opd', usedefault=True)
    os2t = traits.Bool(desc='Outputs seeds to targets', argstr='--os2t')
    n_samples = traits.Int(5000, argstr='--nsamples=%d',
                           desc='number of samples - default=5000', usedefault=True)
    n_steps = traits.Int(argstr='--nsteps=%d', desc='number of steps per sample - default=2000')
    dist_thresh = traits.Float(argstr='--distthresh=%.3f', desc='discards samples shorter than ' +
                              'this threshold (in mm - default=0)')
    c_thresh = traits.Float(argstr='--cthr=%.3f', desc='curvature threshold - default=0.2')
    step_length = traits.Float(argstr='--steplength=%.3f', desc='step_length in mm - default=0.5')
    loop_check = traits.Bool(argstr='--loopcheck', desc='perform loop_checks on paths -' +
                            ' slower, but allows lower curvature threshold')
    fibst = traits.Int(argstr='--fibst=%d', desc='force a starting fibre for tracking - ' +
                       'default=1, i.e. first fibre orientation. Only works if randfib==0')
    s2tastext = traits.Bool(argstr='--s2tastext', desc='output seed-to-target counts as a' +
                            ' text file (useful when seeding from a mesh)')
    out_dir = Directory(exists=True, argstr='--dir=%s',
                       desc='directory to put the final volumes in', genfile=True)
    force_dir = traits.Bool(True, desc='use the actual directory name given - i.e. ' +
                            'do not add + to make a new directory', argstr='--forcedir',
                            usedefault=True)
    
class mapped_ProbTrackXOutputSpec(TraitedSpec):
    matrix = File(exists=True, desc='matrix_seeds_to_all_targets file')

class mapped_ProbTrackX(FSLCommand):
    input_spec = mapped_ProbTrackXInputSpec
    output_spec = mapped_ProbTrackXOutputSpec
    
    _cmd = "probtrackx"
    
    def _run_interface(self, runtime):
        for i in range(1, len(self.inputs.thsamples) + 1):
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.thsamples[i - 1],
                     self.inputs.samples_base_name + "_th%dsamples" % i + ext,
                     copy=True)
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.phsamples[i - 1],
                     self.inputs.samples_base_name + "_ph%dsamples" % i + ext,
                     copy=True)
            _, _, ext = split_filename(self.inputs.thsamples[i - 1])
            copyfile(self.inputs.fsamples[i - 1],
                     self.inputs.samples_base_name + "_f%dsamples" % i + ext,
                     copy=True)

        if isdefined(self.inputs.target_masks):
            f = open("targets.txt", "w")
            for target in self.inputs.target_masks:
                f.write("%s\n" % target)
            f.close()

        runtime = super(mapped_ProbTrackX, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime
    
    def _format_arg(self, name, spec, value):
        if name == 'target_masks' and isdefined(value):
            fname = "targets.txt"
            return super(mapped_ProbTrackX, self)._format_arg(name, spec, [fname])
        elif name == 'seed' and isinstance(value, list):
            fname = "seeds.txt"
            return super(mapped_ProbTrackX, self)._format_arg(name, spec, fname)
        else:
            return super(mapped_ProbTrackX, self)._format_arg(name, spec, value)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_dir):
            out_dir = self._gen_filename("out_dir")
        else:
            out_dir = self.inputs.out_dir

        # handle seeds-to-target output files
        if isdefined(self.inputs.target_masks):
            outputs['matrix'] = os.path.abspath('matrix_seeds_to_all_targets')
        return outputs

    def _gen_filename(self, name):
        if name == "out_dir":
            return os.getcwd()

def create_fsl_tracking_flow(config):
    flow = pe.Workflow(name="tracking")
    
    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["phsamples","fsamples","thsamples","wm_mask_resampled","gm_registered"]),name="inputnode")
    
    # outputnode
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["targets"]),name="outputnode")
    
    fsl_seeds = pe.Node(interface=make_seeds(),name="fsl_seeds")
    
    probtrackx = pe.MapNode(interface=mapped_ProbTrackX(),iterfield=['seed'],name='probtrackx') #
    
    probtrackx.inputs.n_samples = config.number_of_samples
    probtrackx.inputs.n_steps = config.number_of_steps
    probtrackx.inputs.dist_thresh = config.distance_threshold
    probtrackx.inputs.c_thresh = config.curvature_threshold
    probtrackx.inputs.loop_check = True
    probtrackx.inputs.opd = False
    probtrackx.inputs.os2t = True
    probtrackx.inputs.s2tastext = True
    probtrackx.inputs.network = False
    probtrackx.inputs.mode = "seedmask"
    probtrackx.inputs.force_dir = True
    
    flow.connect([
            (inputnode,fsl_seeds,[('wm_mask_resampled','WM_file')]),
            (inputnode,fsl_seeds,[('gm_registered','ROI_files')]),
            (fsl_seeds,probtrackx,[("seed_files","seed")]),
            (fsl_seeds,probtrackx,[("seed_files","target_masks")]),
            (inputnode,probtrackx,[("wm_mask_resampled","mask")]),
            (inputnode,probtrackx,[("fsamples","fsamples")]),
            (inputnode,probtrackx,[("phsamples","phsamples")]),
            (inputnode,probtrackx,[("thsamples","thsamples")]),
            (probtrackx,outputnode,[("matrix","targets")])
            ])
    
    return flow

class gibbs_tracking_CMDInputSpec(CommandLineInputSpec):
    in_file = File(argstr="-i %s",position = 1,mandatory=True,exists=True,desc="input image (tensor, Q-ball or FSL/MRTrix SH-coefficient image)")
    parameter_file = File(argstr="-p %s", position = 2, mandatory = True, exists=True, desc="gibbs parameter file (.gtp)")
    mask = File(argstr="-m %s",position=3,mandatory=False,desc="mask, binary mask image (optional)")
    out_file_name = File(argstr="-o ./%s",position=5,desc='output fiber bundle (.trk)')

class gibbs_tracking_CMDOutputSpec(TraitedSpec):
    out_file = File(desc='output fiber bundle')

class gibbs_tracking_CMD(CommandLine):
    _cmd = 'MitkGibbsTracking.sh'
    input_spec = gibbs_tracking_CMDInputSpec
    output_spec = gibbs_tracking_CMDOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file_name)
        return outputs
    
class gibbs_trackingInputSpec(BaseInterfaceInputSpec):

    # Inputs for XML file
    iterations = Int
    particle_length=Float
    particle_width=Float
    particle_weight=Float
    temp_start=Float
    temp_end=Float
    inexbalance=Int
    fiber_length=Float
    curvature_threshold=Float

    # Command line parameters
    in_file = File(mandatory=True,exists=True,desc="input image (tensor, Q-ball or FSL/MRTrix SH-coefficient image)")
    mask = File(mandatory=False,desc="mask, binary mask image (optional)")

class gibbs_trackingOutputSpec(TraitedSpec):
    out_file = File(desc='output fiber bundle', exists = True)
    param_file = File(desc='gibbs parameters',exists = True)

class gibbs_tracking(BaseInterface):
    input_spec = gibbs_trackingInputSpec
    output_spec = gibbs_trackingOutputSpec

    def _run_interface(self,runtime):
        # Create XML file
        f = open(os.path.abspath('gibbs_parameters.gtp'),'w')
        xml_text = '<?xml version="1.0" ?>\n<global_tracking_parameter_file file_version="0.1">\n    <parameter_set iterations="%s" particle_length="%s" particle_width="%s" particle_weight="%s" temp_start="%s" temp_end="%s" inexbalance="%s" fiber_length="%s" curvature_threshold="%s" />\n</global_tracking_parameter_file>' % (self.inputs.iterations,self.inputs.particle_length,self.inputs.particle_width,self.inputs.particle_weight,self.inputs.temp_start,self.inputs.temp_end,self.inputs.inexbalance,self.inputs.fiber_length, self.inputs.curvature_threshold)
        f.write(xml_text)
        f.close()
        
        # Call gibbs software
        gibbs = gibbs_tracking_CMD(in_file=self.inputs.in_file,parameter_file=os.path.abspath('gibbs_parameters.gtp'))
        gibbs.inputs.mask = self.inputs.mask
        gibbs.inputs.out_file_name = 'global_tractography.trk'
        res = gibbs.run()

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath('global_tractography.trk')
        outputs["param_file"] = os.path.abspath('gibbs_parameters.gtp')
        return outputs
    
class match_orientationInputSpec(BaseInterfaceInputSpec):
    gibbs_output = File(exists=True, mandatory=True,desc="Trackvis file outputed by gibbs miniapp, with the LPS orientation set as default")
    gibbs_input = File(exists=True, mandatory=True, desc="File used as input for the gibbs tracking (wm mask)")

class match_orientationOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='Trackvis file with orientation matching gibbs input')

class match_orientations(BaseInterface):
    
    input_spec = match_orientationInputSpec
    output_spec = match_orientationOutputSpec
    
    def _run_interface(self, runtime):    
        filename = os.path.basename(self.inputs.gibbs_output)
    
        dx, dy, dz = get_data_dims(self.inputs.gibbs_input)
        vx, vy, vz = get_vox_dims(self.inputs.gibbs_input)
        image_file = nib.load(self.inputs.gibbs_input)
        affine = image_file.get_affine()
        import numpy as np
        #Reads MITK tracks
        fib, hdr = nib.trackvis.read(self.inputs.gibbs_output)
        trk_header = nib.trackvis.empty_header()
        trk_header['dim'] = [dx,dy,dz]
        trk_header['voxel_size'] = [vx,vy,vz]
        trk_header['origin'] = [0 ,0 ,0]
        axcode = nib.orientations.aff2axcodes(affine)
        if axcode[0] != str(hdr['voxel_order'])[0]:
            flip_x = -1
        else:
            flip_x = 1
        if axcode[1] != str(hdr['voxel_order'])[1]:
            flip_y = -1
        else:
            flip_y = 1
        if axcode[2] != str(hdr['voxel_order'])[2]:
            flip_z = -1
        else:
            flip_z = 1
        trk_header['voxel_order'] = axcode[0]+axcode[1]+axcode[2]
        new_fib = []
        for i in range(len(fib)):
            temp_fib = fib[i][0].copy()
            for j in range(len(fib[i][0])):
                temp_fib[j] = [flip_x*(fib[i][0][j][0]-hdr['origin'][0])+vx/2,flip_y*(fib[i][0][j][1]-hdr['origin'][1])+vy/2, flip_z*(fib[i][0][j][2]-hdr['origin'][2])+vz/2]
            new_fib.append((temp_fib,None,None))
        nib.trackvis.write(os.path.abspath(filename), new_fib, trk_header, points_space = 'voxmm')
        iflogger.info('file written to %s' % os.path.abspath(filename))
        return runtime
    
    def _list_outputs(self):
        filename = os.path.basename(self.inputs.gibbs_output)
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(filename)
        return outputs

def create_gibbs_tracking_flow(config):
    flow = pe.Workflow(name="tracking")
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["recon_file","wm_mask_resampled"]),name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["track_file","param_file"],mandatory_inputs=True),name="outputnode")

    gibbs = pe.Node(interface=gibbs_tracking(iterations = config.iterations, particle_length=config.particle_length, particle_width=config.particle_width, particle_weight=config.particle_weight, temp_start=config.temp_start, temp_end=config.temp_end, inexbalance=config.inexbalance, fiber_length=config.fiber_length, curvature_threshold=config.curvature_threshold),name="gibbs_tracking")
        
    match_orient = pe.Node(interface=match_orientations(),name='match_orientations')

    flow.connect([
                  (inputnode,gibbs,[("recon_file","in_file")]),
                  (inputnode,gibbs,[("wm_mask_resampled","mask")]),
                  (gibbs,match_orient,[("out_file","gibbs_output")]),
                  (inputnode,match_orient,[("wm_mask_resampled","gibbs_input")]),
                  (match_orient,outputnode,[("out_file","track_file")]),
                  (gibbs,outputnode,[("param_file","param_file")]),
                ])

    return flow
