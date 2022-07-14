# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""This module defines the `connectomemapper3` script that is called by the BIDS App."""

# General imports
import sys
import os
import argparse
import subprocess
import warnings

# CMP imports
import cmp.project
from cmp.info import __version__, __copyright__
from cmtklib.util import print_error, print_blue, print_warning


# Filter warning
warnings.filterwarnings(
    "ignore",
    message="""UserWarning: No valid root directory found for domain 'derivatives'.
                                Falling back on the Layout's root directory. If this isn't the intended behavior,
                                make sure the config file for this domain includes a 'root' key.""",
)


def info():
    """Print version of copyright."""
    print_blue(f"\nConnectome Mapper {__version__}")
    print_warning(f"{__copyright__}\n")


# Checks the needed dependencies. We call directly the functions instead
# of just checking existence in $PATH in order to handle missing libraries.
# Note that not all the commands give the awaited 1 exit code...
def dep_check():
    """Check if dependencies are installed.

    This includes for the moment:
      * FSL
      * FreeSurfer
    """
    nul = open(os.devnull, "w")

    error = ""

    # Check for FSL
    if subprocess.call("fslorient", stdout=nul, stderr=nul, shell=True) != 255:
        error = """  .. ERROR: FSL not installed or not working correctly. Check that the
FSL_DIR variable is exported and the fsl.sh setup script is sourced."""

    # Check for Freesurfer
    if subprocess.call("mri_info", stdout=nul, stderr=nul, shell=True) != 1:
        error = """  .. ERROR: FREESURFER not installed or not working correctly. Check that the
FREESURFER_HOME variable is exported and the SetUpFreeSurfer.sh setup
script is sourced."""

    # Check for MRtrix
    # if subprocess.call("mrconvert", stdout=nul, stderr=nul,shell=True) != 255:
    #     error = """MRtrix3 not installed or not working correctly. Check that PATH variable is updated with MRtrix3 binary (bin) directory."""

    # Check for DTK
    #     if subprocess.call("dti_recon", stdout=nul, stderr=nul, shell=True) != 0 or "DSI_PATH" not in os.environ:
    #         error = """Diffusion Toolkit not installed or not working correctly. Check that
    # the DSI_PATH variable is exported and that the dtk binaries (e.g. dti_recon) are in
    # your path."""

    # Check for DTB
    #     if subprocess.call("DTB_dtk2dir", stdout=nul, stderr=nul, shell=True) != 1:
    #         error = """DTB binaries not installed or not working correctly. Check that the
    # DTB binaries (e.g. DTB_dtk2dir) are in your path and don't give any error."""

    if error != "":
        print_error(error)
        sys.exit(2)


def create_parser():
    """Create the parser of connectomemapper3 python script.

    Returns
    -------
    p : argparse.ArgumentParser
        Parser
    """
    p = argparse.ArgumentParser(description="Connectome Mapper 3 main script.")

    p.add_argument(
        "--bids_dir",
        required=True,
        help="The directory with the input dataset "
        "formatted according to the BIDS standard.",
    )

    p.add_argument(
        "--output_dir",
        required=True,
        help="The directory where the output files "
        "should be stored. If you are running group level analysis "
        "this folder should be prepopulated with the results of the "
        "participant level analysis.",
    )

    p.add_argument(
        "--participant_label",
        required=True,
        help="The label of the participant"
        "that should be analyzed. The label corresponds to"
        "<participant_label> from the BIDS spec "
        '(so it DOES include "sub-"',
    )

    p.add_argument(
        "--anat_pipeline_config",
        required=True,
        help="Configuration .json file for processing stages of "
        "the anatomical MRI processing pipeline",
    )

    p.add_argument(
        "--dwi_pipeline_config",
        help="Configuration .json file for processing stages of "
        "the diffusion MRI processing pipeline",
    )

    p.add_argument(
        "--func_pipeline_config",
        help="Configuration .json file for processing stages of "
        "the fMRI processing pipeline",
    )

    p.add_argument(
        "--eeg_pipeline_config",
        help="Configuration .json file for processing stages of "
        "the EEG source reconstruction pipeline"
    )

    p.add_argument(
        "--session_label",
        help="The label of the participant session "
        "that should be analyzed. The label corresponds to "
        "<session_label> from the BIDS spec "
        '(so it DOES include "ses-"',
    )

    p.add_argument(
        "--number_of_threads",
        type=int,
        help="The number of OpenMP threads used for multi-threading by "
        "Freesurfer, FSL, MRtrix3, Dipy, AFNI "
        "(Set to [Number of available CPUs -1] by default).",
    )

    p.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"Connectome Mapper version {__version__}",
    )

    return p


def main():
    """Main function that runs the connectomemapper3 python script.

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    # Parse script arguments
    parser = create_parser()
    args = parser.parse_args()

    # Check dependencies
    dep_check()

    # Add current directory to the path, useful if DTB_ bins not installed
    os.environ["PATH"] += os.pathsep + os.path.dirname(sys.argv[0])

    # Version and copyright message
    info()

    exit_code = cmp.project.run_individual(
        bids_dir=args.bids_dir,
        output_dir=args.output_dir,
        participant_label=args.participant_label,
        session_label=args.session_label,
        anat_pipeline_config=args.anat_pipeline_config,
        dwi_pipeline_config=args.dwi_pipeline_config,
        func_pipeline_config=args.func_pipeline_config,
        eeg_pipeline_config=args.eeg_pipeline_config,
        number_of_threads=args.number_of_threads,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
