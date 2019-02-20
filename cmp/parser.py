# Copyright (C) 2017-2019, Brain Communication Pathways Sinergia Consortium, Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Multi-scale Brain Parcellator Commandline Parser
"""

from info import __version__
from info import __release_date__

def get():
    import argparse
    p = argparse.ArgumentParser(description='Example BIDS App entrypoint script.')
    p.add_argument('bids_dir', help='The directory with the input dataset '
                        'formatted according to the BIDS standard.')
    p.add_argument('output_dir', help='The directory where the output files '
                        'should be stored. If you are running group level analysis '
                        'this folder should be prepopulated with the results of the'
                        'participant level analysis.')
    p.add_argument('analysis_level', help='Level of the analysis that will be performed. '
                        'Multiple participant level analyses can be run independently '
                        '(in parallel) using the same output_dir.',
                        choices=['participant', 'group'])
    p.add_argument('--participant_label', help='The label(s) of the participant(s) that should be analyzed. The label '
                       'corresponds to sub-<participant_label> from the BIDS spec '
                       '(so it does not include "sub-"). If this parameter is not '
                       'provided all subjects should be analyzed. Multiple '
                       'participants can be specified with a space separated list.',
                       nargs="+")

    p.add_argument('--anat_pipeline_config', help='Configuration .txt file for processing stages of the anatomical MRI processing pipeline')
    p.add_argument('--dwi_pipeline_config', help='Configuration .txt file for processing stages of the diffusion MRI processing pipeline')
    p.add_argument('--func_pipeline_config', help='Configuration .txt file for processing stages of the fMRI processing pipeline')

    # p.add_argument('--skip_bids_validator', help='Whether or not to perform BIDS dataset validation',
    #                    action='store_true')
    p.add_argument('-v', '--version', action='version',
                        version='BIDS-App example version {}'.format(__version__))
    return p
