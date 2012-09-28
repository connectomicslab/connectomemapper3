# Main UI class implementing the UI worker functions and general project interface.
#

# Libraries imports
from enthought.traits.api import *
from enthought.traits.ui.api import *
import subprocess
from enable.api import Canvas
from enable.label import Label as EnableLabel
from enthought.enable.component_editor import ComponentEditor

# CMP imports
from stages.common import CMP_Stage
import project

# Visual elements configuration

# Size of the canvas
canvas_height = 500
canvas_width = 500

# Size of each stage element
stage_width = 160
stage_height = 50

##	Class implementing a Label from the Enable library	
#	
class CMP_Stage_Label(EnableLabel):
	stage = Instance(CMP_Stage)

	def normal_left_down(self, event):
		self.stage.configure_traits()
		event.handled = True
		return

##	Class implementing a Canvas from the Enable library.
#
class CMP_Pipeline_Canvas(Canvas):
	def init_stage_labels(self,stages):
		for stage in stages.values():
			label = CMP_Stage_Label(bounds=[stage_width, stage_height],position=[stage.position_x,stage.position_y],
										text=stage.name,bgcolor=stage.display_color,
										font="Liberation Sans 14",hjustify='center',vjustify='center')
			label.stage = stage
			self.add(label)
	
class CMP_Project_Info(HasTraits):
	base_directory = Directory
	process_type = Enum('Diffusion',['Diffusion'])
	last_date_processed = Str('Not yet processed')
	last_stage_processed = Str('Not yet processed')
	
	stages = Dict
	input_folders = List(Str)

	create_view = View( Item('process_type',style='custom'),
						'base_directory',
	 					title='Select type of pipeline and base directory for new Project',
	 					kind='modal',
	 					width=400,
	 					buttons=['OK','Cancel'])
	 					
	open_view = View('base_directory',
	 					title='Select directory of existing Project',
	 					kind='modal',
	 					width=400,
	 					buttons=['OK','Cancel'])
	 					
	traits_view = View(Group(
							Group(
								Item('base_directory',enabled_when='1>2',show_label=False),
								label='Base directory',
							),
							Group(
								Item('process_type',style='readonly'),
								Item('last_date_processed',style='readonly'),
								Item('last_stage_processed',style='readonly'),
								label='Last processing'
							),
						),
						width=200,
						)
	
## Main window class of the ConnectomeMapper_Pipeline
#
class CMP_MainWindow(HasTraits):
	canvas = CMP_Pipeline_Canvas()
	project_info = Instance(CMP_Project_Info)
	
	new_project = Action(name='New Project...',action='new_project')
	load_project = Action(name='Load Project...',action='load_project')
	preprocessing = Action(name='Preprocessing',action='preprocessing',enabled_when='handler.project_loaded==True')
	map_connectome = Action(name='Map Connectome!',action='map_connectome',enabled_when='handler.inputs_checked==True')

	traits_view = View(HGroup(
							Item('canvas',height=canvas_height,width=canvas_width,editor=ComponentEditor(),show_label=False),
							Item('project_info',style='custom',show_label=False,width=300),
							show_labels=False,
							),
						
						title='Connectome Mapper',
						menubar=MenuBar(Menu(
									ActionGroup(
										new_project,
										load_project,
										Action(name='Save Project as...',action='_save_project'),
									),
									ActionGroup(
										Action(name='Quit',action='_on_close'),
									),
									name='File'),
								Menu(
									Action(name='Save configuration as...',action='_save_config'),
									Action(name='Load configuration...',action='_load_config'),
									name='Configuration'),
								),
						handler = project.ProjectHandler(),
						buttons = [preprocessing, map_connectome],
						)
						
	

