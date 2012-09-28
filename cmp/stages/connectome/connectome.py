
from enthought.traits.api import *
from enthought.traits.ui.api import *
from cmp.stages.common import CMP_Stage

class Connectome_Config(HasTraits):
	cff_creator = Str
	cff_email = Str
	cff_publisher = Str
	cff_license = Str
	
	traits_view = View(Group('cff_creator','cff_email','cff_publisher','cff_license',
						label='CFF creation metadata'
						),
						)
	
class Connectome(CMP_Stage):
	name = 'Connectome'
	display_color = 'mediumpurple'
	position_x = 170
	position_y = 50
	config = Connectome_Config()
	
		
	#def create_workflow(self):
		#flow = pe.Workflow(name="CMP_Parcellation")
		
		#input_node = pe.Node(interface=util.IdentityInterface(fields=["aparc+aseg"]),name="inputnode")

		#if self.config.parcellation_scheme == 'NativeFreesurfer':
		#	...
			
		#output_node = pe.Node(interface=util.IdentityInterface(fields=["WM_mask_1mm","GM_masks_1mm"]),name="outputnode")
		
		#flow.connect([(inputnode,...[(...,...),...]),...])
		
		#return flow
	
