
try: 
	from traits.api import *
except ImportError: 
	from enthought.traits.api import *
try: 
	from traitsui.api import *
except ImportError: 
	from enthought.traits.ui.api import *
from cmp.stages.common import CMP_Stage

class Preprocessing_Config(HasTraits):
	process_type = Enum('Diffusion',['Diffusion'])
	
class Preprocessing(CMP_Stage):
	# General and UI members
	name = 'Preprocessing'
	description = 'Preprocessing stage, converts (if needed) the raw data to nifti file formats and checks if any input is missing.'
	display_color = 'lightgray'
	position_x = 170
	position_y = 410
	config = Preprocessing_Config()	
		
		
	#def create_workflow(self):
		#flow = pe.Workflow(name="CMP_Parcellation")
		
		#input_node = pe.Node(interface=util.IdentityInterface(fields=["aparc+aseg"]),name="inputnode")

		#if self.config.parcellation_scheme == 'NativeFreesurfer':
		#	...
			
		#output_node = pe.Node(interface=util.IdentityInterface(fields=["WM_mask_1mm","GM_masks_1mm"]),name="outputnode")
		
		#flow.connect([(inputnode,...[(...,...),...]),...])
		
		#return flow
	
