
from enthought.traits.api import *
from enthought.traits.ui.api import *
from cmp.stages.common import CMP_Stage

class Registration_Config(HasTraits):
	registration_mode = Enum('Linear','Nonlinear','BBregister')
	
class Registration(CMP_Stage):
	name = 'Registration'
	display_color = 'lightgreen'
	position_x = 170
	position_y = 140
	config = Registration_Config()
	
		
	#def create_workflow(self):
		#flow = pe.Workflow(name="CMP_Parcellation")
		
		#input_node = pe.Node(interface=util.IdentityInterface(fields=["aparc+aseg"]),name="inputnode")

		#if self.config.parcellation_scheme == 'NativeFreesurfer':
		#	...
			
		#output_node = pe.Node(interface=util.IdentityInterface(fields=["WM_mask_1mm","GM_masks_1mm"]),name="outputnode")
		
		#flow.connect([(inputnode,...[(...,...),...]),...])
		
		#return flow
	
