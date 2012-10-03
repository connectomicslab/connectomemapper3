
try: 
	from traits.api import *
except ImportError: 
	from enthought.traits.api import *
try: 
	from traitsui.api import *
except ImportError: 
	from enthought.traits.ui.api import *

import os
import gui
import ConfigParser
import pipelines.diffusion_pipeline as diffusion_pipeline

def get_process_type(project_info):
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(project_info.base_directory, 'config.ini'))
	return config.get('Preprocessing','process_type')

def save_config(project):
	config = ConfigParser.RawConfigParser()
	for stage in project.stages.values():
		config.add_section(stage.name)
		stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop] # possibly dangerous..?
		for key in stage_keys:
			config.set(stage.name, key, getattr(stage.config, key))
			
	with open(os.path.join(project.base_directory, 'config.ini'), 'wb') as configfile:
		config.write(configfile)
		
	
def load_config(project):
	config = ConfigParser.ConfigParser()
	config.read(os.path.join(project.base_directory, 'config.ini'))
	for stage in project.stages.values():
		stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop] # possibly dangerous..?
		for key in stage_keys:
			conf_value = config.get(stage.name, key)
			#if '[' in conf_value: # has to transform into list again... mmmm better way?
			#	conf_value = map(str, conf_value[1:-1].split(','))
			#if conf_value == 'True':
			#	conf_value = True
			#if conf_value == 'False':
			#	conf_value = False
			try:
				conf_value = eval(conf_value)
			except:
				pass
			
			setattr(stage.config, key, conf_value)
			
	return True
	
## Creates (if needed) the folder hierarchy
#
def refresh_folder(base_directory, input_folders):
	paths = ['CMP','FREESURFER','LOG','NIFTI','RAWDATA','STATS','NIPYPE']
	
	for in_f in input_folders:
		paths.append(os.path.join('RAWDATA',in_f))
		
	for p in paths:
		full_p = os.path.join(base_directory,p)
		if not os.path.exists(full_p):
			try:
				os.makedirs(full_p)
			except os.error:
				print "%s was already existing" % full_p
			finally:
				print "Created directory %s" % full_p
		
def init_project(project, canvas, is_new_project):
	if project.process_type == 'Diffusion':
		project.process_callback = diffusion_pipeline.process
		project.input_folders = ['DSI','DTI','HARDI','T1','T2']
		project.stages = diffusion_pipeline.get_stages()
		canvas.init_stage_labels(project.stages)
		
	if is_new_project:
		save_config(project)
	else:
		conf_loaded = load_config(project)
		if not conf_loaded:
			return False
		
	refresh_folder(project.base_directory, project.input_folders)
	return True
						
class ProjectHandler(Handler):
	project_loaded = Bool(False)
	inputs_checked = Bool(False)
	
	def new_project(self, ui_info ):
		new_project = gui.CMP_Project_Info()
		np_res = new_project.configure_traits(view='create_view')
		if np_res and os.path.exists(new_project.base_directory):
			self.project_loaded = init_project(new_project, ui_info.ui.context["object"].canvas, True)
			if self.project_loaded:
				ui_info.ui.context["object"].project_info = new_project
				
	def load_project(self, ui_info ):
		loaded_project = gui.CMP_Project_Info()
		np_res = loaded_project.configure_traits(view='open_view')
		if np_res and os.path.exists(loaded_project.base_directory):
			loaded_project.process_type = get_process_type(loaded_project)
			self.project_loaded = init_project(loaded_project, ui_info.ui.context["object"].canvas, False)
			if self.project_loaded:
				ui_info.ui.context["object"].project_info = loaded_project
				
	def preprocessing(self, ui_info):
		if ui_info.ui.context["object"].project_info.process_type == 'Diffusion':
			[pre_ok, pre_message] = diffusion_pipeline.preprocess(ui_info.ui.context["object"].project_info)
		
		self.inputs_checked = True
		print pre_message
		#preprocessing = ui_info.ui.context["object"].project_info
		#if project.process_type == 'Diffusion'
	
	def map_connectome(self, ui_info):
		if ui_info.ui.context["object"].project_info.process_type == 'Diffusion':
			[proc_ok, proc_message] = diffusion_pipeline.process(ui_info.ui.context["object"].project_info)
		
