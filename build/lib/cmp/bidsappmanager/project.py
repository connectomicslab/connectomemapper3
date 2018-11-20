# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper Controler for handling GUI and non GUI general events
"""
import warnings
warnings.filterwarnings("ignore", message="No valid root directory found for domain 'derivatives'.")

# Global imports
import ast
from traits.api import *
from traitsui.api import *
import shutil
import os
import glob
import fnmatch

from subprocess import Popen
import multiprocessing

import pickle
import string
import gzip

import ConfigParser
from pyface.api import FileDialog, OK

from bids.grabbids import BIDSLayout
import nibabel as nib

# Own imports
#import pipelines.diffusion.diffusion as Diffusion_pipeline
from cmp.bidsappmanager.pipelines.functional import fMRI as FMRI_pipeline
from cmp.bidsappmanager.pipelines.diffusion import diffusion as Diffusion_pipeline
from cmp.bidsappmanager.pipelines.anatomical import anatomical as Anatomical_pipeline

import gui

#import CMP_MainWindow
#import pipelines.egg.eeg as EEG_pipeline

def fix_dataset_directory_in_pickles(local_dir, mode='local'):
    #mode can be local or bidsapp (local by default)

    searchdir = os.path.join(local_dir,'derivatives/cmp')

    for root, dirs, files in os.walk(searchdir):
        files = [ fi for fi in files if fi.endswith(".pklz") ]

        print('----------------------------------------------------')

        for fi in files:
            print("Processing file {} {} {} (mode: {})".format(root,dirs,fi,mode))
            pick = gzip.open(os.path.join(root,fi))
            cont = pick.read()

            print("local_dir : {} , cont.find('/bids_dataset/derivatives'): {} (mode: {})".format(local_dir,cont.find('/bids_dataset/derivatives'),mode))

            # Change pickles: bids app dataset directory -> local dataset directory
            if (mode == 'local'):
                print(' bids app dataset directory -> local dataset directory')
                new_cont = string.replace(cont,'/bids_dataset','{}'.format(local_dir))
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root,'{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)

            # Change pickles: local dataset directory -> bids app dataset directory
            elif (mode == 'bidsapp'):
                print(' local dataset directory -> bids app dataset directory')
                new_cont = string.replace(cont,'{}'.format(local_dir),'/bids_dataset')
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root,'{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)
    return True

# def fix_dataset_directory_in_pickles(local_dir, subject, session='', mode='local'):
#     #mode can be local or bidsapp (local by default)
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
#             pick = gzip.open(os.path.join(root,fi))
#             cont = pick.read()
#
#             # Change pickles: bids app dataset directory -> local dataset directory
#             if (mode == 'local') and cont.find('/bids_dataset/derivatives') and (local_dir != '/bids_dataset'):
#                 new_cont = string.replace(cont,'V/bids_dataset','V{}'.format(local_dir))
#                 pref = fi.split(".")[0]
#                 with gzip.open(os.path.join(root,'{}.pklz'.format(pref)), 'wb') as f:
#                     f.write(new_cont)
#
#             # Change pickles: local dataset directory -> bids app dataset directory
#             elif (mode == 'bidsapp') and not cont.find('/bids_dataset/derivatives') and (local_dir != '/bids_dataset'):
#                 new_cont = string.replace(cont,'V{}'.format(local_dir),'V/bids_dataset')
#                 pref = fi.split(".")[0]
#                 with gzip.open(os.path.join(root,'{}.pklz'.format(pref)), 'wb') as f:
#                     f.write(new_cont)
#     return True


def remove_aborded_interface_pickles(local_dir):

    searchdir = os.path.join(local_dir,'derivatives/cmp')

    for root, dirs, files in os.walk(searchdir):
        files = [ fi for fi in files if fi.endswith(".pklz") ]

        print('----------------------------------------------------')

        for fi in files:
            print("Processing file {} {} {}".format(root,dirs,fi))
            try:
                cont = pickle.load(gzip.open(os.path.join(root,fi)))
            except Exception as e:
                # Remove pickle if unpickling error raised
                print('Unpickling Error: removed {}'.format(os.path.join(root,fi)))
                os.remove(os.path.join(root,fi))


def remove_aborded_interface_pickles(local_dir, subject, session=''):

    if session == '':
        searchdir = os.path.join(local_dir,'derivatives/cmp',subject,'tmp')
    else:
        searchdir = os.path.join(local_dir,'derivatives/cmp',subject,session,'tmp')

    for root, dirs, files in os.walk(searchdir):
        files = [ fi for fi in files if fi.endswith(".pklz") ]

        print('----------------------------------------------------')

        for fi in files:
            print("Processing file {} {} {}".format(root,dirs,fi))
            try:
                cont = pickle.load(gzip.open(os.path.join(root,fi)))
            except Exception as e:
                # Remove pickle if unpickling error raised
                print('Unpickling Error: removed {}'.format(os.path.join(root,fi)))
                os.remove(os.path.join(root,fi))
            # except pickle.UnpicklingError as e:
            #     # normal, somewhat expected
            #     continue
            # except (AttributeError,  EOFError, ImportError, IndexError) as e:
            #     # secondary errors
            #     print(traceback.format_exc(e))
            #     continue

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

def get_fmri_process_detail(project_info, section, detail):
    config = ConfigParser.ConfigParser()
    #print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.fmri_config_file)
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
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
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
                    if key != 'modalities':
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
    print(global_keys)
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
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions" and key != 'modalities':
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
                    if key != 'modalities':
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

def fmri_save_config(pipeline, config_path):
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

def fmri_load_config(pipeline, config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    global_keys = [prop for prop in pipeline.global_conf.traits().keys() if not 'trait' in prop] # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
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
                    if key != 'modalities':
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
def refresh_folder(derivatives_directory, subject, input_folders, session=None):
    paths = []

    if session == None or session == '':
        paths.append(os.path.join(derivatives_directory,'freesurfer',subject))
        paths.append(os.path.join(derivatives_directory,'cmp',subject))

        for in_f in input_folders:
            paths.append(os.path.join(derivatives_directory,'cmp',subject,in_f))

        paths.append(os.path.join(derivatives_directory,'cmp',subject,'tmp'))
    else:
        paths.append(os.path.join(derivatives_directory,'freesurfer','%s_%s'%(subject,session)))
        paths.append(os.path.join(derivatives_directory,'cmp',subject,session))

        for in_f in input_folders:
            paths.append(os.path.join(derivatives_directory,'cmp',subject,session,in_f))

        paths.append(os.path.join(derivatives_directory,'cmp',subject,session,'tmp'))

    for full_p in paths:
        if not os.path.exists(full_p):
            try:
                os.makedirs(full_p)
            except os.error:
                print("%s was already existing" % full_p)
            finally:
                print("Created directory %s" % full_p)

def init_dmri_project(project_info, bids_layout, is_new_project, gui=True):
    dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(project_info)

    derivatives_directory = os.path.join(project_info.base_directory,'derivatives')

    if (project_info.subject_session != '') and (project_info.subject_session != None) :
        refresh_folder(derivatives_directory, project_info.subject, dmri_pipeline.input_folders, session=project_info.subject_session)
    else:
        refresh_folder(derivatives_directory, project_info.subject, dmri_pipeline.input_folders)

    dmri_inputs_checked = dmri_pipeline.check_input(layout=bids_layout,gui=gui)
    if dmri_inputs_checked:
        if is_new_project and dmri_pipeline!= None: #and dmri_pipeline!= None:
            print("Initialize dmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("%s was already existing" % derivatives_directory)
                finally:
                    print("Created directory %s" % derivatives_directory)

            if (project_info.subject_session != '') and (project_info.subject_session != None) :
                project_info.dmri_config_file = os.path.join(derivatives_directory,'%s_%s_diffusion_config.ini' % (project_info.subject,project_info.subject_session))
            else:
                project_info.dmri_config_file = os.path.join(derivatives_directory,'%s_diffusion_config.ini' % (project_info.subject))


            if os.path.exists(project_info.dmri_config_file):
                warn_res = project_info.configure_traits(view='dmri_warning_view')
                if warn_res:
                    print("Read diffusion config file (%s)" % project_info.dmri_config_file)
                    dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
                else:
                    return None
            else:
                print("Create diffusion config file (%s)" % project_info.dmri_config_file)
                dmri_save_config(dmri_pipeline, project_info.dmri_config_file)
        else:
            print("int_project dmri_pipeline.global_config.subjects : ")
            print(dmri_pipeline.global_conf.subjects)

            dmri_conf_loaded = dmri_load_config(dmri_pipeline, project_info.dmri_config_file)

            if not dmri_conf_loaded:
                return None

        print(dmri_pipeline)
        print(dmri_pipeline.global_conf.dmri_bids_acq)
        dmri_pipeline.config_file = project_info.dmri_config_file
    else:
        print("Missing diffusion inputs")

    return dmri_inputs_checked, dmri_pipeline

def init_fmri_project(project_info, bids_layout, is_new_project, gui=True):
    fmri_pipeline = FMRI_pipeline.fMRIPipeline(project_info)

    derivatives_directory = os.path.join(project_info.base_directory,'derivatives')

    if (project_info.subject_session != '') and (project_info.subject_session != None) :
        refresh_folder(derivatives_directory, project_info.subject, fmri_pipeline.input_folders, session=project_info.subject_session)
    else:
        refresh_folder(derivatives_directory, project_info.subject, fmri_pipeline.input_folders)

    fmri_inputs_checked = fmri_pipeline.check_input(layout=bids_layout,gui=gui)
    if fmri_inputs_checked:
        if is_new_project and fmri_pipeline!= None: #and fmri_pipeline!= None:
            print("Initialize fmri project")
            if not os.path.exists(derivatives_directory):
                try:
                    os.makedirs(derivatives_directory)
                except os.error:
                    print("%s was already existing" % derivatives_directory)
                finally:
                    print("Created directory %s" % derivatives_directory)

            if (project_info.subject_session != '') and (project_info.subject_session != None) :
                project_info.fmri_config_file = os.path.join(derivatives_directory,'%s_%s_fMRI_config.ini' % (project_info.subject,project_info.subject_session))
            else:
                project_info.fmri_config_file = os.path.join(derivatives_directory,'%s_fMRI_config.ini' % (project_info.subject))


            if os.path.exists(project_info.fmri_config_file):
                warn_res = project_info.configure_traits(view='fmri_warning_view')
                if warn_res:
                    print("Read fMRI config file (%s)" % project_info.fmri_config_file)
                    fmri_load_config(fmri_pipeline, project_info.fmri_config_file)
                else:
                    return None
            else:
                print("Create fMRI config file (%s)" % project_info.fmri_config_file)
                fmri_save_config(fmri_pipeline, project_info.fmri_config_file)
        else:
            print("int_project fmri_pipeline.global_config.subjects : ")
            print(fmri_pipeline.global_conf.subjects)

            fmri_conf_loaded = fmri_load_config(fmri_pipeline, project_info.fmri_config_file)

            if not fmri_conf_loaded:
                return None

        print(fmri_pipeline)
        fmri_pipeline.config_file = project_info.fmri_config_file
    else:
        print("Missing fmri inputs")

    return fmri_inputs_checked, fmri_pipeline

def init_anat_project(project_info, is_new_project):
    print('Init anat pipeline project_info :')
    print(project_info.base_directory)
    print(project_info.subject)
    print(project_info.subject_session)

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
                print("%s was already existing" % derivatives_directory)
            finally:
                print("Created directory %s" % derivatives_directory)

        if (project_info.subject_session != '') and (project_info.subject_session != None) :
            project_info.anat_config_file = os.path.join(derivatives_directory,'%s_%s_anatomical_config.ini' % (project_info.subject,project_info.subject_session))
        else:
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
        print("int_project anat_pipeline.global_config.subjects : ")
        print(anat_pipeline.global_conf.subjects)

        anat_conf_loaded = anat_load_config(anat_pipeline, project_info.anat_config_file)
        #dmri_conf_loaded = load_config(dmri_pipeline, project_info.dmri_config_file)

        if not anat_conf_loaded:
            return None

        #if not dmri_conf_loaded:
        #    return None

    print(anat_pipeline)
    #print dmri_pipeline
    if (project_info.subject_session != '') and (project_info.subject_session != None) :
        refresh_folder(derivatives_directory, project_info.subject, anat_pipeline.input_folders, session=project_info.subject_session)
    else:
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

def update_fmri_last_processed(project_info, pipeline):
    # last date
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject)):
        out_dirs = os.listdir(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject))
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
    if os.path.exists(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','fMRI_pipeline')):
        stage_dirs = []
        for root, dirnames, _ in os.walk(os.path.join(project_info.base_directory,'derivatives','cmp',project_info.subject,'tmp','fMRI_pipeline')):
            for dirname in fnmatch.filter(dirnames, '*_stage'):
                stage_dirs.append(dirname)
        for stage in pipeline.ordered_stage_list:
            if stage.lower()+'_stage' in stage_dirs:
                pipeline.last_stage_processed = stage
                project_info.dmri_last_stage_processed = stage

class ProjectHandler(Handler):
    project_loaded = Bool(False)

    anat_pipeline = Instance(HasTraits)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    anatomical_processed = Bool(False)

    dmri_pipeline = Instance(HasTraits)
    dmri_inputs_checked = Bool(False)
    dmri_processed = Bool(False)

    fmri_pipeline = Instance(HasTraits)
    fmri_inputs_checked = Bool(False)
    fmri_processed = Bool(False)

    def new_project(self, ui_info ):
        new_project = gui.CMP_Project_Info()
        np_res = new_project.configure_traits(view='create_view')
        ui_info.ui.context["object"].handler = self

        if np_res and os.path.exists(new_project.base_directory):
            try:
                bids_layout = BIDSLayout(new_project.base_directory)
                new_project.bids_layout = bids_layout
                print bids_layout

                for subj in bids_layout.get_subjects():
                    if 'sub-'+str(subj) not in new_project.subjects:
                        new_project.subjects.append('sub-'+str(subj))
                # new_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]

                # new_project.configure_traits(subject=Enum(*subjects))
                # print new_project.subjects

                print "Available subjects : "
                print new_project.subjects
                new_project.number_of_subjects = len(new_project.subjects)

                np_res = new_project.configure_traits(view='subject_view')
                print "Selected subject : "+new_project.subject

                subject = new_project.subject.split('-')[1]
                print "Subject: %s" % subject

                new_project.subject_sessions = ['']
                new_project.subject_session = ''


                sessions = bids_layout.get(target='session', return_type='id', subject=subject)

                print "Sessions: "
                print sessions

                if len(sessions) > 0:
                    print "Warning: multiple sessions"
                    for ses in sessions:
                        new_project.subject_sessions.append('ses-'+str(ses))
                    np_res = new_project.configure_traits(view='subject_session_view')
                    print "Selected session : "+new_project.subject_session

            except:
                error(message="Invalid BIDS dataset. Please see documentation for more details.",title="BIDS error")
                return

            self.anat_pipeline = init_anat_project(new_project, True)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = new_project
                    self.anat_pipeline.number_of_cores = new_project.number_of_cores
                    # self.anat_pipeline.flow = self.anat_pipeline.create_pipeline_flow()
                    ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                    #ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.ui.context["object"].project_info.t1_available = self.anat_inputs_checked

                    ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_anat_pipeline,'subject')
                    ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_anat_pipeline,'subject_session')
                    anat_save_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
                    self.project_loaded = True

                    ui_info.ui.context["object"].project_info.parcellation_scheme = get_anat_process_detail(new_project,'parcellation_stage','parcellation_scheme')
                    ui_info.ui.context["object"].project_info.freesurfer_subjects_dir = get_anat_process_detail(new_project,'segmentation_stage','freesurfer_subjects_dir')
                    ui_info.ui.context["object"].project_info.freesurfer_subject_id = get_anat_process_detail(new_project,'segmentation_stage','freesurfer_subject_id')
                    # ui_info.ui.context["object"].project_info.atlas_info = get_anat_process_detail(new_project,'parcellation_stage','atlas_info')

                    dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(new_project, bids_layout, True)
                    if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
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
                            ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_dmri_pipeline,'subject')
                            ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_dmri_pipeline,'subject_session')
                            #self.diffusion_ready = True
                            dmri_save_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
                            self.dmri_inputs_checked = dmri_inputs_checked
                            ui_info.ui.context["object"].project_info.dmri_available = self.dmri_inputs_checked
                            self.project_loaded = True
                            ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_diffusion_imaging_model,'diffusion_imaging_model')

                    fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(new_project,bids_layout, True)
                    if self.fmri_pipeline != None: #and self.fmri_pipeline != None:
                        if fmri_inputs_checked:
                            # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                            # self.fmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                            self.fmri_pipeline.number_of_cores  = new_project.number_of_cores
                            print "number of cores (pipeline): %s" % self.fmri_pipeline.number_of_cores
                            # print "diffusion_imaging_model (pipeline): %s" % self.fmri_pipeline.diffusion_imaging_model
                            # print "diffusion_imaging_model ui_info: %s" % ui_info.ui.context["object"].project_info.diffusion_imaging_model
                            self.fmri_pipeline.parcellation_scheme = ui_info.ui.context["object"].project_info.parcellation_scheme
                            self.fmri_pipeline.subjects_dir = ui_info.ui.context["object"].project_info.freesurfer_subjects_dir
                            self.fmri_pipeline.subject_id = ui_info.ui.context["object"].project_info.freesurfer_subject_id
                            # self.fmri_pipeline.atlas_info = ui_info.ui.context["object"].project_info.atlas_info
                            ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                            #self.diffusion_ready = True
                            ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_fmri_pipeline,'subject')
                            ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_fmri_pipeline,'subject_session')
                            fmri_save_config(self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)
                            self.fmri_inputs_checked = fmri_inputs_checked
                            ui_info.ui.context["object"].project_info.fmri_available = self.fmri_inputs_checked
                            self.project_loaded = True


    def load_project(self, ui_info ):
        loaded_project = gui.CMP_Project_Info()
        np_res = loaded_project.configure_traits(view='open_view')
        ui_info.ui.context["object"].handler = self

        # print "Default subject : "+loaded_project.subject

        is_bids = False

        print "Base dir: %s" % loaded_project.base_directory
        try:
            bids_layout = BIDSLayout(loaded_project.base_directory)
            loaded_project.bids_layout = bids_layout
            is_bids = True

            loaded_project.subjects = []
            for subj in bids_layout.get_subjects():
                print "sub: %s" % subj
                if 'sub-'+str(subj) not in loaded_project.subjects:
                    loaded_project.subjects.append('sub-'+str(subj))
            # loaded_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
            loaded_project.subjects.sort()

            print "Available subjects : "
            print loaded_project.subjects
            loaded_project.number_of_subjects = len(loaded_project.subjects)

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


            sessions = []
            for subj in bids_layout.get_subjects():
                subj_sessions = bids_layout.get(target='session', return_type='id', subject=subj)
                for subj_session in subj_sessions:
                    sessions.append(subj_session)

            print "sessions:"
            print sessions

            loaded_project.anat_available_config = []

            for subj in bids_layout.get_subjects():
                subj_sessions = bids_layout.get(target='session', return_type='id', subject=subj)
                if len(subj_sessions) > 0:
                    for subj_session in subj_sessions:
                        config_file = os.path.join(loaded_project.base_directory,'derivatives',"sub-%s_ses-%s_anatomical_config.ini" % (subj, subj_session))
                        if os.path.isfile(config_file):
                            loaded_project.anat_available_config.append( "sub-%s_ses-%s" % (subj, subj_session) )
                else:
                    config_file = os.path.join(loaded_project.base_directory,'derivatives',"sub-%s_anatomical_config.ini" % (subj))
                    if os.path.isfile(config_file):
                        loaded_project.anat_available_config.append( "sub-%s" % (subj) )
                        print "no session"

            # if len(sessions) > 0:
            #     print ["_".join((os.path.basename(s)[:-11].split("_")[0],os.path.basename(s)[:-11].split("_")[1])) for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','*_anatomical_config.ini'))]
            #     loaded_project.anat_available_config = ["_".join((os.path.basename(s)[:-11].split("_")[0],os.path.basename(s)[:-11].split("_")[1])) for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','*_anatomical_config.ini'))]
            # else:
            #     loaded_project.anat_available_config = [os.path.basename(s)[:-11].split("_")[0] for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','*_anatomical_config.ini'))]

            print "loaded_project.anat_available_config : "
            print loaded_project.anat_available_config

            if len(loaded_project.anat_available_config) > 1:
                loaded_project.anat_available_config.sort()
                loaded_project.anat_config_to_load = loaded_project.anat_available_config[0]
                anat_config_selected = loaded_project.configure_traits(view='anat_select_config_to_load')

                if not anat_config_selected:
                    return 0
            else:
                loaded_project.anat_config_to_load = loaded_project.anat_available_config[0]

            print "Anatomical config to load: %s"%loaded_project.anat_config_to_load
            loaded_project.anat_config_file = os.path.join(loaded_project.base_directory,'derivatives','%s_anatomical_config.ini' % loaded_project.anat_config_to_load)
            print "Anatomical config file: %s"%loaded_project.anat_config_file

            loaded_project.subject = get_anat_process_detail(loaded_project,'Global','subject')
            loaded_project.subject_sessions = ["ses-%s"%s for s in bids_layout.get(target='session', return_type='id', subject=loaded_project.subject.split('-')[1])]

            if len(loaded_project.subject_sessions)>0:

                loaded_project.subject_session = get_anat_process_detail(loaded_project,'Global','subject_session')
                print "Selected session : "+loaded_project.subject_session
            else:
                loaded_project.subject_sessions = ['']
                loaded_project.subject_session = ''
                print "No session"

            #remove_aborded_interface_pickles(local_dir=loaded_project.base_directory,subject=loaded_project.subject,session=loaded_project.subject_session)

            loaded_project.parcellation_scheme = get_anat_process_detail(loaded_project,'parcellation_stage','parcellation_scheme')
            loaded_project.atlas_info = get_anat_process_detail(loaded_project,'parcellation_stage','atlas_info')
            loaded_project.freesurfer_subjects_dir = get_anat_process_detail(loaded_project,'segmentation_stage','freesurfer_subjects_dir')
            loaded_project.freesurfer_subject_id = get_anat_process_detail(loaded_project,'segmentation_stage','freesurfer_subject_id')

            self.anat_pipeline= init_anat_project(loaded_project, False)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    update_anat_last_processed(loaded_project, self.anat_pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.ui.context["object"].project_info = loaded_project
                    ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_anat_pipeline,'subject')
                    ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_anat_pipeline,'subject_session')
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

            loaded_project.dmri_available_config = []

            subjid = loaded_project.subject.split("-")[1]
            subj_sessions = bids_layout.get(target='session', return_type='id', subject=subjid)

            if len(subj_sessions) > 0:
                for subj_session in subj_sessions:
                    config_file = os.path.join(loaded_project.base_directory,'derivatives',"%s_ses-%s_diffusion_config.ini" % (loaded_project.subject, subj_session))
                    print "config_file: %s " % config_file
                    if os.path.isfile(config_file) and subj_session == loaded_project.subject_session.split("-")[1]:
                        loaded_project.dmri_available_config.append( "%s_ses-%s" % (loaded_project.subject, subj_session) )
            else:
                config_file = os.path.join(loaded_project.base_directory,'derivatives',"sub-%s_diffusion_config.ini" % (loaded_project.subject))
                if os.path.isfile(config_file):
                    loaded_project.dmri_available_config.append( "%s" % (loaded_project.subject) )
                    print "no session"

            # loaded_project.dmri_available_config = [os.path.basename(s)[:-11] for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','%s_diffusion_config.ini'%loaded_project.subject))]

            print "loaded_project.dmri_available_config:"
            print loaded_project.dmri_available_config

            if len(loaded_project.dmri_available_config) > 1:
                loaded_project.dmri_available_config.sort()
                loaded_project.dmri_config_to_load = loaded_project.dmri_available_config[0]
                dmri_config_selected = loaded_project.configure_traits(view='dmri_select_config_to_load')
                if not dmri_config_selected:
                    return 0
            elif not loaded_project.dmri_available_config:
                loaded_project.dmri_config_to_load = '%s_diffusion' % loaded_project.subject
            else:
                loaded_project.dmri_config_to_load = loaded_project.dmri_available_config[0]

            print "Diffusion config to load: %s"%loaded_project.dmri_config_to_load
            loaded_project.dmri_config_file = os.path.join(loaded_project.base_directory,'derivatives','%s_diffusion_config.ini' % loaded_project.dmri_config_to_load)
            print "Diffusion config file: %s"%loaded_project.dmri_config_file

            if os.path.isfile(loaded_project.dmri_config_file):
                print "Load existing diffusion config file"
                loaded_project.process_type = get_dmri_process_detail(loaded_project,'Global','process_type')
                loaded_project.diffusion_imaging_model = get_dmri_process_detail(loaded_project,'Global','diffusion_imaging_model')

                dmri_inputs_checked, self.dmri_pipeline= init_dmri_project(loaded_project, bids_layout, False)
                if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                    if dmri_inputs_checked:
                        update_dmri_last_processed(loaded_project, self.dmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_dmri_pipeline,'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_dmri_pipeline,'subject_session')
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
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_diffusion_imaging_model,'diffusion_imaging_model')
            else:
                dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(loaded_project, bids_layout, True)
                print "No existing config for diffusion pipeline found - Created new diffusion pipeline with default parameters"
                if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                    if dmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_dmri_pipeline,'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_dmri_pipeline,'subject_session')
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
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_diffusion_imaging_model,'diffusion_imaging_model')

            if len(subj_sessions) > 0:
                for subj_session in subj_sessions:
                    config_file = os.path.join(loaded_project.base_directory,'derivatives',"%s_ses-%s_fMRI_config.ini" % (loaded_project.subject, subj_session))
                    print "config_file: %s " % config_file
                    if os.path.isfile(config_file) and subj_session == loaded_project.subject_session.split("-")[1]:
                        loaded_project.fmri_available_config.append( "%s_ses-%s" % (loaded_project.subject, subj_session) )
            else:
                config_file = os.path.join(loaded_project.base_directory,'derivatives',"sub-%s_fMRI_config.ini" % (loaded_project.subject))
                if os.path.isfile(config_file):
                    loaded_project.fmri_available_config.append( "sub-%s" % (loaded_project.subject) )
                    print "no session"

            # loaded_project.fmri_available_config = [os.path.basename(s)[:-11] for s in glob.glob(os.path.join(loaded_project.base_directory,'derivatives','%s_fMRI_config.ini'%loaded_project.subject))]

            print "loaded_project.fmri_available_config:"
            print loaded_project.fmri_available_config

            if len(loaded_project.fmri_available_config) > 1:
                loaded_project.fmri_available_config.sort()
                loaded_project.fmri_config_to_load = loaded_project.fmri_available_config[0]
                fmri_config_selected = loaded_project.configure_traits(view='fmri_select_config_to_load')
                if not fmri_config_selected:
                    return 0
            elif not loaded_project.fmri_available_config:
                loaded_project.fmri_config_to_load = '%s_fMRI' % loaded_project.subject
            else:
                loaded_project.fmri_config_to_load = loaded_project.fmri_available_config[0]

            print "fMRI config to load: %s"%loaded_project.fmri_config_to_load
            loaded_project.fmri_config_file = os.path.join(loaded_project.base_directory,'derivatives','%s_fMRI_config.ini' % loaded_project.fmri_config_to_load)
            print "fMRI config file: %s"%loaded_project.fmri_config_file

            if os.path.isfile(loaded_project.fmri_config_file):
                print "Load existing diffusion config file"
                loaded_project.process_type = get_fmri_process_detail(loaded_project,'Global','process_type')

                fmri_inputs_checked, self.fmri_pipeline= init_fmri_project(loaded_project, bids_layout, False)
                if self.fmri_pipeline != None: #and self.fmri_pipeline != None:
                    if fmri_inputs_checked:
                        update_fmri_last_processed(loaded_project, self.fmri_pipeline)
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_fmri_pipeline,'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_fmri_pipeline,'subject_session')
                        self.fmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.fmri_pipeline.atlas_info = loaded_project.atlas_info
                        self.fmri_pipeline.subjects_dir = loaded_project.freesurfer_subjects_dir
                        self.fmri_pipeline.subject_id = loaded_project.freesurfer_subject_id
                        ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        ui_info.ui.context["object"].fmri_pipeline.number_of_cores = ui_info.ui.context["object"].project_info.number_of_cores
                        #ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        #self.diffusion_ready = True
                        self.fmri_inputs_checked = fmri_inputs_checked
                        ui_info.ui.context["object"].project_info.fmri_available = self.fmri_inputs_checked
                        fmri_save_config(self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)
                        self.project_loaded = True
            else:
                fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(loaded_project, bids_layout, True)
                print "No existing config for diffusion pipeline found - Created new fMRI pipeline with default parameters"
                if self.fmri_pipeline != None: #and self.fmri_pipeline != None:
                    if fmri_inputs_checked:
                        ui_info.ui.context["object"].project_info = loaded_project
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_subject_fmri_pipeline,'subject')
                        ui_info.ui.context["object"].project_info.on_trait_change(ui_info.ui.context["object"].update_session_fmri_pipeline,'subject_session')
                        # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                        # self.fmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                        self.fmri_pipeline.number_of_cores  = loaded_project.number_of_cores
                        print "number of cores (pipeline): %s" % self.fmri_pipeline.number_of_cores
                        # print "diffusion_imaging_model (pipeline): %s" % self.fmri_pipeline.diffusion_imaging_model
                        # print "diffusion_imaging_model ui_info: %s" % ui_info.ui.context["object"].project_info.diffusion_imaging_model
                        self.fmri_pipeline.parcellation_scheme = loaded_project.parcellation_scheme
                        self.fmri_pipeline.atlas_info = loaded_project.atlas_info
                        self.fmri_pipeline.subjects_dir = loaded_project.freesurfer_subjects_dir
                        self.fmri_pipeline.subject_id = loaded_project.freesurfer_subject_id
                        ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                        #self.diffusion_ready = True
                        fmri_save_config(self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)
                        self.fmri_inputs_checked = fmri_inputs_checked
                        ui_info.ui.context["object"].project_info.fmri_available = self.fmri_inputs_checked
                        self.project_loaded = True


    def update_subject_anat_pipeline(self,ui_info):
        ui_info.handler = self

        self.anat_pipeline.subject = ui_info.project_info.subject
        self.anat_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.anat_pipeline.global_conf.subject_session = updated_project.subject_session
            self.anat_pipeline.subject_directory =  os.path.join(updated_project.base_directory,updated_project.subject,updated_project.subject_session)
            updated_project.anat_config_file = os.path.join(updated_project.base_directory,'derivatives','%s_%s_anatomical_config.ini' % (updated_project.subject,updated_project.subject_session))
        else:
            self.anat_pipeline.global_conf.subject_session = ''
            self.anat_pipeline.subject_directory =  os.path.join(updated_project.base_directory,updated_project.subject)
            updated_project.anat_config_file = os.path.join(updated_project.base_directory,'derivatives','%s_anatomical_config.ini' % (updated_project.subject))

        self.anat_pipeline.derivatives_directory =  os.path.join(updated_project.base_directory,'derivatives')

        if os.path.isfile(updated_project.anat_config_file):
            print "Existing anatomical config file for subject %s: %s" % ( updated_project.subject,updated_project.anat_config_file)

            updated_project.parcellation_scheme = get_anat_process_detail(updated_project,'parcellation_stage','parcellation_scheme')
            updated_project.atlas_info = get_anat_process_detail(updated_project,'parcellation_stage','atlas_info')
            updated_project.freesurfer_subjects_dir = get_anat_process_detail(updated_project,'segmentation_stage','freesurfer_subjects_dir')
            updated_project.freesurfer_subject_id = get_anat_process_detail(updated_project,'segmentation_stage','freesurfer_subject_id')

            self.anat_pipeline= init_anat_project(updated_project, False)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    update_anat_last_processed(updated_project, self.anat_pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(ui_info.update_subject_anat_pipeline,'subject')
                    ui_info.project_info.on_trait_change(ui_info.update_session_anat_pipeline,'subject_session')
                    ui_info.anat_pipeline = self.anat_pipeline
                    ui_info.anat_pipeline.number_of_cores = ui_info.project_info.number_of_cores
                    #ui_info.dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline, ui_info.project_info.anat_config_file)
                    self.project_loaded = True
                    self.anat_outputs_checked, msg = self.anat_pipeline.check_output()
                    print "anat_outputs_checked : %s" % self.anat_outputs_checked
                    # ui_info.anat_pipeline.flow = ui_info.anat_pipeline.create_pipeline_flow()
        else:
            print("Unprocessed anatomical data for subject %s"%updated_project.subject)
            self.anat_pipeline = init_anat_project(updated_project, True)
            if self.anat_pipeline != None: #and self.dmri_pipeline != None:
                anat_inputs_checked = self.anat_pipeline.check_input(bids_layout)
                if anat_inputs_checked:
                    # update_last_processed(new_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(ui_info.update_subject_anat_pipeline,'subject')
                    ui_info.project_info.on_trait_change(ui_info.update_session_anat_pipeline,'subject_session')
                    self.anat_pipeline.number_of_cores = new_project.number_of_cores
                    # self.anat_pipeline.flow = self.anat_pipeline.create_pipeline_flow()
                    ui_info.anat_pipeline = self.anat_pipeline
                    #ui_info.dmri_pipeline = self.dmri_pipeline
                    self.anat_inputs_checked = anat_inputs_checked
                    ui_info.project_info.t1_available = self.anat_inputs_checked
                    anat_save_config(self.anat_pipeline, ui_info.project_info.anat_config_file)
                    self.project_loaded = True

            ui_info.project_info.parcellation_scheme = get_anat_process_detail(new_project,'parcellation_stage','parcellation_scheme')
            ui_info.project_info.freesurfer_subjects_dir = get_anat_process_detail(new_project,'segmentation_stage','freesurfer_subjects_dir')
            ui_info.project_info.freesurfer_subject_id = get_anat_process_detail(new_project,'segmentation_stage','freesurfer_subject_id')
            # ui_info.project_info.atlas_info = get_anat_process_detail(new_project,'parcellation_stage','atlas_info')

        return ui_info

    def update_subject_dmri_pipeline(self,ui_info):
        self.dmri_pipeline.subject = ui_info.project_info.subject
        self.dmri_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.dmri_pipeline.global_conf.subject_session = updated_project.subject_session
            self.dmri_pipeline.subject_directory =  os.path.join(updated_project.base_directory,updated_project.subject,updated_project.subject_session)
            updated_project.dmri_config_file = os.path.join(updated_project.base_directory,'derivatives','%s_%s_diffusion_config.ini' % (updated_project.subject,updated_project.subject_session))
        else:
            self.dmri_pipeline.global_conf.subject_session = ''
            self.dmri_pipeline.subject_directory =  os.path.join(updated_project.base_directory,updated_project.subject)
            updated_project.dmri_config_file = os.path.join(updated_project.base_directory,'derivatives','%s_diffusion_config.ini' % (updated_project.subject))

        self.dmri_pipeline.derivatives_directory =  os.path.join(updated_project.base_directory,'derivatives')

        if os.path.isfile(updated_project.dmri_config_file):
            print "Load existing diffusion config file"
            updated_project.process_type = get_dmri_process_detail(updated_project,'Global','process_type')
            updated_project.diffusion_imaging_model = get_dmri_process_detail(updated_project,'diffusion_stage','diffusion_imaging_model')

            dmri_inputs_checked, self.dmri_pipeline= init_dmri_project(updated_project, bids_layout, False)
            if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                if dmri_inputs_checked:
                    update_dmri_last_processed(updated_project, self.dmri_pipeline)
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(ui_info.update_subject_dmri_pipeline,'subject')
                    ui_info.project_info.on_trait_change(ui_info.update_session_dmri_pipeline,'subject_session')
                    self.dmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.dmri_pipeline.atlas_info = updated_project.atlas_info
                    ui_info.dmri_pipeline = self.dmri_pipeline
                    ui_info.dmri_pipeline.number_of_cores = ui_info.project_info.number_of_cores
                    #ui_info.dmri_pipeline = self.dmri_pipeline
                    #self.diffusion_ready = True
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.project_info.dmri_available = self.dmri_inputs_checked
                    dmri_save_config(self.dmri_pipeline, ui_info.project_info.dmri_config_file)
                    self.project_loaded = True
                    ui_info.project_info.on_trait_change(ui_info.update_diffusion_imaging_model,'diffusion_imaging_model')
        else:
            dmri_inputs_checked, self.dmri_pipeline = init_dmri_project(updated_project, bids_layout, True)
            print "No existing config for diffusion pipeline found - Created new diffusion pipeline with default parameters"
            if self.dmri_pipeline != None: #and self.dmri_pipeline != None:
                if dmri_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(ui_info.update_subject_dmri_pipeline,'subject')
                    ui_info.project_info.on_trait_change(ui_info.update_session_dmri_pipeline,'subject_session')
                    # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                    # self.dmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                    self.dmri_pipeline.number_of_cores  = updated_project.number_of_cores
                    print "number of cores (pipeline): %s" % self.dmri_pipeline.number_of_cores
                    # print "diffusion_imaging_model (pipeline): %s" % self.dmri_pipeline.diffusion_imaging_model
                    # print "diffusion_imaging_model ui_info: %s" % ui_info.project_info.diffusion_imaging_model
                    self.dmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.dmri_pipeline.atlas_info = updated_project.atlas_info
                    ui_info.dmri_pipeline = self.dmri_pipeline
                    #self.diffusion_ready = True
                    dmri_save_config(self.dmri_pipeline, ui_info.project_info.dmri_config_file)
                    self.dmri_inputs_checked = dmri_inputs_checked
                    ui_info.project_info.dmri_available = self.dmri_inputs_checked
                    self.project_loaded = True
                    ui_info.project_info.on_trait_change(ui_info.update_diffusion_imaging_model,'diffusion_imaging_model')

        return ui_info

    def show_bidsapp_window(self,ui_info):
        print "Show BIDS App interface"
        ui_info.ui.context["object"].show_bidsapp_interface()


    def update_subject_fmri_pipeline(self,ui_info):
        ui_info.handler = self

        print ui_info
        print ui_info.project_info

        self.fmri_pipeline.subject = ui_info.project_info.subject
        self.fmri_pipeline.global_conf.subject = ui_info.project_info.subject

        updated_project = ui_info.project_info

        bids_layout = BIDSLayout(updated_project.base_directory)

        if len(updated_project.subject_sessions) > 0:
            self.fmri_pipeline.global_conf.subject_session = updated_project.subject_session
            self.fmri_pipeline.subject_directory =  os.path.join(updated_project.base_directory,ui_info.project_info.subject,updated_project.subject_session)
            updated_project.fmri_config_file = os.path.join(updated_project.base_directory,'derivatives','%s_%s_fMRI_config.ini' % (updated_project.subject,updated_project.subject_session))
        else:
            self.fmri_pipeline.global_conf.subject_session = ''
            self.fmri_pipeline.subject_directory =  os.path.join(updated_project.base_directory,ui_info.project_info.subject)
            updated_project.fmri_config_file = os.path.join(updated_project.base_directory,'derivatives','%s_fMRI_config.ini' % (updated_project.subject))

        self.fmri_pipeline.derivatives_directory =  os.path.join(updated_project.base_directory,'derivatives')

        print("fMRI config file loaded/created : %s"%updated_project.fmri_config_file)

        if os.path.isfile(updated_project.fmri_config_file):
            print("Load existing fMRI config file for subject %s"%updated_project.subject)
            updated_project.process_type = get_fmri_process_detail(updated_project,'Global','process_type')

            fmri_inputs_checked, self.fmri_pipeline= init_fmri_project(updated_project, bids_layout, False)
            if self.fmri_pipeline != None: #and self.fmri_pipeline != None:
                if fmri_inputs_checked:
                    update_fmri_last_processed(updated_project, self.fmri_pipeline)
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(ui_info.update_subject_fmri_pipeline,'subject')
                    ui_info.project_info.on_trait_change(ui_info.update_session_fmri_pipeline,'subject_session')
                    self.fmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.fmri_pipeline.atlas_info = updated_project.atlas_info
                    self.fmri_pipeline.subjects_dir = updated_project.freesurfer_subjects_dir
                    self.fmri_pipeline.subject_id = updated_project.freesurfer_subject_id
                    ui_info.fmri_pipeline = self.fmri_pipeline

                    ui_info.fmri_pipeline.number_of_cores = ui_info.project_info.number_of_cores
                    #ui_info.fmri_pipeline = self.fmri_pipeline
                    #self.diffusion_ready = True
                    self.fmri_inputs_checked = fmri_inputs_checked
                    ui_info.project_info.fmri_available = self.fmri_inputs_checked
                    fmri_save_config(self.fmri_pipeline, ui_info.project_info.fmri_config_file)
                    self.project_loaded = True
        else:
            fmri_inputs_checked, self.fmri_pipeline = init_fmri_project(updated_project, bids_layout, True)
            print "No existing config for fMRI pipeline found but available fMRI data- Created new fMRI pipeline with default parameters"
            if self.fmri_pipeline != None: #and self.fmri_pipeline != None:
                if fmri_inputs_checked:
                    ui_info.project_info = updated_project
                    ui_info.project_info.on_trait_change(ui_info.update_subject_fmri_pipeline,'subject')
                    ui_info.project_info.on_trait_change(ui_info.update_session_fmri_pipeline,'subject_session')
                    # new_project.configure_traits(view='diffusion_imaging_model_select_view')
                    # self.fmri_pipeline.diffusion_imaging_model = new_project.diffusion_imaging_model
                    self.fmri_pipeline.number_of_cores  = updated_project.number_of_cores
                    print "number of cores (pipeline): %s" % self.fmri_pipeline.number_of_cores
                    # print "diffusion_imaging_model (pipeline): %s" % self.fmri_pipeline.diffusion_imaging_model
                    # print "diffusion_imaging_model ui_info: %s" % ui_info.project_info.diffusion_imaging_model
                    self.fmri_pipeline.parcellation_scheme = updated_project.parcellation_scheme
                    self.fmri_pipeline.atlas_info = updated_project.atlas_info
                    self.fmri_pipeline.subjects_dir = updated_project.freesurfer_subjects_dir
                    self.fmri_pipeline.subject_id = updated_project.freesurfer_subject_id
                    ui_info.fmri_pipeline = self.fmri_pipeline
                    #self.diffusion_ready = True
                    fmri_save_config(self.fmri_pipeline, ui_info.project_info.fmri_config_file)
                    self.fmri_inputs_checked = fmri_inputs_checked
                    ui_info.project_info.fmri_available = self.fmri_inputs_checked
                    self.project_loaded = True

        return ui_info

    def save_anat_config_file(self, ui_info):
        dialog = FileDialog(action="save as", default_filename=os.path.join(ui_info.ui.context["object"].project_info.base_directory,'code','ref_anatomical_config.ini'))
        dialog.open()
        if dialog.return_code == OK:
            anat_save_config(ui_info.ui.context["object"].anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.anat_config_file:
                shutil.copy(ui_info.ui.context["object"].project_info.anat_config_file, dialog.path)

    def load_anat_config_file(self, ui_info):
        dialog = FileDialog(action="open", wildcard="*anatomical_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.anat_config_file:
                shutil.copy(dialog.path, ui_info.ui.context["object"].project_info.anat_config_file)
            anat_load_config(self.anat_pipeline, ui_info.ui.context["object"].project_info.anat_config_file)
            #TODO: load_config (anat_ or dmri_ ?)

    def save_dmri_config_file(self, ui_info):
        dialog = FileDialog(action="save as", default_filename=os.path.join(ui_info.ui.context["object"].project_info.base_directory,'code','ref_diffusion_config.ini'))
        dialog.open()
        if dialog.return_code == OK:
            dmri_save_config(ui_info.ui.context["object"].dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.dmri_config_file:
                shutil.copy(ui_info.ui.context["object"].project_info.dmri_config_file, dialog.path)

    def load_dmri_config_file(self, ui_info):
        dialog = FileDialog(action="open", wildcard="*diffusion_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.dmri_config_file:
                shutil.copy(dialog.path, ui_info.ui.context["object"].project_info.dmri_config_file)
            dmri_load_config(self.dmri_pipeline, ui_info.ui.context["object"].project_info.dmri_config_file)

    def save_fmri_config_file(self, ui_info):
        dialog = FileDialog(action="save as", default_filename=os.path.join(ui_info.ui.context["object"].project_info.base_directory,'code','ref_fMRI_config.ini'))
        dialog.open()
        if dialog.return_code == OK:
            fmri_save_config(ui_info.ui.context["object"].fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)
            if dialog.path != ui_info.ui.context["object"].project_info.fmri_config_file:
                shutil.copy(ui_info.ui.context["object"].project_info.fmri_config_file, dialog.path)

    def load_fmri_config_file(self, ui_info):
        dialog = FileDialog(action="open", wildcard="*diffusion_config.ini")
        dialog.open()
        if dialog.return_code == OK:
            if dialog.path != ui_info.ui.context["object"].project_info.fmri_config_file:
                shutil.copy(dialog.path, ui_info.ui.context["object"].project_info.fmri_config_file)
            fmri_load_config(self.fmri_pipeline, ui_info.ui.context["object"].project_info.fmri_config_file)


class ProjectHandlerV2(Handler):
    project_loaded = Bool(False)

    anat_pipeline = Instance(HasTraits)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    anatomical_processed = Bool(False)

    dmri_pipeline = Instance(HasTraits)
    dmri_inputs_checked = Bool(False)
    dmri_processed = Bool(False)

    fmri_pipeline = Instance(HasTraits)
    fmri_inputs_checked = Bool(False)
    fmri_processed = Bool(False)

    def load_dataset(self, ui_info):
        print('Load dataset')

        loaded_project = gui.CMP_Project_Info()
        np_res = loaded_project.configure_traits(view='open_view')

        is_bids = False

        t1_available = False
        t2_available = False
        diffusion_available = False
        fmri_available = False

        print "Base dir: %s" % loaded_project.base_directory
        try:
            bids_layout = BIDSLayout(loaded_project.base_directory)
            loaded_project.bids_layout = bids_layout
            is_bids = True

            loaded_project.subjects = []
            for subj in bids_layout.get_subjects():
                print "sub: %s" % subj
                if 'sub-'+str(subj) not in loaded_project.subjects:
                    loaded_project.subjects.append('sub-'+str(subj))
            # loaded_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
            loaded_project.subjects.sort()

            print "Available subjects : "
            print loaded_project.subjects
            loaded_project.number_of_subjects = len(loaded_project.subjects)

            loaded_project.subject=loaded_project.subjects[0]
            print(loaded_project.subject)

            subject = loaded_project.subject.split('-')[1]


            sessions = bids_layout.get(target='session', return_type='id', subject=subject)

            print "Sessions: "
            print sessions

            if len(sessions) > 0:
                loaded_project.subject_sessions = ['ses-{}'.format(sessions[0])]
                loaded_project.subject_session = 'ses-{}'.format(sessions[0])
            else:
                loaded_project.subject_sessions = ['']
                loaded_project.subject_session = ''

            query_files = [f.filename for f in bids_layout.get(subject=subject, type='T1w', extensions=['nii', 'nii.gz'])]
            if len(query_files) > 0:
                print("T1w available: {}".format(query_files))
                t1_available = True

            query_files = [f.filename for f in bids_layout.get(subject=subject, type='T2w', extensions=['nii', 'nii.gz'])]
            if len(query_files) > 0:
                print("T2w available: {}".format(query_files))
                t2_available = True

            query_files = [f.filename for f in bids_layout.get(subject=subject, type='dwi', extensions=['nii', 'nii.gz'])]
            if len(query_files) > 0:
                print("DWI available: {}".format(query_files))
                diffusion_available = True

            query_files = [f.filename for f in bids_layout.get(subject=subject, type='bold', extensions=['nii', 'nii.gz'])]
            if len(query_files) > 0:
                print("BOLD available: {}".format(query_files))
                fmri_available = True

            # types = bids_layout.get_types()
            # print(types)
            # for typ in sorted(types):
            #
            #     if typ == 'dwi':
            #         print "%s available" % typ
            #         diffusion_available = True
            #
            #     if typ == 'T1w':
            #         print "%s available" % typ
            #         t1_available = True
            #
            #     if typ == 'T2w':
            #         print "%s available" % typ
            #         t2_available = True
            #
            #     if typ == 'bold':
            #         print "%s available" % typ
            #         fmri_available = True

        except:
            error(message="Invalid BIDS dataset. Please see documentation for more details.",title="BIDS error")
            return

        ui_info.ui.context["object"].project_info = loaded_project

        anat_inputs_checked = False
        if t1_available:
            anat_inputs_checked = True

        dmri_inputs_checked = False
        if t1_available and diffusion_available:
            dmri_inputs_checked = True

        fmri_inputs_checked = False
        if t1_available and fmri_available:
            fmri_inputs_checked = True

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        if anat_inputs_checked:

            self.anat_pipeline = Anatomical_pipeline.AnatomicalPipeline(loaded_project)
            self.anat_pipeline.number_of_cores = loaded_project.number_of_cores

            code_directory = os.path.join(loaded_project.base_directory,'code')

            anat_config_file = os.path.join(loaded_project.base_directory,'code','ref_anatomical_config.ini')
            loaded_project.anat_config_file = anat_config_file

            if self.anat_pipeline!= None and not os.path.isfile(anat_config_file): #and dmri_pipeline!= None:
                if not os.path.exists(code_directory):
                    try:
                        os.makedirs(code_directory)
                    except os.error:
                        print "%s was already existing" % code_directory
                    finally:
                        print "Created directory %s" % code_directory

                anat_save_config(self.anat_pipeline, loaded_project.anat_config_file)
                print("Created reference anatomical config file :  %s"%loaded_project.anat_config_file)

            else:
                anat_conf_loaded = anat_load_config(self.anat_pipeline, loaded_project.anat_config_file)
                print("Loaded reference anatomical config file :  %s"%loaded_project.anat_config_file)

            self.anat_pipeline.config_file = loaded_project.anat_config_file

            # update_last_processed(loaded_project, self.pipeline) # Not required as the project is new, so no update should be done on processing status
            ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
            loaded_project.t1_available = self.anat_inputs_checked

            loaded_project.parcellation_scheme = get_anat_process_detail(loaded_project,'parcellation_stage','parcellation_scheme')
            loaded_project.freesurfer_subjects_dir = get_anat_process_detail(loaded_project,'segmentation_stage','freesurfer_subjects_dir')
            loaded_project.freesurfer_subject_id = get_anat_process_detail(loaded_project,'segmentation_stage','freesurfer_subject_id')

            ui_info.ui.context["object"].project_info = loaded_project
            # ui_info.ui.context["object"].handler = self

            self.project_loaded = True

            if dmri_inputs_checked:
                self.dmri_pipeline = Diffusion_pipeline.DiffusionPipeline(loaded_project)
                self.dmri_pipeline.number_of_cores  = loaded_project.number_of_cores
                self.dmri_pipeline.parcellation_scheme = ui_info.ui.context["object"].project_info.parcellation_scheme

                code_directory = os.path.join(loaded_project.base_directory,'code')

                dmri_config_file = os.path.join(code_directory,'ref_diffusion_config.ini')
                loaded_project.dmri_config_file = dmri_config_file

                self.dmri_pipeline.config_file = dmri_config_file

                if not os.path.isfile(dmri_config_file) and self.dmri_pipeline!= None: #and dmri_pipeline!= None:

                    #Look for diffusion acquisition model information from filename (acq-*)
                    if loaded_project.subject_session != '':
                        session = loaded_project.subject_session.split('-')[1]
                        diffusion_imaging_models = [i for i in bids_layout.get(subject=subject, session=session, type='dwi', target='acq', return_type='id', extensions=['nii', 'nii.gz'])]

                        if len(diffusion_imaging_models)>0:
                            if len(diffusion_imaging_models)>1:
                                loaded_project.dmri_bids_acqs = diffusion_imaging_models
                                loaded_project.configure_traits(view='dmri_bids_acq_view')
                            else:
                                loaded_project.dmri_bids_acq = diffusion_imaging_models[0]

                            if ('dsi' in loaded_project.dmri_bids_acq) or ('DSI' in loaded_project.dmri_bids_acq):
                                loaded_project.diffusion_imaging_model = 'DSI'
                            elif ('dti' in loaded_project.dmri_bids_acq) or ('DTI' in loaded_project.dmri_bids_acq):
                                loaded_project.diffusion_imaging_model = 'DTI'
                            elif ('hardi' in loaded_project.dmri_bids_acq) or ('HARDI' in loaded_project.dmri_bids_acq):
                                loaded_project.diffusion_imaging_model = 'HARDI'
                            else:
                                loaded_project.diffusion_imaging_model = 'DTI'
                        else:
                            loaded_project.configure_traits(view='diffusion_imaging_model_select_view')

                        files = [f.filename for f in bids_layout.get(subject=subject, session=session, type='dwi', extensions=['nii', 'nii.gz'])]

                        if (loaded_project.dmri_bids_acq != ''):
                            for file in files:
                                if (loaded_project.dmri_bids_acq in file):
                                    dwi_file = file
                                    break
                        else:
                            dwi_file = files[0]
                    else:
                        diffusion_imaging_models = [i for i in bids_layout.get(subject=subject, type='dwi', target='acq', return_type='id', extensions=['nii', 'nii.gz'])]

                        if len(diffusion_imaging_models)>0:
                            if len(diffusion_imaging_models)>1:
                                loaded_project.dmri_bids_acqs = diffusion_imaging_models
                                loaded_project.configure_traits(view='dmri_bids_acq_view')
                            else:
                                loaded_project.dmri_bids_acq = diffusion_imaging_models[0]

                            if ('dsi' in loaded_project.dmri_bids_acq) or ('DSI' in loaded_project.dmri_bids_acq):
                                loaded_project.diffusion_imaging_model = 'DSI'
                            elif ('dti' in loaded_project.dmri_bids_acq) or ('DTI' in loaded_project.dmri_bids_acq):
                                loaded_project.diffusion_imaging_model = 'DTI'
                            elif ('hardi' in loaded_project.dmri_bids_acq) or ('HARDI' in loaded_project.dmri_bids_acq):
                                loaded_project.diffusion_imaging_model = 'HARDI'
                            else:
                                loaded_project.diffusion_imaging_model = 'DTI'
                        else:
                            loaded_project.dmri_bids_acq = ''
                            loaded_project.configure_traits(view='diffusion_imaging_model_select_view')

                        files = [f.filename for f in bids_layout.get(subject=subject, type='dwi', extensions=['nii', 'nii.gz'])]

                        if (loaded_project.dmri_bids_acq != ''):
                            for file in files:
                                if (loaded_project.dmri_bids_acq in file):
                                    dwi_file = file
                                    break
                        else:
                            dwi_file = files[0]
                    max_volume_idx = nib.load(dwi_file).shape[3] - 1
                    self.dmri_pipeline.stages["Preprocessing"].end_vol = max_volume_idx
                    self.dmri_pipeline.stages["Preprocessing"].max_vol = max_volume_idx
                    self.dmri_pipeline.diffusion_imaging_model  = loaded_project.diffusion_imaging_model
                    self.dmri_pipeline.global_conf.diffusion_imaging_model  = loaded_project.diffusion_imaging_model
                    self.dmri_pipeline.global_conf.dmri_bids_acq  = loaded_project.dmri_bids_acq
                    self.dmri_pipeline.stages["Diffusion"].diffusion_imaging_model  = loaded_project.diffusion_imaging_model
                    dmri_save_config(self.dmri_pipeline, dmri_config_file)
                    print("Created reference diffusion config file :  %s"%loaded_project.dmri_config_file)
                else:
                    print("Loaded reference diffusion config file :  %s"%loaded_project.dmri_config_file)
                    dmri_conf_loaded = dmri_load_config(self.dmri_pipeline, loaded_project.dmri_config_file)
                    # TODO: check if diffusion imaging model (DSI/DTI/HARDI) is correct/valid.

                ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                loaded_project.dmri_available = self.dmri_inputs_checked

                ui_info.ui.context["object"].project_info = loaded_project
                # ui_info.ui.context["object"].handler = self

                self.project_loaded = True

                if fmri_inputs_checked: #and self.fmri_pipeline != None:
                    self.fmri_pipeline = FMRI_pipeline.fMRIPipeline(loaded_project)
                    self.fmri_pipeline.number_of_cores  = loaded_project.number_of_cores
                    self.fmri_pipeline.parcellation_scheme = ui_info.ui.context["object"].project_info.parcellation_scheme

                    code_directory = os.path.join(loaded_project.base_directory,'code')

                    fmri_config_file = os.path.join(code_directory,'ref_fMRI_config.ini')
                    loaded_project.fmri_config_file = fmri_config_file

                    self.fmri_pipeline.config_file = fmri_config_file

                    if not os.path.isfile(fmri_config_file) and self.fmri_pipeline!= None: #and fmri_pipeline!= None:
                        fmri_save_config(self.fmri_pipeline, fmri_config_file)
                        print("Created reference fMRI config file :  %s"%loaded_project.fmri_config_file)
                    else:
                        print("Loaded reference fMRI config file :  %s"%loaded_project.fmri_config_file)
                        fmri_conf_loaded = fmri_load_config(self.fmri_pipeline, loaded_project.fmri_config_file)

                    ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                    loaded_project.fmri_available = self.fmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project
                    # ui_info.ui.context["object"].handler = self

                    self.project_loaded = True


class CMP_BIDSAppWindowHandler(Handler):

    docker_process = Instance(Popen)

    def check_settings(self, ui_info):
        ui_info.ui.context["object"].settings_checked = True
        ui_info.ui.context["object"].handler = self

        if os.path.isdir(ui_info.ui.context["object"].bids_root):
            print("BIDS root directory : {}".format(ui_info.ui.context["object"].bids_root))
        else:
            print("Error: BIDS root invalid!")
            ui_info.ui.context["object"].settings_checked = False

        # if not ui_info.ui.context["object"].list_of_subjects_to_be_processed.empty():
        #     print("List of subjects to be processed : {}".format(ui_info.ui.context["object"].list_of_subjects_to_be_processed))
        # else:
        #     print("Warning: List of subjects empty!")

        if os.path.isfile(ui_info.ui.context["object"].anat_config):
            print("Anatomical configuration file : {}".format(ui_info.ui.context["object"].anat_config))
        else:
            print("Error: Configuration file for anatomical pipeline not existing!")
            ui_info.ui.context["object"].settings_checked = False

        if os.path.isfile(ui_info.ui.context["object"].dmri_config):
            print("Diffusion configuration file : {}".format(ui_info.ui.context["object"].dmri_config))
        else:
            print("Warning: Configuration file for diffusion pipeline not existing!")

        if os.path.isfile(ui_info.ui.context["object"].fmri_config):
            print("fMRI configuration file : {}".format(ui_info.ui.context["object"].fmri_config))
        else:
            print("Warning: Configuration file for fMRI pipeline not existing!")

        if os.path.isfile(ui_info.ui.context["object"].fs_license):
            print("Freesurfer license : {}".format(ui_info.ui.context["object"].fs_license))
        else:
            print("Error: Invalid Freesurfer license ({})!".format(ui_info.ui.context["object"].fs_license))
            ui_info.ui.context["object"].settings_checked = False

        if os.path.isdir(ui_info.ui.context["object"].fs_average):
            print("fsaverage directory : {}".format(ui_info.ui.context["object"].fs_average))
        else:
            print("Error: fsaverage directory ({}) not existing!".format(ui_info.ui.context["object"].fs_average))
            ui_info.ui.context["object"].settings_checked = False

        print("Valid inputs for BIDS App : {}".format(ui_info.ui.context["object"].settings_checked))
        print("Docker running ? {}".format(ui_info.ui.context["object"].docker_running))
        return True

    def start_bidsapp_process(self, ui_info, participant_label):
        cmd = ['docker','run','-it','--rm',
               '-v', '{}:/bids_dataset'.format(ui_info.ui.context["object"].bids_root),
               '-v', '{}/derivatives:/outputs'.format(ui_info.ui.context["object"].bids_root),
               '-v', '{}:/bids_dataset/derivatives/freesurfer/fsaverage'.format(ui_info.ui.context["object"].fs_average),
               '-v', '{}:/opt/freesurfer/license.txt'.format(ui_info.ui.context["object"].fs_license),
               '-v', '{}:/code/ref_anatomical_config.ini'.format(ui_info.ui.context["object"].anat_config)]

        if ui_info.ui.context["object"].run_dmri_pipeline:
            cmd.append('-v')
            cmd.append('{}:/code/ref_diffusion_config.ini'.format(ui_info.ui.context["object"].dmri_config))

        if ui_info.ui.context["object"].run_fmri_pipeline:
            cmd.append('-v')
            cmd.append('{}:/code/ref_fMRI_config.ini'.format(ui_info.ui.context["object"].fmri_config))

        cmd.append('-u')
        cmd.append('{}:{}'.format(os.geteuid(),os.getegid()))

        cmd.append('sebastientourbier/connectomemapper-bidsapp:latest')
        cmd.append('/bids_dataset')
        cmd.append('/outputs')
        cmd.append('participant')

        cmd.append('--participant_label')
        cmd.append('{}'.format(participant_label))

        cmd.append('--anat_pipeline_config')
        cmd.append('/code/ref_anatomical_config.ini')

        if ui_info.ui.context["object"].run_dmri_pipeline:
            cmd.append('--dwi_pipeline_config')
            cmd.append('/code/ref_diffusion_config.ini')

        if ui_info.ui.context["object"].run_fmri_pipeline:
            cmd.append('--func_pipeline_config')
            cmd.append('/code/ref_fMRI_config.ini')


        print(cmd)

        log_filename = os.path.join(ui_info.ui.context["object"].bids_root,'derivatives/cmp','sub-{}_log-cmpbidsapp.txt'.format(participant_label))

        with open(log_filename, 'w+') as log:
            proc = Popen(cmd, stdout=log, stderr=log)
            #docker_process.communicate()

        return proc

    def manage_bidsapp_procs(self, proclist):
        for proc in proclist:
            if proc.poll() is not None:
                proclist.remove(proc)

    def start_bids_app(self, ui_info):
        print("Start BIDS App")

        maxprocs = multiprocessing.cpu_count()
        processes = []

        ui_info.ui.context["object"].docker_running = True

        fix_dataset_directory_in_pickles(local_dir=ui_info.ui.context["object"].bids_root,mode='bidsapp')

        for label in ui_info.ui.context["object"].list_of_subjects_to_be_processed:
            while len(processes) == maxprocs:
                self.manage_bidsapp_procs(processes)

            proc = self.start_bidsapp_process(ui_info, label)
            processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        fix_dataset_directory_in_pickles(local_dir=ui_info.ui.context["object"].bids_root,mode='local')

        print('Processing with BIDS App Finished')

        ui_info.ui.context["object"].docker_running = False

        # cmd = ['docke
        return True

    def stop_bids_app(self, ui_info):
        print("Stop BIDS App")
        #self.docker_process.kill()
        ui_info.ui.context["object"].docker_running = False
        return True
