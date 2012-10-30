# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper Controler for handling GUI and non GUI general events
""" 

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
import pipelines.diffusion.diffusion as diffusion_pipeline

def get_process_type(project_info):
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(project_info.base_directory, 'config.ini'))
    return config.get('Global','process_type')

def save_config(pipeline, config_path):
    config = ConfigParser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if not 'trait' in prop] # possibly dangerous..?
    for key in global_keys:
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in pipeline.stages.values():
        config.add_section(stage.name)
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop] # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key: # subconfig
                stage_sub_keys = [prop for prop in keyval.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key+'.'+sub_key, getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)

    with open(config_path, 'wb') as configfile:
        config.write(configfile)

def load_config(pipeline, config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if not 'trait' in prop] # possibly dangerous..?
    for key in global_keys:
        conf_value = config.get('Global', key)
        setattr(pipeline.global_conf, key, conf_value)
    for stage in pipeline.stages.values():
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop] # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key: #subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in sub_config.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    conf_value = config.get(stage.name, key+'.'+sub_key)
                    try:
                        conf_value = eval(conf_value)
                    except:
                        pass
                    setattr(sub_config, sub_key, conf_value)
            else:
                conf_value = config.get(stage.name, key)
                try:
                    conf_value = eval(conf_value)
                except:
                    pass
                setattr(stage.config, key, conf_value)

    return True

## Creates (if needed) the folder hierarchy
#
def refresh_folder(base_directory, input_folders):
    paths = ['RESULTS','FREESURFER','LOG','NIFTI','RAWDATA','STATS','NIPYPE']

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

def init_project(project_info, is_new_project):
    pipeline = None
    
    if project_info.process_type == 'Diffusion':
        pipeline = diffusion_pipeline.Pipeline(base_directory=project_info.base_directory)

    if is_new_project and pipeline!= None:
        project_info.config_file = os.path.join(project_info.base_directory,'config.ini')
        save_config(pipeline, project_info.config_file)
    else:
        conf_loaded = load_config(pipeline, project_info.config_file)
        if not conf_loaded:
            return None

    refresh_folder(project_info.base_directory, pipeline.input_folders)
    return pipeline

class ProjectHandler(Handler):
    pipeline = Instance(HasTraits)
    project_loaded = Bool(False)
    inputs_checked = Bool(False)

    def new_project(self, ui_info ):
        new_project = gui.CMP_Project_Info()
        np_res = new_project.configure_traits(view='create_view')
        if np_res and os.path.exists(new_project.base_directory):
            self.pipeline = init_project(new_project, True)
            if self.pipeline != None:
                ui_info.ui.context["object"].project_info = new_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                self.project_loaded = True

    def load_project(self, ui_info ):
        loaded_project = gui.CMP_Project_Info()
        np_res = loaded_project.configure_traits(view='open_view')
        if np_res and os.path.exists(loaded_project.base_directory):
            loaded_project.process_type = get_process_type(loaded_project)
            loaded_project.config_file = os.path.join(loaded_project.base_directory,'config.ini')
#           self.project_loaded = init_project(loaded_project, ui_info.ui.context["object"].canvas, False)
            self.pipeline = init_project(loaded_project, False)
            if self.pipeline != None:
                ui_info.ui.context["object"].project_info = loaded_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                self.project_loaded = True

    def check_input(self, ui_info):
        self.inputs_checked = self.pipeline.check_input()
        if self.inputs_checked:
            save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)

    def map_connectome(self, ui_info):
        save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)
        self.pipeline.process()
        
    def map_custom(self, ui_info):
        cus_res = ui_info.ui.context["object"].project_info.stage_names = self.pipeline.ordered_stage_list
        cus_res = ui_info.ui.context["object"].project_info.configure_traits(view='custom_map_view')
        if cus_res:
            self.pipeline.define_custom_mapping(ui_info.ui.context["object"].project_info.custom_map_stop)


