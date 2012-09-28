
import re
import os

from enthought.traits.api import *
from enthought.traits.ui.api import *
from cmp.stages.common import CMP_Stage
import cmp.DTB_nipype

import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl

class Diffusion_Config(HasTraits):
	imaging_model_choices = List(['No diffusion input'])
	imaging_model = List(editor = CheckListEditor(name='imaging_model_choices'))
	maximum_b_value = Int(1000)
	gradient_table = Enum('siemens_06',['mgh_dti_006','mgh_dti_018','mgh_dti_030','mgh_dti_042','mgh_dti_060','mgh_dti_072','mgh_dti_090','mgh_dti_120','mgh_dti_144',
								'siemens_06','siemens_12','siemens_20','siemens_30','siemens_64','siemens_256'])
	#dsi_number_of_directions = Enum('514',['514','257','124'])
	dsi_number_of_directions = Int(514)
	#number_of_directions = Property(Int,depends_on=['imaging_model','dsi_number_of_directions','gradient_table'])
	number_of_directions = Int()
	number_of_output_directions = Int(181)
	multiple_high_b_values = Bool(False)
	number_of_b0_volumes = Int(1)
	#recon_matrix_file = Property(Str('DSI_matrix_515dx181.dat'),depends_on='dsi_number_of_directions')
	recon_matrix_file = Str('DSI_matrix_515x181.dat')
	apply_gradient_orientation_correction = Bool(True)
	
	angle_threshold = Int(60)	
	
	apply_spline_filter = Bool(True)
	
	number_of_averages = Int(3)
	mask1_threshold_auto = Bool(True)
	mask1_threshold = List([0.0,1.0])
	mask1_input = Enum('DWI',['B0','DWI'])
	#oblique_correction = Bool(False)

	traits_view = View('imaging_model',
						Group(
							Item('maximum_b_value',visible_when='imaging_model=="DTI"'),Item('gradient_table',visible_when='imaging_model!="DSI"'),
							Item('dsi_number_of_directions',visible_when='imaging_model=="DSI"'),
							Item('number_of_directions',visible_when='imaging_model!="DSI"',style='readonly'),
							Item('number_of_averages',visible_when='imaging_model=="DTI"'),
							Item('multiple_high_b_values',visible_when='imaging_model=="DTI"'),
							'number_of_b0_volumes',Item('apply_gradient_orientation_correction',visible_when='imaging_model!="DSI"'),
							label='Reconstruction',show_border=True, visible_when='imaging_model!="No diffusion input"'),
						Group(
							'mask1_input',
							'angle_threshold','mask1_threshold_auto',Item('mask1_threshold',enabled_when='mask1_threshold_auto==False'),
							label='Tracking',show_border=True),
						'apply_spline_filter',
						)
	def _get_recon_matrix_file(self):
		mat_file =  'DSI_matrix_%(n_directions)dx181.dat' % {'n_directions':int(self.dsi_number_of_directions)+1}
		return mat_file

	def _get_number_of_directions(self):
		if self.imaging_model == 'DSI':
			return self.dsi_number_of_directions
		else:
			return int(re.search('\d+',self.gradient_table).group(0))
			
			
def strip_suffix(file_input, prefix):
	import os
	from nipype.utils.filemanip import split_filename
	path, _, _ = split_filename(file_input)
	return os.path.join(path, prefix+'_')
	
class Diffusion(CMP_Stage):
	name = 'Diffusion'
	display_color = 'pink'
	position_x = 295
	position_y = 320
	config = Diffusion_Config()
	
	
		
	def create_workflow(self):
		flow = pe.Workflow(name="Diffusion_stage")
		
		# inputnode
		inputnode = pe.Node(interface=util.IdentityInterface(fields=["DSI","DTI","HARDI"]),name="inputnode")
		
		# resampling to 2x2x2m3 and setting output type to short
		fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii',out_datatype='short',vox_size=(2,2,2),out_file='diffusion_resampled.nii'),name="fs_mriconvert")
		
		if True:#self.config.imaging_model == 'DSI':
			prefix = 'dsi'
		
			dtk_recon = pe.Node(interface=dtk.ODFRecon(dsi=True, out_prefix=prefix),name='dtk_recon')
			dtk_recon.inputs.matrix = os.path.join(os.environ['DSI_PATH'],self.config.recon_matrix_file)
			dtk_recon.inputs.n_b0 = self.config.number_of_b0_volumes
			dtk_recon.inputs.n_directions = int(self.config.dsi_number_of_directions)+1
			dtk_recon.inputs.n_output_directions = self.config.number_of_output_directions
			
			dtb_gfa = pe.Node(interface=cmp.DTB_nipype.DTB_gfa(moment=2),name='dtb_gfa')
			dtb_skewness = pe.Node(interface=cmp.DTB_nipype.DTB_gfa(moment=3),name='dtb_skewness')
			dtb_curtosis = pe.Node(interface=cmp.DTB_nipype.DTB_gfa(moment=4),name='dtb_curtosis')
			dtb_p0 = pe.Node(interface=cmp.DTB_nipype.DTB_P0(),name='dtb_p0')
			
			
			flow.connect([
						(inputnode,fs_mriconvert,[('DSI','in_file')]),
						(fs_mriconvert,dtk_recon,[('out_file','DWI')]),
						(dtk_recon,dtb_gfa,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
						(dtk_recon,dtb_skewness,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
						(dtk_recon,dtb_curtosis,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
						(inputnode,dtb_p0,[('DSI','dwi_file')]),
						(dtk_recon,dtb_p0,[(('ODF',strip_suffix,prefix),'dsi_basepath')]),
						])

		#if self.config.parcellation_scheme == 'NativeFreesurfer':
		#	...
			
		#output_node = pe.Node(interface=util.IdentityInterface(fields=["WM_mask_1mm","GM_masks_1mm"]),name="outputnode")
		
		#flow.connect([(inputnode,...[(...,...),...]),...])
		
		return flow
	
