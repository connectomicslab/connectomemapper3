# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for building connectivity matrices and resulting CFF file
""" 

try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

import glob
import os

# Nipype imports
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec,\
    traits, File, TraitedSpec, InputMultiPath, OutputMultiPath, isdefined

from cmtklib.connectome import cmat

from cmp.stages.common import CMP_Stage
from nipype.utils.filemanip import split_filename

class Connectome_Config(HasTraits):
    compute_curvature = Bool(True)
    cff_enabled_trait = Bool(False)
    cff_creator = Str
    cff_email = Str
    cff_publisher = Str
    cff_license = Str
    
    output_types = List(['gPickle'], editor=CheckListEditor(values=['gPickle','mat','cff'],cols=3))

    traits_view = View(Item('output_types',style='custom'),
                        Group('compute_curvature',label='Connectivity matrix', show_border=True),
                        Group('cff_creator','cff_email','cff_publisher','cff_license',
                        label='CFF creation metadata', show_border=True, visible_when='cff_enabled_trait==True'
                        ),
                        kind='live',
                        )
                        
    def _output_type_changed(self, new):
        if 'cff' in new:
            self.cff_enabled_trait = True
        else:
            self.cff_enabled_trait = False
                        
class CMTK_cmatInputSpec(BaseInterfaceInputSpec):
    track_file = File(desc='Tractography result', exists=True, mandatory=True)
    roi_volumes = InputMultiPath(File(exists=True), desc='ROI volumes registered to diffusion space')
    parcellation_scheme = traits.Enum('Lausanne2008',['Lausanne2008','Nativefreesurfer'], usedefault=True)
    compute_curvature = traits.Bool(True, desc='Compute curvature', usedefault=True)
    additional_maps = traits.List(File,desc='Additional calculated maps (ADC, gFA, ...)')
    output_types = traits.List(Str, desc='Output types of the connectivity matrices')
    
class CMTK_cmatOutputSpec(TraitedSpec):
    endpoints_file = File()
    endpoints_mm_file = File()
    final_fiberslength_files = OutputMultiPath(File())
    filtered_fiberslabel_files = OutputMultiPath(File())
    final_fiberlabels_files = OutputMultiPath(File())
    streamline_final_files = OutputMultiPath(File())
    connectivity_matrices = OutputMultiPath(File())
    
class CMTK_cmat(BaseInterface):
    input_spec = CMTK_cmatInputSpec
    output_spec = CMTK_cmatOutputSpec
    
    def _run_interface(self, runtime):
        if isdefined(self.inputs.additional_maps):
            additional_maps = dict( (split_filename(add_map)[1],add_map) for add_map in self.inputs.additional_maps if add_map != '')
        else:
            additional_maps = {}

        cmat(intrk=self.inputs.track_file, roi_volumes=self.inputs.roi_volumes,
             parcellation_scheme=self.inputs.parcellation_scheme,
             compute_curvature=self.inputs.compute_curvature,
             additional_maps=additional_maps,output_types=self.inputs.output_types)
             
        return runtime
        
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['endpoints_file'] = os.path.abspath('endpoints.npy')
        outputs['endpoints_mm_file'] = os.path.abspath('endpointsmm.npy')
        outputs['final_fiberslength_files'] = glob.glob(os.path.abspath('final_fiberslength*'))
        outputs['filtered_fiberslabel_files'] = glob.glob(os.path.abspath('filtered_fiberslabel*'))
        outputs['final_fiberlabels_files'] = glob.glob(os.path.abspath('final_fiberlabels*'))
        outputs['streamline_final_files'] = glob.glob(os.path.abspath('streamline_final*'))
        outputs['connectivity_matrices'] = glob.glob(os.path.abspath('connectome*'))
        
        return outputs
    

class Connectome(CMP_Stage):
    name = 'Connectome'
    config = Connectome_Config()
    
    def create_workflow(self):
        flow = pe.Workflow(name="Connectome_stage")
        
        # define inputs and outputs
        inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion_b0_resampled","roi_volumes","track_file","parcellation_scheme","gFA","skewness","kurtosis","P0","T1-TO-B0_mat"]),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=["endpoints_file","endpoints_mm_file","final_fiberslength_files",
                             "filtered_fiberslabel_files","final_fiberlabels_files","streamline_final_files","connectivity_matrices"]),name="outputnode")
        
        cmtk_cmat = pe.Node(interface=CMTK_cmat(),name="cmtk_cmat")
        cmtk_cmat.inputs.compute_curvature = self.config.compute_curvature
        cmtk_cmat.inputs.output_types = self.config.output_types

        # Additional maps
        map_merge = pe.Node(interface=util.Merge(4),name="map_merge")
        
        # Register ROI Volumes to B0 space
        fsl_applyxfm = pe.MapNode(interface=fsl.ApplyXfm(apply_xfm=True, interp="nearestneighbour"),name="fsl_applyxfm",iterfield=["in_file"])
        
        flow.connect([
                     (inputnode,map_merge, [('gFA','in1'),('skewness','in2'),('kurtosis','in3'),('P0','in4')]),
                     (inputnode,fsl_applyxfm, [('roi_volumes','in_file'),('diffusion_b0_resampled','reference'),('T1-TO-B0_mat','in_matrix_file')]),
                     (inputnode,cmtk_cmat, [('track_file','track_file'),('parcellation_scheme','parcellation_scheme')]),
                     (fsl_applyxfm,cmtk_cmat, [('out_file','roi_volumes')]),
                     (map_merge,cmtk_cmat, [('out','additional_maps')]),
                     (cmtk_cmat,outputnode, [('endpoints_file','endpoints_file'),('endpoints_mm_file','endpoints_mm_file'),
                             ('final_fiberslength_files','final_fiberslength_files'),('filtered_fiberslabel_files','filtered_fiberslabel_files'),
                             ('final_fiberlabels_files','final_fiberlabels_files'),('streamline_final_files','streamline_final_files'),
                             ('connectivity_matrices','connectivity_matrices')])
                     ])
        return flow


