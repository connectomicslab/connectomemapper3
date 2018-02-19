# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper Controler for handling GUI and non GUI general events
"""

# Global imports
import ast
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
#import pipelines.diffusion.diffusion as Diffusion_pipeline
#import pipelines.functional.functional as FMRI_pipeline
from pipelines.diffusion import diffusion as Diffusion_pipeline
from pipelines.anatomical import anatomical as Anatomical_pipeline
#import pipelines.egg.eeg as EEG_pipeline

def get_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    #print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.config_file)
    return config.get(section, detail)

def get_anat_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    #print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.anat_config_file)
    res = None
    if detail == "atlas_info":
        res = ast.literal_eval(config.get(section, detail))
    else:
        res = config.get(section, detail)
    return res

def get_dmri_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    #print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.dmri_config_file)
    return config.get(section, detail)

def anat_save_config(pipeline, config_path):
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

def anat_load_config(pipeline, config_path):
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

def dmri_save_config(pipeline, config_path):
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

def dmri_load_config(pipeline, config_path):
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

    paths.append(os.path.join(derivatives_directory,'cmp',subject,'tmp'))

    for full_p in paths:
        if not os.path.exists(full_p):
            try:
                os.makedirs(full_p)
            except os.error:
                print "%s was already existing" % full_p
            finally:
                print "Created directory %s" % full_p

def init_dmri_project(project_info, is_new_project):
    dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(project_info)

    derivatives_directory = os.path.join(project_info.base_directory,'derivatives')

    if is_new_project and dmri_pipeline!= None: #and dmri_pipeline!= None:
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print "%s was already existing" % derivatives_directory
            finally:
                print "Created directory %s" % derivatives_directory

        project_info.dmri_config_file = os.path.join(derivatives_directory,'%s_diffusion_config.ini' % (project_info.subject))

        if os.path.exists(project_info.dmri_config_file):
            warn_res = project_info.configure_traits(view='dmri_warning_view')
            if warn_res:
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
            else:
                return None
        else:
            dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
    else:
        print "int_project dmri_pipeline.global_config.subjects : "
        print dmri_pipeline.global_conf.subjects

        dmri_conf_loaded = dmri_load_config(dmri_pipeline, project_info.dmri_config_file)

        if not dmri_conf_loaded:
            return None

    print dmri_pipeline
    refresh_folder(derivatives_directory, project_info.subject, dmri_pipeline.input_folders)
    dmri_pipeline.config_file = project_info.dmri_config_file
    return dmri_pipeline

def init_anat_project(project_info, is_new_project):
    anat_pipeline = Anatomical_pipeline.AnatomicalPipeline(project_info)
    #dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(project_info,anat_pipeline.flow)
    #fmri_pipeline = FMRI_pipeline.fMRIPipeline
    #egg_pipeline = None

    # if project_info.process_type == 'diffusion':
    #     pipeline = diffusion_pipeline.DiffusionPipeline(project_info)
    # elif project_info.process_type == 'fMRI':
    #     pipeline = fMRI_pipeline.fMRIPipeline(project_info)

    derivatives_directory = os.path.join(project_info.base_directory,'derivatives')

    if is_new_project and anat_pipeline!= None: #and dmri_pipeline!= None:
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print "%s was already existing" % derivatives_directory
            finally:
                print "Created directory %s" % derivatives_directory

        project_info.anat_config_file = os.path.join(derivatives_directory,'%s_anatomical_config.ini' % (project_info.subject))
        #project_info.dmri_config_file = os.path.join(derivatives_directory,'%s_diffusion_config.ini' % (project_info.subject))

        if os.path.exists(project_info.anat_config_file):
            warn_res = project_info.configure_traits(view='anat_warning_view')
            if warn_res:
                anat_save_config(anat_pipeline, project_info.anat_config_file)
            else:
                return None
        else:
            anat_save_config(anat_pipeline, project_info.anat_config_file)

        # if os.path.exists(project_info.dmri_config_file):
        #     warn_res = project_info.configure_traits(view='warning_view')
        #     if warn_res:
        #         save_config(dmri_pipeline, project_info.dmri_config_file)
        #     else:
        #         return None
        # else:
        #     save_config(dmri_pipeline, project_info.dmri_config_file)
    else:
        print "int_project anat_pipeline.global_config.subjects : "
        print anat_pipeline.global_conf.subjects

        anat_conf_loaded = anat_load_config(anat_pipeline, project_info.anat_config_file)
        #dmri_conf_loaded = load_config(dmri_pipeline, project_info.dmri_config_file)

        if not anat_conf_loaded:
            return None

        #if not dmri_conf_loaded:
        #    return None

    print anat_pipeline
    #print dmri_pipeline
    refresh_folder(derivatives_directory, project_info.subject, anat_pipeline.input_folders)
    #refresh_folder(derivatives_directory, project_info.subject, dmri_pipeline.input_folders)
    anat_pipeline.config_file = project_info.anat_config_file
    #dmri_pipeline.config_file = project_info.dmri_config_file
    return anat_pipeline#, dmri_pipeline

def update_anat_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (project_info.anat_last_date_processed == "Not yet processed" or
            pipeline.now > project_info.anat_last_date_processed):
            pipeline.anat_last_date_processed = pipeline.now
            project_info.anat_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','anatomical_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','anatomical_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower()+'_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.anat_last_stage_processed = stage

    # last parcellation scheme
    project_info.parcellation_scheme = pipeline.parcellation_scheme
    project_info.atlas_info = pipeline.atlas_info


def update_dmri_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out

        if (project_info.dmri_last_date_processed == "Not yet processed" or
            pipeline.now > project_info.dmri_last_date_processed):
            pipeline.dmri_last_date_processed = pipeline.now
            project_info.dmri_last_date_processed = pipeline.now

    # last stage
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','diffusion_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','diffusion_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower()+'_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage

class ProjectHandler(Handler):
    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    project_loaded = Bool(False)
    anatomical_processed = Bool(False)
    dmri_processed = Bool(False)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    dmri_inputs_checked = Bool(False)

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
                return

            self.anat_pipeline= init_anat_project(new_project, True)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input()
                if anat_inputs_checked:
                    # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = new_project
                    self.anat_pipeline.number_of_cores = new_project.number_of_cores
                    # self.anat_pipeline.flow = self.anat_pipeline.create_pipeline_flow()
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True

                    ui_info.ui.context["object"].project_info.parcellation_scheme = get_anat_process_detail(new_project,'parcellation_stage','parcellation_scheme')
                    # ui_info.ui.context["object"].project_info.atlas_info = get_anat_process_detail(new_project,'parcellation_stage','atlas_info')

                    self.dmri_pipeline= init_dmri_project(new_project, True)
                    if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                        dmri_inputs_checked = self.dmri_pipeline.check_input()
                        if dmri_inputs_checked:
                            # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                            # self.dmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                            self.dmri_pipeline.number_of_cores  = new_project.number_of_cores
                            print "number of cores (pipeline): %s" % self.dmri_pipeline.number_of_cores
                            # print "diffusion_imaging_model (pipeline): %s" % self.dmri_pipeline.diffusion_imaging_model
                            # print "diffusion_imaging_model ui_info: %s" % ui_info.ui.context["object"].project_info.diffusion_imaging_model
                            self.dmri_pipeline.parcellation_scheme = ui_info.ui.context["object"].project_info.parcellation_scheme
                            # self.dmri_pipeline.atlas_info = ui_info.ui.context["object"].project_info.atlas_info
                            ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                            #self.diffusion_ready = True
                            dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                            self.dmri_inputs_checked = dmri_inputs_checked
                            ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
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
            return

        self.anat_inputs_checked = False
        #self.dmri_inputs_checked = False

        print loaded_project.subjects

        if np_res and os.path.exists(loaded_project.base_directory) and is_bids:
            # # Retrocompatibility with v2.1.0 where only one config.ini file was created
            # if os.path.exists(os.path.join(loaded_project.base_directory,'derivatives','config.ini')):
            #     loaded_project.config_file = os.path.join(loaded_project.base_directory,'derivatives','config.ini')
            # # Load new format: <process_type>_config.ini
            # else:
            loaded_project.anat_available_config = [os.path.basename(s)[:-11] for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','*_anatomical_config.ini'))]
            if len(loaded_project.anat_available_config) > 1:
                loaded_project.anat_available_config.sort()
                loaded_project.anat_config_to_load = loaded_project.anat_available_config[0]
                anat_config_selected = loaded_project.configure_traits(view='anat_select_config_to_load')
                if not anat_config_selected:
                    return 0
            else:
                loaded_project.anat_config_to_load = loaded_project.anat_available_config[0]

            loaded_project.subject = loaded_project.anat_config_to_load.split("_")[0]

            print "Anatomical config to load: %s"%loaded_project.anat_config_to_load
            loaded_project.anat_config_file = os.path.join(loaded_project.base_directory,'derivatives','%s_config.ini' % loaded_project.anat_config_to_load)
            print "Anatomical config file: %s"%loaded_project.anat_config_file

            loaded_project.parcellation_scheme = get_anat_process_detail(loaded_project,'parcellation_stage','parcellation_scheme')
            loaded_project.atlas_info = get_anat_process_detail(loaded_project,'parcellation_stage','atlas_info')

            self.anat_pipeline= init_anat_project(loaded_project, False)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input()
                if anat_inputs_checked:
                    update_anat_last_processed(loaded_project, self.anat_pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = loaded_project
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    ui_info.ui.context["object"].anat_pipeline.number_of_cores = ui_info.ui.context["object"].project_info.number_of_cores
                    #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True
                    self.anat_outputs_checked, msg = self.anat_pipeline.check_output()
                    print "anat_outputs_checked : %s" % self.anat_outputs_checked
                    # ui_info.ui.context["object"].anat_pipeline.flow = ui_info.ui.context["object"].anat_pipeline.create_pipeline_flow()

            loaded_project.dmri_available_config = [os.path.basename(s)[:-11] for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','%s_diffusion_config.ini'%loaded_project.subject))]
            print "loaded_project.dmri_available_config:"
            print loaded_project.dmri_available_config

            if len(loaded_project.dmri_available_config) > 1:
                loaded_project.dmri_available_config.sort()
                loaded_project.dmri_config_to_load = loaded_project.dmri_available_config[0]
                dmri_config_selected = loaded_project.configure_traits(view='dmri_select_config_to_load')
                if not dmri_config_selected:
                    return 0
            else:
                loaded_project.dmri_config_to_load = loaded_project.dmri_available_config[0]

            print "Diffusion config to load: %s"%loaded_project.dmri_config_to_load
            loaded_project.dmri_config_file = os.path.join(loaded_project.base_directory,'derivatives','%s_config.ini' % loaded_project.dmri_config_to_load)
            print "Diffusion config file: %s"%loaded_project.dmri_config_file

            if os.path.isfile(loaded_project.dmri_config_file):

                loaded_project.process_type = get_dmri_process_detail(loaded_project,'Global','process_type')
                loaded_project.diffusion_imaging_model = get_dmri_process_detail(loaded_project,'Global','diffusion_imaging_model')

                self.dmri_pipeline= init_dmri_project(loaded_project, False)
                if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                    dmri_inputs_checked = self.dmri_pipeline.check_input()
                    if dmri_inputs_checked:
                        update_dmri_last_processed(loaded_project, self.dmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        self.dmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.dmri_pipeline.atlas_info = loaded_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        ui_info.ui.context["object"].dmri_pipeline.number_of_cores = ui_info.ui.context["object"].project_info.number_of_cores
                        #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        #self.diffusion_ready = True
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                        dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                        self.project_loaded = True
            else:
                self.dmri_pipeline= init_dmri_project(loaded_project, True)
                print "No existing config for diffusion pipeline found - Created new diffusion pipeline with default parameters"
                if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                    dmri_inputs_checked = self.dmri_pipeline.check_input()
                    if dmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                        # self.dmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                        self.dmri_pipeline.number_of_cores  = loaded_project.number_of_cores
                        print "number of cores (pipeline): %s" % self.dmri_pipeline.number_of_cores
                        # print "diffusion_imaging_model (pipeline): %s" % self.dmri_pipeline.diffusion_imaging_model
                        # print "diffusion_imaging_model ui_info: %s" % ui_info.ui.context["object"].project_info.diffusion_imaging_model
                        self.dmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.dmri_pipeline.atlas_info = loaded_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        #self.diffusion_ready = True
                        dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                        self.project_loaded = True


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

        self.anat_inputs_checked = False
        #self.dmri_inputs_checked = False

        changed_project.anat_config_file = os.path.join(changed_project.base_directory,'derivatives','%s_anatomical_config.ini' % (changed_project.subject))
        changed_project.dmri_config_file = os.path.join(changed_project.base_directory,'derivatives','%s_diffusion_config.ini' % (changed_project.subject))

        if os.path.isfile(changed_project.anat_config_file): # and os.path.isfile(changed_project.dmri_config_file): # If existing config file / connectome data, load subject project

            print "Existing anatomical config file for subject %s: %s" % ( changed_project.subject,changed_project.anat_config_file)

            #changed_project.process_type = get_process_detail(changed_project,'Global','process_type')
            #changed_project.diffusion_imaging_model = get_process_detail(changed_project,'Global','diffusion_imaging_model')

            #self.anat_pipeline, self.dmri_pipeline = init_project(changed_project, False)

            self.anat_pipeline= init_anat_project(changed_project, False)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input()
                if anat_inputs_checked:
                    update_anat_last_processed(changed_project, self.anat_pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = changed_project
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    ui_info.ui.context["object"].anat_pipeline.number_of_cores = ui_info.ui.context["object"].project_info.number_of_cores
                    #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True
                    print "Config loaded !"
                    self.anat_outputs_checked, msg = self.anat_pipeline.check_output()
                    print "anat_outputs_checked : %s" % self.anat_outputs_checked

            changed_project.parcellation_scheme = get_anat_process_detail(changed_project,'parcellation_stage','parcellation_scheme')
            changed_project.atlas_info = get_anat_process_detail(changed_project,'parcellation_stage','atlas_info')

            if os.path.isfile(changed_project.dmri_config_file):
                print "Existing diffusion config file for subject %s: %s" % ( changed_project.subject,changed_project.dmri_config_file)

                changed_project.process_type = get_dmri_process_detail(changed_project,'Global','process_type')
                changed_project.diffusion_imaging_model = get_dmri_process_detail(changed_project,'Global','diffusion_imaging_model')

                self.dmri_pipeline= init_dmri_project(changed_project, False)
                if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                    dmri_inputs_checked = self.dmri_pipeline.check_input()
                    if dmri_inputs_checked:
                        update_dmri_last_processed(changed_project, self.dmri_pipeline)
                        ui_info.ui.context["object"].project_info = changed_project
                        self.dmri_pipeline.parcellation_scheme = changed_project.parcellation_scheme
                        self.dmri_pipeline.atlas_info = changed_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        ui_info.ui.context["object"].dmri_pipeline.number_of_cores = ui_info.ui.context["object"].project_info.number_of_cores
                        #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        #self.diffusion_ready = True
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                        dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                        self.project_loaded = True

            else:
                print "Not existing diffusion config file (%s) for subject %s - Created new diffusion pipeline" % (changed_project,changed_project.subject)
                self.dmri_pipeline= init_dmri_project(changed_project, True)
                if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                    dmri_inputs_checked = self.dmri_pipeline.check_input()
                    if dmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = changed_project
                        # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                        # self.dmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                        self.dmri_pipeline.number_of_cores  = changed_project.number_of_cores
                        print "number of cores (pipeline): %s" % self.dmri_pipeline.number_of_cores
                        # print "diffusion_imaging_model (pipeline): %s" % self.dmri_pipeline.diffusion_imaging_model
                        # print "diffusion_imaging_model ui_info: %s" % ui_info.ui.context["object"].project_info.diffusion_imaging_model
                        self.dmri_pipeline.parcellation_scheme = changed_project.parcellation_scheme
                        self.dmri_pipeline.atlas_info = changed_project.atlas_info
                        ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                        #self.diffusion_ready = True
                        dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                        self.dmri_inputs_checked = dmri_inputs_checked
                        ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                        self.project_loaded = True

        else:
            print "Not existing anatomical config file (%s) for subject %s - Created new anatomical and diffusion pipeline" % (changed_project,changed_project.subject)
            #self.anat_pipeline, self.dmri_pipeline = init_project(changed_project, True)
            self.anat_pipeline= init_anat_project(changed_project, True)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input()
                if anat_inputs_checked:
                    # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = changed_project
                    self.anat_pipeline.number_of_cores = changed_project.number_of_cores
                    # self.anat_pipeline.flow = self.anat_pipeline.create_pipeline_flow()
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True
                    print "New anatomical pipeline created (config: %s)" % ui_info.ui.context["object"].project_info.anat_config_file

            self.dmri_pipeline= init_dmri_project(changed_project, True)
            if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                dmri_inputs_checked = self.dmri_pipeline.check_input()
                if dmri_inputs_checked:
                    ui_info.ui.context["object"].project_info = changed_project
                    # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                    # self.dmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                    self.dmri_pipeline.number_of_cores  = changed_project.number_of_cores
                    print "number of cores (pipeline): %s" % self.dmri_pipeline.number_of_cores
                    # print "diffusion_imaging_model (pipeline): %s" % self.dmri_pipeline.diffusion_imaging_model
                    # print "diffusion_imaging_model ui_info: %s" % ui_info.ui.context["object"].project_info.diffusion_imaging_model
                    self.dmri_pipeline.parcellation_scheme = changed_project.parcellation_scheme
                    self.dmri_pipeline.atlas_info = changed_project.atlas_info
                    ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    #self.diffusion_ready = True
                    dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                    self.project_loaded = True
                    print "New diffusion pipeline created (config: %s)" % ui_info.ui.context["object"].project_info.dmri_config_file

    # def check_anat_input(self, ui_info):
    #     self.anat_inputs_checked = self.anat_pipeline.check_input()
    #     if self.anat_inputs_checked:
    #         anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)

    # def check_dmri_input(self, ui_info):
    #     self.dmri_inputs_checked = self.dmri_pipeline.check_input()
    #     if self.dmri_inputs_checked:
    #         dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)

    # def map_connectome(self, ui_info):
    #     ui_info.ui.context["object"].project_info.config_error_msg = self.pipeline.check_config()
    #     if ui_info.ui.context["object"].project_info.config_error_msg != '':
    #         ui_info.ui.context["object"].project_info.configure_traits(view='config_error_view')
    #     else:
    #         save_config(self.pipeline, ui_info.ui.context["object"].project_info.config_file)
    #         self.pipeline.launch_process()
    #         self.pipeline.launch_progress_window()
    #         update_last_processed(ui_info.ui.context["object"].project_info, self.pipeline)


    def process_anatomical(self, ui_info):
        ui_info.ui.context["object"].project_info.anat_config_error_msg = self.anat_pipeline.check_config()
        if ui_info.ui.context["object"].project_info.anat_config_error_msg != '':
            ui_info.ui.context["object"].project_info.configure_traits(view='config_error_view')
        else:
            anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
            ui_info.ui.context["object"].project_info.parcellation_scheme = get_anat_process_detail(ui_info.ui.context["object"].project_info,'parcellation_stage','parcellation_scheme')
            ui_info.ui.context["object"].project_info.atlas_info = get_anat_process_detail(ui_info.ui.context["object"].project_info,'parcellation_stage','atlas_info')

            try:
                self.anat_pipeline.launch_process()
                self.anat_pipeline.launch_progress_window()
                update_anat_last_processed(ui_info.ui.context["object"].project_info, self.anat_pipeline)
                anatomical_processed = True
                self.anat_outputs_checked = True
            except:
                self.anat_outputs_checked = False
        # ui_info.ui.context["object"].dmri_pipeline.anat_flow = self.anat_pipeline.flow

        #self.anat_pipeline,self.dmri_pipeline = init_project(new_project, True)



    def map_dmri_connectome(self, ui_info):
        ui_info.ui.context["object"].project_info.dmri_config_error_msg = self.dmri_pipeline.check_config()
        valid_anat_output,ui_info.ui.context["object"].project_info.anat_config_error_msg = self.anat_pipeline.check_output()

        if ui_info.ui.context["object"].project_info.anat_config_error_msg != '':
            ui_info.ui.context["object"].project_info.configure_traits(view='anat_config_error_view')
        else:
            if ui_info.ui.context["object"].project_info.dmri_config_error_msg != '':
                ui_info.ui.context["object"].project_info.configure_traits(view='config_error_view')
            else:
                self.dmri_pipeline.parcellation_scheme = ui_info.ui.context["object"].project_info.parcellation_scheme
                print "self.dmri_pipeline.parcellation_scheme: %s" % self.dmri_pipeline.parcellation_scheme
                self.dmri_pipeline.atlas_info = ui_info.ui.context["object"].project_info.atlas_info
                print "self.dmri_pipeline.atlas_info: %s" % self.dmri_pipeline.atlas_info
                dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                self.dmri_pipeline.launch_process()
                self.dmri_pipeline.launch_progress_window()
                update_dmri_last_processed(ui_info.ui.context["object"].project_info, self.dmri_pipeline)
            dmri_processed = True

    # def process_anatomical_and_diffusion(self, ui_info):

    # def map_dmri_connectome(self, ui_info):
    #     ui_info.ui.context["object"].project_info.dmri_config_error_msg = self.dmri_pipeline.check_config()
    #     if ui_info.ui.context["object"].project_info.dmri_config_error_msg != '':
    #         ui_info.ui.context["object"].project_info.configure_traits(view='config_error_view')
    #     else:
    #         dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
    #         self.dmri_pipeline.launch_process()
    #         self.dmri_pipeline.launch_progress_window()
    #         update_dmri_last_processed(ui_info.ui.context["object"].project_info, self.dmri_pipeline)

    # def map_custom(self, ui_info):
    #     if ui_info.ui.context["object"].project_info.custom_last_stage == '':
    #         ui_info.ui.context["object"].project_info.custom_last_stage = self.pipeline.ordered_stage_list[0]
    #     ui_info.ui.context["object"].project_info.stage_names = self.pipeline.ordered_stage_list
    #     cus_res = ui_info.ui.context["object"].project_info.configure_traits(view='custom_map_view')
    #     if cus_res:
    #         self.pipeline.define_custom_mapping(ui_info.ui.context["object"].project_info.custom_last_stage)

    # def map_dmri_custom(self, ui_info):
    #     if ui_info.ui.context["object"].project_info.dmri_custom_last_stage == '':
    #         ui_info.ui.context["object"].project_info.dmri_custom_last_stage = self.dmri_pipeline.ordered_stage_list[0]
    #     ui_info.ui.context["object"].project_info.dmri_stage_names = self.dmri_pipeline.ordered_stage_list
    #     cus_res = ui_info.ui.context["object"].project_info.configure_traits(view='dmri_custom_map_view')
    #     if cus_res:
    #         self.dmri_pipeline.define_custom_mapping(ui_info.ui.context["object"].project_info.dmri_custom_last_stage)

    def process_anatomical_custom(self, ui_info):
        if ui_info.ui.context["object"].project_info.anat_custom_last_stage == '':
            ui_info.ui.context["object"].project_info.anat_custom_last_stage = self.anat_pipeline.ordered_stage_list[0]
        ui_info.ui.context["object"].project_info.anat_stage_names = self.anat_pipeline.ordered_stage_list
        cus_res = ui_info.ui.context["object"].project_info.configure_traits(view='anat_custom_map_view')
        if cus_res:
            self.anat_pipeline.define_custom_mapping(ui_info.ui.context["object"].project_info.anat_custom_last_stage)

    def save_anat_config_file(self, ui_info):
        dialog = FileDialog(action="save as", default_filename="anatomical_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.anat_config_file:
                shutil.copy(ui_info.ui.context["object"].project_info.anat_config_file, dialog.path)

    def load_anat_config_file(self, ui_info):
        dialog = FileDialog(action="open", wildcard="*anatomical_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.anat_config_file:
                shutil.copy(dialog.path, ui_info.ui.context["object"].project_info.anat_config_file)
            load_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
            #TODO: load_config (anat_ or dmri_ ?)

    # def save_dmri_config_file(self, ui_info):
    #     dialog = FileDialog(action="save as", default_filename="diffusion_config.ini")
    #     dialog.open()
    #     if dialog.return_code == OK:
    #         save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
    #         if dialog.path != ui_info.ui.context["object"].project_info.dmri_config_file:
    #             shutil.copy(ui_info.ui.context["object"].project_info.dmri_config_file, dialog.path)
    #
    # def load_dmri_config_file(self, ui_info):
    #     dialog = FileDialog(action="open", wildcard="*diffusion_config.ini")
    #     dialog.open()
    #     if dialog.return_code == OK:
    #         if dialog.path != ui_info.ui.context["object"].project_info.dmri_config_file:
    #             shutil.copy(dialog.path, ui_info.ui.context["object"].project_info.dmri_config_file)
    #         load_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
