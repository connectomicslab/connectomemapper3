
from enthought.traits.api import *
from enthought.traits.ui.api import *
import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine

from cmp.stages.common import CMP_Stage

class CMP_Parcellation_Config(HasTraits):
	parcellation_scheme = Enum('Lausanne2008',['NativeFreesurfer','Lausanne2008'])
	#parcellation = Property(List,depends_on='parcellation_scheme')
	parcellation_options_trait = List(['resolution83', 'resolution150', 'resolution258', 'resolution500', 'resolution1015'])
	parcellation = List(editor = CheckListEditor(name='parcellation_options_trait'))

	traits_view = View('parcellation_scheme',Item('parcellation',style='custom'),height=300)
	
	def _parcellation_scheme_changed(self, old, new):
		if new == 'NativeFreesurfer':
			self.parcellation_options_trait = ['freesurferaparc']
		if self.parcellation_scheme == 'Lausanne2008':
			self.parcellation_options_trait = ['resolution83', 'resolution150', 'resolution258', 'resolution500', 'resolution1015']
			

	#def _get_parcellation(self):
	#	if self.parcellation_scheme == 'NativeFreesurfer':
	#		return ['freesurferaparc']
	#	if self.parcellation_scheme == 'Lausanne2008':
	#		return ['resolution83', 'resolution150', 'resolution258', 'resolution500', 'resolution1015']
	
class Parcellation(CMP_Stage):
	name = 'Parcellation'
	display_color = 'lightyellow'
	position_x = 45
	position_y = 230
	config = CMP_Parcellation_Config()
	
		
	#def create_workflow(self):
		#flow = pe.Workflow(name="CMP_Parcellation")
		
		#input_node = pe.Node(interface=util.IdentityInterface(fields=["aparc+aseg"]),name="inputnode")

		#if self.config.parcellation_scheme == 'NativeFreesurfer':
		#	...
			
		#output_node = pe.Node(interface=util.IdentityInterface(fields=["WM_mask_1mm","GM_masks_1mm"]),name="outputnode")
		
		#flow.connect([(inputnode,...[(...,...),...]),...])
		
		#return flow
	
