# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Reconstruction methods and workflows
""" 

# General imports
import re
import os
from traits.api import *
from traitsui.api import *
import pkg_resources

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.diffusion_toolkit as dtk
from nipype.utils.filemanip import split_filename

from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, TraitedSpec, BaseInterface, BaseInterfaceInputSpec
import nipype.interfaces.base as nibase
    
class DTK_recon_config(HasTraits):
    imaging_model = Str
    maximum_b_value = Int(1000)
    gradient_table_file = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
                          'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256','Custom...'])
    gradient_table = Str
    custom_gradient_table = File
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
                       Item('gradient_table_file',visible_when='imaging_model!="DSI"'),
                       Item('dsi_number_of_directions',visible_when='imaging_model=="DSI"'),
                       Item('number_of_directions',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
                       Item('custom_gradient_table',visible_when='imaging_model!="DSI"',enabled_when='gradient_table_file=="Custom..."'),
                       Item('number_of_averages',visible_when='imaging_model=="DTI"'),
                       Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
                       'number_of_b0_volumes',
                       Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
                       Item('compute_additional_maps',style='custom',visible_when='imaging_model!="DTI"'),
                       )
    
    def _dsi_number_of_directions_changed(self, new):
        self.number_of_directions = int(new)
        self.recon_matrix_file = 'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(new)+1}
        
    def _gradient_table_file_changed(self, new):
        if new != 'Custom...':
            self.gradient_table = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),new+'.txt')
            self.number_of_directions = int(re.search('\d+',new).group(0))
            
    def _custom_gradient_table_changed(self, new):
        self.gradient_table = new
        
    def _imaging_model_changed(self, new):
        if new == 'DTI' or new == 'HARDI':
            self._gradient_table_file_changed(self.gradient_table_file)
        if new == 'DSI':
            self._dsi_number_of_directions_changed(self.number_of_directions)
            
# Nipype interfaces for DTB commands

class DTB_P0InputSpec(CommandLineInputSpec):
    dsi_basepath = traits.Str(desc='DSI path/basename (e.g. \"data/dsi_\")',position=1,mandatory=True,argstr = "--dsi %s")
    dwi_file = nibase.File(desc='DWI file',position=2,mandatory=True,exists=True,argstr = "--dwi %s")

class DTB_P0OutputSpec(TraitedSpec):
    out_file = nibase.File(desc='Resulting P0 file')

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
    out_file = nibase.File(desc='Resulting file')

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
            
def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')
                        
def create_dtk_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    
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
        dtk_hardimat.inputs.gradient_table = config.gradient_table
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
        dtk_dtirecon.inputs.gradient_matrix = config.gradient_table
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
