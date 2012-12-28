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
    reconstruction = Enum('DTK',['DTK'])
    tracking = Enum('DTB',['DTB'])
    dtk_recon_config = Instance(HasTraits)
    dtk_tracking_config = Instance(HasTraits)
    dtb_tracking_config = Instance(HasTraits)
    
    traits_view = View(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
                       Group('reconstruction',
                             Item('dtk_recon_config',style='custom',visible_when='reconstruction=="DTK"'),
                             label='Reconstruction', show_border=True, show_labels=False),
                       Group('tracking',
                             Item('dtb_tracking_config',style='custom',visible_when='tracking=="DTB"'),
                             label='Tracking', show_border=True, show_labels=False),
                       )

    def __init__(self):
        self.dtk_recon_config = DTK_recon_config(imaging_model=self.imaging_model)
        self.dtk_tracking_config = DTK_tracking_config()
        self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.imaging_model)
        
    def _imaging_model_changed(self, new):
        self.dtk_recon_config.imaging_model = new
        self.dtk_tracking_config.imaging_model = new
        self.dtb_tracking_config.imaging_model = new
        
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
        
        # Reconstruction
        if self.config.reconstruction == 'DTK':
            recon_flow = create_dtk_recon_flow(self.config.dtk_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (fs_mriconvert,recon_flow,[('out_file','inputnode.diffusion_resampled')]),
                        ])
        
        # Tracking
        if self.config.tracking == 'DTB':
            track_flow = create_dtb_tracking_flow(self.config.dtb_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_registered')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
                        ])
                        

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

