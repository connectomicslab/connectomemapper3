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

    base_dir = traits.Str(
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
        base_dir = self.inputs.base_dir
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query

        self._create_src_space(subject, base_dir)

        self.derivative_list.append('MNE')

        self.output_query['src'] = {
            'scope': 'MNE',
            'extensions': ['fif']
        }

        return runtime

    @staticmethod
    def _create_src_space(subject,base_dir):
        # from notebook 
        overwrite_src = True 
        src_fname = os.path.join(base_dir,'derivatives','mne',subject,subject+'-oct6-src_surf_only.fif')
        subjects_dir = os.path.join(base_dir,'derivatives','freesurfer','subjects')
        src = mne.setup_source_space(subject=subject, spacing='oct6', subjects_dir=subjects_dir)
        mne.write_source_spaces(src_fname,src,overwrite=overwrite_src)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
