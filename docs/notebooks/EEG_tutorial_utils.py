#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 17 15:25:54 2022

@author: katharina
"""

import os
import shutil
import nibabel
import mne
import numpy as np
from cmtklib.bids.io import __cmp_directory__, __freesurfer_directory__


def create_trans_files(data_dir,sub):
    '''
    Helper function that will create the -trans.fif-files necessary to adjust
    electrode positions and run the EEG pipeline tutorial with VEPCON data.
    '''

    # create transform matrix and turn it into trans object
    # transform matrix is a 4x4 matrix whose last column, rows 1-3 indicate shifts
    # in directions x: left to right, y: front to back, z: up to down
    head_to_mri_shift_flipped = np.zeros((3,))
    
    if sub=='sub-01':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.011
    elif sub=='sub-02':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.019
    elif sub=='sub-03':
        head_to_mri_shift_flipped[0] = 0.004
        head_to_mri_shift_flipped[1] = -0.002
        head_to_mri_shift_flipped[2] = 0.015
    elif sub=='sub-04':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = 0
        head_to_mri_shift_flipped[2] = 0.015
    elif sub=='sub-06':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.014
        head_to_mri_shift_flipped[2] = 0.0124
    elif sub=='sub-07':
        head_to_mri_shift_flipped[0] = 0.0025
        head_to_mri_shift_flipped[1] = -0.0085
        head_to_mri_shift_flipped[2] = 0.021
    elif sub=='sub-08':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.005
        head_to_mri_shift_flipped[2] = 0.02
    elif sub=='sub-09':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.02
    elif sub=='sub-10':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.005
        head_to_mri_shift_flipped[2] = 0.02
    elif sub=='sub-11':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.013
        head_to_mri_shift_flipped[2] = 0.013
    elif sub=='sub-12':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = 0
        head_to_mri_shift_flipped[2] = 0.015
    elif sub=='sub-13':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = 0.003
        head_to_mri_shift_flipped[2] = 0.013
    elif sub=='sub-14':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = -0.013
        head_to_mri_shift_flipped[2] = 0.017
    elif sub=='sub-16':
        head_to_mri_shift_flipped[0] = 0.001
        head_to_mri_shift_flipped[1] = -0.012
        head_to_mri_shift_flipped[2] = 0.012
    elif sub=='sub-17':
        head_to_mri_shift_flipped[0] = 0
        head_to_mri_shift_flipped[1] = -0.006
        head_to_mri_shift_flipped[2] = 0.015
    elif sub=='sub-18':
        head_to_mri_shift_flipped[0] = 0.001
        head_to_mri_shift_flipped[1] = -0.009
        head_to_mri_shift_flipped[2] = 0.005
    elif sub=='sub-19':
        head_to_mri_shift_flipped[0] = 0.003
        head_to_mri_shift_flipped[1] = -0.013
        head_to_mri_shift_flipped[2] = 0.012
    elif sub=='sub-20':
        head_to_mri_shift_flipped[0] = 0.002
        head_to_mri_shift_flipped[1] = -0.005
        head_to_mri_shift_flipped[2] = 0.015
        
    head_to_mri = np.eye(4)
    
    head_to_mri[:-1,-1] = head_to_mri_shift_flipped
    np.fill_diagonal(head_to_mri, 1.)
    
    # turn it into trans object and save
    trans = mne.transforms.Transform('head','mri',trans=head_to_mri)
    trans_dir = os.path.join(data_dir,'derivatives',__cmp_directory__,sub,'eeg')
    # if dir doesn't exist yet, create it
    if not os.path.exists(os.path.join(data_dir,'derivatives',__cmp_directory__,sub)):
        os.mkdir(os.path.join(data_dir,'derivatives',__cmp_directory__,sub))
    if not os.path.exists(trans_dir):
        os.mkdir(trans_dir)
    mne.write_trans(os.path.join(trans_dir,sub+'-trans.fif'),trans)