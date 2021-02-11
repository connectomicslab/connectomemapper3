# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Module that defines CMTK Config file function."""
import os
import configparser
import json
from collections.abc import Iterable


def get_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the global section of the JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.CMP_Project_Info)
        Instance of :class:`cmp.project.CMP_Project_Info` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.config_file, 'r') as f:
        config = json.load(f)
    return config[section][detail]


def get_anat_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the anatomical JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.CMP_Project_Info)
        Instance of :class:`cmp.project.CMP_Project_Info` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.anat_config_file, 'r') as f:
        config = json.load(f)
    res = None
    if detail == "atlas_info":
        res = eval(config[section][detail])
    else:
        res = config[section][detail]
    return res


def get_dmri_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the diffusion JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.CMP_Project_Info)
        Instance of :class:`cmp.project.CMP_Project_Info` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.dmri_config_file, 'r') as f:
        config = json.load(f)
    return config[section][detail]


def get_fmri_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the fMRI JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.CMP_Project_Info)
        Instance of :class:`cmp.project.CMP_Project_Info` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.fmri_config_file, 'r') as f:
        config = json.load(f)
    return config[section][detail]


def anat_save_config(pipeline, config_path):
    """Save the configuration file of an anatomical pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.anatomical.anatomical.AnatomicalPipeline)
        Instance of AnatomicalPipeline

    config_path : string
        Path of the configuration file
    """
    config = configparser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in list(pipeline.stages.values()):
        config.add_section(stage.name)
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key:  # subconfig
                stage_sub_keys = [prop for prop in list(
                        keyval.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key + '.' + sub_key,
                               getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)

    config.add_section('Multi-processing')
    config.set('Multi-processing', 'number_of_cores', pipeline.number_of_cores)

    # with open(config_path, 'w') as configfile:
    #     config.write(configfile)

    # print('Config file (anat) saved as {}'.format(config_path))

    config_json = {}

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):

            if isinstance(value, Iterable) and not isinstance(value, str):
                config_json[section][name] = [x for x in value if x]
            elif isinstance(value, bool):
                config_json[section][name] = [value]
            elif value and not isinstance(value, str):
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                config_json[section][name] = [value.strip()]
            else:
                print(f'Type: {type(value)} / value : {value}')
                config_json[section][name] = []

            if len(config_json[section][name]) == 1:
                config_json[section][name] = config_json[section][name][0]
            elif len(config_json[section][name]) == 0:
                config_json[section][name] = ''

            if config_json[section][name] == '':
                del config_json[section][name]

    # config_json_path = '.'.join([os.path.splitext(config_path)[0], 'json'])
    with open(config_path, 'w') as outfile:
        json.dump(config_json, outfile, indent=4)

    print('Config json file (anat) saved as {}'.format(config_path))


def anat_load_config_json(pipeline, config_path):
    """Load the JSON configuration file of an anatomical pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.anatomical.anatomical.AnatomicalPipeline)
        Instance of AnatomicalPipeline

    config_path : string
        Path of the JSON configuration file
    """
    print('>> Load anatomical config file : {}'.format(config_path))
    # datalad_is_available = is_tool('datalad')
    with open(config_path, 'r') as f:
        config = json.load(f)

    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
            if key in config['Global'].keys():
                conf_value = config['Global'][key]
                setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits().keys()) if
                      'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(sub_config.traits().keys()) if
                                  'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        tmp_key = key + '.' + sub_key
                        if tmp_key in config[stage.name].keys():
                            conf_value = config[stage.name][tmp_key]
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key in config[stage.name].keys():
                        conf_value = config[stage.name][key]
                    try:
                        conf_value = eval(conf_value)
                    except Exception:
                        pass
                    setattr(stage.config, key, conf_value)
                except Exception:
                    pass
    setattr(pipeline, 'number_of_cores', int(
            config['Multi-processing']['number_of_cores']))

    return True


def dmri_save_config(pipeline, config_path):
    """Save the INI configuration file of a diffusion pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.diffusion.diffusion.DiffusionPipeline)
        Instance of DiffusionPipeline

    config_path : string
        Path of the INI configuration file
    """
    config = configparser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    print(global_keys)
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in list(pipeline.stages.values()):
        config.add_section(stage.name)
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key:  # subconfig
                stage_sub_keys = [prop for prop in list(
                        keyval.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key + '.' + sub_key,
                               getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)

    config.add_section('Multi-processing')
    config.set('Multi-processing', 'number_of_cores', pipeline.number_of_cores)

    # with open(config_path, 'w') as configfile:
    #     config.write(configfile)

    # print('Config file (dwi) saved as {}'.format(config_path))

    config_json = {}

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):

            if isinstance(value, Iterable) and not isinstance(value, str):
                config_json[section][name] = [x for x in value if x]
            elif isinstance(value, bool):
                config_json[section][name] = [value]
            elif value and not isinstance(value, str):
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                config_json[section][name] = [value.strip()]
            else:
                print(f'Type: {type(value)} / value : {value}')
                config_json[section][name] = []

            if len(config_json[section][name]) == 1:
                config_json[section][name] = config_json[section][name][0]
            elif len(config_json[section][name]) == 0:
                config_json[section][name] = ''

            if config_json[section][name] == '':
                del config_json[section][name]

    # config_json_path = '.'.join([os.path.splitext(config_path)[0], 'json'])
    with open(config_path, 'w') as outfile:
        json.dump(config_json, outfile, indent=4)

    print('Config json file (dwi) saved as {}'.format(config_path))


def dmri_load_config_json(pipeline, config_path):
    """Load the JSON configuration file of a diffusion pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.diffusion.diffusion.DiffusionPipeline)
        Instance of DiffusionPipeline

    config_path : string
        Path of the JSON configuration file
    """
    print('>> Load diffusion config file : {}'.format(config_path))
    # datalad_is_available = is_tool('datalad')
    with open(config_path, 'r') as f:
        config = json.load(f)

    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
            if key in config['Global'].keys():
                conf_value = config['Global'][key]
                setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits().keys()) if
                      'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(sub_config.traits().keys()) if
                                  'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        tmp_key = key + '.' + sub_key
                        if tmp_key in config[stage.name].keys():
                            conf_value = config[stage.name][tmp_key]
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key in config[stage.name].keys():
                        conf_value = config[stage.name][key]
                    try:
                        conf_value = eval(conf_value)
                    except Exception:
                        pass
                    setattr(stage.config, key, conf_value)
                except Exception:
                    pass
    setattr(pipeline, 'number_of_cores', int(
            config['Multi-processing']['number_of_cores']))

    return True


def fmri_save_config(pipeline, config_path):
    """Save the INI configuration file of a fMRI pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.functional.fMRI.fMRIPipeline)
        Instance of fMRIPipeline

    config_path : string
        Path of the INI configuration file
    """
    config = configparser.RawConfigParser()
    config.add_section('Global')
    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set('Global', key, getattr(pipeline.global_conf, key))
    for stage in list(pipeline.stages.values()):
        config.add_section(stage.name)
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if 'config' in key:  # subconfig
                stage_sub_keys = [prop for prop in list(
                        keyval.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    config.set(stage.name, key + '.' + sub_key,
                               getattr(keyval, sub_key))
            else:
                config.set(stage.name, key, keyval)

    config.add_section('Multi-processing')
    config.set('Multi-processing', 'number_of_cores', pipeline.number_of_cores)

    # with open(config_path, 'w') as configfile:
    #     config.write(configfile)

    # print('Config file (fMRI) saved as {}'.format(config_path))

    config_json = {}

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):

            if isinstance(value, Iterable) and not isinstance(value, str):
                config_json[section][name] = [x for x in value if x]
            elif isinstance(value, bool):
                config_json[section][name] = [value]
            elif value and not isinstance(value, str):
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                config_json[section][name] = [value.strip()]
            else:
                print(f'Type: {type(value)} / value : {value}')
                config_json[section][name] = []

            if len(config_json[section][name]) == 1:
                config_json[section][name] = config_json[section][name][0]
            elif len(config_json[section][name]) == 0:
                config_json[section][name] = ''

            if config_json[section][name] == '':
                del config_json[section][name]

    # config_json_path = '.'.join([os.path.splitext(config_path)[0], 'json'])
    with open(config_path, 'w') as outfile:
        json.dump(config_json, outfile, indent=4)

    print('Config json file (fMRI) saved as {}'.format(config_path))


def fmri_load_config_json(pipeline, config_path):
    """Load the JSON configuration file of a fMRI pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.functional.fMRI.fMRIPipeline)
        Instance of fMRIPipeline

    config_path : string
        Path of the INI configuration file
    """
    print('>> Load fMRI config file : {}'.format(config_path))
    # datalad_is_available = is_tool('datalad')
    with open(config_path, 'r') as f:
        config = json.load(f)

    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
            if key in config['Global'].keys():
                conf_value = config['Global'][key]
                setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits().keys()) if
                      'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(sub_config.traits().keys()) if
                                  'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        tmp_key = key + '.' + sub_key
                        if tmp_key in config[stage.name].keys():
                            conf_value = config[stage.name][tmp_key]
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key in config[stage.name].keys():
                        conf_value = config[stage.name][key]
                    try:
                        conf_value = eval(conf_value)
                    except Exception:
                        pass
                    setattr(stage.config, key, conf_value)
                except Exception:
                    pass
    setattr(pipeline, 'number_of_cores', int(
            config['Multi-processing']['number_of_cores']))

    return True
