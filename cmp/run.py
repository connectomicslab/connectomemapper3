#!/usr/bin/env python2
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
import cmp.project
from cmp.info import __version__

# __version__ = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
#                                 'version')).read()

def info():
    print "\nConnectome Mapper (CMP) " + __version__
    print """Copyright (C) 2009-2018, Ecole Polytechnique Fédérale de Lausanne (EPFL) and
             Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
             All rights reserved.\n"""

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

    # Check for MRtrix
    # if subprocess.call("mrconvert",stdout=nul,stderr=nul,shell=True) != 255:
    #     error = """MRtrix3 not installed or not working correctly. Check that PATH variable is updated with MRtrix3 binary (bin) directory."""

    # Check for DTK
    #     if subprocess.call("dti_recon",stdout=nul,stderr=nul,shell=True) != 0 or "DSI_PATH" not in os.environ:
    #         error = """Diffusion Toolkit not installed or not working correctly. Check that
    # the DSI_PATH variable is exported and that the dtk binaries (e.g. dti_recon) are in
    # your path."""

    # Check for DTB
    #     if subprocess.call("DTB_dtk2dir",stdout=nul,stderr=nul,shell=True) != 1:
    #         error = """DTB binaries not installed or not working correctly. Check that the
    # DTB binaries (e.g. DTB_dtk2dir) are in your path and don't give any error."""

    if error != "":
        print error
        sys.exit(2)


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

# running participant level
if args.analysis_level == "participant":

    # find all T1s and skullstrip them
    for subject_label in subjects_to_analyze:


        for T1_file in glob(os.path.join(args.bids_dir, "sub-%s"%subject_label,
                                         "anat", "*_T1w.nii*")) + glob(os.path.join(args.bids_dir,"sub-%s"%subject_label,"ses-*","anat", "*_T1w.nii*")):
            out_file = os.path.split(T1_file)[-1].replace("_T1w.", "_brain.")
            # cmd = "bet %s %s"%(T1_file, os.path.join(args.output_dir, out_file))
            # print(cmd)
            # run(cmd)

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
