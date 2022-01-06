# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module defines the `connectomemapper3_docker.py` script that wraps calls to the Docker BIDS APP image."""

# General imports
import sys

# Own imports
from cmp.parser import get_docker_wrapper_parser
from cmtklib.util import check_directory_exists
from cmtklib.process import run


def create_docker_cmd(args):
    """Function that creates and returns the BIDS App docker run command.

    Parameters
    ----------
    args : dict
        Dictionary of parsed input argument in the form::

            {
                'bids_dir': "/path/to/bids/dataset/directory",
                'output_dir': "/path/to/output/directory",
                'analysis_level': "participant",
                'participant_label': ['01', '02', '03'],
                'anat_pipeline_config': "/path/to/ref_anatomical_config.json",
                'dwi_pipeline_config': "/path/to/ref_diffusion_config.json",
                'func_pipeline_config': "/path/to/ref_fMRI_config.json",
                ('number_of_threads': 1,)
                ('number_of_participants_processed_in_parallel': 1,)
                ('mrtrix_random_seed': 1234,)
                ('ants_random_seed': 1234,)
                ('ants_number_of_threads': 2,)
                ('fs_license': "/path/to/license.txt",)
                ('notrack': True)
            }

    Returns
    -------
    cmd : string
        String containing the command to be run via `subprocess.run()`
    """
    # Docker run command prelude
    cmd = 'docker run -t --rm '
    cmd += '-u $(id -u):$(id -g) '
    if args.coverage:
        cmd += '--entrypoint /app/run_coverage_cmp3.sh '
    cmd += f'-v {args.bids_dir}:/bids_dir '
    cmd += f'-v {args.output_dir}:/output_dir '
    if args.config_dir:
        cmd += f'-v {args.config_dir}:/config '
    else:
        cmd += f'-v {args.bids_dir}/code:/config '
    if args.fs_license:
        cmd += f'-v {args.fs_license}:/bids_dir/code/license.txt '

    cmd += f'{args.docker_image} '

    # Standard BIDS App inputs
    cmd += '/bids_dir '
    cmd += '/output_dir '
    cmd += f'{args.analysis_level} '
    if args.participant_label:
        cmd += '--participant_label '
        for label in args.participant_label:
            cmd += f'{label} '
    if args.session_label:
        cmd += '--session_label '
        for label in args.session_label:
            cmd += f'{label} '
    if args.anat_pipeline_config:
        cmd += f'--anat_pipeline_config /config/{args.anat_pipeline_config} '
    if args.dwi_pipeline_config:
        cmd += f'--dwi_pipeline_config /config/{args.dwi_pipeline_config} '
    if args.func_pipeline_config:
        cmd += f'--func_pipeline_config /config/{args.func_pipeline_config} '
    cmd += f'--fs_license /bids_dir/code/license.txt '
    optional_single_args = (
        "number_of_threads", "number_of_participants_processed_in_parallel",
        "mrtrix_random_seed", "ants_random_seed", "ants_number_of_threads",
    )
    for arg_name in optional_single_args:
        argument_value = getattr(args, arg_name)
        if argument_value:
            cmd += f'--{arg_name} {argument_value} '
    if args.notrack:
        cmd += "--notrack "
    if args.coverage:
        cmd += "--coverage"

    return cmd


def main():
    """Main function that creates and executes the BIDS App docker command.

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    # Create and parse arguments
    parser = get_docker_wrapper_parser()
    args = parser.parse_args()

    check_directory_exists(args.bids_dir)
    # Create the docker run command
    cmd = create_docker_cmd(args)

    # Execute the docker run command
    try:
        print(f'... cmd: {cmd}')
        run(cmd)
        exit_code = 0
    except Exception as e:
        print('Failed')
        print(e)
        exit_code = 1

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
