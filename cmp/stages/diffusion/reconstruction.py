# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Reconstruction methods and workflows
""" 

# General imports
import re
import os
import shutil
from traits.api import *
from traitsui.api import *
import pkg_resources

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.mrtrix as mrtrix
import nipype.interfaces.camino as camino
from nipype.utils.filemanip import split_filename

from nipype.interfaces.base import CommandLine, CommandLineInputSpec,\
    traits, TraitedSpec, BaseInterface, BaseInterfaceInputSpec
import nipype.interfaces.base as nibase

from nipype import logging
iflogger = logging.getLogger('interface')

# Reconstruction configuration
    
class DTK_recon_config(HasTraits):
    imaging_model = Str
    maximum_b_value = Int(1000)
    gradient_table_file = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
                          'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256','Custom...'])
    gradient_table = Str
    custom_gradient_table = File
    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    dsi_number_of_directions = Enum([514,257,124])
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
                       Item('flip_table_axis',style='custom',label='Flip table:'),
                       Item('number_of_averages',visible_when='imaging_model=="DTI"'),
                       Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
                       'number_of_b0_volumes',
                       Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
                       Item('compute_additional_maps',style='custom',visible_when='imaging_model!="DTI"'),
                       )
    
    def _dsi_number_of_directions_changed(self, new):
        print("Number of directions changed to %d" % new )
        self.recon_matrix_file = 'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(new)+1}
        
    def _gradient_table_file_changed(self, new):
        if new != 'Custom...':
            self.gradient_table = os.path.join(pkg_resources.resource_filename('cmtklib',os.path.join('data','diffusion','gradient_tables')),new+'.txt')
            if os.path.exists('cmtklib'):
                self.gradient_table = os.path.abspath(self.gradient_table)
            self.number_of_directions = int(re.search('\d+',new).group(0))
            
    def _custom_gradient_table_changed(self, new):
        self.gradient_table = new
        
    def _imaging_model_changed(self, new):
        if new == 'DTI' or new == 'HARDI':
            self._gradient_table_file_changed(self.gradient_table_file)

class MRtrix_recon_config(HasTraits):
    gradient_table = File
    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    local_model_editor = Dict({False:'1:Tensor',True:'2:Constrained Spherical Deconvolution'})
    local_model = Bool(False)
    lmax_order = Enum(['Auto',2,4,6,8,10,12,14,16])
    normalize_to_B0 = Bool(False)
    single_fib_thr = Float(0.7,min=0,max=1)
    recon_mode = Str    
    
    traits_view = View(Item('gradient_table',label='Gradient table (x,y,z,b):'),
                       Item('flip_table_axis',style='custom',label='Flip table:'),
                       #Item('custom_gradient_table',enabled_when='gradient_table_file=="Custom..."'),
		       #Item('b_value'),
		       #Item('b0_volumes'),
                       Item('local_model',editor=EnumEditor(name='local_model_editor')),
		       Group(Item('lmax_order'),
		       Item('normalize_to_B0'),
		       Item('single_fib_thr',label = 'FA threshold'),visible_when='local_model'),
                       )

    def _recon_mode_changed(self,new):
        if new == 'Probabilistic':
            self.local_model_editor = {True:'Constrained Spherical Deconvolution'}
            self.local_model = True
        else:
            self.local_model_editor = {False:'1:Tensor',True:'2:Constrained Spherical Deconvolution'}

class Camino_recon_config(HasTraits):
    b_value = Int (1000)
    model_type = Enum('Single-Tensor',['Single-Tensor','Two-Tensor','Three-Tensor','Other models'])
    singleTensor_models = {'dt':'Linear fit','nldt_pos':'Non linear positive semi-definite','nldt':'Unconstrained non linear','ldt_wtd':'Weighted linear'}
    local_model = Str('dt')
    local_model_editor = Dict(singleTensor_models)
    snr = Float(10.0)
    mixing_eq = Bool()
    fallback_model = Str('dt')
    fallback_editor = Dict(singleTensor_models)
    fallback_index = Int(1) # index for 'dt' which is the default fallback_model
    inversion = Int(1)
    
    gradient_table = File
    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    
    traits_view = View(Item('gradient_table',label='Gradient table (x,y,z,b):'),
                       Item('flip_table_axis',style='custom',label='Flip table:'),
                       'model_type',
		               VGroup(Item('local_model',label="Camino model",editor=EnumEditor(name='local_model_editor')),
                              Item('snr',visible_when='local_model=="restore"'),
                              Item('mixing_eq',label='Compartment mixing parameter = 0.5',visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"'),
                              Item('fallback_model',label='Initialisation and fallback model',editor=EnumEditor(name='fallback_editor'),visible_when='model_type == "Two-Tensor" or model_type == "Three-Tensor"')
                       )
                       )

    def _model_type_changed(self,new):
        if new == 'Single-Tensor':
            self.local_model_editor = self.singleTensor_models
            self.local_model = 'dt'
            self.mixing_eq = False
        elif new == 'Two-Tensor':
            self.local_model_editor = {'cylcyl':'Both Cylindrically symmetric','pospos':'Both positive','poscyl':'One positive, one cylindrically symmetric'}
            self.local_model = 'cylcyl'
        elif new == 'Three-Tensor':
            self.local_model_editor = {'cylcylcyl':'All cylindrically symmetric','pospospos':'All positive','posposcyl':'Two positive, one cylindrically symmetric','poscylcyl':'Two cylindrically symmetric, one positive'}
            self.local_model = 'cylcylcyl'
        elif new == 'Other models':
            self.local_model_editor = {'adc':'ADC','ball_stick':'Ball stick', 'restore':'Restore'}
            self.local_model = 'adc'
            self.mixing_eq = False
            
        self.update_inversion()
        
    def update_inversion(self):
        inversion_dict = {'ball_stick':-3, 'restore':-2, 'adc':-1, 'ltd':1, 'dt':1, 'nldt_pos':2,'nldt':4,'ldt_wtd':7,'cylcyl':10, 'pospos':30, 'poscyl':50, 'cylcylcyl':210, 'pospospos':230, 'posposcyl':250, 'poscylcyl':270}
        if self.model_type == 'Single-Tensor' or self.model_type == 'Other models':
            self.inversion = inversion_dict[self.local_model]
        else:
            self.inversion = inversion_dict[self.local_model] + inversion_dict[self.fallback_model]
            self.fallback_index = inversion_dict[self.fallback_model]
            if self.mixing_eq:
                self.inversion = self.inversion + 10
            
    def _local_model_changed(self,new):
        self.update_inversion()
        
    def _mixing_eq_changed(self,new):
        self.update_inversion()
    
    def _fallback_model_changed(self,new):
        self.update_inversion()

class FSL_recon_config(HasTraits):

    b_values = File()
    b_vectors = File()
    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    
    # BEDPOSTX parameters
    burn_period = Int(0)
    fibres_per_voxel = Int(1)
    jumps = Int(1250)
    sampling = Int(25)
    weight = Float(1.00)
    
    traits_view = View('b_values',
                       'b_vectors',
                       Item('flip_table_axis',style='custom',label='Flip table:'),
                       VGroup('burn_period','fibres_per_voxel','jumps','sampling','weight',show_border=True,label = 'BEDPOSTX parameters'),
                      ) 

class Gibbs_recon_config(HasTraits):
    recon_model = Enum(['Tensor','CSD'])
    b_values = File()
    b_vectors = File()
    flip_table_axis = List(editor=CheckListEditor(values=['x','y','z'],cols=3))
    sh_order = Enum(4,[2,4,6,8,10,12,14,16])
    reg_lambda = Float(0.006)
    csa = Bool(True)

    traits_view = View(Item('recon_model',label='Reconstruction  model:'),
                       'b_values',
                       'b_vectors',
                       Item('flip_table_axis',style='custom',label='Flip table:'),
                       Group(Item('sh_order',label="Spherical Harmonics order"),
                             Item('reg_lambda', label="Regularisation lambda factor"),
                             Item('csa',label="Use constant solid angle"),
                             show_border=True,label='CSD parameters', visible_when='recon_model == "CSD"'),
	           )

            
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
        import shutil
        outputs = self._outputs().get()
        path, base, _ = split_filename(self.inputs.dsi_basepath)
        if self.inputs.moment == 2:
            shutil.move(os.path.join(path,base+'gfa.nii'),os.path.abspath(base+'gfa.nii'))
            outputs["out_file"]  = os.path.abspath(base+'gfa.nii')
        elif self.inputs.moment == 3:
            shutil.move(os.path.join(path,base+'skewness.nii'),os.path.abspath(base+'skewness.nii'))
            outputs["out_file"]  = os.path.abspath(base+'skewness.nii')
        elif self.inputs.moment == 4:
            shutil.move(os.path.join(path,base+'kurtosis.nii'),os.path.abspath(base+'kurtosis.nii'))
            outputs["out_file"]  = os.path.abspath(base+'kurtosis.nii')
        #if self.inputs.moment == 2:
        #    outputs["out_file"]  = os.path.join(path,base+'gfa.nii')
        #if self.inputs.moment == 3:
        #    outputs["out_file"]  = os.path.join(path,base+'skewness.nii')
        #if self.inputs.moment == 4:
        #    outputs["out_file"]  = os.path.join(path,base+'kurtosis.nii')

        return outputs
            
def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')

class flipTableInputSpec(BaseInterfaceInputSpec):
    table = File(exists=True)
    flipping_axis = List()
    delimiter = Str()
    header_lines = Int(0)
    orientation = Enum(['v','h'])
    
class flipTableOutputSpec(TraitedSpec):
    table = File(exists=True)

class flipTable(BaseInterface):
    input_spec = flipTableInputSpec
    output_spec = flipTableOutputSpec
    
    def _run_interface(self,runtime):
        axis_dict = {'x':0, 'y':1, 'z':2}
        import numpy as np
        f = open(self.inputs.table,'r')
        header = ''
        for h in range(self.inputs.header_lines):
            header += f.readline()
        if self.inputs.delimiter == ' ':
            table = np.loadtxt(f)
        else:
            table = np.loadtxt(f, delimiter=self.inputs.delimiter)
        f.close()
        if self.inputs.orientation == 'v':
            for i in self.inputs.flipping_axis:
                table[:,axis_dict[i]] = -table[:,axis_dict[i]]
        elif self.inputs.orientation == 'h':
            for i in self.inputs.flipping_axis:
                table[axis_dict[i],:] = -table[axis_dict[i],:]
        out_f = file(os.path.abspath('flipped_table.txt'),'a')
        if self.inputs.header_lines > 0:
            out_f.write(header)
        np.savetxt(out_f,table,delimiter=self.inputs.delimiter)
        out_f.close()
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["table"] = os.path.abspath('flipped_table.txt')
        return outputs
                        
def create_dtk_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    
    # inputnode
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion","diffusion_resampled"]),name="inputnode")
    
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","B0","ODF","gFA","skewness","kurtosis","P0","max","V1"]),name="outputnode") 
    
    if config.imaging_model == "DSI":
        prefix = "dsi"
        dtk_odfrecon = pe.Node(interface=dtk.ODFRecon(out_prefix=prefix),name='dtk_odfrecon')
        dtk_odfrecon.inputs.matrix = os.path.join(os.environ['DSI_PATH'],config.recon_matrix_file)
        config.dsi_number_of_directions
        config.number_of_output_directions
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
        
        #dtk_hardimat.inputs.gradient_table = config.gradient_table
        # Flip gradient table
        flip_table = pe.Node(interface=flipTable(),name='flip_table')
        flip_table.inputs.table = config.gradient_table
        flip_table.inputs.flipping_axis = config.flip_table_axis
        flip_table.inputs.delimiter = ','
        flip_table.inputs.header_lines = 0
        flip_table.inputs.orientation = 'v'
        flow.connect([
                (flip_table,dtk_hardimat,[("table","gradient_table")]),
                ])
        
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
        
        flip_table = pe.Node(interface=flipTable(),name='flip_table')
        flip_table.inputs.table = config.gradient_table
        flip_table.inputs.flipping_axis = config.flip_table_axis
        flip_table.inputs.delimiter = ','
        flip_table.inputs.header_lines = 0
        flip_table.inputs.orientation = 'v'
        
        dtk_dtirecon = pe.Node(interface=dtk.DTIRecon(out_prefix=prefix),name='dtk_dtirecon')
        dtk_dtirecon.inputs.b_value = config.maximum_b_value
        dtk_dtirecon.inputs.multiple_b_values = config.multiple_high_b_values
        dtk_dtirecon.inputs.n_averages = config.number_of_averages
        dtk_dtirecon.inputs.number_of_b0 = config.number_of_b0_volumes
        dtk_dtirecon.inputs.oblique_correction = config.apply_gradient_orientation_correction
        
        flow.connect([
                    (inputnode,dtk_dtirecon,[('diffusion','DWI')]),
                    (flip_table, dtk_dtirecon,[('table', 'gradient_matrix')]),
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

class MRtrix_mul_InputSpec(CommandLineInputSpec):
    input1 = nibase.File(desc='Input1 file',position=1,mandatory=True,exists=True,argstr = "%s")
    input2 = nibase.File(desc='Input2 file',position=2,mandatory=True,exists=True,argstr = "%s")
    out_filename = traits.Str(desc='out filename',position=3,mandatory=True,argstr = "%s")

class MRtrix_mul_OutputSpec(TraitedSpec):
    out_file = nibase.File(desc='Multiplication result file')

class MRtrix_mul(CommandLine):
    _cmd = 'mrmult'
    input_spec = MRtrix_mul_InputSpec
    output_spec = MRtrix_mul_OutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(self._gen_outfilename())
        return outputs

    def _gen_filename(self, name):
        if name is 'out_filename':
            return self._gen_outfilename()
        else:
            return None

    def _gen_outfilename(self):
        _, name , _ = split_filename(self.inputs.input1)
        return name + '_masked.mif'

def create_mrtrix_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion","diffusion_resampled","wm_mask_resampled"]),name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","FA","eigVec","RF","grad"],mandatory_inputs=True),name="outputnode")
    
    # Flip gradient table
    flip_table = pe.Node(interface=flipTable(),name='flip_table')
    flip_table.inputs.table = config.gradient_table
    flip_table.inputs.flipping_axis = config.flip_table_axis
    flip_table.inputs.delimiter = ' '
    flip_table.inputs.header_lines = 0
    flip_table.inputs.orientation = 'v'
    flow.connect([
                (flip_table,outputnode,[("table","grad")]),
                ])

    # Tensor
    mrtrix_tensor = pe.Node(interface=mrtrix.DWI2Tensor(),name='mrtrix_make_tensor')
    
    flow.connect([
		(inputnode, mrtrix_tensor,[('diffusion_resampled','in_file')]),
        (flip_table,mrtrix_tensor,[("table","encoding_file")]),
		])

    # Tensor -> FA map
    mrtrix_FA = pe.Node(interface=mrtrix.Tensor2FractionalAnisotropy(),name='mrtrix_FA')
    convert_FA = pe.Node(interface=mrtrix.MRConvert(out_filename="FA.nii"),name='convert_FA')

    flow.connect([
		(mrtrix_tensor,mrtrix_FA,[('tensor','in_file')]),
		(mrtrix_FA,convert_FA,[('FA','in_file')]),
        (convert_FA,outputnode,[("converted","FA")])
		])

    # Tensor -> Eigenvectors
    mrtrix_eigVectors = pe.Node(interface=mrtrix.Tensor2Vector(),name="mrtrix_eigenvectors")

    flow.connect([
		(mrtrix_tensor,mrtrix_eigVectors,[('tensor','in_file')]),
		(mrtrix_eigVectors,outputnode,[('vector','eigVec')])
		])

    # Constrained Spherical Deconvolution
    if config.local_model:
        # Compute single fiber voxel mask
        mrtrix_erode = pe.Node(interface=mrtrix.Erode(),name="mrtrix_erode")
        mrtrix_erode.inputs.number_of_passes = 3
        mrtrix_mul_eroded_FA = pe.Node(interface=MRtrix_mul(),name='mrtrix_mul_eroded_FA')
        mrtrix_mul_eroded_FA.inputs.out_filename = "diffusion_resampled_tensor_FA_masked.mif"
        mrtrix_thr_FA = pe.Node(interface=mrtrix.Threshold(),name='mrtrix_thr')
        mrtrix_thr_FA.inputs.absolute_threshold_value = config.single_fib_thr

        flow.connect([
		    (inputnode,mrtrix_erode,[("wm_mask_resampled",'in_file')]),
		    (mrtrix_erode,mrtrix_mul_eroded_FA,[('out_file','input2')]),
		    (mrtrix_FA,mrtrix_mul_eroded_FA,[('FA','input1')]),
		    (mrtrix_mul_eroded_FA,mrtrix_thr_FA,[('out_file','in_file')])
		    ])
        # Compute single fiber response function
        mrtrix_rf = pe.Node(interface=mrtrix.EstimateResponseForSH(),name="mrtrix_rf")
        if config.lmax_order != 'Auto':
            mrtrix_rf.inputs.maximum_harmonic_order = config.lmax_order

        mrtrix_rf.inputs.normalise = config.normalize_to_B0
        flow.connect([
		    (inputnode,mrtrix_rf,[("diffusion_resampled","in_file")]),
		    (mrtrix_thr_FA,mrtrix_rf,[("out_file","mask_image")]),
            (flip_table,mrtrix_rf,[("table","encoding_file")]),
		    ])
        
        # Perform spherical deconvolution
        mrtrix_CSD = pe.Node(interface=mrtrix.ConstrainedSphericalDeconvolution(),name="mrtrix_CSD")
        mrtrix_CSD.inputs.normalise = config.normalize_to_B0
        flow.connect([
		    (inputnode,mrtrix_CSD,[('diffusion_resampled','in_file')]),
		    (mrtrix_rf,mrtrix_CSD,[('response','response_file')]),
		    (mrtrix_rf,outputnode,[('response','RF')]),
		    (inputnode,mrtrix_CSD,[("wm_mask_resampled",'mask_image')]),
            (flip_table,mrtrix_CSD,[("table","encoding_file")]),
		    (mrtrix_CSD,outputnode,[('spherical_harmonics_image','DWI')])
		    ])
    else:
        flow.connect([
		    (inputnode,outputnode,[('diffusion_resampled','DWI')])
		    ])
        
    return flow

def create_camino_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion","diffusion_resampled","wm_mask_resampled"]),name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["DWI","FA","MD","eigVec","RF","SD","grad"],mandatory_inputs=True),name="outputnode")
    
    # Flip gradient table
    flip_table = pe.Node(interface=flipTable(),name='flip_table')
    flip_table.inputs.table = config.gradient_table
    flip_table.inputs.flipping_axis = config.flip_table_axis
    flip_table.inputs.delimiter = ' '
    flip_table.inputs.header_lines = 2
    flip_table.inputs.orientation = 'v'
    flow.connect([
                (flip_table,outputnode,[("table","grad")]),
                ])
    
    # Convert diffusion data to camino format
    camino_convert = pe.Node(interface=camino.Image2Voxel(),name='camino_convert')
    flow.connect([
		(inputnode,camino_convert,[('diffusion_resampled','in_file')])
		])

    # Fit model
    camino_ModelFit = pe.Node(interface=camino.ModelFit(),name='camino_ModelFit')
    if config.model_type == "Two-Tensor" or config.model_type == "Three-Tensor":
        if config.mixing_eq:
            camino_ModelFit.inputs.model = config.local_model + '_eq ' + config.fallback_model
        else:
            camino_ModelFit.inputs.model = config.local_model + ' ' + config.fallback_model
    else:
        camino_ModelFit.inputs.model = config.local_model
    
    if config.local_model == 'restore':
        camino_ModelFit.inputs.sigma = config.snr

    flow.connect([
		(camino_convert,camino_ModelFit,[('voxel_order','in_file')]),
		(inputnode,camino_ModelFit,[('wm_mask_resampled','bgmask')]),
        (flip_table,camino_ModelFit,[("table","scheme_file")]),
		(camino_ModelFit,outputnode,[('fitted_data','DWI')])
		])

    # Compute FA map
    camino_FA = pe.Node(interface=camino.ComputeFractionalAnisotropy(),name='camino_FA')
    if config.model_type == 'Single-Tensor' or config.model_type == 'Other models':
        camino_FA.inputs.inputmodel = 'dt'
    elif config.model_type == 'Two-Tensor':
        camino_FA.inputs.inputmodel = 'twotensor'
    elif config.model_type == 'Three-Tensor':
        camino_FA.inputs.inputmodel = 'threetensor'
    elif config.model_type == 'Multitensor':
        camino_FA.inputs.inputmodel = 'multitensor'
        
    convert_FA = pe.Node(interface=camino.Voxel2Image(output_root="FA"),name="convert_FA")

    flow.connect([
		(camino_ModelFit,camino_FA,[('fitted_data','in_file')]),
		(camino_FA,convert_FA,[("fa","in_file")]),
        (inputnode,convert_FA,[("wm_mask_resampled","header_file")]),
        (convert_FA,outputnode,[('image_file','FA')]),
		])

    # Compute MD map
    camino_MD = pe.Node(interface=camino.ComputeMeanDiffusivity(),name='camino_MD')
    if config.model_type == 'Single-Tensor' or config.model_type == 'Other models':
        camino_MD.inputs.inputmodel = 'dt'
    elif config.model_type == 'Two-Tensor':
        camino_MD.inputs.inputmodel = 'twotensor'
    elif config.model_type == 'Three-Tensor':
        camino_MD.inputs.inputmodel = 'threetensor'
    elif config.model_type == 'Multitensor':
        camino_MD.inputs.inputmodel = 'multitensor'

    flow.connect([
		(camino_ModelFit,camino_MD,[('fitted_data','in_file')]),
		(camino_MD,outputnode,[('md','MD')]),
		])

    # Compute Eigenvalues
    camino_eigenvectors = pe.Node(interface=camino.ComputeEigensystem(),name='camino_eigenvectors')
    if config.model_type == 'Single-Tensor' or config.model_type == 'Other models':
        camino_eigenvectors.inputs.inputmodel = 'dt'
    else:
        camino_eigenvectors.inputs.inputmodel = 'multitensor'
        if config.model_type == 'Three-Tensor':
            camino_eigenvectors.inputs.maxcomponents = 3
        elif config.model_type == 'Two-Tensor':
            camino_eigenvectors.inputs.maxcomponents = 2

    flow.connect([
		(camino_ModelFit,camino_eigenvectors,[('fitted_data','in_file')]),
		(camino_eigenvectors,outputnode,[('eigen','eigVec')])
		])
    return flow

def create_fsl_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion_resampled","wm_mask_resampled"]),name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["phsamples","fsamples","thsamples"],mandatory_inputs=True),name="outputnode")
    
    # Flip gradient table
    flip_table = pe.Node(interface=flipTable(),name='flip_table')
    flip_table.inputs.table = config.b_vectors
    flip_table.inputs.flipping_axis = config.flip_table_axis
    flip_table.inputs.delimiter = ' '
    flip_table.inputs.header_lines = 0
    flip_table.inputs.orientation = 'h'
    
    fsl_node = pe.Node(interface=fsl.BEDPOSTX(),name='BEDPOSTX')
    
    fsl_node.inputs.bvals = config.b_values
    fsl_node.inputs.burn_period = config.burn_period
    fsl_node.inputs.fibres = config.fibres_per_voxel
    fsl_node.inputs.jumps = config.jumps
    fsl_node.inputs.sampling = config.sampling
    fsl_node.inputs.weight = config.weight
    
    flow.connect([
                (inputnode,fsl_node,[("diffusion_resampled","dwi")]),
                (inputnode,fsl_node,[("wm_mask_resampled","mask")]),
                (flip_table,fsl_node,[("table","bvecs")]),
                (fsl_node,outputnode,[("merged_fsamples","fsamples")]),
                (fsl_node,outputnode,[("merged_phsamples","phsamples")]),
                (fsl_node,outputnode,[("merged_thsamples","thsamples")]),
                ])
    
    return flow

class MITKqball_commandInputSpec(CommandLineInputSpec):
    in_file = File(argstr="-i %s",position = 1,mandatory=True,exists=True,desc="input raw dwi (.dwi or .fsl/.fslgz)")
    out_file_name = String(argstr="-o %s",position=2,desc='output fiber name (.dti)')
    sh_order = Int(argstr="-sh %d", position=3,des='spherical harmonics order (optional), (default: 4)')
    reg_lambda = Float(argstr="-r %0.4f", position=4, desc='ragularization factor lambda (optional), (default: 0.006)')
    csa = Bool(argstr="-csa", position=5, desc='use constant solid angle consideration (optional)')

class MITKqball_commandOutputSpec(TraitedSpec):
    out_file = File(exists=True,desc='output tensor file')

class MITKqball(CommandLine):
    _cmd = 'MitkQballReconstruction.sh'
    input_spec = MITKqball_commandInputSpec
    output_spec = MITKqball_commandOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = self.inputs.out_file_name
        return outputs
    
class MITKtensor_commandInputSpec(CommandLineInputSpec):
    in_file = File(argstr="-i %s",position = 1,mandatory=True,exists=True,desc="input raw dwi (.dwi or .fsl/.fslgz)")
    out_file_name = String(argstr="-o %s",position=2,desc='output fiber name (.dti)')

class MITKtensor_commandOutputSpec(TraitedSpec):
    out_file = File(exists=True,desc='output tensor file')

class MITKtensor(CommandLine):
    _cmd = 'MitkTensorReconstruction.sh'
    input_spec = MITKtensor_commandInputSpec
    output_spec = MITKtensor_commandOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = self.inputs.out_file_name
        return outputs
    
class gibbs_reconInputSpec(BaseInterfaceInputSpec):

    dwi = File(exists=True)
    bvals = File(exists=True)
    bvecs = File(exists=True)
    recon_model = Enum(['Tensor','CSD'])
    sh_order = Int(argstr="-sh %d", position=3,des='spherical harmonics order (optional), (default: 4)')
    reg_lambda = Float(argstr="-t %0.4f", position=4, desc='ragularization factor lambda (optional), (default: 0.006)')
    csa = Bool(argstr="-csa", position=5, desc='use constant solid angle consideration (optional)')

class gibbs_reconOutputSpec(TraitedSpec):
    recon_file = File(exists=True)

class gibbs_recon(BaseInterface):
    input_spec = gibbs_reconInputSpec
    output_spec = gibbs_reconOutputSpec

    def _run_interface(self,runtime):
        # change DWI and gradient table names
        mitk_dwi = os.path.abspath(os.path.basename(self.inputs.dwi)+'.fsl')
        shutil.copyfile(self.inputs.dwi,mitk_dwi)
        mitk_bvec = os.path.abspath(os.path.basename(self.inputs.dwi)+'.fsl.bvecs')
        shutil.copyfile(self.inputs.bvecs,mitk_bvec)
        mitk_bval = os.path.abspath(os.path.basename(self.inputs.dwi)+'.fsl.bvals')
        shutil.copyfile(self.inputs.bvals,mitk_bval)
        if self.inputs.recon_model == 'Tensor':
            tensor = pe.Node(interface=MITKtensor(in_file = mitk_dwi, out_file_name = os.path.abspath('mitk_tensor.dti')),name="mitk_tensor")
            res = tensor.run()
        elif self.inputs.recon_model == 'CSD':
            csd = pe.Node(interface=MITKqball(),name='mitk_CSD')
            csd.inputs.in_file = mitk_dwi
            csd.inputs.out_file_name = os.path.abspath('mitk_qball.qbi')
            csd.inputs.sh_order = self.inputs.sh_order
            csd.inputs.reg_lambda = self.inputs.reg_lambda
            csd.inputs.csa = self.inputs.csa
            res = csd.run()
            
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        if self.inputs.recon_model == 'Tensor':
            outputs["recon_file"] = os.path.abspath('mitk_tensor.dti')
        elif self.inputs.recon_model == 'CSD':
            outputs["recon_file"] = os.path.abspath('mitk_qball.qbi')
        return outputs
    
def create_gibbs_recon_flow(config):
    flow = pe.Workflow(name="reconstruction")
    
    inputnode = pe.Node(interface=util.IdentityInterface(fields=["diffusion_resampled"]),name="inputnode")
    outputnode = pe.Node(interface=util.IdentityInterface(fields=["recon_file"],mandatory_inputs=True),name="outputnode")
    
    # Flip gradient table
    flip_table = pe.Node(interface=flipTable(),name='flip_table')
    flip_table.inputs.table = config.b_vectors
    flip_table.inputs.flipping_axis = config.flip_table_axis
    flip_table.inputs.delimiter = ' '
    flip_table.inputs.header_lines = 0
    flip_table.inputs.orientation = 'h'
    
    gibbs_node = pe.Node(interface=gibbs_recon(),name='gibbs_reconstruction')
    gibbs_node.inputs.bvals = config.b_values
    gibbs_node.inputs.recon_model = config.recon_model
    gibbs_node.inputs.sh_order = config.sh_order
    gibbs_node.inputs.reg_lambda = config.reg_lambda
    gibbs_node.inputs.csa = config.csa
    
    flow.connect([
                  (flip_table,gibbs_node,[("table","bvecs")]),
                  (inputnode,gibbs_node,[("diffusion_resampled","dwi")]),
                  (gibbs_node,outputnode,[("recon_file","recon_file")])
                ])
    return flow