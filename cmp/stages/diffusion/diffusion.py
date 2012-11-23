# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Diffusion reconstruction and tractography
""" 

# General imports
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

# Nipype imports
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.diffusion_toolkit as dtk
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec,\
    traits, File, TraitedSpec, isdefined
from nipype.utils.filemanip import split_filename

# Own imports
from cmp.stages.common import CMP_Stage
from cmp_dtk import *
from cmp_dtb import *
from cmtklib.diffusion import filter_fibers


class Diffusion_Config(HasTraits):
    imaging_model = Str
    resampling = Tuple(2,2,2)
    reconstruction = Enum('DTK',['DTK','Camino'])
    tracking = Enum('DTB',['DTK','DTB'])
    dtk_recon_config = Instance(HasTraits)
    dtk_tracking_config = Instance(HasTraits)
    dtb_tracking_config = Instance(HasTraits)
    
    traits_view = View(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
                       Group('reconstruction',
                             Item('dtk_recon_config',style='custom',visible_when='reconstruction=="DTK"'),
                             label='Reconstruction', show_border=True, show_labels=False),
                       Group('tracking',
                             Item('dtb_tracking_config',style='custom',visible_when='tracking=="DTB"'),
                             Item('dtk_tracking_config',style='custom',visible_when='tracking=="DTK"'),
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


def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')

class Diffusion(CMP_Stage):
    name = 'Diffusion'
    config = Diffusion_Config()

    def create_workflow(self):
        flow = pe.Workflow(name="Diffusion_stage")

        # inputs and outputs
        inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion","wm_mask","T1-TO-B0_mat","diffusion_b0_resampled"]),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=["track_file","lengths_file","gFA","skewness","kurtosis","P0"]),name="outputnode")

        # resampling diffusion image and setting output type to short
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii',out_datatype='short',out_file='diffusion_resampled.nii'),name="fs_mriconvert")
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
                        (inputnode, track_flow,[('wm_mask','inputnode.wm_mask'),('T1-TO-B0_mat','inputnode.T1-TO-B0_mat'),('diffusion_b0_resampled','inputnode.diffusion_b0_resampled')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
                        ])
                        
        # Fibers spline and length filtering
        dtk_splinefilter = pe.Node(interface=dtk.SplineFilter(step_length=1), name="dtk_splinefilter")
        cmtk_filterfibers = pe.Node(interface=CMTK_filterfibers(), name="cmtk_filterfibers")
        flow.connect([
                    (track_flow,dtk_splinefilter, [('outputnode.track_file','track_file')]),
                    (dtk_splinefilter,cmtk_filterfibers, [('smoothed_track_file','track_file')]),
                    (recon_flow,outputnode, [("outputnode.gFA","gFA"),("outputnode.skewness","skewness"),
                                             ("outputnode.kurtosis","kurtosis"),("outputnode.P0","P0")]),
                    (cmtk_filterfibers,outputnode, [('filtered_track_file','track_file'),('lengths_file','lengths_file')])
                    ])
        
        return flow

