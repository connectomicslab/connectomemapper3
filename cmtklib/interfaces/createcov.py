# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

import os
import pickle
import mne
import numpy as np
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec


class CreateCovInputSpec(BaseInterfaceInputSpec):
    """Input specification for creating noise covariance matrix."""
    
    epochs_fif_fname = traits.File(
        desc='eeg * epochs in .set format', mandatory=True)
    
    noise_cov_fname = traits.File(
        desc='Location and name to store noise covariance matrix in fif format', mandatory=True)

class CreateCovOutputSpec(TraitedSpec):
    """Output specification for creating noise covariance matrix."""

    has_run = traits.Bool(False, desc='if true, covariance matrix has been produced')


class CreateCov(BaseInterface):
    input_spec = CreateCovInputSpec
    output_spec = CreateCovOutputSpec

    def _run_interface(self, runtime):

        epochs_fname = self.inputs.epochs_fif_fname
        noise_cov_fname = self.inputs.noise_cov_fname
        
        if os.path.exists(noise_cov_fname):
            self.has_run = True
        else:
            self.has_run = self._create_Cov(epochs_fname,noise_cov_fname)

        return runtime

    @staticmethod
    def _create_Cov(epochs_fname,noise_cov_fname):
        # load events and EEG data 
        epochs = mne.read_epochs(epochs_fname)
        noise_cov = mne.compute_covariance(epochs,
                                           keep_sample_mean=True,
                                           tmin=-0.2, tmax=0., 
                                           method=['shrunk', 'empirical'], 
                                           verbose=True)
        mne.write_cov(noise_cov_fname,noise_cov)
        has_run = True
        return has_run 
        

        # montage.ch_names = epochs.ch_names
        # epochs.set_montage(montage)
        # epochs.apply_baseline((-.2,0))
        # epochs.set_eeg_reference(ref_channels='average',projection = True)
        # epochs.crop(tmin=-.2,tmax=.6)
        # epochs.apply_proj()
        

    def _list_outputs(self):
        outputs = self._outputs().get()
        # outputs['output_query'] = self.output_query
        # outputs['derivative_list'] = self.derivative_list
        #outputs['noise_cov_file'] = 'bla'
        return outputs
