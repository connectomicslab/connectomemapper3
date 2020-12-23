#!/usr/bin/env python2
# -*-coding:Latin-1 -*

# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
from cmtklib.util import BColors
from cmp import parser
from cmp.info import __version__
from cmp.project import CMP_Project_Info, run_individual

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

# __version__ = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
#                                 'version')).read()

# def report_app_run_to_google_analytics():
#     params = urllib.parse.urlencode({'v': 1,
#                                'tid': '247732290',
#                                'cid': '555',
#                                'an' : 'ConnectomeMapper3',
#                                'av' : __version__,
#                                't': 'event',
#                                'ec': 'run',
#                                'ea': 'start'})

#     connection = http.client.HTTPConnection('www.google-analytics.com')
#     connection.request('POST', '/collect', params)
#     response = connection.getresponse()
#     print("{}, {}".format(response.status, response.reason))


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
    tracking_url = 'https://www.google-analytics.com/collect?v=1&t=event&tid={}&cid={}&ec={}&ea={}&el={}&aip=1'.format(tracking_id,
                                                                                                                 clientid_str,
                                                                                                                 event_category,
                                                                                                                 event_action,
                                                                                                                 event_label)
    r = requests.post(tracking_url)

    if verbose:
        print(r)

    print('Report execution to Google Analytics. \n'
          'Thanks to support us in the task of finding new funds for CMP3 development!')


def create_cmp_command(project, run_anat, run_dmri, run_fmri, number_of_threads=1):
    """Create the command to run the `connectomemapper3` python script.

    Parameters
    ----------
    project : cmp.project.CMP_Project_Info
        Instance of `cmp.project.CMP_Project_Info`

    run_anat : bool
        If True, append the anatomical configuration file to the command

    run_dmri : bool
        If True, append the diffusion configuration file to the command

    run_fmri : bool
        If True, append the fMRI configuration file to the command

    number_of_threads : int
        Number of threads used by Nipype

    Returns
    -------
    Command : string
        The command to execute the `connectomemapper3` python script
    """
    cmd = []

    cmd.append("connectomemapper3")
    cmd.append("--bids_dir")
    cmd.append(project.base_directory)
    cmd.append("--output_dir")
    cmd.append(project.output_directory)
    cmd.append("--participant_label")
    cmd.append(project.subject)

    if project.subject_session != '':
        cmd.append("--session_label")
        cmd.append(project.subject_session)

        # TODO: review how to handle anatomical pipeline processing
    if run_anat:
        cmd.append("--anat_pipeline_config")
        cmd.append(project.anat_config_file)
    else:
        print("ERROR: anatomical pipeline is mandatory")

    if run_dmri:
        cmd.append("--dwi_pipeline_config")
        cmd.append(project.dmri_config_file)
    else:
        print("INFO: diffusion pipeline not performed")

    if run_fmri:
        cmd.append("--func_pipeline_config")
        cmd.append(project.fmri_config_file)
    else:
        print("INFO: functional pipeline not performed")

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


def create_subject_configuration_from_ref(project, ref_conf_file, pipeline_type, multiproc_number_of_cores=1):
    """Create the pipeline configuration file for an individual subject from a reference given as input.

    Parameters
    ----------
    project : cmp.project.CMP_Project_Info
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

    if project.subject_session != '':  # Session structure
        # print('With session : {}'.format(project.subject_session))
        subject_conf_file = os.path.join(subject_derivatives_dir, 'cmp', project.subject, project.subject_session,
                                         "{}_{}_{}_config.ini".format(project.subject, project.subject_session,
                                                                      pipeline_type))
    else:
        # print('With NO session ')
        subject_conf_file = os.path.join(subject_derivatives_dir, 'cmp', project.subject,
                                         "{}_{}_config.ini".format(project.subject, pipeline_type))

    if os.path.isfile(subject_conf_file):
        print("WARNING: rewriting config file {}".format(subject_conf_file))
        os.remove(subject_conf_file)

    # Change relative path to absolute path if needed (required when using singularity)
    if not os.path.isabs(ref_conf_file):
        ref_conf_file = os.path.abspath(ref_conf_file)

    # Copy and edit appropriate fields/lines
    f = open(subject_conf_file, 'w')
    for line in readLineByLine(ref_conf_file):
        if "subject = " in line:
            f.write("subject = {}\n".format(project.subject))
        elif "subjects = " in line:
            f.write("subjects = {}\n".format(project.subjects))
        elif "subject_sessions = " in line:
            f.write("subject_sessions = {}\n".format(project.subject_sessions))
        elif "subject_session = " in line:
            f.write("subject_session = {}\n".format(project.subject_session))
        elif "number_of_cores = " in line:
            f.write("number_of_cores = {}\n".format(multiproc_number_of_cores))
        else:
            f.write("{}\n".format(line))
    f.close()

    return subject_conf_file


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


def clean_cache(bids_root):
    """Clean cache generated by BIDS App execution.

    Parameters
    ----------
    bids_root : string
        BIDS dataset root directory
    """
    print('> Clean docker image cache stored in /tmp')
    # Clean cache (issue related that the dataset directory is mounted into /tmp,
    # which is used for caching by java/matlab/matplotlib/xvfb-run in the docker image)

    # Folder can be code/ derivatives/ sub-*/ .datalad/ .git/
    # File can be README.txt CHANGES.txt participants.tsv project_description.json

    for f in glob(os.path.join(bids_root, '._java*')):
        print('... DEL: {}'.format(f))
        try:
            os.remove(f)
        except Exception:
            pass

    for f in glob(os.path.join(bids_root, 'mri_segstats.tmp*')):
        print('... DEL: {}'.format(f))
        try:
            os.remove(f)
        except Exception:
            pass

    for d in glob(os.path.join(bids_root, 'MCR_*')):
        print('... DEL: {}'.format(d))
        try:
            shutil.rmtree(d)
        except Exception:
            pass

    # for d in glob(os.path.join(bids_root,'matplotlib*')):
    #     print('... DEL: {}'.format(d))
    #     try:
    #         shutil.rmtree(d)
    #     except Exception:
    #         pass

    # for d in glob(os.path.join(bids_root,'xvfb-run.*')):
    #     print('... DEL: {}'.format(d))
    #     shutil.rmtree(d)
    #
    # for d in glob(os.path.join(bids_root,'.X11*')):
    #     print('... DEL: {}'.format(d))
    #     shutil.rmtree(d)
    #
    # for d in glob(os.path.join(bids_root,'.X11-unix')):
    #     print('... DEL: {}'.format(d))
    #     shutil.rmtree(d)

    for f in glob(os.path.join(bids_root, '.X99*')):
        print('... DEL: {}'.format(f))
        try:
            os.remove(f)
        except Exception:
            pass


def run(command, env={}, log_filename={}):
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
    merged_env.update(env)

    with open(log_filename, 'w+') as log:
        process = subprocess.Popen(command, stdout=log,
                                   stderr=log, shell=True,
                                   env=merged_env)

    return process
    # while True:
    #     line = process.stdout.readline()
    #     line = str(line)[:-1]
    #     print(line)
    #     if line == '' and process.poll() is not None:
    #         break
    # if process.returncode != 0:
    #     raise Exception("Non zero return code: %d"%process.returncode)


# Initialize random generator for enhanced reproducibility
numpy.random.seed(1234)

cmp_parser = parser.get()
args = cmp_parser.parse_args()

print('> BIDS dataset: {}'.format(args.bids_dir))

# if not args.skip_bids_validator:
#     run('bids-validator %s'%args.bids_dir)

subjects_to_analyze = []
# only for a subset of subjects
if args.participant_label:
    subjects_to_analyze = args.participant_label
# for all subjects
else:
    subject_dirs = glob(os.path.join(args.bids_dir, "sub-*"))
    subjects_to_analyze = [subject_dir.split(
        "-")[-1] for subject_dir in subject_dirs]

print("> Subjects to analyze : {}".format(subjects_to_analyze))

# Derivatives directory creation if it does not exist
derivatives_dir = os.path.abspath(args.output_dir)
if not os.path.isdir(derivatives_dir):
    os.makedirs(derivatives_dir)

tools = ['cmp', 'freesurfer', 'nipype']

for tool in tools:
    tool_dir = os.path.join(args.output_dir, tool)
    if not os.path.isdir(tool_dir):
        os.makedirs(tool_dir)

# Make sure freesurfer is happy with the license
print('> Set $FS_LICENSE which points to FreeSurfer license location (BIDS App)')

if os.access(os.path.join('/bids_dir¨', 'code', 'license.txt'), os.F_OK):
    os.environ['FS_LICENSE'] = os.path.join('/bids_dir', 'code', 'license.txt')
    # Not anymore needed as we are using the environment variable
    # print('... src : {}'.format(os.path.join('/tmp','code','license.txt')))
    # print('... dst : {}'.format(os.path.join('/opt','freesurfer','license.txt')))
    # shutil.copyfile(src=os.path.join('/tmp','code','license.txt'),dst=os.path.join('/opt','freesurfer','license.txt'))
elif args.fs_license:
    os.environ['FS_LICENSE'] = os.path.abspath(args.fs_license)
    # Not anymore needed as we are using the environment variable
    # print('... src : {}'.format(os.environ['FS_LICENSE']))
    # print('... dst : {}'.format(os.path.join('/opt','freesurfer','license.txt')))
    # shutil.copyfile(src=os.environ['FS_LICENSE'],dst=os.path.join('/opt','freesurfer','license.txt'))
else:
    print(
        "ERROR: Missing license.txt in code/ directory OR unspecified Freesurfer license with the option --fs_license ")
    sys.exit(1)

print('  ... $FS_LICENSE : {}'.format(os.environ['FS_LICENSE']))

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
            '  * Number of subjects to be processed in parallel set to the maximal number of available cores ({})'.format(
                max_number_of_cores))
        print(
            BColors.WARNING +
            '    WARNING: the specified number of subjects to be processed in parallel ({})'.format(args.number_of_participants_processed_in_parallel) +
            ' exceeds the number of available cores ({})'.format(max_number_of_cores) +
            BColors.ENDC)
        parallel_number_of_subjects = max_number_of_cores
    elif parallel_number_of_subjects <= 0:
        print(
            '  * Number of subjects to be processed in parallel set to one (sequential run)')
        print(
            BColors.WARNING +
            '    WARNING: the specified number of subjects to be processed in parallel ({}) '.format(args.number_of_participants_processed_in_parallel) +
            'should be greater to 0' + BColors.ENDC)
        parallel_number_of_subjects = 1
    else:
        print('  * Number of subjects to be processed in parallel set to {} (Total of cores available: {})'.format(
            parallel_number_of_subjects, max_number_of_cores))
else:
    print('  * Number of subjects to be processed in parallel set to one (sequential run)')
    parallel_number_of_subjects = 1

# Setup number of threads to be used fro multithreading by OpenMP
if args.number_of_threads is not None:
    number_of_threads = int(args.number_of_threads)
    if parallel_number_of_subjects == 1:
        if number_of_threads > max_number_of_cores:
            print('  * Number of parallel threads set to the maximal number of available cores ({})'.format(
                max_number_of_cores))
            print(BColors.WARNING +
                  '   WARNING: the specified number of pipeline processes executed in parallel ({}) '.format(args.number_of_threads) +
                  'exceeds the number of available cores ({})'.format(max_number_of_cores) +
                  BColors.ENDC)
            number_of_threads = max_number_of_cores
        elif number_of_threads <= 0:
            print('  * Number of parallel threads set to one (total of cores: {})'.format(max_number_of_cores))
            print(BColors.WARNING + '    WARNING: the specified of pipeline processes executed in parallel ({}) '.format(args.number_of_threads) +
                  'should be greater to 0' + BColors.ENDC)
            number_of_threads = 1
        else:
            print('  * Number of parallel threads set to {} (total of cores: {})'.format(
                number_of_threads, max_number_of_cores))
    else:
        # Make sure that the total number of threads used does not exceed the total number of available cores
        # Otherwise parallelize only at the subject level
        total_number_of_threads = parallel_number_of_subjects * number_of_threads
        if total_number_of_threads > max_number_of_cores:
            print(BColors.WARNING +
                  '  * Total number of cores used (Subjects in parallel: {}, Threads in parallel: {}, Total: {})'.format(parallel_number_of_subjects,
                                                                                                                         number_of_threads,
                                                                                                                         total_number_of_threads) +
                  'is greater than the number of available cores ({})'.format(max_number_of_cores) + BColors.ENDC)
            number_of_threads = 1
            parallel_number_of_subjects = max_number_of_cores
            print(BColors.WARNING +
                  '    Processing will be ONLY parallelized at the subject level using {} cores.'.format(parallel_number_of_subjects) +
                  BColors.ENDC)
else:
    print('  * Number of parallel threads set to one (total of cores: {})'.format(max_number_of_cores))
    number_of_threads = 1

# Set number of threads used by programs based on OpenMP multi-threading library
# This includes AFNI, Dipy, Freesurfer, FSL, MRtrix3.
os.environ['OMP_NUM_THREADS'] = '{}'.format(number_of_threads)
print('  * OMP_NUM_THREADS set to {} (total of cores: {})'.format(os.environ['OMP_NUM_THREADS'], max_number_of_cores))

# Set number of threads used by ANTs if specified.
# Otherwise use the same as the number of OpenMP threads
if args.ants_number_of_threads is not None:
    os.environ['ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS'] = f'{args.ants_number_of_threads}'
    print(f'  * ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS set to {os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"]}')
else:
    os.environ['ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS'] = os.environ['OMP_NUM_THREADS']
    print(f'  * ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS set to {os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"]}')

# Set random generator seed of MRtrix if specified
if args.mrtrix_random_seed is not None:
    os.environ['MRTRIX_RNG_SEED'] = f'{args.mrtrix_random_seed}'
    print(f'  * MRTRIX_RNG_SEED set to {os.environ["MRTRIX_RNG_SEED"]}')

# Set random generator seed of ANTs if specified
if args.ants_random_seed is not None:
    os.environ['ANTS_RANDOM_SEED'] = f'{args.ants_random_seed}'
    print(f'  * ANTS_RANDOM_SEED set to {os.environ["ANTS_RANDOM_SEED"]}')

# TODO: Implement log for subject(_session)
# with open(log_filename, 'w+') as log:
#     proc = Popen(cmd, stdout=log, stderr=log, cwd=os.path.join(self.bids_root,'derivatives'))

# running participant level
if args.analysis_level == "participant":

    # report_app_run_to_google_analytics()
    if args.notrack is not True:
        report_usage('BIDS App', 'Run', __version__)

    maxprocs = parallel_number_of_subjects
    processes = []

    # find all T1s and skullstrip them
    for subject_label in subjects_to_analyze:

        project = CMP_Project_Info()
        project.base_directory = args.bids_dir
        project.output_directory = args.output_dir

        project.subjects = ['sub-{}'.format(label)
                            for label in subjects_to_analyze]
        project.subject = 'sub-{}'.format(subject_label)

        if args.session_label is not None:
            print("> Sessions specified by input args : {}".format(
                args.session_label))
            subject_session_labels = args.session_label
            project.subject_sessions = ['ses-{}'.format(subject_session_label) for subject_session_label in
                                        subject_session_labels]
            # Check if session exists
            for session in project.subject_sessions:
                session_path = os.path.join(
                    args.bids_dir, project.subject, session)
                if not os.path.exists(session_path):
                    print(
                        "ERROR: The directory {} corresponding to the session {} specified by --session_label input flag DOES NOT exist.".format(
                            session_path, session.split("-")[-1]))
                    sys.exit(1)
                else:
                    print(
                        "INFO: The directory {} corresponding to the session {} specified by --session_label input flag DOES exist.".format(
                            session_path, session.split("-")[-1]))
        else:
            # Check if multiple session (sub-XX/ses-YY/anat/... structure or sub-XX/anat.. structure?)
            subject_session_dirs = glob(os.path.join(
                args.bids_dir, project.subject, "ses-*"))
            project.subject_sessions = ['ses-{}'.format(subject_session_dir.split("-")[-1]) for subject_session_dir in
                                        subject_session_dirs]

        if len(project.subject_sessions) > 0:  # Session structure

            print("> Sessions to analyze : {}".format(project.subject_sessions))

            for session in project.subject_sessions:

                if not args.coverage:
                    while len(processes) == maxprocs:
                        manage_processes(processes)

                print('> Process subject {} session {}'.format(
                    project.subject, session))
                project.subject_session = session

                # Derivatives folder creation (Folder is first deleted if it already exists)
                for tool in tools:
                    if tool == 'freesurfer':
                        session_derivatives_dir = os.path.join(args.output_dir, tool,
                                                               '{}_{}'.format(project.subject, project.subject_session))
                    else:
                        session_derivatives_dir = os.path.join(args.output_dir, tool, project.subject,
                                                               project.subject_session)

                    if not os.path.isdir(session_derivatives_dir):
                        os.makedirs(session_derivatives_dir)

                run_anat = False
                run_dmri = False
                run_fmri = False

                if args.anat_pipeline_config is not None:
                    project.anat_config_file = create_subject_configuration_from_ref(project, args.anat_pipeline_config,
                                                                                     'anatomical')
                    run_anat = True
                    print("... Anatomical config created : {}".format(
                        project.anat_config_file))
                if args.dwi_pipeline_config is not None:
                    project.dmri_config_file = create_subject_configuration_from_ref(project, args.dwi_pipeline_config,
                                                                                     'diffusion')
                    run_dmri = True
                    print("... Diffusion config created : {}".format(
                        project.dmri_config_file))
                if args.func_pipeline_config is not None:
                    project.fmri_config_file = create_subject_configuration_from_ref(project, args.func_pipeline_config,
                                                                                     'fMRI')
                    run_fmri = True
                    print("... fMRI config created : {}".format(
                        project.fmri_config_file))

                if args.anat_pipeline_config is not None:
                    print("... Running pipelines : ")
                    print("        - Anatomical MRI (segmentation and parcellation)")

                    if args.dwi_pipeline_config is not None:
                        print(
                            "        - Diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("        - fMRI (functional connectivity matrices)")

                    if args.coverage:
                        if run_anat:
                            if run_dmri and not run_fmri:
                                run_individual(project.base_directory,
                                               project.output_directory,
                                               project.subject,
                                               project.subject_session,
                                               project.anat_config_file,
                                               project.dmri_config_file,
                                               None,
                                               number_of_threads=number_of_threads)
                            elif not run_dmri and run_fmri:
                                run_individual(project.base_directory,
                                               project.output_directory,
                                               project.subject,
                                               project.subject_session,
                                               project.anat_config_file,
                                               None,
                                               project.fmri_config_file,
                                               number_of_threads=number_of_threads)
                            elif run_dmri and run_fmri:
                                run_individual(project.base_directory,
                                               project.output_directory,
                                               project.subject,
                                               project.subject_session,
                                               project.anat_config_file,
                                               project.dmri_config_file,
                                               project.fmri_config_file,
                                               number_of_threads=number_of_threads)
                            # anatomical pipeline only
                            else:
                                run_individual(project.base_directory,
                                               project.output_directory,
                                               project.subject,
                                               project.subject_session,
                                               project.anat_config_file,
                                               None,
                                               None,
                                               number_of_threads=number_of_threads)
                    else:
                        cmd = create_cmp_command(project=project,
                                                 run_anat=run_anat,
                                                 run_dmri=run_dmri,
                                                 run_fmri=run_fmri,
                                                 number_of_threads=number_of_threads)
                        print("... cmd : {}".format(cmd))

                        proc = run(command=cmd, env={},
                                   log_filename=os.path.join(project.output_directory, 'cmp', project.subject,
                                                             project.subject_session,
                                                             '{}_{}_log.txt'.format(project.subject,
                                                                                    project.subject_session)))
                        processes.append(proc)
                else:
                    print(
                        "... Error: at least anatomical configuration file has to be specified (--anat_pipeline_config)")

        else:  # No session structure

            print('> Process subject {}'.format(project.subject))

            if not args.coverage:
                while len(processes) == maxprocs:
                    manage_processes(processes)

            project.subject_sessions = ['']
            project.subject_session = ''

            # Derivatives folder creation (Folder is first deleted if it already exists)
            for tool in tools:
                subject_derivatives_dir = os.path.join(
                    args.output_dir, tool, project.subject)
                if not os.path.isdir(subject_derivatives_dir):
                    os.makedirs(subject_derivatives_dir)

            run_anat = False
            run_dmri = False
            run_fmri = False

            if args.anat_pipeline_config is not None:
                project.anat_config_file = create_subject_configuration_from_ref(project, args.anat_pipeline_config,
                                                                                 'anatomical')
                run_anat = True
                print("... Anatomical config created : {}".format(
                    project.anat_config_file))
            if args.dwi_pipeline_config is not None:
                project.dmri_config_file = create_subject_configuration_from_ref(project, args.dwi_pipeline_config,
                                                                                 'diffusion')
                run_dmri = True
                print("... Diffusion config created : {}".format(
                    project.dmri_config_file))
            if args.func_pipeline_config is not None:
                project.fmri_config_file = create_subject_configuration_from_ref(project, args.func_pipeline_config,
                                                                                 'fMRI')
                run_fmri = True
                print("... fMRI config created : {}".format(
                    project.fmri_config_file))

            if args.anat_pipeline_config is not None:
                print("... Running pipelines : ")
                print("        - Anatomical MRI (segmentation and parcellation)")

                if args.dwi_pipeline_config is not None:
                    print("        - Diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("        - fMRI (functional connectivity matrices)")

                if args.coverage:
                    if run_anat:
                        if run_dmri and not run_fmri:
                            run_individual(project.base_directory,
                                           project.output_directory,
                                           project.subject,
                                           project.subject_session,
                                           project.anat_config_file,
                                           project.dmri_config_file,
                                           None,
                                           number_of_threads=number_of_threads)
                        if not run_dmri and run_fmri:
                            run_individual(project.base_directory,
                                           project.output_directory,
                                           project.subject,
                                           project.subject_session,
                                           project.anat_config_file,
                                           None,
                                           project.fmri_config_file,
                                           number_of_threads=number_of_threads)
                        if run_dmri and run_fmri:
                            run_individual(project.base_directory,
                                           project.output_directory,
                                           project.subject,
                                           project.subject_session,
                                           project.anat_config_file,
                                           project.dmri_config_file,
                                           project.fmri_config_file,
                                           number_of_threads=number_of_threads)
                        # anatomical pipeline only
                        else:
                            run_individual(project.base_directory,
                                           project.output_directory,
                                           project.subject,
                                           project.subject_session,
                                           project.anat_config_file,
                                           None,
                                           None,
                                           number_of_threads=number_of_threads)
                else:

                    cmd = create_cmp_command(project=project,
                                             run_anat=run_anat,
                                             run_dmri=run_dmri,
                                             run_fmri=run_fmri,
                                             number_of_threads=number_of_threads)
                    print("... cmd : {}".format(cmd))

                    proc = run(command=cmd, env={},
                               log_filename=os.path.join(project.output_directory,
                                                         'cmp', project.subject,
                                                         '{}_log.txt'.format(project.subject))
                               )
                    processes.append(proc)
            else:
                print(
                    "... Error: at least anatomical configuration file has to be specified (--anat_pipeline_config)")

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
