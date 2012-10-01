
try: 
	from traits.api import *
	from traitsui.api import *
except ImportError: 
	from enthought.traits.api import *
	from enthought.traits.ui.api import *
from cmp.stages.common import CMP_Stage

class Segmentation_Config(HasTraits):
	pass
	#process_type = Enum('Diffusion',['Diffusion'])
	
class Segmentation(CMP_Stage):
	# General and UI members
	name = 'Segmentation'
	display_color = 'lightyellow'
	position_x = 45
	position_y = 320
	config = Segmentation_Config()
	
		
	#def create_workflow(self):
		#flow = pe.Workflow(name="CMP_Parcellation")
		
		#input_node = pe.Node(interface=util.IdentityInterface(fields=["aparc+aseg"]),name="inputnode")

		#if self.config.parcellation_scheme == 'NativeFreesurfer':
		#	...
			
		#output_node = pe.Node(interface=util.IdentityInterface(fields=["WM_mask_1mm","GM_masks_1mm"]),name="outputnode")
		
		#flow.connect([(inputnode,...[(...,...),...]),...])
		
		#return flow
	
