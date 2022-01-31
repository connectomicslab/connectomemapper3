#!/usr/bin/env python
# -*-coding:Latin-1 -*

# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

# Remove warnings visible whenever you import scipy (or another package)
# that was compiled against an older numpy than is installed.
import multiprocessing
import subprocess
import shutil
import sys
import os
import warnings

from glob import glob
import numpy
# import http.client
# import urllib
import requests
from datetime import datetime

# Own imports
from cmtklib.util import BColors, print_error, print_blue
from cmtklib.config import (
    create_subject_configuration_from_ref,
    check_configuration_format,
    convert_config_ini_2_json
)
from cmp import parser
from cmp.info import __version__
from cmtklib.bids.io import (
    __cmp_directory__,
    __freesurfer_directory__,
    __nipype_directory__
)
from cmp.project import ProjectInfo, run_individual

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


def report_usage(event_category, event_action, event_label, verbose=False):
    """Send HTTP POST event to Google Analytics

    Parameters
    ----------
    event_category : string
        Event category

    event_action : string
        Event action type

    event_label : string
        Event label

    verbose : bool
        If True, verbose mode
    """
    tracking_id = 'UA-124877585-4'
    clientid_str = str(datetime.now())
    tracking_url = ('https://www.google-analytics.com/collect?v=1&t=event&'
                    'tid={}&cid={}&ec={}&ea={}&el={}&aip=1'.format(tracking_id,
                                                                   clientid_str,
                                                                   event_category,
                                                                   event_action,
                                                                   event_label))
    r = requests.post(tracking_url)

    if verbose:
        print(r)

    print(BColors.OKGREEN +
          '  .. INFO: Report execution to Google Analytics. \n' +
          'Thanks to support us in the task of finding new funds for CMP3 development!' +
          BColors.ENDC)


def create_cmp_command(project, run_anat, run_dmri, run_fmri, number_of_threads=1):
    """Create the command to run the `connectomemapper3` python script.

    Parameters
    ----------
    project : cmp.project.ProjectInfo
        Instance of `cmp.project.CMP_Project_Info`

    run_anat : bool
        If True, append the anatomical configuration file to the command

    run_dmri : bool
        If True, append the diffusion configuration file to the command

    run_fmri : bool
        If True, append the fMRI configuration file to the command

    number_of_threads : int
        Number of threads used OpenMP-parallelized tools
        (Default: 1)

    Returns
    -------
    Command : string
        The command to execute the `connectomemapper3` python script
    """
    cmd = ["connectomemapper3",
           "--bids_dir", project.base_directory,
           "--output_dir", project.output_directory,
           "--participant_label", project.subject]

    if project.subject_session != '':
        cmd.append("--session_label")
        cmd.append(project.subject_session)

        # TODO: review how to handle anatomical pipeline processing
    if run_anat:
        cmd.append("--anat_pipeline_config")
        cmd.append(project.anat_config_file)
    else:
        print_error("  .. ERROR: anatomical pipeline is mandatory")
        return 1

    if run_dmri:
        cmd.append("--dwi_pipeline_config")
        cmd.append(project.dmri_config_file)
    else:
        print("  .. INFO: diffusion pipeline not performed")

    if run_fmri:
        cmd.append("--func_pipeline_config")
        cmd.append(project.fmri_config_file)
    else:
        print("  .. INFO: functional pipeline not performed")

    cmd.append('--number_of_threads')
    cmd.append(str(number_of_threads))

    return ' '.join(cmd)


def readLineByLine(filename):
    """Read a text file line by line.

    Parameters
    ----------
    filename : string
        Text file
    """
    # Use with statement to correctly close the file when you read all the lines.
    with open(filename, 'r') as f:
        # Use implicit iterator over filehandler to minimize memory used
        for line in f:
            # Use generator, to minimize memory used, removing trailing carriage return as it is not part of the command.
            yield line.strip('\n')


def manage_processes(proclist):
    """Manages parallel processes.

    Parameters
    ----------
    proclist : list
        List of processes
    """
    for proc in proclist:
        if proc.poll() is not None:
            proclist.remove(proc)


def remove_files(path, debug=False):
    """Remove files (if existing) given a path with glob expression.

    Parameters
    ----------
    path : string
        Path of the files to be removed

    debug : bool
        If `True`, print output
    """
    for f in glob(path):
        if debug:  # pragma: no cover
            print('  ... DEL: {}'.format(f))
        try:
            os.remove(f)
        except Exception:
            pass


def remove_dirs(path, debug=False):
    """Remove directories (and sub-directories) given a path with glob expression.

    Parameters
    ----------
    path : string
        Paths of the directory (and subdirectories) to be removed

    debug : bool
        If `True`, print output
    """
    for d in glob(path):
        if debug:  # pragma: no cover
            print('  ... DEL: {}'.format(d))
        try:
            shutil.rmtree(d)
        except Exception:
            pass


def clean_cache(bids_root, debug=False):
    """Clean cache generated by BIDS App execution.

    Parameters
    ----------
    bids_root : string
        BIDS dataset root directory

    debug : bool
        If `True`, debugging mode with extra printed outputs
    """
    if debug:  # pragma: no cover
        print('> Clean docker image cache stored in /tmp')
    # Clean cache (issue related that the dataset directory is mounted into /tmp,
    # which is used for caching by java/matlab/matplotlib/xvfb-run in the docker image)
    remove_files(os.path.join(bids_root, '._java*'))
    remove_files(os.path.join(bids_root, 'mri_segstats.tmp*'))
    remove_dirs(os.path.join(bids_root, 'MCR_*'))
    remove_files(os.path.join(bids_root, '.X99*'))


def run(command, env=None, log_filename=None):
    """Execute a command via `subprocess.Popen`.

    Parameters
    ----------
    command : string
        Command to be executed

    env : os.environ
        Custom `os.environ`

    log_filename : string
        Execution log file

    Returns
    -------
    process : `subprocess.Popen`
        A `subprocess.Popen` process
    """
    merged_env = os.environ
    if env is not None:  # pragma: no cover
        merged_env.update(env)
    if log_filename is not None:
        with open(log_filename, 'w+') as log:
            process = subprocess.Popen(command, stdout=log,
                                       stderr=log, shell=True,
                                       env=merged_env)
    else:  # pragma: no cover
        process = subprocess.Popen(command, shell=True,
                                   env=merged_env)
    return process


def check_and_return_valid_nb_of_cores(args):
    """Function that checks and returns a valid number of subjects to be processed and a maximal number of threads.

    Parameters
    ----------
    args : dict
        Dictionary containing the parser argument

    Returns
    -------
    parallel_number_of_subjects : int
        Valid number of subject to be processed in parallel

    number_of_threads : int
        Valid number of maximal threads in parallel for a particular subject

    """
    # Get the number of available cores and keep one for light processes if possible
    max_number_of_cores = multiprocessing.cpu_count() - 1

    # handles case with one CPU available
    if max_number_of_cores < 1:
        max_number_of_cores = 1

    # Setup number of subjects to be processed in parallel
    if args.number_of_participants_processed_in_parallel is not None:
        parallel_number_of_subjects = int(
                args.number_of_participants_processed_in_parallel)
        if parallel_number_of_subjects > max_number_of_cores:
            print(
                '  * Number of subjects to be processed in parallel set to the maximal ' +
                f'number of available cores ({max_number_of_cores})')
            print(
                BColors.WARNING +
                '  .. WARNING: the specified number of subjects to be processed in parallel ({})'.format(
                    args.number_of_participants_processed_in_parallel) +
                f' exceeds the number of available cores ({max_number_of_cores})' +
                BColors.ENDC)
            parallel_number_of_subjects = max_number_of_cores
        elif parallel_number_of_subjects <= 0:
            print(
                '  * Number of subjects to be processed in parallel set to one (sequential run)')
            print(BColors.WARNING +
                  '  .. WARNING: the specified number of subjects to be processed in parallel' +
                  f' ({args.number_of_participants_processed_in_parallel}) ' +
                  'should be greater to 0' + BColors.ENDC)
            parallel_number_of_subjects = 1
        else:
            print('  * Number of subjects to be processed in parallel set to ' +
                  f'{parallel_number_of_subjects} (Total of cores available: {max_number_of_cores})')
    else:
        print('  * Number of subjects to be processed in parallel set to one (sequential run)')
        parallel_number_of_subjects = 1

    # Setup number of threads to be used for multithreading by OpenMP
    if args.number_of_threads is not None:
        number_of_threads = int(args.number_of_threads)
        if parallel_number_of_subjects == 1:
            if number_of_threads > max_number_of_cores:
                print('  * Number of parallel threads set to the maximal ' +
                      f'number of available cores ({max_number_of_cores})')
                print(BColors.WARNING +
                      '  .. WARNING: the specified number of pipeline processes ' +
                      f'executed in parallel ({args.number_of_threads}) ' +
                      f'exceeds the number of available cores ({max_number_of_cores})' +
                      BColors.ENDC)
                number_of_threads = max_number_of_cores
            elif number_of_threads <= 0:
                print(f'  * Number of parallel threads set to one (total of cores: {max_number_of_cores})')
                print(BColors.WARNING +
                      f'  .. WARNING: The specified of pipeline processes executed in parallel ({args.number_of_threads}) ' +
                      'should be greater to 0' + BColors.ENDC)
                number_of_threads = 1
            else:
                print(f'  * Number of parallel threads set to {number_of_threads} (total of cores: {max_number_of_cores})')
        else:
            # Make sure that the total number of threads used does not exceed the total number of available cores
            # Otherwise parallelize only at the subject level
            total_number_of_threads = parallel_number_of_subjects * number_of_threads
            if total_number_of_threads > max_number_of_cores:
                print(BColors.WARNING +
                      '  * Total number of cores used ' +
                      f'(Subjects in parallel: {parallel_number_of_subjects}, ' +
                      f'Threads in parallel: {number_of_threads}, ' +
                      f'Total: {total_number_of_threads})' +
                      f'is greater than the number of available cores ({max_number_of_cores})' +
                      BColors.ENDC)
                number_of_threads = 1
                parallel_number_of_subjects = max_number_of_cores
                print(BColors.WARNING +
                      '  .. WARNING: Processing will be ONLY parallelized at the subject level ' +
                      f'using {parallel_number_of_subjects} cores.' +
                      BColors.ENDC)
    else:
        print(f'  * Number of parallel threads set to one (total of cores: {max_number_of_cores})')
        number_of_threads = 1

    return parallel_number_of_subjects, number_of_threads


def main():
    """Main function of the BIDS App entrypoint script."""
    # Parse script arguments
    cmp_parser = parser.get()
    args = cmp_parser.parse_args()

    print('> BIDS dataset: {}'.format(args.bids_dir))

    # if not args.skip_bids_validator:
    #     run('bids-validator %s'%args.bids_dir)

    if args.participant_label:  # only for a subset of subjects
        subjects_to_analyze = args.participant_label
    else:  # for all subjects
        subject_dirs = glob(os.path.join(args.bids_dir, "sub-*"))
        subjects_to_analyze = [subject_dir.split(
            "-")[-1] for subject_dir in subject_dirs]

    print("> Subjects to analyze : {}".format(subjects_to_analyze))

    # Derivatives directory creation if it does not exist
    derivatives_dir = os.path.abspath(args.output_dir)
    if not os.path.isdir(derivatives_dir):
        os.makedirs(derivatives_dir)

    tools = [__cmp_directory__, __freesurfer_directory__, __nipype_directory__]

    for tool in tools:
        tool_dir = os.path.join(args.output_dir, tool)
        if not os.path.isdir(tool_dir):
            os.makedirs(tool_dir)

    # Make sure freesurfer is happy with the license
    print('> Set $FS_LICENSE which points to FreeSurfer license location (BIDS App)')

    if os.access(os.path.join('/bids_dir', 'code', 'license.txt'), os.F_OK):
        os.environ['FS_LICENSE'] = os.path.join('/bids_dir', 'code', 'license.txt')
    elif args.fs_license:
        os.environ['FS_LICENSE'] = os.path.abspath(args.fs_license)
    else:
        print_error("  .. ERROR: Missing license.txt in code/ directory OR unspecified Freesurfer license with the option --fs_license ")
        return 1

    print('  .. INFO: $FS_LICENSE set to {}'.format(os.environ['FS_LICENSE']))

    parallel_number_of_subjects, number_of_threads = check_and_return_valid_nb_of_cores(args)

    # Set number of threads used by programs based on OpenMP multi-threading library
    # This includes AFNI, Dipy, Freesurfer, FSL, MRtrix3.
    # os.environ.update(OMP_NUM_THREADS=f'{number_of_threads}')
    # print('  * OMP_NUM_THREADS set to {} (total of cores: {})'.format(os.environ['OMP_NUM_THREADS'], max_number_of_cores))

    # Set number of threads used by ANTs if specified.
    # Otherwise use the same as the number of OpenMP threads
    if args.ants_number_of_threads is not None:
        os.environ['ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS'] = f'{args.ants_number_of_threads}'
        print(f'  * ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS set to {os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"]}')

    # Initialize random generator for enhanced reproducibility
    # Numpy needs to be imported after setting the different multi-threading environment variable
    # See https://stackoverflow.com/questions/30791550/limit-number-of-threads-in-numpy for more details
    # noinspection PyPep8
    numpy.random.seed(1234)

    # Set random generator seed of MRtrix if specified
    if args.mrtrix_random_seed is not None:
        os.environ['MRTRIX_RNG_SEED'] = f'{args.mrtrix_random_seed}'
        print(f'  * MRTRIX_RNG_SEED set to {os.environ["MRTRIX_RNG_SEED"]}')

    # Set random generator seed of ANTs if specified
    if args.ants_random_seed is not None:
        os.environ['ANTS_RANDOM_SEED'] = f'{args.ants_random_seed}'
        print(f'  * ANTS_RANDOM_SEED set to {os.environ["ANTS_RANDOM_SEED"]}')

    # running participant level
    if args.analysis_level == "participant":

        # report_app_run_to_google_analytics()
        if args.notrack is not True:
            report_usage('BIDS App', 'Run', __version__)

        maxprocs = parallel_number_of_subjects
        processes = []

        # find all T1s and skullstrip them
        for subject_label in subjects_to_analyze:

            project = ProjectInfo()
            project.base_directory = args.bids_dir
            project.output_directory = args.output_dir

            project.subjects = ['sub-{}'.format(label)
                                for label in subjects_to_analyze]
            project.subject = 'sub-{}'.format(subject_label)
            print('> Process subject {}'.format(project.subject))

            if args.session_label is not None:
                print("> Sessions specified by input args : {}".format(
                    args.session_label))
                subject_session_labels = args.session_label
                project.subject_sessions = [
                    'ses-{}'.format(subject_session_label) for subject_session_label in subject_session_labels
                ]
                # Check if session exists
                for session in project.subject_sessions:
                    session_path = os.path.join(
                        args.bids_dir, project.subject, session)
                    if not os.path.exists(session_path):
                        print_error(f'  .. ERROR: The directory {session_path} corresponding '
                                    f'to the session {session.split("-")[-1]} '
                                    "specified by --session_label input flag DOES NOT exist.")
                        return 1
                    else:
                        print(f'  .. INFO: The directory {session_path} corresponding '
                              f'to the session {session.split("-")[-1]} '
                              'specified by --session_label input flag DOES exist.')
            else:
                # Check if multiple session (sub-XX/ses-YY/anat/... structure or sub-XX/anat.. structure?)
                subject_session_dirs = glob(os.path.join(
                    args.bids_dir, project.subject, "ses-*"))
                project.subject_sessions = [
                    'ses-{}'.format(subject_session_dir.split("-")[-1]) for subject_session_dir in subject_session_dirs
                ]

            if len(project.subject_sessions) > 0:  # Session structure
                print("> Sessions to analyze : {}".format(project.subject_sessions))
            else:
                project.subject_sessions = ['']

            for session in project.subject_sessions:

                if not args.coverage:
                    while len(processes) == maxprocs:
                        manage_processes(processes)

                if session != "":
                    print('> Process session {}'.format(session))

                project.subject_session = session

                # Derivatives folder creation
                for tool in tools:
                    if project.subject_session == "":
                        derivatives_dir = os.path.join(args.output_dir, tool, project.subject)
                    elif project.subject_session != "" and tool == __freesurfer_directory__:
                        derivatives_dir = os.path.join(args.output_dir, tool,
                                                       f'{project.subject}_{project.subject_session}')
                    elif project.subject_session != "" and tool != __freesurfer_directory__:
                        derivatives_dir = os.path.join(args.output_dir, tool,
                                                       project.subject, project.subject_session)
                    if not os.path.isdir(derivatives_dir):
                        os.makedirs(derivatives_dir)

                run_anat = False
                run_dmri = False
                run_fmri = False

                if args.anat_pipeline_config is not None:
                    if check_configuration_format(args.anat_pipeline_config) == '.ini':
                        anat_pipeline_config = convert_config_ini_2_json(args.anat_pipeline_config)
                    else:
                        anat_pipeline_config = args.anat_pipeline_config
                    project.anat_config_file = create_subject_configuration_from_ref(
                            project, anat_pipeline_config, 'anatomical'
                    )
                    run_anat = True
                    print(f"\t ... Anatomical config created : {project.anat_config_file}")
                if args.dwi_pipeline_config is not None:
                    if check_configuration_format(args.dwi_pipeline_config) == '.ini':
                        dwi_pipeline_config = convert_config_ini_2_json(args.dwi_pipeline_config)
                    else:
                        dwi_pipeline_config = args.dwi_pipeline_config
                    project.dmri_config_file = create_subject_configuration_from_ref(
                        project, dwi_pipeline_config, 'diffusion'
                    )
                    run_dmri = True
                    print(f"\t ... Diffusion config created : {project.dmri_config_file}")
                if args.func_pipeline_config is not None:
                    if check_configuration_format(args.func_pipeline_config) == '.ini':
                        func_pipeline_config = convert_config_ini_2_json(args.func_pipeline_config)
                    else:
                        func_pipeline_config = args.func_pipeline_config
                    project.fmri_config_file = create_subject_configuration_from_ref(
                        project, func_pipeline_config, 'fMRI'
                    )
                    run_fmri = True
                    print(f"\t ... fMRI config created : {project.fmri_config_file}")

                if args.anat_pipeline_config is not None:
                    print("  .. INFO: Running pipelines : ")
                    print("\t\t- Anatomical MRI (segmentation and parcellation)")

                    if args.dwi_pipeline_config is not None:
                        print("\t\t- Diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("\t\t- fMRI (functional connectivity matrices)")

                    if args.coverage:
                        if run_anat:
                            run_individual(project.base_directory,
                                           project.output_directory,
                                           project.subject,
                                           project.subject_session,
                                           anat_pipeline_config=project.anat_config_file,
                                           dwi_pipeline_config=(None
                                                                if not run_dmri
                                                                else project.dmri_config_file),
                                           func_pipeline_config=(None
                                                                 if not run_fmri
                                                                 else project.fmri_config_file),
                                           number_of_threads=number_of_threads)
                    else:
                        cmd = create_cmp_command(project=project,
                                                 run_anat=run_anat,
                                                 run_dmri=run_dmri,
                                                 run_fmri=run_fmri,
                                                 number_of_threads=number_of_threads)
                        print_blue("... cmd : {}".format(cmd))
                        if project.subject_session != "":
                            log_file = '{}_{}_log.txt'.format(project.subject,
                                                              project.subject_session)
                        else:
                            log_file = '{}_log.txt'.format(project.subject)
                        proc = run(command=cmd, env={},
                                   log_filename=os.path.join(project.output_directory, __cmp_directory__,
                                                             project.subject, project.subject_session,
                                                             log_file)
                                   )
                        processes.append(proc)
                else:
                    print("... Error: at least anatomical configuration file "
                          "has to be specified (--anat_pipeline_config)")
                    return 1

        if not args.coverage:
            while len(processes) > 0:
                manage_processes(processes)

        clean_cache(args.bids_dir)

    # running group level; ultimately it will compute average connectivity matrices
    # elif args.analysis_level == "group":
    #     brain_sizes = []
    #     for subject_label in subjects_to_analyze:
    #         for brain_file in glob(os.path.join(args.output_dir, "sub-%s*.nii*"%subject_label)):
    #             data = nibabel.load(brain_file).get_data()
    #             # calcualte average mask size in voxels
    #             brain_sizes.append((data != 0).sum())
    #
    #     with open(os.path.join(args.output_dir, "avg_brain_size.txt"), 'w') as fp:
    # fp.write("Average brain size is %g voxels"%numpy.array(brain_sizes).mean())

    return 1


if __name__ == '__main__':
    sys.exit(main())
