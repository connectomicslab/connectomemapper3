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

    base_dir = traits.Str(
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
        base_dir = self.inputs.base_dir
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query

        self._create_BEM(subject, base_dir)

        self.derivative_list.append('MNE')

        self.output_query['bem'] = {
            'scope': 'MNE',
            'extensions': ['fif']
        }

        return runtime

    @staticmethod
    def _create_BEM(subject,base_dir):
        # from notebook 
        # create the boundaries between the tissues, using segmentation file 
        subjects_dir = os.path.join(base_dir,'derivatives','freesurfer','subjects')
        if "bem" not in os.listdir(os.path.join(subjects_dir,subject)):
            # probably not necessary because already done 
            #cmd = "export SUBJECTS_DIR="+subjects_dir
            #os.system(cmd)
            cmd = "mne watershed_bem -s "+subject
            os.system(cmd)
        
        # create the conductor model 
        conductivity = (0.3, 0.006, 0.3)  # for three layers
        bemfilename = os.path.join(subjects_dir,subject,'bem',subject+'_conductor_model.fif')
        for elem in ["inner_skull","outer_skull","outer_skin"]:
            if (elem not in os.listdir(os.path.join(subjects_dir,subject,'bem'))) and ("watershed" in os.listdir(os.path.join(subjects_dir,subject,'bem'))):
                cmd = 'cp '+ os.path.join(subjects_dir,subject,'bem','watershed','*'+elem+'*') + ' ' + os.path.join(subjects_dir,'sub-'+subject,'bem',elem+'.surf')
                os.system(cmd)  
            model = mne.make_bem_model(subject=subject, ico=4,
                               conductivity=conductivity,
                               subjects_dir=subjects_dir)
            bem = mne.make_bem_solution(model)
            mne.write_bem_solution(bemfilename,bem,overwrite=True)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
