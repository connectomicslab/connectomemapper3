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


class CreateSrcInputSpec(BaseInterfaceInputSpec):
    """Input specification for creating MNE source space."""

    subject = traits.Str(
        desc='subject', mandatory=True)

    bids_dir = traits.Str(
        desc='base directory', mandatory=True)

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateSrcOutputSpec(TraitedSpec):
    """Output specification for creating MNE source space."""

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateSrc(BaseInterface):
    input_spec = CreateSrcInputSpec
    output_spec = CreateSrcOutputSpec

    def _run_interface(self, runtime):
        subject = self.inputs.subject
        bids_dir = self.inputs.bids_dir
        
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query
        
        src_fname = os.path.join(bids_dir,'derivatives','cmp',subject,'eeg',subject+'_src.fif')
        if not os.path.exists(src_fname):
            self._create_src_space(subject,bids_dir,src_fname)
        if 'cmp' not in self.derivative_list:
            self.derivative_list.append('cmp') 

        self.output_query['src'] = {
            'suffix': 'src',
            'extensions': ['fif']
        }

        return runtime

    @staticmethod
    def _create_src_space(subject,bids_dir,src_fname):
        # from notebook 
        overwrite_src = True 
        
        subjects_dir = os.path.join(bids_dir,'derivatives','freesurfer')
        src = mne.setup_source_space(subject=subject, spacing='oct6', subjects_dir=subjects_dir)
        mne.write_source_spaces(src_fname,src,overwrite=overwrite_src)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
