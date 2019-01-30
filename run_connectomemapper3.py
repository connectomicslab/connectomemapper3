#!/usr/bin/env python2
# -*-coding:Latin-1 -*

# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

# Remove warnings visible whenever you import scipy (or another package) that was compiled against an older numpy than is installed.
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

#Imports
import argparse
import os
import subprocess
import nibabel
import numpy
from glob import glob

#Own imports
#import cmp.gui
import cmp.gui as gui
import cmp.project as project
from cmp.info import __version__

# __version__ = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
#                                 'version')).read()

def create_cmp_command(project,run_anat,run_dmri,run_fmri):

    if len(project.subject_sessions)>0:
        if run_fmri:
            cmd = "connectomemapper3 %s %s %s %s %s %s %s %s %s"%(project.base_directory,project.subject,project.subject_session,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri,project.fmri_config_file,run_fmri)
        else:
            if run_dmri:
                cmd = "connectomemapper3 %s %s %s %s %s %s %s"%(project.base_directory,project.subject,project.subject_session,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri)
            else:
                if run_anat:
                    cmd = "connectomemapper3 %s %s %s %s %s"%(project.base_directory,project.subject,project.subject_session,project.anat_config_file,run_anat)
    else:
        if run_fmri:
            cmd = "connectomemapper3 %s %s %s %s %s %s %s %s"%(project.base_directory,project.subject,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri,project.fmri_config_file,run_fmri)
        else:
            if run_dmri:
                cmd = "connectomemapper3 %s %s %s %s %s %s"%(project.base_directory,project.subject,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri)
            else:
                if run_anat:
                    cmd = "connectomemapper3 %s %s %s %s"%(project.base_directory,project.subject,project.anat_config_file,run_anat)

    return cmd

def readLineByLine(filename):
    with open(filename, 'r') as f: #Use with statement to correctly close the file when you read all the lines.
        for line in f:    # Use implicit iterator over filehandler to minimize memory used
            yield line.strip('\n') #Use generator, to minimize memory used, removing trailing carriage return as it is not part of the command.

def create_subject_configuration_from_ref(project, ref_conf_file, pipeline_type):

    subject_derivatives_dir = os.path.join(project.base_directory,"derivatives")

    print('project.subject_session: {}'.format(project.subject_session))

    if project.subject_session != '': #Session structure
        print('With session : {}'.format(project.subject_session))
        subject_conf_file = os.path.join(subject_derivatives_dir,"{}_{}_{}_config.ini".format(project.subject,project.subject_session,pipeline_type))
    else:
        print('With NO session ')
        subject_conf_file = os.path.join(subject_derivatives_dir,"{}_{}_config.ini".format(project.subject,pipeline_type))

    if os.path.isfile(subject_conf_file):
        print "WARNING: rewriting config file {}".format(subject_conf_file)
        os.remove(subject_conf_file)

    #Copy and edit appropriate fields/lines
    f = open(subject_conf_file,'w')
    for line in readLineByLine(ref_conf_file):
        if "subject = " in line:
            f.write("subject = {}\n".format(project.subject))
        elif "subjects = " in line:
            f.write("subjects = {}\n".format(project.subjects))
        elif "subject_sessions = " in line:
            f.write("subject_sessions = {}\n".format(project.subject_sessions))
        elif "subject_session = " in line:
            f.write("subject_session = {}\n".format(project.subject_session))
        else:
            f.write("{}\n".format(line))
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
        line = str(line)[:-1]
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

parser.add_argument('--anat_pipeline_config', help='Configuration .txt file for processing stages of the anatomical MRI processing pipeline')
parser.add_argument('--dwi_pipeline_config', help='Configuration .txt file for processing stages of the diffusion MRI processing pipeline')
parser.add_argument('--func_pipeline_config', help='Configuration .txt file for processing stages of the fMRI processing pipeline')

# parser.add_argument('--skip_bids_validator', help='Whether or not to perform BIDS dataset validation',
#                    action='store_true')
parser.add_argument('-v', '--version', action='version',
                    version='BIDS-App example version {}'.format(__version__))


args = parser.parse_args()

print('BIDS dataset: {}'.format(args.bids_dir))

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

print("subjects to analyze : ")
print(subjects_to_analyze)

#Derivatives directory creation if it does not exist
derivatives_dir = os.path.abspath(args.output_dir)
if not os.path.isdir(derivatives_dir):
    os.mkdir(derivatives_dir)

tools = ['cmp','freesurfer','nipype']

for tool in tools:
    tool_dir = os.path.join(args.output_dir, tool)
    if not os.path.isdir(tool_dir):
        os.mkdir(tool_dir)

# running participant level
if args.analysis_level == "participant":

    # find all T1s and skullstrip them
    for subject_label in subjects_to_analyze:

        project = gui.CMP_Project_Info()
        project.base_directory = args.bids_dir
        project.output_directory = args.output_dir

        project.subjects = ['sub-{}'.format(label) for label in subjects_to_analyze]

        print("project.subjects: ")
        print(project.subjects)

        project.subject = 'sub-{}'.format(subject_label)

        # Check if multiple session (sub-XX/ses-YY/anat/... structure or sub-XX/anat.. structure?)
        subject_session_dirs = glob(os.path.join(args.bids_dir, project.subject, "ses-*"))
        project.subject_sessions = ['ses-{}'.format(subject_session_dir.split("-")[-1]) for subject_session_dir in subject_session_dirs]

        if len(project.subject_sessions) > 0: #Session structure

            for session in project.subject_sessions:
                print('Process session {}'.format(session))
                project.subject_session = session

                #Derivatives folder creation (Folder is first deleted if it already exists)
                for tool in tools:
                    if tool == 'freesurfer':
                        session_derivatives_dir = os.path.join(args.output_dir,tool, '{}_{}'.format(project.subject, project.subject_session))
                    else:
                        session_derivatives_dir = os.path.join(args.output_dir,tool, project.subject, project.subject_session)

                    if not os.path.isdir(session_derivatives_dir):
                        os.makedirs(session_derivatives_dir)

                run_anat = False
                run_dmri = False
                run_fmri = False

                if args.anat_pipeline_config is not None:
                    project.anat_config_file = create_subject_configuration_from_ref(project,args.anat_pipeline_config,'anatomical')
                    run_anat = True
                if args.dwi_pipeline_config is not None:
                    project.dmri_config_file = create_subject_configuration_from_ref(project,args.dwi_pipeline_config,'diffusion')
                    run_dmri = True
                if args.func_pipeline_config is not None:
                    project.fmri_config_file = create_subject_configuration_from_ref(project,args.func_pipeline_config,'fMRI')
                    run_fmri = True

                if args.anat_pipeline_config is not None:
                    print("Running pipelines : ")
                    print("- anatomical MRI (segmentation and parcellation)")

                    if args.dwi_pipeline_config is not None:
                        print("- diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("- fMRI (functional connectivity matrices)")

                    cmd = create_cmp_command(project=project, run_anat=run_anat, run_dmri=run_dmri, run_fmri=run_fmri)
                    print cmd
                    run(command=cmd)
                else:
                    print "Error: at least anatomical configuration file has to be specified (--anat_pipeline_config)"

        else: #No session structure
            project.subject_sessions = ['']
            project.subject_session = ''

            #Derivatives folder creation (Folder is first deleted if it already exists)
            for tool in tools:
                subject_derivatives_dir = os.path.join(args.output_dir, tool, project.subject)
                if not os.path.isdir(subject_derivatives_dir):
                    os.makedirs(subject_derivatives_dir)

            run_anat = False
            run_dmri = False
            run_fmri = False

            if args.anat_pipeline_config is not None:
                project.anat_config_file = create_subject_configuration_from_ref(project,args.anat_pipeline_config,'anatomical')
                run_anat = True
            if args.dwi_pipeline_config is not None:
                project.dmri_config_file = create_subject_configuration_from_ref(project,args.dwi_pipeline_config,'diffusion')
                run_dmri = True
            if args.func_pipeline_config is not None:
                project.fmri_config_file = create_subject_configuration_from_ref(project,args.func_pipeline_config,'fMRI')
                run_fmri = True

            if args.anat_pipeline_config is not None:
                print("Running pipelines : ")
                print("- anatomical MRI (segmentation and parcellation)")

                if args.dwi_pipeline_config is not None:
                    print("- diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("- fMRI (functional connectivity matrices)")

                cmd = create_cmp_command(project=project, run_anat=run_anat, run_dmri=run_dmri, run_fmri=run_fmri)
                print cmd
                run(command=cmd)
            else:
                print "Error: at least anatomical configuration file has to be specified (--anat_pipeline_config)"

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
