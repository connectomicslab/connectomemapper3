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
import pickle

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl

# Own imports
from cmp.stages.common import Stage
from reconstruction import *
from tracking import *

class DiffusionConfig(HasTraits):
    imaging_model = Str
    resampling = Tuple(2,2,2)
    #recon_editor = List(['DTK','MRtrix','Camino']) # list of available reconstruction methods. Update _imaging_model_changed when adding new
    #reconstruction_software = Str ('DTK') # default recon method
    #tracking_editor = List(['DTB','MRtrix','Camino']) # list of available tracking methods
    #tracking_software = Str('DTB') # default tracking method
    processing_tool_editor = List(['DTK','MRtrix','Camino','FSL','Gibbs'])
    processing_tool = Str('DTK')
    dtk_recon_config = Instance(HasTraits)
    mrtrix_recon_config = Instance(HasTraits)
    camino_recon_config = Instance(HasTraits)
    fsl_recon_config = Instance(HasTraits)
    gibbs_recon_config = Instance(HasTraits)
    gibbs_model_config = Instance(HasTraits)
    dtk_tracking_config = Instance(HasTraits)
    dtb_tracking_config = Instance(HasTraits)
    mrtrix_tracking_config = Instance(HasTraits)
    camino_tracking_config = Instance(HasTraits)
    fsl_tracking_config = Instance(HasTraits)
    diffusion_model_editor = List(['Deterministic','Probabilistic'])
    diffusion_model = Str('Deterministic')
    
    traits_view = View(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
		       Item('processing_tool',editor=EnumEditor(name='processing_tool_editor')),
                       Group(#Item('reconstruction_software',editor=EnumEditor(name='recon_editor')),
			     Item('gibbs_recon_config',style='custom',visible_when='processing_tool=="Gibbs"'),
			     Item('gibbs_model_config',style='custom',visible_when='processing_tool=="Gibbs"'),
                             Item('dtk_recon_config',style='custom',visible_when='processing_tool=="DTK"'),
			     Item('mrtrix_recon_config',style='custom',visible_when='processing_tool=="MRtrix"'),
			     Item('camino_recon_config',style='custom',visible_when='processing_tool=="Camino"'),
                 Item('fsl_recon_config',style='custom',visible_when='processing_tool=="FSL"'),
                             label='Reconstruction', show_border=True, show_labels=False),
                       Group(#Item('tracking_software',editor=EnumEditor(name='tracking_editor')),
			     Item('diffusion_model',editor=EnumEditor(name='diffusion_model_editor')),
                             Item('dtb_tracking_config',style='custom',visible_when='processing_tool=="DTK"'),
			     Item('mrtrix_tracking_config',style='custom',visible_when='processing_tool=="MRtrix"'),
			     Item('camino_tracking_config',style='custom',visible_when='processing_tool=="Camino"'),
                 Item('fsl_tracking_config',style='custom',visible_when='processing_tool=="FSL"'),
                             label='Tracking', show_border=True, show_labels=False,visible_when='processing_tool!="Gibbs"'),
                       )

    def __init__(self):
        self.dtk_recon_config = DTK_recon_config(imaging_model=self.imaging_model)
        self.mrtrix_recon_config = MRtrix_recon_config(imaging_model=self.imaging_model,recon_mode=self.diffusion_model)
        self.camino_recon_config = Camino_recon_config(imaging_model=self.imaging_model)
        self.fsl_recon_config = FSL_recon_config()
        self.gibbs_recon_config = Gibbs_recon_config()
        self.gibbs_model_config = Gibbs_model_config()
        self.dtk_tracking_config = DTK_tracking_config()
        self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.imaging_model)
        self.mrtrix_tracking_config = MRtrix_tracking_config(imaging_model=self.imaging_model,tracking_mode=self.diffusion_model)
        self.camino_tracking_config = Camino_tracking_config(imaging_model=self.imaging_model,tracking_mode=self.diffusion_model)
        self.fsl_tracking_config = FSL_tracking_config()
        
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'model_type')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'local_model')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'inversion')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'fallback_index')
        
    def _imaging_model_changed(self, new):
        self.dtk_recon_config.imaging_model = new
        #self.mrtrix_recon_config.imaging_model = new
        #self.camino_recon_config.imaging_model = new
        self.dtk_tracking_config.imaging_model = new
        self.dtb_tracking_config.imaging_model = new
        # Remove MRtrix from recon and tracking methods and Probabilistic from diffusion model if imaging_model is DSI
        if new == 'DSI':
            if (not self.processing_tool == 'DTK'):
                self._processing_tool_changed('DTK')
                self.processing_tool = 'DTK'
            self.processing_tool_editor = ['DTK']
        else:
            self.diffusion_model_editor = ['Deterministic','Probabilistic']
            self.processing_tool_editor = ['DTK','MRtrix','Camino','FSL','Gibbs']

    def _processing_tool_changed(self, new):
        if new == 'DTK' or new == 'Gibbs':
            self.diffusion_model_editor = ['Deterministic']
            self.diffusion_model = 'Deterministic'
            self._diffusion_model_changed('Deterministic')
        elif new == "FSL":
            self.diffusion_model_editor = ['Probabilistic']
            self.diffusion_model = 'Probabilistic'       
        else:
            self.diffusion_model_editor = ['Deterministic','Probabilistic']

    def _diffusion_model_changed(self,new):
        self.mrtrix_recon_config.recon_mode = new # Probabilistic tracking only available for Spherical Deconvoluted data
        self.mrtrix_tracking_config.tracking_model = new
        self.camino_tracking_config.tracking_mode = new
        self.update_camino_tracking_model()
        
    def update_camino_tracking_model(self):
        if self.diffusion_model == 'Probabilistic':
            self.camino_tracking_config.tracking_model = 'pico'
        elif self.camino_recon_config.model_type == 'Single-Tensor' or self.camino_recon_config.local_model == 'restore' or self.camino_recon_config.local_model == 'adc':
            self.camino_tracking_config.tracking_model = 'dt'
        elif self.camino_recon_config.local_model == 'ball_stick':
            self.camino_tracking_config.tracking_model = 'ballstick'
        else:
            self.camino_tracking_config.tracking_model = 'multitensor'
            
    def update_camino_tracking_inversion(self):
        self.camino_tracking_config.inversion_index = self.camino_recon_config.inversion
        self.camino_tracking_config.fallback_index = self.camino_recon_config.fallback_index

        
def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')

class DiffusionStage(Stage):
    name = 'diffusion_stage'
    config = DiffusionConfig()
    inputs = ["diffusion","wm_mask_registered","roi_volumes"]
    outputs = ["track_file","gFA","skewness","kurtosis","P0","roi_volumes"]


    def create_workflow(self, flow, inputnode, outputnode):
        # resampling diffusion image and setting output type to short
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii',out_file='diffusion_resampled.nii'),name="diffusion_resample")
        fs_mriconvert.inputs.vox_size = self.config.resampling
        flow.connect([(inputnode,fs_mriconvert,[('diffusion','in_file')])])

        fs_mriconvert_wm_mask = pe.Node(interface=fs.MRIConvert(out_type='nii',resample_type='nearest',out_file='wm_mask_resampled.nii'),name="mask_resample")
        fs_mriconvert_wm_mask.inputs.vox_size = self.config.resampling
        flow.connect([(inputnode,fs_mriconvert_wm_mask,[('wm_mask_registered','in_file')])])

        fs_mriconvert_ROIs = pe.MapNode(interface=fs.MRIConvert(out_type='nii',resample_type='nearest'),name="ROIs_resample",iterfield=['in_file'])
        fs_mriconvert_ROIs.inputs.vox_size = self.config.resampling
        flow.connect([(inputnode,fs_mriconvert_ROIs,[('roi_volumes','in_file')])])
        if self.config.processing_tool != 'DTK':
            dilate_rois = pe.MapNode(interface=fsl.DilateImage(),iterfield=['in_file'],name='dilate_rois')
            dilate_rois.inputs.operation = 'modal'
            flow.connect([
                          (fs_mriconvert_ROIs,dilate_rois,[("out_file","in_file")]),
                          (dilate_rois,outputnode,[("out_file","roi_volumes")])
                        ])
        else:
            flow.connect([
                          (fs_mriconvert,outputnode,[("out_file","roi_volumes")])
                        ])
        
        # Reconstruction
        if self.config.processing_tool == 'DTK':
            recon_flow = create_dtk_recon_flow(self.config.dtk_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
                        ])
        elif self.config.processing_tool == 'MRtrix':
            recon_flow = create_mrtrix_recon_flow(self.config.mrtrix_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
			(fs_mriconvert_wm_mask, recon_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        ])

        elif self.config.processing_tool == 'Camino':
            recon_flow = create_camino_recon_flow(self.config.camino_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
			(fs_mriconvert_wm_mask, recon_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        ])
        
        elif self.config.processing_tool == 'FSL':
            recon_flow = create_fsl_recon_flow(self.config.fsl_recon_config)
            flow.connect([
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
                        (fs_mriconvert_wm_mask,recon_flow,[('out_file','inputnode.wm_mask_resampled')])
                        ])

        elif self.config.processing_tool == 'Gibbs':
            recon_flow = create_gibbs_recon_flow(self.config.gibbs_recon_config,self.config.gibbs_model_config)
            flow.connect([
			(fs_mriconvert,recon_flow,[("out_file","inputnode.diffusion_resampled")]),
			(fs_mriconvert_wm_mask,recon_flow,[("out_file","inputnode.wm_mask_resampled")]),
            (recon_flow,outputnode,[('outputnode.track_file','track_file')])
			])
        
        # Tracking
        if self.config.processing_tool == 'DTK':
            track_flow = create_dtb_tracking_flow(self.config.dtb_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_registered')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')])
                        ])

        elif self.config.processing_tool == 'MRtrix':
            track_flow = create_mrtrix_tracking_flow(self.config.mrtrix_tracking_config,self.config.mrtrix_recon_config.gradient_table,self.config.mrtrix_recon_config.local_model)
            flow.connect([
                        (fs_mriconvert_wm_mask, track_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
			             #(recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
			             #(recon_flow, track_flow,[('outputnode.grad','inputnode.grad')]),
                        ])
            if self.config.diffusion_model == 'Probabilistic':
                flow.connect([
    			    (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
    			    ])
            flow.connect([
                        (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])

        elif self.config.processing_tool == 'Camino':
            track_flow = create_camino_tracking_flow(self.config.camino_tracking_config,self.config.camino_recon_config.gradient_table)
            flow.connect([
                        (fs_mriconvert_wm_mask, track_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')])
                        ])
            if self.config.diffusion_model == 'Probabilistic':
                flow.connect([
                    (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
                    ])
            flow.connect([
                        (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])
        
        elif self.config.processing_tool == 'FSL':
            track_flow = create_fsl_tracking_flow(self.config.fsl_tracking_config)
            flow.connect([
                        (fs_mriconvert_wm_mask,track_flow,[('out_file','inputnode.wm_mask_resampled')]),
                        (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
                        (recon_flow,track_flow,[('outputnode.fsamples','inputnode.fsamples')]),
                        (recon_flow,track_flow,[('outputnode.phsamples','inputnode.phsamples')]),
                        (recon_flow,track_flow,[('outputnode.thsamples','inputnode.thsamples')]),
                        ])
            flow.connect([
                        (track_flow,outputnode,[("outputnode.fdt_paths","track_file")]),
                        ])
                        
        if self.config.processing_tool == 'DTK':
            flow.connect([
			    (recon_flow,outputnode, [("outputnode.gFA","gFA"),("outputnode.skewness","skewness"),
			                             ("outputnode.kurtosis","kurtosis"),("outputnode.P0","P0")]),
			    (track_flow,outputnode, [('outputnode.track_file','track_file')])
			    ])

    def define_inspect_outputs(self):

        if self.config.processing_tool == 'DTK':
            diff_results_path = os.path.join(self.stage_dir,"tracking","dtb_streamline","result_fiber_tracking.pklz")
            if(os.path.exists(diff_results_path)):
                diff_results = pickle.load(gzip.open(diff_results_path))
                self.inspect_outputs_dict['DTK streamline'] = ['trackvis',diff_results.outputs.track_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()

        elif self.config.processing_tool == 'MRtrix':

            if self.config.mrtrix_recon_config.local_model:
                RF_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_rf","result_mrtrix_rf.pklz")
                if(os.path.exists(RF_path)):
                    RF_results = pickle.load(gzip.open(RF_path))
                    self.inspect_outputs_dict['MRTRIX Response function'] = ['disp_profile','-response',RF_results.outputs.response]
                    self.inspect_outputs = self.inspect_outputs_dict.keys()

            FA_map_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_FA","result_mrtrix_FA.pklz")
            if os.path.exists(FA_map_path):
                FA_map_res = pickle.load(gzip.open(FA_map_path))
                self.inspect_outputs_dict['MRtrix FA map'] = ['mrview', FA_map_res.outputs.FA]
                self.inspect_outputs = self.inspect_outputs_dict.keys()

            FA_thr_map_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_thr","result_mrtrix_thr.pklz")
            if os.path.exists(FA_thr_map_path):
                FA_thr_map_res = pickle.load(gzip.open(FA_thr_map_path))
                self.inspect_outputs_dict['MRtrix thresholded FA'] = ['mrview', FA_map_res.outputs.FA, FA_thr_map_res.outputs.out_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()
                
            diff_results_path = os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz")
            if os.path.exists(diff_results_path):
                diff_results = pickle.load(gzip.open(diff_results_path))
                self.inspect_outputs_dict['MRTrix streamline'] = ['trackvis',diff_results.outputs.out_file]
                self.inspect_outputs = self.inspect_outputs_dict.keys()

            
    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"tracking","dtb_streamline","result_dtb_streamline.pklz"))

