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
import sys
import shutil
import subprocess
import multiprocessing
import nibabel
import numpy
from glob import glob

#Own imports
from cmp.project import CMP_Project_Info
from cmp.info import __version__
from cmp import parser

# __version__ = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
#                                 'version')).read()

def create_cmp_command(project,run_anat,run_dmri,run_fmri):

    if len(project.subject_sessions)>0:
        if run_fmri:
            cmd = "connectomemapper3 %s %s %s %s %s %s %s %s %s %s"%(project.base_directory,project.output_directory,project.subject,project.subject_session,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri,project.fmri_config_file,run_fmri)
        else:
            if run_dmri:
                cmd = "connectomemapper3 %s %s %s %s %s %s %s %s"%(project.base_directory,project.output_directory,project.subject,project.subject_session,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri)
            else:
                if run_anat:
                    cmd = "connectomemapper3 %s %s %s %s %s %s"%(project.base_directory,project.output_directory,project.subject,project.subject_session,project.anat_config_file,run_anat)
    else:
        if run_fmri:
            cmd = "connectomemapper3 %s %s %s %s %s %s %s %s %s"%(project.base_directory,project.output_directory,project.subject,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri,project.fmri_config_file,run_fmri)
        else:
            if run_dmri:
                cmd = "connectomemapper3 %s %s %s %s %s %s %s"%(project.base_directory,project.output_directory,project.subject,project.anat_config_file,run_anat,project.dmri_config_file,run_dmri)
            else:
                if run_anat:
                    cmd = "connectomemapper3 %s %s %s %s %s"%(project.base_directory,project.output_directory,project.subject,project.anat_config_file,run_anat)

    return cmd

def readLineByLine(filename):
    with open(filename, 'r') as f: #Use with statement to correctly close the file when you read all the lines.
        for line in f:    # Use implicit iterator over filehandler to minimize memory used
            yield line.strip('\n') #Use generator, to minimize memory used, removing trailing carriage return as it is not part of the command.

def create_subject_configuration_from_ref(project, ref_conf_file, pipeline_type):

    subject_derivatives_dir = os.path.join(project.output_directory)

    # print('project.subject_session: {}'.format(project.subject_session))

    if project.subject_session != '': #Session structure
        # print('With session : {}'.format(project.subject_session))
        subject_conf_file = os.path.join(subject_derivatives_dir,"{}_{}_{}_config.ini".format(project.subject,project.subject_session,pipeline_type))
    else:
        # print('With NO session ')
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

def manage_processes(proclist):
    for proc in proclist:
        if proc.poll() is not None:
            proclist.remove(proc)

def clean_cache(bids_root):
    print('> Clean docker image cache stored in /tmp')
    # Clean cache (issue related that the dataset directory is mounted into /tmp,
    # which is used for caching by java/matlab/matplotlib/xvfb-run in the docker image)

    #Folder can be code/ derivatives/ sub-*/ .datalad/ .git/
    #File can be README.txt CHANGES.txt participants.tsv project_description.json

    for f in glob(os.path.join(bids_root,'._java*')):
        print('... DEL: {}'.format(f))
        try:
            os.remove(f)
        except:
            pass

    for f in glob(os.path.join(bids_root,'mri_segstats.tmp*')):
        print('... DEL: {}'.format(f))
        try:
            os.remove(f)
        except:
            pass

    for d in glob(os.path.join(bids_root,'MCR_*')):
        print('... DEL: {}'.format(d))
        try:
            shutil.rmtree(d)
        except:
            pass

    # for d in glob(os.path.join(bids_root,'matplotlib*')):
    #     print('... DEL: {}'.format(d))
    #     try:
    #         shutil.rmtree(d)
    #     except:
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

    for f in glob(os.path.join(bids_root,'.X99*')):
        print('... DEL: {}'.format(f))
        try:
            os.remove(f)
        except:
            pass


def run(command, env={}, log_filename={}):
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
    #     if line == '' and process.poll() != None:
    #         break
    # if process.returncode != 0:
    #     raise Exception("Non zero return code: %d"%process.returncode)

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
    subjects_to_analyze = [subject_dir.split("-")[-1] for subject_dir in subject_dirs]

print("> Subjects to analyze : {}".format(subjects_to_analyze))

#Derivatives directory creation if it does not exist
derivatives_dir = os.path.abspath(args.output_dir)
if not os.path.isdir(derivatives_dir):
    os.mkdir(derivatives_dir)

tools = ['cmp','freesurfer','nipype']

for tool in tools:
    tool_dir = os.path.join(args.output_dir, tool)
    if not os.path.isdir(tool_dir):
        os.mkdir(tool_dir)

# Make sure freesurfer is happy with the license
print('> Copy FreeSurfer license (BIDS App) ')


if os.access(os.path.join('/tmp','code','license.txt'),os.F_OK):
    os.environ['FS_LICENSE'] = os.path.join('/tmp','code','license.txt')
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
    print("ERROR: Missing license.txt in code/ directory OR unspecified Freesurfer license with the option --fs_license ")
    sys.exit(1)

# TODO: Implement log for subject(_session)
# with open(log_filename, 'w+') as log:
#     proc = Popen(cmd, stdout=log, stderr=log, cwd=os.path.join(self.bids_root,'derivatives'))

# running participant level
if args.analysis_level == "participant":

    maxprocs = multiprocessing.cpu_count()
    processes = []

    # find all T1s and skullstrip them
    for subject_label in subjects_to_analyze:

        project = CMP_Project_Info()
        project.base_directory = args.bids_dir
        project.output_directory = args.output_dir

        project.subjects = ['sub-{}'.format(label) for label in subjects_to_analyze]
        project.subject = 'sub-{}'.format(subject_label)

        # Check if multiple session (sub-XX/ses-YY/anat/... structure or sub-XX/anat.. structure?)
        subject_session_dirs = glob(os.path.join(args.bids_dir, project.subject, "ses-*"))
        project.subject_sessions = ['ses-{}'.format(subject_session_dir.split("-")[-1]) for subject_session_dir in subject_session_dirs]

        if len(project.subject_sessions) > 0: #Session structure

            print("> Sessions to analyze : {}".format(project.subject_sessions))

            for session in project.subject_sessions:

                while len(processes) == maxprocs:
                    self.manage_processes(processes)

                print('> Process subject {} session {}'.format(project.subject,session))
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
                    print("... Anatomical config created : {}".format(project.anat_config_file))
                if args.dwi_pipeline_config is not None:
                    project.dmri_config_file = create_subject_configuration_from_ref(project,args.dwi_pipeline_config,'diffusion')
                    run_dmri = True
                    print("... Diffusion config created : {}".format(project.dmri_config_file))
                if args.func_pipeline_config is not None:
                    project.fmri_config_file = create_subject_configuration_from_ref(project,args.func_pipeline_config,'fMRI')
                    run_fmri = True
                    print("... fMRI config created : {}".format(project.fmri_config_file))

                if args.anat_pipeline_config is not None:
                    print("... Running pipelines : ")
                    print("        - Anatomical MRI (segmentation and parcellation)")

                    if args.dwi_pipeline_config is not None:
                        print("        - Diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("        - fMRI (functional connectivity matrices)")

                    cmd = create_cmp_command(project=project, run_anat=run_anat, run_dmri=run_dmri, run_fmri=run_fmri)
                    print("... cmd : {}".format(cmd))

                    # for label in self.list_of_subjects_to_be_processed:
                    #     while len(processes) == maxprocs:
                    #         self.manage_bidsapp_procs(processes)
                    #
                    #     proc = self.start_bidsapp_participant_level_process(self.bidsapp_tag,label)
                    #     processes.append(proc)
                    #
                    # while len(processes) > 0:
                    #     self.manage_bidsapp_procs(processes)

                    proc = run(command=cmd,env={},log_filename=os.path.join(project.output_directory,'cmp','{}_{}_log.txt'.format(project.subject,project.subject_session)))
                    processes.append(proc)
                else:
                    print "... Error: at least anatomical configuration file has to be specified (--anat_pipeline_config)"

        else: #No session structure

            print('> Process subject {}'.format(project.subject))

            while len(processes) == maxprocs:
                manage_processes(processes)

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
                print("... Anatomical config created : {}".format(project.anat_config_file))
            if args.dwi_pipeline_config is not None:
                project.dmri_config_file = create_subject_configuration_from_ref(project,args.dwi_pipeline_config,'diffusion')
                run_dmri = True
                print("... Diffusion config created : {}".format(project.dmri_config_file))
            if args.func_pipeline_config is not None:
                project.fmri_config_file = create_subject_configuration_from_ref(project,args.func_pipeline_config,'fMRI')
                run_fmri = True
                print("... fMRI config created : {}".format(project.fmri_config_file))

            if args.anat_pipeline_config is not None:
                print("... Running pipelines : ")
                print("        - Anatomical MRI (segmentation and parcellation)")

                if args.dwi_pipeline_config is not None:
                    print("        - Diffusion MRI (structural connectivity matrices)")

                    if args.func_pipeline_config is not None:
                        print("        - fMRI (functional connectivity matrices)")

                cmd = create_cmp_command(project=project, run_anat=run_anat, run_dmri=run_dmri, run_fmri=run_fmri)
                print("... cmd : {}".format(cmd))

                proc = run(command=cmd,env={},log_filename=os.path.join(project.output_directory,'cmp','{}_log.txt'.format(project.subject)))
                processes.append(proc)
            else:
                print "... Error: at least anatomical configuration file has to be specified (--anat_pipeline_config)"

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
