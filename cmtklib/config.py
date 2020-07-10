# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMTK Config file function
"""

import configparser

def get_process_detail(project_info, section, detail):
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.config_file)
    return config.get(section, detail)


def get_anat_process_detail(project_info, section, detail):
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.anat_config_file)
    res = None
    if detail == "atlas_info":
        res = eval(config.get(section, detail))
    else:
        res = config.get(section, detail)
    return res


def get_dmri_process_detail(project_info, section, detail):
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.dmri_config_file)
    return config.get(section, detail)


def get_fmri_process_detail(project_info, section, detail):
    config = configparser.ConfigParser()
    # print('Loading config from file: %s' % project_info.config_file)
    config.read(project_info.fmri_config_file)
    return config.get(section, detail)


def anat_save_config(pipeline, config_path):
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


def anat_load_config(pipeline, config_path):
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


def dmri_save_config(pipeline, config_path):
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


def dmri_load_config(pipeline, config_path):
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


def fmri_save_config(pipeline, config_path):
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


def fmri_load_config(pipeline, config_path):
    print('>> Load anatomical config file : {}'.format(config_path))
    config = configparser.ConfigParser()

    # datalad_is_available = is_tool('datalad')
    try:
        config.read(config_path)
    except configparser.MissingSectionHeaderError:
        print(
            '... error : file is a datalad git annex but it has not been retrieved yet. Please do datalad get ... and reload the dataset (File > Load BIDS Dataset...)')

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