# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Module that defines methods for handling CMP3 configuration files."""
import os
from pathlib import Path
import configparser
import json
from collections.abc import Iterable
from ast import literal_eval

from cmp.info import __version__
from cmtklib.util import BColors, print_warning, print_error, print_blue


def check_configuration_version(config):
    """Check the version of CMP3 used to generate a configuration.

    Parameters
    ----------
    config : Dict
        Dictionary of configuration parameters loaded from JSON file

    Returns
    -------
    is_same : bool
        `True` if the version used to generate the
        configuration matches the version currently used
        (`cmp.info.__version__`).
    """
    is_same = False
    if "version" in config["Global"].keys():
        if config["Global"]["version"] == __version__:
            print(
                BColors.OKGREEN
                + "  .. INFO: Generated with the same CMP3 version"
                + BColors.ENDC
            )
            is_same = True
        else:
            conf_version = config["Global"]["version"]
            print_warning(
                "  .. WARNING: CMP3 version used to generate the "
                + f"configuration files ({conf_version}) "
                + f" and version of CMP3 used ({__version__}) differ"
            )
            is_same = False
    return is_same


def check_configuration_format(config_path):
    """Check format of the configuration file.

    Parameters
    ----------
    config_path : string
        Path to pipeline configuration file

    Returns
    -------
    ext : '.ini' or '.json'
        Format extension of the pipeline configuration file
    """
    ext = None
    if ".ini" in config_path:
        ext = ".ini"
    elif ".json" in config_path:
        ext = ".json"
    return ext


def save_configparser_as_json(config, config_json_path, ini_mode=False, debug=False):
    """Save a ConfigParser to JSON file.

    Parameters
    ----------
    config : Instance(configparser.ConfigParser)
        Instance of ConfigParser

    config_json_path : string
        Output path of JSON configuration file

    ini_mode : bool
        If `True`, handles all content stored in strings

    debug : bool
        If `True`, show additional prints
    """
    config_json = {}

    # In the case of anatomical pipeline
    if "segmentation_stage" in config.sections():
        segmentation_tool = config["segmentation_stage"].get("seg_tool")
    if "parcellation_stage" in config.sections():
        parcellation_scheme = config["parcellation_stage"].get("parcellation_scheme")

    # In the case of diffusion pipeline
    if "diffusion_stage" in config.sections():
        recon_processing_tool = config["diffusion_stage"].get("recon_processing_tool")
        tracking_processing_tool = config["diffusion_stage"].get(
            "tracking_processing_tool"
        )

    for section in config.sections():
        config_json[section] = {}
        for name, value in config.items(section):
            # Keep only parameters that are used by the diffusion stage
            # of the diffusion pipeline. This simplifies the reading of
            # its configuration file
            if "diffusion_stage" in section:
                # Skip adding diffusion reconstruction parameters
                if recon_processing_tool == "Dipy":
                    if "mrtrix_recon_config" in name:
                        continue
                elif recon_processing_tool == "MRtrix":
                    if "dipy_recon_config" in name:
                        continue
                # Skip adding tracking parameters
                if tracking_processing_tool == "Dipy":
                    if "mrtrix_tracking_config" in name:
                        continue
                elif tracking_processing_tool == "MRtrix":
                    if "dipy_tracking_config" in name:
                        continue
            if "segmentation_stage" in section:
                if segmentation_tool == "Custom segmentation":
                    if "custom" not in name and "seg_tool" not in name:
                        if debug:
                            print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                        continue
                else:
                    if "custom" in name or "freesurfer_subjects_dir" in name or "freesurfer_subject_id" in name:
                        if debug:
                            print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                        continue

            if "parcellation_stage" in section:
                if parcellation_scheme == "Custom":
                    if "custom" not in name and "parcellation_scheme" not in name:
                        if debug:
                            print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                        continue
                else:
                    if "custom" in name:
                        if debug:
                            print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                        continue

            if "_editor" in name:
                if debug:
                    print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                continue

            if "log_visualization" in name:
                if debug:
                    print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                continue

            if "circular_layout" in name:
                if debug:
                    print_warning(f"  .. DEBUG: Skip parameter {section} / {name}")
                continue

            is_iterable = False

            if ini_mode:
                try:
                    if not(section == 'parcellation_stage' and name == 'ants_precision_type'):
                        value = literal_eval(value)
                        if debug:
                            print_warning(f"  .. DEBUG: String {value} evaluated")
                    else:
                        if debug:
                            print_warning(f"  .. DEBUG: String {value} not evaluated")
                except Exception:
                    if debug:
                        print_error(
                            f"  .. EXCEPTION: String {value} COULD NOT BE evaluated"
                        )
                    pass

            if isinstance(value, dict):
                if debug:
                    print_warning(
                        f"  .. DEBUG: Processing {section} / {name} / {value} as dict"
                    )
                config_json[section][name] = value
                is_iterable = True
            elif isinstance(value, list):
                if debug:
                    print_warning(
                        f"  .. DEBUG: Processing {section} / {name} / {value} as list"
                    )
                config_json[section][name] = value
                is_iterable = True
            elif isinstance(value, Iterable) and not isinstance(value, str):
                if debug:
                    print_warning(
                        f"  .. DEBUG: Processing {section} / {name} / {value} as iterable"
                    )
                config_json[section][name] = [x for x in value if x]
                is_iterable = True
            elif isinstance(value, bool):
                if debug:
                    print_warning(
                        f"  .. DEBUG: Processing {section} / {name} / {value} as boolean"
                    )
                config_json[section][name] = [value]
            elif value and not isinstance(value, str):
                if debug:
                    print_warning(
                        f"  .. DEBUG: Processing {section} / {name} / {value} as not a string"
                    )
                config_json[section][name] = [value]
            elif value and isinstance(value, str):
                value = value.strip()
                if value.isnumeric():
                    if debug:
                        print_warning(
                            f"  .. DEBUG: Processing {section} / {name} / {value} as number"
                        )
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                    config_json[section][name] = [value]
                else:
                    if debug:
                        print_warning(
                            f"  .. DEBUG: Processing {section} / {name} / {value} as string"
                        )
                    config_json[section][name] = [value]
            else:
                if debug:
                    print_warning(f"  .. DEBUG : Type: {type(value)} / value : {value}")
                config_json[section][name] = ""

            if not is_iterable:
                if len(config_json[section][name]) == 1:
                    config_json[section][name] = config_json[section][name][0]
                elif len(config_json[section][name]) == 0:
                    config_json[section][name] = ""

            if config_json[section][name] == "":
                del config_json[section][name]

    config_json["Global"]["version"] = __version__

    if debug:
        print_blue(f"  .. DEBUG: {config_json}")

    with open(config_json_path, "w") as outfile:
        json.dump(config_json, outfile, indent=4)


def convert_config_ini_2_json(config_ini_path):
    """Convert a configuration file in old INI format to new JSON format.

    Parameters
    ----------
    config_ini_path : string
        Path to configuration file in old INI format

    Returns
    -------
    config_json_path : string
        Path to converted configuration file in new JSON format
    """
    print(">> Load config file : {}".format(config_ini_path))
    config = configparser.ConfigParser()

    try:
        config.read(config_ini_path)
    except configparser.MissingSectionHeaderError:
        print_error(
            "  .. ERROR : file is a datalad git annex but it has not been retrieved yet."
            + " Please do datalad get ... and reload the dataset (File > Load BIDS Dataset...)"
        )

    config_json_path = ".".join([os.path.splitext(config_ini_path)[0], "json"])
    save_configparser_as_json(config, config_json_path, ini_mode=True)
    print(f"  .. Config file converted to JSON and saved as {config_json_path}")

    return config_json_path


def create_subject_configuration_from_ref(
    project, ref_conf_file, pipeline_type, multiproc_number_of_cores=1
):
    """Create the pipeline configuration file for an individual subject from a reference given as input.

    Parameters
    ----------
    project : cmp.project.ProjectInfo
        Instance of `cmp.project.CMP_Project_Info`

    ref_conf_file : string
        Reference configuration file

    pipeline_type : 'anatomical', 'diffusion', 'fMRI'
        Type of pipeline

    multiproc_number_of_cores : int
        Number of threads used by Nipype

    Returns
    -------
    subject_conf_file : string
        Configuration file of the individual subject
    """
    subject_derivatives_dir = os.path.join(project.output_directory)

    # print('project.subject_session: {}'.format(project.subject_session))

    if project.subject_session != "":  # Session structure
        # print('With session : {}'.format(project.subject_session))
        subject_conf_file = os.path.join(
            subject_derivatives_dir,
            f"cmp-{__version__}",
            project.subject,
            project.subject_session,
            "{}_{}_{}_config.json".format(
                project.subject, project.subject_session, pipeline_type
            ),
        )
    else:
        # print('With NO session ')
        subject_conf_file = os.path.join(
            subject_derivatives_dir,
            f"cmp-{__version__}",
            project.subject,
            "{}_{}_config.json".format(project.subject, pipeline_type),
        )

    if os.path.isfile(subject_conf_file):
        print_warning(
            "  .. WARNING: rewriting config file {}".format(subject_conf_file)
        )
        os.remove(subject_conf_file)

    # Change relative path to absolute path if needed (required when using singularity)
    if not os.path.isabs(ref_conf_file):
        ref_conf_file = os.path.abspath(ref_conf_file)

    with open(ref_conf_file, "r") as f:
        config = json.load(f)

    config["Global"]["subject"] = project.subject
    config["Global"]["subjects"] = project.subjects

    if "subject_sessions" in config["Global"].keys():
        config["Global"]["subject_sessions"] = project.subject_sessions

    if "subject_session" in config["Global"].keys():
        config["Global"]["subject_session"] = project.subject_session

    config["Multi-processing"]["number_of_cores"] = multiproc_number_of_cores

    subject_conf_file_dir = Path(subject_conf_file).parent
    if not os.path.isdir(str(subject_conf_file_dir)):
        os.makedirs(str(subject_conf_file_dir), exist_ok=True)
    with open(subject_conf_file, "w") as outfile:
        json.dump(config, outfile, indent=4)

    return subject_conf_file


def get_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the global section of the JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.ProjectInfo)
        Instance of :class:`cmp.project.ProjectInfo` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.config_file, "r") as f:
        config = json.load(f)
    return config[section][detail]


def get_anat_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the anatomical JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.ProjectInfo)
        Instance of :class:`cmp.project.ProjectInfo` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.anat_config_file, "r") as f:
        config = json.load(f)
    res = None
    if detail == "atlas_info":
        res = literal_eval(config[section][detail])
    else:
        res = config[section][detail]
    return res


def get_dmri_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the diffusion JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.ProjectInfo)
        Instance of :class:`cmp.project.ProjectInfo` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.dmri_config_file, "r") as f:
        config = json.load(f)
    return config[section][detail]


def get_fmri_process_detail_json(project_info, section, detail):
    """Get the value for a parameter key (detail) in the stage section of the fMRI JSON config file.

    Parameters
    ----------
    project_info : Instance(cmp.project.ProjectInfo)
        Instance of :class:`cmp.project.ProjectInfo` class

    section : string
        Stage section name

    detail : string
        Parameter key

    Returns
    -------
    The parameter value
    """
    with open(project_info.fmri_config_file, "r") as f:
        config = json.load(f)
    return config[section][detail]


def set_pipeline_attributes_from_config(pipeline, config, debug=False):
    """Set the pipeline stage attributes given a configuration.

    Parameters
    ----------
    pipeline : Instance(Pipeline)
        Instance of pipeline

    config : Dict
        Dictionary of configuration parameter loaded
        from the JSON configuration file

    debug : bool
        If `True`, show additional prints
    """
    global_keys = [
        prop
        for prop in list(pipeline.global_conf.traits().keys())
        if "trait" not in prop
    ]  # possibly dangerous..?
    for key in global_keys:
        if (
            key != "subject"
            and key != "subjects"
            and key != "subject_session"
            and key != "subject_sessions"
        ):
            if key in config["Global"].keys():
                conf_value = config["Global"][key]
                setattr(pipeline.global_conf, key, conf_value)

    for stage in list(pipeline.stages.values()):
        stage_keys = [
            prop for prop in list(stage.config.traits().keys()) if "trait" not in prop
        ]  # possibly dangerous..?
        for key in stage_keys:
            if "config" in key or key in ['custom_brainmask',
                                          'custom_wm_mask',
                                          'custom_gm_mask',
                                          'custom_csf_mask',
                                          'custom_aparcaseg',
                                          'custom_parcellation']:  # subconfig or custom inputs
                sub_config = getattr(stage.config, key)
                stage_sub_keys = [
                    prop
                    for prop in list(sub_config.traits().keys())
                    if "trait" not in prop
                ]
                for sub_key in stage_sub_keys:
                    if stage.name in config.keys():
                        tmp_key = key + "." + sub_key
                        if tmp_key in config[stage.name].keys():
                            conf_value = config[stage.name][tmp_key]
                            try:
                                # Convert parameter to proper expected type
                                if isinstance(getattr(sub_config, sub_key), tuple):
                                    conf_value = tuple(conf_value)
                                elif isinstance(getattr(sub_config, sub_key), bool):
                                    conf_value = bool(conf_value)
                                elif isinstance(getattr(sub_config, sub_key), list):
                                    conf_value = list(conf_value)
                                elif isinstance(getattr(sub_config, sub_key), dict):
                                    conf_value = dict(conf_value)
                                elif isinstance(getattr(sub_config, sub_key), int):
                                    conf_value = int(float(conf_value))
                                elif isinstance(getattr(sub_config, sub_key), float):
                                    conf_value = float(conf_value)
                                setattr(sub_config, sub_key, conf_value)
                                if debug:
                                    print(
                                        f" .. DEBUG: Set {sub_config}.{sub_key} to {conf_value}"
                                    )
                            except Exception as e:
                                if debug:
                                    print_warning(
                                        "  .. EXCEPTION raised while setting "
                                        + f"{sub_config}.{sub_key} to {conf_value}"
                                    )
                                    print_error(f"    {e}")
                                pass
            else:
                if stage.name in config.keys():
                    if key in config[stage.name].keys():
                        conf_value = config[stage.name][key]
                        try:
                            # Convert parameter to proper expected type
                            if isinstance(getattr(stage.config, key), tuple):
                                conf_value = tuple(conf_value)
                            elif isinstance(getattr(stage.config, key), bool):
                                conf_value = bool(conf_value)
                            elif isinstance(getattr(stage.config, key), list):
                                conf_value = list(conf_value)
                            elif isinstance(getattr(stage.config, key), dict):
                                conf_value = dict(conf_value)
                            elif isinstance(getattr(stage.config, key), int):
                                conf_value = int(float(conf_value))
                            elif isinstance(getattr(stage.config, key), float):
                                conf_value = float(conf_value)
                            setattr(stage.config, key, conf_value)
                            if debug:
                                print(
                                    f" .. DEBUG: Set {stage.config}.{key} to {conf_value}"
                                )
                        except Exception as e:
                            if debug:
                                print_warning(
                                    "  .. EXCEPTION raised while setting "
                                    + f"{stage.config}.{key} to {conf_value}"
                                )
                                print_error(f"   {e}")
                            pass

    setattr(
        pipeline, "number_of_cores", int(config["Multi-processing"]["number_of_cores"])
    )


def create_configparser_from_pipeline(pipeline, debug=False):
    """Create a `ConfigParser` object from a Pipeline instance.

    Parameters
    ----------
    pipeline : Instance(Pipeline)
        Instance of pipeline

    debug : bool
        If `True`, show additional prints

    Returns
    -------
    config : Instance(`configparser.ConfigParser`)
        Instance of ConfigParser
    """
    config = configparser.RawConfigParser()
    # Add global section and corresponding parameters
    config.add_section("Global")
    global_keys = [
        prop
        for prop in list(pipeline.global_conf.traits().keys())
        if "trait" not in prop
    ]  # possibly dangerous..?
    if debug:
        print(global_keys)
    for key in global_keys:
        # if key != "subject" and key != "subjects":
        config.set("Global", key, getattr(pipeline.global_conf, key))

    # Add stage section and corresponding parameters
    for stage in list(pipeline.stages.values()):
        config.add_section(stage.name)
        stage_keys = [
            prop for prop in list(stage.config.traits().keys()) if "trait" not in prop
        ]  # possibly dangerous..?
        for key in stage_keys:
            keyval = getattr(stage.config, key)
            if "config" in key or key in ['custom_brainmask',
                                          'custom_wm_mask',
                                          'custom_gm_mask',
                                          'custom_csf_mask',
                                          'custom_aparcaseg',
                                          'custom_parcellation']:  # subconfig or custom inputs
                stage_sub_keys = [
                    prop for prop in list(keyval.traits().keys()) if "trait" not in prop
                ]
                for sub_key in stage_sub_keys:
                    config.set(
                        stage.name, key + "." + sub_key, getattr(keyval, sub_key)
                    )
            else:
                config.set(stage.name, key, keyval)

    config.add_section("Multi-processing")
    config.set("Multi-processing", "number_of_cores", pipeline.number_of_cores)

    if debug:
        print(config)

    return config


def anat_save_config(pipeline, config_path):
    """Save the configuration file of an anatomical pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.anatomical.anatomical.AnatomicalPipeline)
        Instance of AnatomicalPipeline

    config_path : string
        Path of the JSON configuration file
    """
    config = create_configparser_from_pipeline(pipeline)
    save_configparser_as_json(config, config_path)
    print_blue("  .. SAVE: Config json file (anat) saved as {}".format(config_path))


def anat_load_config_json(pipeline, config_path):
    """Load the JSON configuration file of an anatomical pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.anatomical.anatomical.AnatomicalPipeline)
        Instance of AnatomicalPipeline

    config_path : string
        Path of the JSON configuration file
    """
    print_blue("  .. LOAD: Load anatomical config file : {}".format(config_path))
    # datalad_is_available = is_tool('datalad')
    with open(config_path, "r") as f:
        config = json.load(f)

    check_configuration_version(config)
    set_pipeline_attributes_from_config(pipeline, config)

    return True


def dmri_save_config(pipeline, config_path):
    """Save the INI configuration file of a diffusion pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.diffusion.diffusion.DiffusionPipeline)
        Instance of DiffusionPipeline

    config_path : string
        Path of the JSON configuration file
    """
    config = create_configparser_from_pipeline(pipeline)
    save_configparser_as_json(config, config_path)
    print_blue(
        "  .. SAVE: Config json file (diffusion) saved as {}".format(config_path)
    )


def dmri_load_config_json(pipeline, config_path):
    """Load the JSON configuration file of a diffusion pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.diffusion.diffusion.DiffusionPipeline)
        Instance of DiffusionPipeline

    config_path : string
        Path of the JSON configuration file
    """
    print_blue("  .. LOAD: Load diffusion config file : {}".format(config_path))
    # datalad_is_available = is_tool('datalad')
    with open(config_path, "r") as f:
        config = json.load(f)

    check_configuration_version(config)
    set_pipeline_attributes_from_config(pipeline, config)

    return True


def fmri_save_config(pipeline, config_path):
    """Save the INI configuration file of a fMRI pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.functional.fMRI.fMRIPipeline)
        Instance of fMRIPipeline

    config_path : string
        Path of the JSON configuration file
    """
    config = create_configparser_from_pipeline(pipeline)
    save_configparser_as_json(config, config_path)
    print_blue("  .. SAVE: Config json file (fMRI) saved as {}".format(config_path))


def fmri_load_config_json(pipeline, config_path):
    """Load the JSON configuration file of a fMRI pipeline.

    Parameters
    ----------
    pipeline : Instance(cmp.pipelines.functional.fMRI.fMRIPipeline)
        Instance of fMRIPipeline

    config_path : string
        Path of the JSON configuration file
    """
    print_blue("  .. LOAD: Load fMRI config file : {}".format(config_path))
    # datalad_is_available = is_tool('datalad')
    with open(config_path, "r") as f:
        config = json.load(f)

    check_configuration_version(config)
    set_pipeline_attributes_from_config(pipeline, config)

    return True
