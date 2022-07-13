#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 17 15:25:54 2022
Modified on Sat Jul 09 2022

@author: katharina Glomb, Sebastien Tourbier
"""

import os
import json
import mne
import numpy as np


def create_trans_files(data_dir, cmp3_dir, sub):
    """
    Helper function that will create the -trans.fif-files necessary to adjust
    electrode positions and run the EEG pipeline tutorial with VEPCON data.
    """

    # Create transform matrix and turn it into trans object
    # transform matrix is a 4x4 matrix whose last column, rows 1-3 indicate shifts
    # in directions x: left to right, y: front to back, z: up to down
    head_to_mri_shift_flipped = np.zeros((3,))
    
    if sub == 'sub-01':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.011
    elif sub == 'sub-02':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.019
    elif sub ==' sub-03':
        head_to_mri_shift_flipped[0] = 0.004
        head_to_mri_shift_flipped[1] = -0.002
        head_to_mri_shift_flipped[2] = 0.015
    elif sub == 'sub-04':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = 0
        head_to_mri_shift_flipped[2] = 0.015
    elif sub == 'sub-06':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.014
        head_to_mri_shift_flipped[2] = 0.0124
    elif sub == 'sub-07':
        head_to_mri_shift_flipped[0] = 0.0025
        head_to_mri_shift_flipped[1] = -0.0085
        head_to_mri_shift_flipped[2] = 0.021
    elif sub ==' sub-08':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.005
        head_to_mri_shift_flipped[2] = 0.02
    elif sub == 'sub-09':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.02
    elif sub == 'sub-10':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.005
        head_to_mri_shift_flipped[2] = 0.02
    elif sub == 'sub-11':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.013
        head_to_mri_shift_flipped[2] = 0.013
    elif sub == 'sub-12':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = 0
        head_to_mri_shift_flipped[2] = 0.015
    elif sub == 'sub-13':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = 0.003
        head_to_mri_shift_flipped[2] = 0.013
    elif sub == 'sub-14':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = -0.013
        head_to_mri_shift_flipped[2] = 0.017
    elif sub == 'sub-16':
        head_to_mri_shift_flipped[0] = 0.001
        head_to_mri_shift_flipped[1] = -0.012
        head_to_mri_shift_flipped[2] = 0.012
    elif sub == 'sub-17':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.006
        head_to_mri_shift_flipped[2] = 0.015
    elif sub == 'sub-18':
        head_to_mri_shift_flipped[0] = 0.001
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.005
    elif sub == 'sub-19':
        head_to_mri_shift_flipped[0] = 0.003
        head_to_mri_shift_flipped[1] = -0.013
        head_to_mri_shift_flipped[2] = 0.012
    elif sub == 'sub-20':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = -0.005
        head_to_mri_shift_flipped[2] = 0.015
        
    head_to_mri = np.eye(4)
    
    head_to_mri[:-1, -1] = head_to_mri_shift_flipped
    np.fill_diagonal(head_to_mri, 1.)
    
    # turn it into trans object and save
    trans = mne.transforms.Transform('head', 'mri', trans=head_to_mri)
    trans_dir = os.path.join(data_dir, 'derivatives', cmp3_dir, sub, 'eeg')
    # if dir doesn't exist yet, create it
    if not os.path.exists(trans_dir):
        os.makedirs(trans_dir)
    trans_file = os.path.join(trans_dir, sub+'_trans.fif')
    if not os.path.exists(trans_file):
        print(f'Create transform file: {trans_file}')
        mne.write_trans(trans_file, trans)


def fix_vepcon_derivatives_dataset_description_files(vepcon_dir):
    """
    Helper function that fixes in the VEPCON dataset (v1.1.1) `dataset_description.json` files
    in the `derivatives/cartool-v3.80` and `derivatives/eeglab-v14.1.1`.
    """
    dataset_description_files = {
        'cartool': {
            "Name": "Cartool Outputs (v3.80)",
            "BIDSVersion": "n/a",
            "DatasetType": "derivatives",
            "GeneratedBy": [
                {
                    "Name": "cartool",
                    "Version": "v3.80"
                }
            ]
        },
        'eeglab': {
            "Name": "EEGLAB Outputs (v14.1.1)",
            "BIDSVersion": "n/a",
            "DatasetType": "derivatives",
            "GeneratedBy": [
                {
                    "Name": "EEGLAB",
                    "Version": "v14.1.1"
                }
            ],
            "License": "TODO: To be updated (See https://creativecommons.org/about/cclicenses/)"
        }
    }
    for key, dd_dict in dataset_description_files.items():
        dd_file = os.path.join(
            vepcon_dir, 'derivatives',
            f'{key}-{dd_dict["GeneratedBy"][0]["Version"]}',
            'dataset_description.json'
        )
        with open(dd_file, 'w') as f:
            print(f'Replace {dd_file}')
            json.dump(dd_dict, f, indent=4)
