# Copyright (C) 2009-2019, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper Controler for handling non GUI general events
"""
import pickle
import warnings

warnings.filterwarnings("ignore",
                        message="UserWarning: No valid root directory found for domain 'derivatives'. Falling back on the Layout's root directory. If this isn't the intended behavior, make sure the config file for this domain includes a 'root' key.")

# Global imports
import ast
from traits.api import *
import shutil
import os
import gzip
import glob
import string
import fnmatch

import multiprocessing

import ConfigParser

from bids import BIDSLayout

# Own imports
# import pipelines.diffusion.diffusion as Diffusion_pipeline
from cmp.pipelines.functional import fMRI as FMRI_pipeline
from cmp.pipelines.diffusion import diffusion as Diffusion_pipeline
from cmp.pipelines.anatomical import anatomical as Anatomical_pipeline

from cmtklib.bids.utils import write_derivative_description


##from cmp.configurator.project import fix_dataset_directory_in_pickles, remove_aborded_interface_pickles

# import CMP_MainWindow
# import pipelines.egg.eeg as EEG_pipeline

class CMP_Project_Info(HasTraits):
    base_directory = Directory
    output_directory = Directory
    
    bids_layout = Instance(BIDSLayout)
    subjects = List([])
    subject = Enum(values='subjects')
    
    number_of_subjects = Int()
    
    subject_sessions = List([])
    subject_session = Enum(values='subject_sessions')
    
    # current_subj = Str()
    anat_warning_msg = Str(
        '\nWarning: selected directory is already configured for anatomical data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    dmri_warning_msg = Str(
        '\nWarning: selected directory is already configured for diffusion data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    fmri_warning_msg = Str(
        '\nWarning: selected directory is already configured for resting-state data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    
    # process_type = Enum('diffusion',['diffusion','fMRI'])
    diffusion_imaging_model = Enum('DTI', ['DSI', 'DTI', 'HARDI'])
    parcellation_scheme = Str('Lausanne2008')
    atlas_info = Dict()
    freesurfer_subjects_dir = Str('')
    freesurfer_subject_id = Str('')
    
    pipeline_processing_summary = List()
    
    t1_available = Bool(False)
    dmri_available = Bool(False)
    fmri_available = Bool(False)
    
    anat_config_error_msg = Str('')
    anat_config_to_load = Str()
    anat_available_config = List()
    anat_config_to_load_msg = Str('Several configuration files available. Select which one to load:\n')
    anat_last_date_processed = Str('Not yet processed')
    anat_last_stage_processed = Str('Not yet processed')
    
    anat_stage_names = List
    anat_custom_last_stage = Str
    
    dmri_config_error_msg = Str('')
    dmri_config_to_load = Str()
    dmri_available_config = List()
    dmri_config_to_load_msg = Str('Several configuration files available. Select which one to load:\n')
    dmri_last_date_processed = Str('Not yet processed')
    dmri_last_stage_processed = Str('Not yet processed')
    
    dmri_stage_names = List
    dmri_custom_last_stage = Str
    
    fmri_config_error_msg = Str('')
    fmri_config_to_load = Str()
    fmri_available_config = List()
    fmri_config_to_load_msg = Str('Several configuration files available. Select which one to load:\n')
    fmri_last_date_processed = Str('Not yet processed')
    fmri_last_stage_processed = Str('Not yet processed')
    
    fmri_stage_names = List
    fmri_custom_last_stage = Str
    
    number_of_cores = Enum(1, range(1, multiprocessing.cpu_count() + 1))


def fix_dataset_directory_in_pickles(local_dir, mode='local', debug=False):
    # mode can be local or bidsapp (local by default)
    
    searchdir = os.path.join(local_dir, 'derivatives', 'nipype')
    
    for root, dirs, files in os.walk(searchdir):
        files = [fi for fi in files if fi.endswith(".pklz")]
        
        if debug:
            print('----------------------------------------------------')
        
        for fi in files:
            if debug:
                print("Processing file {} {} {}".format(root, dirs, fi))
            pick = gzip.open(os.path.join(root, fi))
            cont = pick.read()
            
            # Change pickles: bids app dataset directory -> local dataset directory
            if (mode == 'local') and cont.find('/bids_dataset/derivatives') and (local_dir != '/bids_dataset'):
                new_cont = string.replace(cont, 'V/bids_dataset', 'V{}'.format(local_dir))
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)
            
            # Change pickles: local dataset directory -> bids app dataset directory
            elif (mode == 'bidsapp') and not cont.find('/bids_dataset/derivatives') and (local_dir != '/bids_dataset'):
                new_cont = string.replace(cont, 'V{}'.format(local_dir), 'V/bids_dataset')
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)
    return True


def remove_aborded_interface_pickles(local_dir, debug=False):
    searchdir = os.path.join(local_dir, 'derivatives', 'nipype')
    
    for root, dirs, files in os.walk(searchdir):
        files = [fi for fi in files if fi.endswith(".pklz")]
        
        if debug:
            print('----------------------------------------------------')
        
        for fi in files:
            if debug:
                print("Processing file {} {} {}".format(root, dirs, fi))
            try:
                cont = pickle.load(gzip.open(os.path.join(root, fi)))
            except Exception as e:
                # Remove pickle if unpickling error raised
                print('Unpickling Error: removed {}'.format(os.path.join(root, fi)))
                os.remove(os.path.join(root, fi))


# def remove_aborded_interface_pickles(local_dir, subject, session=''):
#
#     if session == '':
#         searchdir = os.path.join(local_dir,'derivatives/cmp',subject,'tmp')
#     else:
#         searchdir = os.path.join(local_dir,'derivatives/cmp',subject,session,'tmp')
#
#     for root, dirs, files in os.walk(searchdir):
#         files = [ fi for fi in files if fi.endswith(".pklz") ]
#
#         print('----------------------------------------------------')
#
#         for fi in files:
#             print("Processing file {} {} {}".format(root,dirs,fi))
#             try:
#                 cont = pickle.load(gzip.open(os.path.join(root,fi)))
#             except Exception as e:
#                 # Remove pickle if unpickling error raised
#                 print('Unpickling Error: removed {}'.format(os.path.join(root,fi)))
#                 os.remove(os.path.join(root,fi))


def get_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.config_file)
    return config.get(section, detail)


def get_anat_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.anat_config_file)
    res = None
    if detail == "atlas_info":
        res = ast.literal_eval(config.get(section, detail))
    else:
        res = config.get(section, detail)
    return res


def get_dmri_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.dmri_config_file)
    return config.get(section, detail)


def get_fmri_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.fmri_config_file)
    return config.get(section, detail)


def anat_save_config(pipeline, config_path):
    config = ConfigParser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if
                   not 'trait' in prop]  # possibly dangerous..?
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in pipeline.stages.values():
        config.add_section(stage.name)
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key:  # subconfig
                stage_sub_keys = [prop for prop in keyval.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key + '.' + sub_key, getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)
    
    config.add_section('Multi-processing')
    config.set('Multi-processing', 'number_of_cores', pipeline.number_of_cores)
    
    with open(config_path, 'wb') as configfile:
        config.write(configfile)
    
    print('Config file (anat) saved as {}'.format(config_path))


def anat_load_config(pipeline, config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if
                   not 'trait' in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions" and key != 'modalities':
            conf_value = config.get('Global', key)
            setattr(pipeline.global_conf, key, conf_value)
    for stage in pipeline.stages.values():
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in sub_config.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config.get(stage.name, key + '.' + sub_key)
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
    setattr(pipeline, 'number_of_cores', int(config.get('Multi-processing', 'number_of_cores')))
    
    return True


def dmri_save_config(pipeline, config_path):
    config = ConfigParser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if
                   not 'trait' in prop]  # possibly dangerous..?
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in pipeline.stages.values():
        config.add_section(stage.name)
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key:  # subconfig
                stage_sub_keys = [prop for prop in keyval.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key + '.' + sub_key, getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)
    
    config.add_section('Multi-processing')
    config.set('Multi-processing', 'number_of_cores', pipeline.number_of_cores)
    
    with open(config_path, 'wb') as configfile:
        config.write(configfile)
    
    print('Config file (dmri) saved as {}'.format(config_path))


def dmri_load_config(pipeline, config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if
                   not 'trait' in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions" and key != 'modalities':
            conf_value = config.get('Global', key)
            setattr(pipeline.global_conf, key, conf_value)
    for stage in pipeline.stages.values():
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in sub_config.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config.get(stage.name, key + '.' + sub_key)
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
    setattr(pipeline, 'number_of_cores', int(config.get('Multi-processing', 'number_of_cores')))
    return True


def fmri_save_config(pipeline, config_path):
    config = ConfigParser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if
                   not 'trait' in prop]  # possibly dangerous..?
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in pipeline.stages.values():
        config.add_section(stage.name)
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key:  # subconfig
                stage_sub_keys = [prop for prop in keyval.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key + '.' + sub_key, getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)
    
    config.add_section('Multi-processing')
    config.set('Multi-processing', 'number_of_cores', pipeline.number_of_cores)
    
    with open(config_path, 'wb') as configfile:
        config.write(configfile)
    
    print('Config file (fmri) saved as {}'.format(config_path))


def fmri_load_config(pipeline, config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if
                   not 'trait' in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions" and key != 'modalities':
            conf_value = config.get('Global', key)
            setattr(pipeline.global_conf, key, conf_value)
    for stage in pipeline.stages.values():
        stage_keys = [prop for prop in stage.config.traits().keys() if not 'trait' in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in sub_config.traits().keys() if not 'trait' in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config.get(stage.name, key + '.' + sub_key)
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
    setattr(pipeline, 'number_of_cores', int(config.get('Multi-processing', 'number_of_cores')))
    return True


## Creates (if needed) the folder hierarchy
#
def refresh_folder(bids_directory, derivatives_directory, subject, input_folders, session=None):
    paths = []
    
    if session == None or session == '':
        paths.append(os.path.join(derivatives_directory, 'freesurfer', subject))
        paths.append(os.path.join(derivatives_directory, 'cmp', subject))
        paths.append(os.path.join(derivatives_directory, 'nipype', subject))
        
        for in_f in input_folders:
            paths.append(os.path.join(derivatives_directory, 'cmp', subject, in_f))
            # paths.append(os.path.join(derivatives_directory,'nipype',subject,in_f))
    
    else:
        paths.append(os.path.join(derivatives_directory, 'freesurfer', '%s_%s' % (subject, session)))
        paths.append(os.path.join(derivatives_directory, 'cmp', subject, session))
        paths.append(os.path.join(derivatives_directory, 'nipype', subject, session))
        
        for in_f in input_folders:
            paths.append(os.path.join(derivatives_directory, 'cmp', subject, session, in_f))
            # paths.append(os.path.join(derivatives_directory,'nipype',subject,session,in_f))
    
    for full_p in paths:
        if not os.path.exists(full_p):
            try:
                os.makedirs(full_p)
            except os.error:
                print("%s was already existing" % full_p)
            finally:
                print("Created directory %s" % full_p)
    
    write_derivative_description(bids_directory, derivatives_directory, 'cmp')
    write_derivative_description(bids_directory, derivatives_directory, 'freesurfer')
    write_derivative_description(bids_directory, derivatives_directory, 'nipype')


def init_dmri_project(project_info, bids_layout, is_new_project, gui=True, debug=False):
    dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(project_info)
    
    bids_directory = os.path.abspath(project_info.base_directory)
    
    derivatives_directory = os.path.abspath(project_info.output_directory)
    
    if len(project_info.subject_sessions) > 0:
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, dmri_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, dmri_pipeline.input_folders)
    
    dmri_inputs_checked = dmri_pipeline.check_input(layout=bids_layout, gui=gui)
    if dmri_inputs_checked:
        if is_new_project and dmri_pipeline != None:  # and dmri_pipeline!= None:
            print("> Initialize dmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("... Info : %s was already existing" % derivatives_directory)
                finally:
                    print("... Info : Created directory %s" % derivatives_directory)
            
            if (project_info.subject_session != '') and (project_info.subject_session != None):
                project_info.dmri_config_file = os.path.join(derivatives_directory, '%s_%s_diffusion_config.ini' % (
                project_info.subject, project_info.subject_session))
            else:
                project_info.dmri_config_file = os.path.join(derivatives_directory,
                                                             '%s_diffusion_config.ini' % (project_info.subject))
            
            if os.path.exists(project_info.dmri_config_file):
                warn_res = project_info.configure_traits(view='dmri_warning_view')
                if warn_res:
                    print("... Read : Diffusion config file (%s)" % project_info.dmri_config_file)
                    dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
                else:
                    return None
            else:
                print("... Create : Diffusion config file (%s)" % project_info.dmri_config_file)
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
        else:
            if debug:
                print("int_project dmri_pipeline.global_config.subjects : ")
                print(dmri_pipeline.global_conf.subjects)
            
            dmri_conf_loaded = dmri_load_config(dmri_pipeline, project_info.dmri_config_file)
            
            if not dmri_conf_loaded:
                return None
        
        dmri_pipeline.config_file = project_info.dmri_config_file
    else:
        print("INFO: Missing diffusion inputs")
    
    return dmri_inputs_checked, dmri_pipeline


def init_fmri_project(project_info, bids_layout, is_new_project, gui=True, debug=False):
    fmri_pipeline = FMRI_pipeline.fMRIPipeline(project_info)
    
    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)
    
    if len(project_info.subject_sessions) > 0:
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, fmri_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, fmri_pipeline.input_folders)
    
    fmri_inputs_checked = fmri_pipeline.check_input(layout=bids_layout, gui=gui, debug=False)
    if fmri_inputs_checked:
        if is_new_project and fmri_pipeline != None:  # and fmri_pipeline!= None:
            print("> Initialize fmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("... Info : %s was already existing" % derivatives_directory)
                finally:
                    print("... Info : Created directory %s" % derivatives_directory)
            
            if (project_info.subject_session != '') and (project_info.subject_session != None):
                project_info.fmri_config_file = os.path.join(derivatives_directory, '%s_%s_fMRI_config.ini' % (
                project_info.subject, project_info.subject_session))
            else:
                project_info.fmri_config_file = os.path.join(derivatives_directory,
                                                             '%s_fMRI_config.ini' % (project_info.subject))
            
            if os.path.exists(project_info.fmri_config_file):
                warn_res = project_info.configure_traits(view='fmri_warning_view')
                if warn_res:
                    print("... Read : fMRI config file (%s)" % project_info.fmri_config_file)
                    fmri_load_config(fmri_pipeline, project_info.fmri_config_file)
                else:
                    return None
            else:
                print("... Create : fMRI config file (%s)" % project_info.fmri_config_file)
                fmri_save_config(fmri_pipeline, project_info.fmri_config_file)
        else:
            if debug:
                print("int_project fmri_pipeline.global_config.subjects : ")
                print(fmri_pipeline.global_conf.subjects)
            
            fmri_conf_loaded = fmri_load_config(fmri_pipeline, project_info.fmri_config_file)
            
            if not fmri_conf_loaded:
                return None
        
        fmri_pipeline.config_file = project_info.fmri_config_file
    else:
        print("INFO : Missing fmri inputs")
    
    return fmri_inputs_checked, fmri_pipeline


def init_anat_project(project_info, is_new_project, debug=False):
    anat_pipeline = Anatomical_pipeline.AnatomicalPipeline(project_info)
    
    bids_directory = os.path.abspath(project_info.base_directory)
    derivatives_directory = os.path.abspath(project_info.output_directory)
    
    if (project_info.subject_session != '') and (project_info.subject_session != None):
        if debug:
            print('Refresh folder WITH session')
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, anat_pipeline.input_folders,
                       session=project_info.subject_session)
    else:
        if debug:
            print('Refresh folder WITHOUT session')
        refresh_folder(bids_directory, derivatives_directory, project_info.subject, anat_pipeline.input_folders)
    
    if is_new_project and anat_pipeline != None:  # and dmri_pipeline!= None:
        print("> Initialize anatomical project")
        if not os.path.exists(derivatives_directory):
            try:
                os.makedirs(derivatives_directory)
            except os.error:
                print("... Info: %s was already existing" % derivatives_directory)
            finally:
                print("... Info : Created directory %s" % derivatives_directory)
        
        if (project_info.subject_session != '') and (project_info.subject_session != None):
            project_info.anat_config_file = os.path.join(derivatives_directory, '%s_%s_anatomical_config.ini' % (
            project_info.subject, project_info.subject_session))
        else:
            project_info.anat_config_file = os.path.join(derivatives_directory,
                                                         '%s_anatomical_config.ini' % (project_info.subject))
        
        if os.path.exists(project_info.anat_config_file):
            warn_res = project_info.configure_traits(view='anat_warning_view')
            if warn_res:
                anat_save_config(anat_pipeline, project_info.anat_config_file)
            else:
                return None
        else:
            anat_save_config(anat_pipeline, project_info.anat_config_file)
    
    else:
        if debug:
            print("int_project anat_pipeline.global_config.subjects : ")
            print(anat_pipeline.global_conf.subjects)
        
        anat_conf_loaded = anat_load_config(anat_pipeline, project_info.anat_config_file)
        
        if not anat_conf_loaded:
            return None
    
    anat_pipeline.config_file = project_info.anat_config_file
    
    return anat_pipeline


def update_anat_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.output_directory, 'nipype', project_info.subject))
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
    if os.path.exists(
            os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'anatomical_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(
                os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'anatomical_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.anat_last_stage_processed = stage
    
    # last parcellation scheme
    project_info.parcellation_scheme = pipeline.parcellation_scheme
    project_info.atlas_info = pipeline.atlas_info


def update_dmri_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.output_directory, 'nipype', project_info.subject))
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
    if os.path.exists(
            os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'diffusion_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(
                os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'diffusion_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage


def update_fmri_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.output_directory, 'nipype', project_info.subject))
        # for out in out_dirs:
        #     if (project_info.last_date_processed == "Not yet processed" or
        #         out > project_info.last_date_processed):
        #         pipeline.last_date_processed = out
        #         project_info.last_date_processed = out
        
        if (project_info.fmri_last_date_processed == "Not yet processed" or
                pipeline.now > project_info.fmri_last_date_processed):
            pipeline.fmri_last_date_processed = pipeline.now
            project_info.fmri_last_date_processed = pipeline.now
    
    # last stage
    if os.path.exists(os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'fMRI_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(
                os.path.join(project_info.output_directory, 'nipype', project_info.subject, 'fMRI_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower() + '_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage
