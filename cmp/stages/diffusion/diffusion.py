# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Diffusion reconstruction and tractography
""" 

# General imports
from traits.api import *
from traitsui.api import *
import gzip

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs

# Own imports
from cmp.stages.common import Stage
from reconstruction import *
from tracking import *

class DiffusionConfig(HasTraits):
    imaging_model = Str
    resampling = Tuple(2,2,2)
    recon_editor = List(['DTK','MRtrix','Camino']) # list of available reconstruction methods. Update _imaging_model_changed when adding new
    reconstruction = Str ('DTK') # default recon method
    tracking_editor = List(['DTB','MRtrix','Camino']) # list of available tracking methods
    tracking = Str('DTB') # default tracking method
    dtk_recon_config = Instance(HasTraits)
    mrtrix_recon_config = Instance(HasTraits)
    camino_recon_config = Instance(HasTraits)
    dtk_tracking_config = Instance(HasTraits)
    dtb_tracking_config = Instance(HasTraits)
    mrtrix_tracking_config = Instance(HasTraits)
    camino_tracking_config = Instance(HasTraits)
    
    traits_view = View(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
                       Group(Item('reconstruction',editor=EnumEditor(name='recon_editor')),
                             Item('dtk_recon_config',style='custom',visible_when='reconstruction=="DTK"'),
			     Item('mrtrix_recon_config',style='custom',visible_when='reconstruction=="MRtrix"'),
			     Item('camino_recon_config',style='custom',visible_when='reconstruction=="Camino"'),
                             label='Reconstruction', show_border=True, show_labels=False),
                       Group(Item('tracking',editor=EnumEditor(name='tracking_editor')),
                             Item('dtb_tracking_config',style='custom',visible_when='tracking=="DTB"'),
			     Item('mrtrix_tracking_config',style='custom',visible_when='tracking=="MRtrix"'),
			     Item('camino_tracking_config',style='custom',visible_when='tracking=="Camino"'),
                             label='Tracking', show_border=True, show_labels=False),
                       )

    def __init__(self):
        self.dtk_recon_config = DTK_recon_config(imaging_model=self.imaging_model)
        self.mrtrix_recon_config = MRtrix_recon_config(imaging_model=self.imaging_model)
	self.camino_recon_config = Camino_recon_config(imaging_model=self.imaging_model)
        self.dtk_tracking_config = DTK_tracking_config()
        self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.imaging_model)
        self.mrtrix_tracking_config = MRtrix_tracking_config(imaging_model=self.imaging_model)
	self.camino_tracking_config = Camino_tracking_config(imaging_model=self.imaging_model)
        
    def _imaging_model_changed(self, new):
        self.dtk_recon_config.imaging_model = new
        self.mrtrix_recon_config.imaging_model = new
	self.camino_recon_config.imaging_model = new
        self.dtk_tracking_config.imaging_model = new
        self.dtb_tracking_config.imaging_model = new
	# Remove MRtrix from recon and tracking methods if imaging_model is DSI
	if new == 'DSI':
		self.recon_editor = ['DTK']
		self.reconstruction = 'DTK'
		self.tracking_editor = ['DTB']
		self.tracking = 'DTB'
	else:
		self.recon_editor = ['DTK','MRtrix','Camino']
		self.tracking_editor = ['DTB','MRtrix','Camino']

    def _reconstruction_changed(self, new):
	if new == 'DTK':
		self.tracking = 'DTB'
	elif new == 'MRtrix':
		self.tracking = 'MRtrix'
	elif new == 'Camino':
		self.tracking = 'Camino'

    def _tracking_changed(self,new):
	if new == 'DTB':
		self.reconstruction = 'DTK'
	if new == 'MRtrix':
		self.reconstruction = 'MRtrix'
	if new == 'Camino':
		self.reconstruction = 'Camino'
        
def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')

class DiffusionStage(Stage):
    name = 'diffusion_stage'
    config = DiffusionConfig()
    inputs = ["diffusion","wm_mask_registered"]
    outputs = ["track_file","gFA","skewness","kurtosis","P0"]


    def create_workflow(self, flow, inputnode, outputnode):
        # resampling diffusion image and setting output type to short
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii',out_datatype='short',out_file='diffusion_resampled.nii'),name="diffusion_resample")
        fs_mriconvert.inputs.vox_size = self.config.resampling
        flow.connect([(inputnode,fs_mriconvert,[('diffusion','in_file')])])

	fs_mriconvert_wm_mask = pe.Node(interface=fs.MRIConvert(out_type='nii',out_datatype='short',out_file='wm_mask_resampled.nii'),name="mask_resample")
        fs_mriconvert_wm_mask.inputs.vox_size = self.config.resampling
        flow.connect([(inputnode,fs_mriconvert_wm_mask,[('wm_mask_registered','in_file')])])
        
        # Reconstruction
        if self.config.reconstruction == 'DTK':
            recon_flow = create_dtk_recon_flow(self.config.dtk_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
                        ])
 	elif self.config.reconstruction == 'MRtrix':
            recon_flow = create_mrtrix_recon_flow(self.config.mrtrix_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
			(fs_mriconvert_wm_mask, recon_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        ])

	elif self.config.reconstruction == 'Camino':
            recon_flow = create_camino_recon_flow(self.config.camino_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
			(fs_mriconvert_wm_mask, recon_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        ])
        
        # Tracking
        if self.config.tracking == 'DTB':
            track_flow = create_dtb_tracking_flow(self.config.dtb_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_registered')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
                        ])
	elif self.config.tracking == 'MRtrix':
            track_flow = create_mrtrix_tracking_flow(self.config.mrtrix_tracking_config,self.config.mrtrix_recon_config.gradient_table,self.config.mrtrix_recon_config.compute_CSD)
            flow.connect([
                        (fs_mriconvert_wm_mask, track_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
			(recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
			(recon_flow, track_flow,[('outputnode.grad','inputnode.grad')]),
                        ])

	elif self.config.tracking == 'Camino':
            track_flow = create_camino_tracking_flow(self.config.camino_tracking_config)
            flow.connect([
                        (fs_mriconvert_wm_mask, track_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
                        ])
                        
	if self.config.reconstruction == 'DTK':
		flow.connect([
			    (recon_flow,outputnode, [("outputnode.gFA","gFA"),("outputnode.skewness","skewness"),
			                             ("outputnode.kurtosis","kurtosis"),("outputnode.P0","P0")]),
			    (track_flow,outputnode, [('outputnode.track_file','track_file')])
			    ])

    def define_inspect_outputs(self):
        diff_results_path = os.path.join(self.stage_dir,"tracking","dtb_streamline","result_fiber_tracking.pklz")
        if(os.path.exists(diff_results_path)):
            diff_results = pickle.load(gzip.open(diff_results_path))
            self.inspect_outputs_dict['streamline'] = ['trackvis',diff_results.outputs.track_file]
            self.inspect_outputs = self.inspect_outputs_dict.keys()
            
    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"tracking","dtb_streamline","result_dtb_streamline.pklz"))

