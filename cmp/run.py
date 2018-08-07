#!/usr/bin/env python2
# -*-coding:Latin-1 -*

# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

import argparse
import os
import subprocess
import nibabel
import numpy
from glob import glob

#import cmp.gui
import gui
import project
from info import __version__

# __version__ = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
#                                 'version')).read()

def info():
    print "\nConnectome Mapper (CMP) " + __version__
    print unicode("""Copyright (C) 2009-2018, Ecole Polytechnique Fédérale de Lausanne (EPFL) and
             Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
             All rights reserved.\n""")

# Checks the needed dependencies. We call directly the functions instead
# of just checking existence in $PATH in order to handl missing libraries.
# Note that not all the commands give the awaited 1 exit code...
def dep_check():

    nul = open(os.devnull, 'w')

    error = ""

    # Check for FSL
    if subprocess.call("fslorient",stdout=nul,stderr=nul,shell=True) != 255:
        error = """FSL not installed or not working correctly. Check that the
                FSL_DIR variable is exported and the fsl.sh setup script is sourced."""

    # Check for Freesurfer
    if subprocess.call("mri_info",stdout=nul,stderr=nul,shell=True) != 1:
        error = """FREESURFER not installed or not working correctly. Check that the
                FREESURFER_HOME variable is exported and the SetUpFreeSurfer.sh setup
                script is sourced."""

    if error != "":
        print error
        sys.exit(2)

def create_cmp_command(project):

    if len(project.subject_sessions)>0:
        cmd = "connectomemapper3 %s %s %s %s %s %s %s %s %s"%(project.base_directory,project.subject,project.subject_session,project.anat_config_file,True,project.dmri_config_file,True,project.fmri_config_file,True)
    else:
        cmd = "connectomemapper3 %s %s %s %s %s %s %s %s"%(project.base_directory,project.subject,project.anat_config_file,True,project.dmri_config_file,True,project.fmri_config_file,True)

    return cmd

def readLineByLine(filename):
    with open(filename, 'r') as f: #Use with statement to correctly close the file when you read all the lines.
        for line in f:    # Use implicit iterator over filehandler to minimize memory used
            yield line.strip('\n') #Use generator, to minimize memory used, removing trailing carriage return as it is not part of the command.

def create_subject_configuration_from_ref(project, ref_conf_file, pipeline_type):

    subject_derivatives_dir = os.path.join(project.base_directory,"derivatives")

    if len(project.subject_sessions) > 0: #Session structure
        subject_conf_file = os.path.join(subject_derivatives_dir,"{}_{}_{}_config.ini".format(project.subject,project.subject_session,pipeline_type))
    else:
        subject_conf_file = os.path.join(subject_derivatives_dir,"{}_{}_config.ini".format(project.subject,pipeline_type))

    if os.path.isfile(subject_conf_file):
        print "WARNING: rewriting config file {}".format(subject_conf_file)
        os.remove(subject_conf_file)

    #Copy and edit appropriate fields/lines
    f = open(subject_conf_file,'w')
    for line in readLineByLine(ref_conf_file):
        if "subject = " in line:
            f.write("subject = {}".format(project.subject) + os.linesep)
        elif "subjects = " in line:
            f.write("subjects = {}".format(project.subjects) + os.linesep)
        elif "subject_sessions = " in line:
            f.write("subject_sessions = {}".format(project.subject_sessions) + os.linesep)
        elif "subject_session = " in line:
            f.write("subject_session = {}".format(project.subject_session) + os.linesep)
        else:
            f.write(line)
    f.close()

    return subject_conf_file

def run(command, env={}):
    merged_env = os.environ
    merged_env.update(env)
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, shell=True,
                               env=merged_env)
    while True:
        line = process.stdout.readline()
        line = str(line, 'utf-8')[:-1]
        print(line)
        if line == '' and process.poll() != None:
            break
    if process.returncode != 0:
        raise Exception("Non zero return code: %d"%process.returncode)

parser = argparse.ArgumentParser(description='Example BIDS App entrypoint script.')
parser.add_argument('bids_dir', help='The directory with the input dataset '
                    'formatted according to the BIDS standard.')
parser.add_argument('output_dir', help='The directory where the output files '
                    'should be stored. If you are running group level analysis '
                    'this folder should be prepopulated with the results of the'
                    'participant level analysis.')
parser.add_argument('analysis_level', help='Level of the analysis that will be performed. '
                    'Multiple participant level analyses can be run independently '
                    '(in parallel) using the same output_dir.',
                    choices=['participant', 'group'])
parser.add_argument('--participant_label', help='The label(s) of the participant(s) that should be analyzed. The label '
                   'corresponds to sub-<participant_label> from the BIDS spec '
                   '(so it does not include "sub-"). If this parameter is not '
                   'provided all subjects should be analyzed. Multiple '
                   'participants can be specified with a space separated list.',
                   nargs="+")

parser.add_argument('anat_pipeline_config', help='Configuration .txt file for processing stages of the anatomical MRI processing pipeline')
parser.add_argument('dwi_pipeline_config', help='Configuration .txt file for processing stages of the diffusion MRI processing pipeline')
parser.add_argument('func_pipeline_config', help='Configuration .txt file for processing stages of the fMRI processing pipeline')

# parser.add_argument('--skip_bids_validator', help='Whether or not to perform BIDS dataset validation',
#                    action='store_true')
parser.add_argument('-v', '--version', action='version',
                    version='BIDS-App example version {}'.format(__version__))


args = parser.parse_args()

# check dependencies
dep_check()

# add current directory to the path, useful if DTB_ bins not installed
os.environ["PATH"] += os.pathsep + os.path.dirname(sys.argv[0])

# version and copyright message
info()

# if not args.skip_bids_validator:
#     run('bids-validator %s'%args.bids_dir)

subjects_to_analyze = []
# only for a subset of subjects
if args.participant_label:
    subjects_to_analyze = args.participant_label
# for all subjects
else:
    subject_dirs = glob(os.path.join(args.bids_dir, "sub-*"))
    subjects_to_analyze = [subject_dir.split("-")[-1] for subject_dir in subject_dirs]

project = cmp.gui.CMP_Project_Info()
project.base_directory = args.bids_dir
project.subjects = ['sub-{}'.format(label) for label in subjects_to_analyze]

#Derivatives directory creation if it does not exist
cmp_derivatives_dir = os.path.join(args.bids_dir, "derivatives" , "cmp")
if not os.path.isdir(cmp_derivatives_dir):
    os.mkdir(cmp_derivatives_dir)

# running participant level
if args.analysis_level == "participant":

    # find all T1s and skullstrip them
    for subject_label in subjects_to_analyze:

        project.subject = 'sub-{}'.format(subject_label)

        # Check if multiple session (sub-XX/ses-YY/anat/... structure or sub-XX/anat.. structure?)
        subject_session_dirs = glob(os.path.join(args.bids_dir, project.subject, "ses-*"))
        project.subject_sessions = ['ses-{}'.format(subject_session_dir.split("-")[-1]) for subject_session_dir in subject_session_dirs]

        if len(project.subject_sessions) > 0: #Session structure

            for session in project.subject_sessions:
                project.subject_session = session

                #Derivatives folder creation (Folder is first deleted if it already exists)
                session_derivatives_dir = os.path.join(cmp_derivatives_dir, project.subject, project.subject_session)
                if not os.path.isdir(session_derivatives_dir):
                    os.makedirs(session_derivatives_dir)

                project.anat_config_file = create_subject_configuration_from_ref(project,args.anat_pipeline_config)
                project.dmri_config_file = create_subject_configuration_from_ref(project,args.dwi_pipeline_config)
                project.fmri_config_file = create_subject_configuration_from_ref(project,args.func_pipeline_config)

                cmd = create_cmp_command(project=project)
                run(command=cmd)


        else: #No session structure
            project.subject_sessions = ['']
            project.subject_session = ''

            #Derivatives folder creation (Folder is first deleted if it already exists)
            subject_derivatives_dir = os.path.join(cmp_derivatives_dir, project.subject)
            if not os.path.isdir(subject_derivatives_dir):
                os.makedirs(subject_derivatives_dir)

            project.anat_config_file = create_subject_configuration_from_ref(project,args.anat_pipeline_config,'anatomical')
            project.dmri_config_file = create_subject_configuration_from_ref(project,args.dwi_pipeline_config,'diffusion')
            project.fmri_config_file = create_subject_configuration_from_ref(project,args.func_pipeline_config,'fMRI')

            cmd = create_cmp_command(project=project)

            print cmd
            #run(command=cmd)


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
