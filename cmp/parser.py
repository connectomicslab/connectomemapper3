# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper 3 Commandline Parser."""

import argparse

from .info import __version__
from .info import __release_date__


def get():
    """Return the argparse parser of the BIDS App.

    Returns
    -------
    p : object
       Instance of :class:`argparse.ArgumentParser` class
    """

    p = argparse.ArgumentParser(
        description="Entrypoint script of the BIDS-App Connectome Mapper version {}".format(
            __version__
        )
    )
    p.add_argument(
        "bids_dir",
        help="The directory with the input dataset "
        "formatted according to the BIDS standard.",
    )
    p.add_argument(
        "output_dir",
        help="The directory where the output files "
        "should be stored. If you are running group level analysis "
        "this folder should be prepopulated with the results of the "
        "participant level analysis.",
    )
    p.add_argument(
        "analysis_level",
        help="Level of the analysis that will be performed. "
        "Multiple participant level analyses can be run independently "
        "(in parallel) using the same output_dir.",
        choices=["participant", "group"],
    )
    p.add_argument(
        "--participant_label",
        help="The label(s) of the participant(s) that should be analyzed. The label "
        "corresponds to sub-<participant_label> from the BIDS spec "
        '(so it does not include "sub-"). If this parameter is not '
        "provided all subjects should be analyzed. Multiple "
        "participants can be specified with a space separated list.",
        nargs="+",
    )

    p.add_argument(
        "--session_label",
        help="""The label(s) of the session that should be analyzed.
                                            The label corresponds to ses-<session_label> from the
                                            BIDS spec (so it does not include "ses-"). If this
                                            parameter is not provided all sessions should be
                                            analyzed. Multiple sessions can be specified
                                            with a space separated list.""",
        nargs="+",
    )

    p.add_argument(
        "--anat_pipeline_config",
        help="Configuration .txt file for processing stages of the anatomical MRI processing pipeline",
    )
    p.add_argument(
        "--dwi_pipeline_config",
        help="Configuration .txt file for processing stages of the diffusion MRI processing pipeline",
    )
    p.add_argument(
        "--func_pipeline_config",
        help="Configuration .txt file for processing stages of the fMRI processing pipeline",
    )

    p.add_argument(
        "--number_of_threads",
        type=int,
        help="The number of OpenMP threads used for multi-threading by "
        "Freesurfer (Set to [Number of available CPUs -1] by default).",
    )

    p.add_argument(
        "--number_of_participants_processed_in_parallel",
        default=1,
        type=int,
        help="The number of subjects to be processed in parallel (One by default).",
    )

    p.add_argument(
        "--mrtrix_random_seed",
        default=None,
        type=int,
        help="Fix MRtrix3 random number generator seed to the specified value",
    )

    p.add_argument(
        "--ants_random_seed",
        default=None,
        type=int,
        help="Fix ANTS random number generator seed to the specified value",
    )

    p.add_argument(
        "--ants_number_of_threads",
        default=None,
        type=int,
        help="Fix number of threads in ANTs. If not specified ANTs will "
        "use the same number as the number of OpenMP threads "
        "(see `----number_of_threads` option flag)",
    )

    p.add_argument("--fs_license", help="Freesurfer license.txt")

    p.add_argument(
        "--coverage", help="Run connectomemapper3 with coverage", action="store_true"
    )

    p.add_argument(
        "--notrack",
        help="Do not send event to Google analytics to report BIDS App execution, which is enabled by default.",
        action="store_true",
    )

    # p.add_argument('--skip_bids_validator', help='Whether or not to perform BIDS dataset validation',
    #                    action='store_true')
    p.add_argument(
        "-v",
        "--version",
        action="version",
        version="BIDS-App Connectome Mapper version {} \nRelease date: {}".format(
            __version__, __release_date__
        ),
    )
    return p


def get_docker_wrapper_parser():
    """Return the argparse parser of the Docker BIDS App.
    
    Returns
    -------
    p : object
       Instance of :class:`argparse.ArgumentParser` class
    """
    p = get()
    p.description = f"Entrypoint script of the BIDS-App Connectome Mapper version {__version__} via Docker."
    p.add_argument(
        '--docker_image',
        type=str,
        default=f'sebastientourbier/connectomemapper-bidsapp:{__version__}',
        help="The path to the docker image.",
    )
    p.add_argument(
        '--config_dir',
        type=str,
        default=None,
        help="The path to the directory containing the configuration files.",
    )
    return p


def get_singularity_wrapper_parser():
    """Return the argparse parser of the Singularity BIDS App.
    
    Returns
    -------
    p : object
       Instance of :class:`argparse.ArgumentParser` class
    """
    p = get()
    p.description = f"Entrypoint script of the BIDS-App Connectome Mapper version {__version__} via Singularity."
    p.add_argument(
        '--singularity_image',
        type=str,
        default=f'library://connectomicslab/default/connectomemapper-bidsapp:{__version__}',
        help="The path to the singularity image.",
    )
    p.add_argument(
        '--config_dir',
        type=str,
        default=None,
        help="The path to the directory containing the configuration files.",
    )
    return p
