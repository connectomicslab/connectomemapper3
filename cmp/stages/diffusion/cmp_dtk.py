# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP sub-stages of Diffusion stage for DTK-reconstruction and tracking
""" 

# General imports
import re
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *
    
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.diffusion_toolkit as dtk
    
from cmp_dtb import *

class DTK_recon_config(HasTraits):
    imaging_model = Str
    maximum_b_value = Int(1000)
    gradient_table = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
                          'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256'])
    dsi_number_of_directions = Enum(514,[514,257,124])
    number_of_directions = Int(514)
    number_of_output_directions = Int(181)
    recon_matrix_file = Str('DSI_matrix_515x181.dat')
    apply_gradient_orientation_correction = Bool(True)
    number_of_averages = Int(1)
    multiple_high_b_values = Bool(False)
    number_of_b0_volumes = Int(1)
    
    compute_additional_maps = List(['gFA','skewness','kurtosis','P0'],
                                  editor=CheckListEditor(values=['gFA','skewness','kurtosis','P0'],cols=4))
    
    traits_view = View(Item('maximum_b_value',visible_when='imaging_model=="DTI"'),
                       Item('gradient_table',visible_when='imaging_model!="DSI"'),
                       Item('dsi_number_of_directions',visible_when='imaging_model=="DSI"'),
                       Item('number_of_directions',visible_when='imaging_model!="DSI"',style='readonly'),
                       Item('number_of_averages',visible_when='imaging_model=="DTI"'),
                       Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
                       'number_of_b0_volumes',
                       Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
                       Item('compute_additional_maps',style='custom',visible_when='imaging_model!="DTI"'),
                       )
    
    def _dsi_number_of_directions_changed(self, new):
        self.number_of_directions = int(new)
        self.recon_matrix_file = 'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(new)+1}
        
    def _gradient_table_changed(self, new):
        self.number_of_directions = int(re.search('\d+',self.gradient_table).group(0))
        
    def _imaging_model_changed(self, new):
        if new == 'DTI' or new == 'HARDI':
            self._gradient_table_changed(self.gradient_table)
        if new == 'DSI':
            self._dsi_number_of_directions_changed(self.number_of_directions)
            
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
                        
def create_dtk_recon_flow(config):
    flow = pe.Workflow(name="DTK_reconstruction_substage")
    
    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion","diffusion_resampled"]),name="inputnode")
    
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","B0","ODF","gFA","skewness","kurtosis","P0","max","V1"]),name="outputnode")
    
    if config.imaging_model == "DSI":
        prefix = "dsi"
        dtk_odfrecon = pe.Node(interface=dtk.ODFRecon(out_prefix=prefix),name='dtk_odfrecon')
        dtk_odfrecon.inputs.matrix = os.path.join(os.environ['DSI_PATH'],config.recon_matrix_file)
        dtk_odfrecon.inputs.n_b0 = config.number_of_b0_volumes
        dtk_odfrecon.inputs.n_directions = int(config.dsi_number_of_directions)+1
        dtk_odfrecon.inputs.n_output_directions = config.number_of_output_directions
        dtk_odfrecon.inputs.dsi = True
        
        flow.connect([
                    (inputnode,dtk_odfrecon,[('diffusion_resampled','DWI')]),
                    (dtk_odfrecon,outputnode,[('DWI','DWI'),('B0','B0'),('ODF','ODF'),('max','max')])])
                    
    if config.imaging_model == "HARDI":
        prefix = "hardi"
        dtk_hardimat = pe.Node(interface=dtk.HARDIMat(),name='dtk_hardimat')
        dtk_hardimat.inputs.gradient_table = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),config.gradient_table+'.txt')
        dtk_hardimat.inputs.oblique_correction = config.apply_gradient_orientation_correction
        
        dtk_odfrecon = pe.Node(interface=dtk.ODFRecon(out_prefix=prefix),name='dtk_odfrecon')
        dtk_odfrecon.inputs.n_b0 = config.number_of_b0_volumes
        dtk_odfrecon.inputs.n_directions = int(config.number_of_directions)+1
        dtk_odfrecon.inputs.n_output_directions = config.number_of_output_directions

        flow.connect([
                    (inputnode,dtk_hardimat,[('diffusion_resampled','reference_file')]),
                    (dtk_hardimat,dtk_odfrecon,[('out_file','matrix')]),
                    (inputnode,dtk_odfrecon,[('diffusion_resampled','DWI')]),
                    (dtk_odfrecon,outputnode,[('DWI','DWI'),('B0','B0'),('ODF','ODF'),('max','max')])])
                    
                        
    if config.imaging_model == "DTI":
        prefix = "dti"
        dtk_dtirecon = pe.Node(interface=dtk.DTIRecon(out_prefix=prefix),name='dtk_dtirecon')
        dtk_dtirecon.inputs.b_value = config.maximum_b_value
        dtk_dtirecon.inputs.gradient_matrix = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),config.gradient_table+'.txt')
        dtk_dtirecon.inputs.multiple_b_values = config.multiple_high_b_values
        dtk_dtirecon.inputs.n_averages = config.number_of_averages
        dtk_dtirecon.inputs.number_of_b0 = config.number_of_b0_volumes
        dtk_dtirecon.inputs.oblique_correction = config.apply_gradient_orientation_correction
        
        flow.connect([
                    (inputnode,dtk_dtirecon,[('diffusion','DWI')]),
                    (dtk_dtirecon,outputnode,[('DWI','DWI'),('B0','B0'),('V1','V1')])])
    else:
        if 'gFA' in config.compute_additional_maps:
            dtb_gfa = pe.Node(interface=DTB_gfa(moment=2),name='dtb_gfa')
            flow.connect([
                        (dtk_odfrecon,dtb_gfa,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
                        (dtb_gfa,outputnode,[('out_file','gFA')])])
        if 'skewness' in config.compute_additional_maps:
            dtb_skewness = pe.Node(interface=DTB_gfa(moment=3),name='dtb_skewness')
            flow.connect([
                        (dtk_odfrecon,dtb_skewness,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
                        (dtb_skewness,outputnode,[('out_file','skewness')])])
        if 'kurtosis' in config.compute_additional_maps:
            dtb_kurtosis = pe.Node(interface=DTB_gfa(moment=4),name='dtb_kurtosis')
            flow.connect([
                        (dtk_odfrecon,dtb_kurtosis,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
                        (dtb_kurtosis,outputnode,[('out_file','kurtosis')])])
        if 'P0' in config.compute_additional_maps:
            dtb_p0 = pe.Node(interface=DTB_P0(),name='dtb_P0')
            flow.connect([
                        (inputnode,dtb_p0,[('diffusion','dwi_file')]),
                        (dtk_odfrecon,dtb_p0,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
                        (dtb_p0,outputnode,[('out_file','P0')])])
                    
    return flow
