#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  7 10:05:30 2021

@author: katharina
"""

import os
import pickle
import mne
import numpy as np
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec


class CreateBEMInputSpec(BaseInterfaceInputSpec):
    """Input specification for creating MNE source space."""

    subject = traits.Str(
        desc='subject', mandatory=True)

    bids_dir = traits.Str(
        desc='base directory', mandatory=True)

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateBEMOutputSpec(TraitedSpec):
    """Output specification for creating MNE source space."""

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateBEM(BaseInterface):
    input_spec = CreateBEMInputSpec
    output_spec = CreateBEMOutputSpec

    def _run_interface(self, runtime):
        subject = self.inputs.subject
        bids_dir = self.inputs.bids_dir
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query
        
        # bem_dir = os.path.join(bids_dir,'derivatives','freesurfer','subjects',subject,'bem')
        # if not os.path.isdir(bem_dir):
        self._create_BEM(subject, bids_dir)
        
        if 'cmp' not in self.derivative_list:
            self.derivative_list.append('cmp')

        self.output_query['bem'] = {
            'suffix': 'bem',
            'extensions': ['fif']
        }

        return runtime

    @staticmethod
    def _create_BEM(subject,bids_dir):
        # create the boundaries between the tissues, using segmentation file 
        subjects_dir = os.path.join(bids_dir,'derivatives','freesurfer')
        bemfilename = os.path.join(bids_dir,'derivatives','cmp',subject,'eeg',subject+'_bem.fif')
        if not "bem" in os.listdir(os.path.join(subjects_dir,subject)):
            mne.bem.make_watershed_bem(subject,subjects_dir,overwrite=True) # still need to check if this actually works
            # file names required by mne's make_bem_model not consistent with file names outputted by mne's make_watershed_bem - copy and rename 
            for elem in ["inner_skull","outer_skull","outer_skin"]:
                elem1 = subject+'_'+elem+'_surface' # file name used by make_watershed_bem 
                elem2 = elem+'.surf' # file name used by make_bem_model
                if (elem2 not in os.listdir(os.path.join(subjects_dir,subject,'bem'))) and ("watershed" in os.listdir(os.path.join(subjects_dir,subject,'bem'))):
                    cmd = 'cp '+ os.path.join(subjects_dir,subject,'bem','watershed',elem1) + ' ' + os.path.join(subjects_dir,subject,'bem',elem2)
                    os.system(cmd)  
            
        if not os.path.exists(bemfilename):
            # create the conductor model 
            conductivity = (0.3, 0.006, 0.3)  # for three layers 
            model = mne.make_bem_model(subject=subject, ico=4, conductivity=conductivity, subjects_dir=subjects_dir)
            bem = mne.make_bem_solution(model)
            mne.write_bem_solution(bemfilename,bem)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
