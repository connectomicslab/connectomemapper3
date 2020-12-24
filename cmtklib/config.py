# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Module that defines CMTK Config file function."""
import os
import configparser
import json
from collections.abc import Iterable


def get_process_detail_ini(project_info, section, detail):
    """Get the value for a parameter key (detail) in the Global section of the INI config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.CMP_Project_Info)
        Instance of :class:`cmp.project.CMP_Project_Info` class

    section : string
        Stage name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.config_file)
    return config.get(section, detail)


def get_anat_process_detail_ini(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the anatomical INI config file.

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
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.anat_config_file)
    res = None
    if detail == "atlas_info":
        res = eval(config.get(section, detail))
    else:
        res = config.get(section, detail)
    return res


def get_dmri_process_detail_ini(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the diffusion INI config file.

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
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.dmri_config_file)
    return config.get(section, detail)


def get_fmri_process_detail_ini(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the fMRI INI config file.

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
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.fmri_config_file)
    return config.get(section, detail)


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

    with open(config_path, 'w') as configfile:
        config.write(configfile)

    print('Config file (anat) saved as {}'.format(config_path))

    config_json = {}

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):
            if isinstance(value, Iterable) and not isinstance(value, str):
                config_json[section][name] = [x for x in value if x]
            elif value and not isinstance(value, str):
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                config_json[section][name] = [value.strip()]
            else:
                config_json[section][name] = []
            if len(config_json[section][name]) == 1:
                config_json[section][name] = config_json[section][name][0]
            elif len(config_json[section][name]) == 0:
                config_json[section][name] = ''

    config_json_path = '.'.join([os.path.splitext(config_path)[0], 'json'])
    with open(config_json_path, 'w') as outfile:
        json.dump(config_json, outfile, indent=4)

    print('Config json file (anat) saved as {}'.format(config_json_path))


def anat_load_config_ini(pipeline, config_path):
    """Load the configuration file of an anatomical pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.anatomical.anatomical.AnatomicalPipeline)
        Instance of AnatomicalPipeline

    config_path : string
        Path of the configuration file
    """
    print('>> Load anatomical config file : {}'.format(config_path))
    config = configparser.ConfigParser()

    # datalad_is_available = is_tool('datalad')
    try:
        config.read(config_path)
    except configparser.MissingSectionHeaderError:
        print(
            '... error : file is a datalad git annex but it has not been retrieved yet.' +
            ' Please do datalad get ... and reload the dataset (File > Load BIDS Dataset...)'
            )

    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
            conf_value = config.get('Global', key)
            setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(
                    sub_config.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config.get(
                            stage.name, key + '.' + sub_key)
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key != 'modalities':
                        conf_value = config.get(stage.name, key)
                    try:
                        conf_value = eval(conf_value)
                    except Exception:
                        pass
                    setattr(stage.config, key, conf_value)
                except Exception:
                    pass
    setattr(pipeline, 'number_of_cores', int(
        config.get('Multi-processing', 'number_of_cores')))

    return True


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
            conf_value = config['Global'][key]
            setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(
                    sub_config.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config[stage.name][key + '.' + sub_key]
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key != 'modalities':
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

    with open(config_path, 'w') as configfile:
        config.write(configfile)

    print('Config file (dwi) saved as {}'.format(config_path))

    config_json = {}

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):
            if isinstance(value, Iterable) and not isinstance(value, str):
                config_json[section][name] = [x for x in value if x]
            elif value and not isinstance(value, str):
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                config_json[section][name] = [value.strip()]
            else:
                config_json[section][name] = []
            if len(config_json[section][name]) == 1:
                config_json[section][name] = config_json[section][name][0]
            elif len(config_json[section][name]) == 0:
                config_json[section][name] = ''

    config_json_path = '.'.join([os.path.splitext(config_path)[0], 'json'])
    with open(config_json_path, 'w') as outfile:
        json.dump(config_json, outfile, indent=4)

    print('Config json file (dwi) saved as {}'.format(config_json_path))


def dmri_load_config_ini(pipeline, config_path):
    """Load the INI configuration file of a diffusion pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.diffusion.diffusion.DiffusionPipeline)
        Instance of DiffusionPipeline

    config_path : string
        Path of the INI configuration file
    """
    print('>> Load diffusion config file : {}'.format(config_path))
    config = configparser.ConfigParser()

    # datalad_is_available = is_tool('datalad')
    try:
        config.read(config_path)
    except configparser.MissingSectionHeaderError:
        print('... error : file is a datalad git annex but it has not been retrieved yet.'
              'Please do datalad get ... and reload the dataset (File > Load BIDS Dataset...)')

    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions" and key != 'modalities':
            conf_value = config.get('Global', key)
            setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(
                    sub_config.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config.get(
                            stage.name, key + '.' + sub_key)
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key != 'modalities':
                        conf_value = config.get(stage.name, key)
                    try:
                        conf_value = eval(conf_value)
                    except Exception:
                        pass
                    setattr(stage.config, key, conf_value)
                except Exception:
                    pass
    setattr(pipeline, 'number_of_cores', int(
        config.get('Multi-processing', 'number_of_cores')))
    return True


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
            conf_value = config['Global'][key]
            setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(
                    sub_config.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config[stage.name][key + '.' + sub_key]
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key != 'modalities':
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

    with open(config_path, 'w') as configfile:
        config.write(configfile)

    print('Config file (fMRI) saved as {}'.format(config_path))

    config_json = {}

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):
            if isinstance(value, Iterable) and not isinstance(value, str):
                config_json[section][name] = [x for x in value if x]
            elif value and not isinstance(value, str):
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                config_json[section][name] = [value.strip()]
            else:
                config_json[section][name] = []
            if len(config_json[section][name]) == 1:
                config_json[section][name] = config_json[section][name][0]
            elif len(config_json[section][name]) == 0:
                config_json[section][name] = ''

    config_json_path = '.'.join([os.path.splitext(config_path)[0], 'json'])
    with open(config_json_path, 'w') as outfile:
        json.dump(config_json, outfile, indent=4)

    print('Config json file (fMRI) saved as {}'.format(config_json_path))


def fmri_load_config_ini(pipeline, config_path):
    """Load the INI configuration file of a fMRI pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.functional.fMRI.fMRIPipeline)
        Instance of fMRIPipeline

    config_path : string
        Path of the INI configuration file
    """
    print('>> Load fMRI config file : {}'.format(config_path))
    config = configparser.ConfigParser()

    # datalad_is_available = is_tool('datalad')
    try:
        config.read(config_path)
    except configparser.MissingSectionHeaderError:
        print(
            '... error : file is a datalad git annex but it has not been retrieved yet.'
            ' Please do datalad get ... and reload the dataset (File > Load BIDS Dataset...)')

    global_keys = [prop for prop in list(pipeline.global_conf.traits().keys()) if
                   'trait' not in prop]  # possibly dangerous..?
    for key in global_keys:
        if key != "subject" and key != "subjects" and key != "subject_session" and key != "subject_sessions":
            conf_value = config.get('Global', key)
            setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(
                    sub_config.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config.get(
                            stage.name, key + '.' + sub_key)
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key != 'modalities':
                        conf_value = config.get(stage.name, key)
                    try:
                        conf_value = eval(conf_value)
                    except Exception:
                        pass
                    setattr(stage.config, key, conf_value)
                except Exception:
                    pass
    setattr(pipeline, 'number_of_cores', int(
        config.get('Multi-processing', 'number_of_cores')))
    return True


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
            conf_value = config['Global'][key]
            setattr(pipeline.global_conf, key, conf_value)
    for stage in list(pipeline.stages.values()):
        stage_keys = [prop for prop in list(stage.config.traits(
        ).keys()) if 'trait' not in prop]  # possibly dangerous..?
        for key in stage_keys:
            if 'config' in key:  # subconfig
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [prop for prop in list(
                    sub_config.traits().keys()) if 'trait' not in prop]
                for sub_key in stage_sub_keys:
                    try:
                        conf_value = config[stage.name][key + '.' + sub_key]
                        try:
                            conf_value = eval(conf_value)
                        except Exception:
                            pass
                        setattr(sub_config, sub_key, conf_value)
                    except Exception:
                        pass
            else:
                try:
                    if key != 'modalities':
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
