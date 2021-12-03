# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module defines the `connectome_mapper_singularity` script that wraps calls to the Singularity BIDS APP image."""

# General imports
import sys

# Own imports
from cmp.info import __version__
from cmp.parser import get
from cmp.bidsappmanager.core import run


def create_singularity_cmd(args):
    """Function that creates and returns the BIDS App singularity run command.

    Parameters
    ----------
    args : dict
        Dictionary of parsed input argument in the form::

            {
                'bids_dir': "/path/to/bids/dataset/directory",
                'output_dir': "/path/to/output/directory",
                'param_file': "/path/to/configuration/parameter/file",
                'analysis_level': "participant",
                'participant_label': ['01', '02', '03'],
                'openmp_nb_of_cores': 1,
                'nipype_nb_of_cores': 1,
                'masks_derivatives_dir': 'manual_masks'
            }

    Returns
    -------
    cmd : string
        String containing the command to be run via `subprocess.run()`
    """
    # Singularity run command prelude
    cmd = 'singularity run --containall '
    cmd += f'--bind {args.bids_dir}:/bids_dir '
    cmd += f'--bind {args.output_dir}:/output_dir '
    # cmd += f'--bind {args.param_file}:/bids_dir/code/participants_params.json '
    cmd += f'library://tourbier/mialsuperresolutiontoolkit-bidsapp:v{__version__} '

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

    optional_single_args = (
        "anat_pipeline_config", "dwi_pipeline_config", "func_pipeline_config",
        "number_of_threads", "number_of_participants_processed_in_parallel",
        "mrtrix_random_seed", "ants_random_seed", "ants_number_of_threads",
        "fs_license", "notrack"
    )

    for arg_name in optional_single_args:
        argument_value = getattr(args, arg_name)
        if argument_value:
            cmd += f'--{arg_name} {argument_value} '

    return cmd


def main():
    """Main function that creates and executes the BIDS App singularity command.

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    # Create and parse arguments
    parser = get()
    args = parser.parse_args()

    # Create the singularity run command
    cmd = create_singularity_cmd(args)

    # Execute the singularity run command
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
