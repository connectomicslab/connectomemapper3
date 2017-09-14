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

from bids.grabbids import BIDSLayout

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
        #if key != "subject" and key != "subjects":
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
        if key != "subject" and key != "subjects":
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
def refresh_folder(derivatives_directory, subject, input_folders):
    paths = []

    paths.append(os.path.join(derivatives_directory,'freesurfer',subject))
    paths.append(os.path.join(derivatives_directory,'cmp',subject))

    for in_f in input_folders:
        paths.append(os.path.join(derivatives_directory,'cmp',subject,in_f))

    paths.append(os.path.join(derivatives_directory,'cmp',subject,'tmp','nipype'))

    for full_p in paths:
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

    derivatives_directory = os.path.join(project_info.base_directory,'derivatives')

    if is_new_project and pipeline!= None:
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print "%s was already existing" % derivatives_directory
            finally:
                print "Created directory %s" % derivatives_directory

        project_info.config_file = os.path.join(derivatives_directory,'%s_%s_config.ini' % (project_info.subject,pipeline.global_conf.process_type))
        if os.path.exists(project_info.config_file):
            warn_res = project_info.configure_traits(view='warning_view')
            if warn_res:
                save_config(pipeline, project_info.config_file)
            else:
                return None
        else:
            save_config(pipeline, project_info.config_file)
    else:
        print "int_project pipeline.global_config.subjects : "
        print pipeline.global_conf.subjects

        conf_loaded = load_config(pipeline, project_info.config_file)

        if not conf_loaded:
            return None

    print pipeline
    refresh_folder(derivatives_directory, project_info.subject, pipeline.input_folders)
    pipeline.config_file = project_info.config_file
    return pipeline

def update_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (project_info.last_date_processed == "Not yet processed" or
            pipeline.now > project_info.last_date_processed):
            pipeline.last_date_processed = pipeline.now
            project_info.last_date_processed = pipeline.now

    # last stage
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','nipype',project_info.process_type+'_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','nipype')):
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
            try:
                bids_layout = BIDSLayout(new_project.base_directory)
                for subj in bids_layout.get_subjects():
                    new_project.subjects.append('sub-'+str(subj))
                # new_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]

                # new_project.configure_traits(subject=Enum(*subjects))
                # print new_project.subjects

                print "Default subject : "+new_project.subject
                np_res = new_project.configure_traits(view='subject_view')
                print "Selected subject : "+new_project.subject
            except:
                error(message="Invalid BIDS dataset. Please see documentation for more details.",title="BIDS error")

            self.pipeline = init_project(new_project, True)
            if self.pipeline != None:
                # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                ui_info.ui.context["object"].project_info = new_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                self.project_loaded = True


    def load_project(self, ui_info ):
        loaded_project = gui.CMP_Project_Info()
        np_res = loaded_project.configure_traits(view='open_view')

        print "Default subject : "+loaded_project.subject

        is_bids = False

        print "Base dir: %s" % loaded_project.base_directory
        try:
            bids_layout = BIDSLayout(loaded_project.base_directory)
            is_bids = True
            loaded_project.subjects = []
            for subj in bids_layout.get_subjects():
                print "sub: %s" % subj
                loaded_project.subjects.append('sub-'+str(subj))
            # loaded_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
            loaded_project.subjects.sort()
        except:
            error(message="Invalid BIDS dataset. Please see documentation for more details.",title="BIDS error")

        self.inputs_checked = False

        print loaded_project.subjects

        if np_res and os.path.exists(loaded_project.base_directory) and is_bids:
            # Retrocompatibility with v2.1.0 where only one config.ini file was created
            if os.path.exists(os.path.join(loaded_project.base_directory,'derivatives','config.ini')):
                loaded_project.config_file = os.path.join(loaded_project.base_directory,'derivatives','config.ini')
            # Load new format: <process_type>_config.ini
            else:
                loaded_project.available_config = [os.path.basename(s)[:-11] for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','*_config.ini'))]
                if len(loaded_project.available_config) > 1:
                    loaded_project.available_config.sort()
                    loaded_project.config_to_load = loaded_project.available_config[0]
                    config_selected = loaded_project.configure_traits(view='select_config_to_load')
                    if not config_selected:
                        return 0
                else:
                    loaded_project.config_to_load = loaded_project.available_config[0]

                loaded_project.subject = loaded_project.config_to_load.split("_")[0]

                print "Config to load: %s"%loaded_project.config_to_load
                loaded_project.config_file = os.path.join(loaded_project.base_directory,'derivatives','%s_config.ini' % loaded_project.config_to_load)
                print "Config file: %s"%loaded_project.config_file

            loaded_project.process_type = get_process_detail(loaded_project,'Global','process_type')
            loaded_project.diffusion_imaging_model = get_process_detail(loaded_project,'Global','diffusion_imaging_model')
            self.pipeline = init_project(loaded_project, False)
            if self.pipeline != None:
                update_last_processed(loaded_project, self.pipeline)
                ui_info.ui.context["object"].project_info = loaded_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                print "Config for subject %s loaded !"%ui_info.ui.context["object"].project_info.subject
                self.project_loaded = True
                # Move old to new config filename format
                if os.path.exists(os.path.join(loaded_project.base_directory,'derivatives','config.ini')):
                    loaded_project.config_file = '%s_config.ini' % get_process_detail(loaded_project,'Global','process_type')
                    os.remove(os.path.join(loaded_project.base_directory,'derivatives','config.ini'))
                    save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)

    def change_subject(self, ui_info):
        changed_project = ui_info.ui.context["object"].project_info


        print "BIDS directoy : %s" % changed_project.base_directory
        try:
            bids_layout = BIDSLayout(changed_project.base_directory)
            changed_project.subjects = []
            for subj in bids_layout.get_subjects():
                changed_project.subjects.append('sub-'+str(subj))
            # changed_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
            print "Subjects : %s" % changed_project.subjects

            print "Previous selected subject : %s" % changed_project.subject
            changed_project.configure_traits(view='subject_view')
            print "New selected subject : %s" % changed_project.subject
        except:
            error(message="Invalid BIDS dataset. Please see documentation for more details.",title="BIDS error")

        self.inputs_checked = False

        changed_project.config_file = os.path.join(changed_project.base_directory,'derivatives','%s_%s_config.ini' % (changed_project.subject,changed_project.process_type))

        if os.path.isfile(changed_project.config_file): # If existing config file / connectome data, load subject project

            print "Existing config file for subject %s: %s" % (changed_project.config_file, changed_project.subject)

            changed_project.process_type = get_process_detail(changed_project,'Global','process_type')
            changed_project.diffusion_imaging_model = get_process_detail(changed_project,'Global','diffusion_imaging_model')

            self.pipeline = init_project(changed_project, False)
            if self.pipeline != None:
                update_last_processed(changed_project, self.pipeline)
                ui_info.ui.context["object"].project_info = changed_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                print "Config for subject %s loaded !"%ui_info.ui.context["object"].project_info.subject
                self.project_loaded = True

        else:
            print "Not existing config file (%s) / connectome data for subject %s - Created new project" % (changed_project,changed_project.subject)
            self.pipeline = init_project(changed_project, True)
            if self.pipeline != None:
                # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                ui_info.ui.context["object"].project_info = changed_project
                ui_info.ui.context["object"].pipeline = self.pipeline
                self.project_loaded = True

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
