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

class CreateCovOutputSpec(TraitedSpec):
    """Output specification for creating noise covariance matrix."""

    noise_cov_file = traits.File(
        exists=True, desc="noise covariance matrix in fif format", mandatory=True)


class CreateCov(BaseInterface):
    input_spec = CreateCovInputSpec
    output_spec = CreateCovOutputSpec

    def _run_interface(self, runtime):

        epochs_fname = self.inputs.epochs_fif_fname
        self._create_Cov(epochs_fname)

        # self.noise_cov_file = os.path.join(base_dir,'derivatives','cmp',subject,'eeg',subject+'_noise_cov.fif')

        return runtime

    @staticmethod
    def _create_Cov(epochs_fname):
        # load events and EEG data 
        events = mne.read_events(epochs_fname)
        import pdb
        pdb.set_trace()
        # epochs = mne.read_epochs_eeglab(EEG_data, events=events,event_id=event_id, eog=(), verbose=None, uint16_codec=None)
        # montage.ch_names = epochs.ch_names
        # epochs.set_montage(montage)
        # epochs.apply_baseline((-.2,0))
        # epochs.set_eeg_reference(ref_channels='average',projection = True)
        # epochs.crop(tmin=-.2,tmax=.6)
        # epochs.apply_proj()
    
        # # noise covariance matrix     
        # noise_cov = mne.compute_covariance(epochs,
        #                                    keep_sample_mean=True,
        #                                    tmin=-0.2, tmax=0., 
        #                                    method=['shrunk', 'empirical'], 
        #                                    verbose=True)
        # mne.write_cov(cov_fname,noise_cov)
        

    def _list_outputs(self):
        outputs = self._outputs().get()
        # outputs['output_query'] = self.output_query
        # outputs['derivative_list'] = self.derivative_list
        outputs['noise_cov_file'] = 'bla'
        return outputs
