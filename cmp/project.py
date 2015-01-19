# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper Controler for handling GUI and non GUI general events
""" 

# Global imports
from traits.api import *
from traitsui.api import *
import shutil
import os
import glob
import fnmatch
import gui
import ConfigParser
from pyface.api import FileDialog, OK

# Own imports
import pipelines.diffusion.diffusion as diffusion_pipeline
import pipelines.functional.functional as fMRI_pipeline

def get_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    #print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.config_file)
    return config.get(section, detail)

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
                
    config.add_section('Multi-processing')
    config.set('Multi-processing','number_of_cores',pipeline.number_of_cores)

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
                    try:
                        conf_value = config.get(stage.name, key+'.'+sub_key)
                        try:
                            conf_value = eval(conf_value)
                        except:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except:
                        pass
            else:
                try:
                    conf_value = config.get(stage.name, key)
                    try:
                        conf_value = eval(conf_value)
                    except:
                        pass
                    setattr(stage.config, key, conf_value)
                except:
                    pass
    setattr(pipeline,'number_of_cores',int(config.get('Multi-processing','number_of_cores')))

    return True

## Creates (if needed) the folder hierarchy
#
def refresh_folder(base_directory, input_folders):
    paths = ['FREESURFER','RESULTS','LOG','NIFTI','RAWDATA','STATS','NIPYPE']

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
    
    if project_info.process_type == 'diffusion':
        pipeline = diffusion_pipeline.DiffusionPipeline(project_info)
    elif project_info.process_type == 'fMRI':
        pipeline = fMRI_pipeline.fMRIPipeline(project_info)

    if is_new_project and pipeline!= None:
        project_info.config_file = os.path.join(project_info.base_directory,'%s_config.ini' % pipeline.global_conf.process_type)
        if os.path.exists(project_info.config_file):
            warn_res = project_info.configure_traits(view='warning_view')
            if warn_res:
                save_config(pipeline, project_info.config_file)
            else:
                return None
        else:
            save_config(pipeline, project_info.config_file)
    else:
        conf_loaded = load_config(pipeline, project_info.config_file)
        if not conf_loaded:
            return None

    refresh_folder(project_info.base_directory, pipeline.input_folders)
    pipeline.config_file = project_info.config_file
    return pipeline
    
def update_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.base_directory,'RESULTS',pipeline.global_conf.imaging_model)):
        out_dirs = os.listdir(os.path.join(project_info.base_directory,'RESULTS',pipeline.global_conf.imaging_model))
        for out in out_dirs:
            if (project_info.last_date_processed == "Not yet processed" or 
                out > project_info.last_date_processed):
                pipeline.last_date_processed = out
                project_info.last_date_processed = out
                
    # last stage
    if os.path.exists(os.path.join(project_info.base_directory,'NIPYPE',project_info.process_type+'_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(os.path.join(project_info.base_directory,'NIPYPE')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower()+'_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.last_stage_processed = stage
    

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
                # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                ui_info.ui.context["object"].project_info = new_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                self.project_loaded = True

    def load_project(self, ui_info ):
        loaded_project = gui.CMP_Project_Info()
        np_res = loaded_project.configure_traits(view='open_view')
        if np_res and os.path.exists(loaded_project.base_directory):
            # Retrocompatibility with v2.1.0 where only one config.ini file was created
            if os.path.exists(os.path.join(loaded_project.base_directory,'config.ini')):
                loaded_project.config_file = os.path.join(loaded_project.base_directory,'config.ini')
            # Load new format: <process_type>_config.ini
            else:
                loaded_project.available_config = [os.path.basename(s)[:-11] for s in glob.glob(os.path.join(loaded_project.base_directory,'*_config.ini'))]
                if len(loaded_project.available_config) > 1:
                    loaded_project.config_to_load = loaded_project.available_config[0]
                    config_selected = loaded_project.configure_traits(view='select_config_to_load')
                    if not config_selected:
                        return 0
                else:
                    loaded_project.config_to_load = loaded_project.available_config[0]
                loaded_project.config_file = os.path.join(loaded_project.base_directory,'%s_config.ini' % loaded_project.config_to_load)
            
            loaded_project.process_type = get_process_detail(loaded_project,'Global','process_type')
            loaded_project.imaging_model = get_process_detail(loaded_project,'Global','imaging_model')
            self.pipeline = init_project(loaded_project, False)
            if self.pipeline != None:
                update_last_processed(loaded_project, self.pipeline)
                ui_info.ui.context["object"].project_info = loaded_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                self.project_loaded = True
                # Move old to new config filename format
                if os.path.exists(os.path.join(loaded_project.base_directory,'config.ini')):
                    loaded_project.config_file = '%s_config.ini' % get_process_detail(loaded_project,'Global','process_type')
                    os.remove(os.path.join(loaded_project.base_directory,'config.ini'))
                    save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)

    def check_input(self, ui_info):
        self.inputs_checked = self.pipeline.check_input()
        if self.inputs_checked:
            save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)

    def map_connectome(self, ui_info):
        ui_info.ui.context["object"].project_info.config_error_msg = self.pipeline.check_config()
        if ui_info.ui.context["object"].project_info.config_error_msg != '':
            ui_info.ui.context["object"].project_info.configure_traits(view='config_error_view')
        else:
            save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)
            self.pipeline.launch_process()
            self.pipeline.launch_progress_window()
            update_last_processed(ui_info.ui.context["object"].project_info, self.pipeline)
        
    def map_custom(self, ui_info):
        if ui_info.ui.context["object"].project_info.custom_last_stage == '':
            ui_info.ui.context["object"].project_info.custom_last_stage = self.pipeline.ordered_stage_list[0]
        ui_info.ui.context["object"].project_info.stage_names = self.pipeline.ordered_stage_list
        cus_res = ui_info.ui.context["object"].project_info.configure_traits(view='custom_map_view')
        if cus_res:
            self.pipeline.define_custom_mapping(ui_info.ui.context["object"].project_info.custom_last_stage)
            
    def save_config_file(self, ui_info):
        dialog = FileDialog(action="save as", default_filename="config.ini")
        dialog.open()
        if dialog.return_code == OK:
            save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.config_file:
                shutil.copy(ui_info.ui.context["object"].project_info.config_file, dialog.path)
    
    def load_config_file(self, ui_info):
        dialog = FileDialog(action="open", wildcard="*.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.config_file:
                shutil.copy(dialog.path, ui_info.ui.context["object"].project_info.config_file)
            load_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)

