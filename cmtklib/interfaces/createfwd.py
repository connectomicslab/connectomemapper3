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


class CreateFwdInputSpec(BaseInterfaceInputSpec):
    """Input specification for creating MNE source space."""
    
    fwd_fname = traits.File(
        desc='forward solution created with MNE')    

    src = traits.List(
        exists=True, desc='source space created with MNE', mandatory=True)
    
    bem = traits.List(
        exists=True, desc='boundary surfaces for MNE head model', mandatory=True)
    
    trans_fname = traits.File(
        exists=True, desc='trans.fif file containing co-registration information (electrodes x MRI)')
    
    epochs_fif_fname = traits.File(
        desc='eeg * epochs in .fif format, containing information about electrode montage', mandatory=True)

class CreateFwdOutputSpec(TraitedSpec):
    """Output specification for creating MNE source space."""
    
    has_run = traits.Bool(False, desc='if true, forward solution has been produced')

class CreateFwd(BaseInterface):
    input_spec = CreateFwdInputSpec
    output_spec = CreateFwdOutputSpec

    def _run_interface(self, runtime):

        fwd_fname = self.inputs.fwd_fname      
        src = self.inputs.src[0]
        bem = self.inputs.bem[0]
        trans = self.inputs.trans_fname
        epochs_fname = self.inputs.epochs_fif_fname
        epochs = mne.read_epochs(epochs_fname)
        info = epochs.info 
        
        if os.path.exists(fwd_fname):
            self.has_run = True
        else:
            self.has_run = self._create_Fwd(src, bem, trans, info, fwd_fname)

        return runtime

    @staticmethod
    def _create_Fwd(src,bem,trans,info,fwd_fname):
        mindist = 0. # 5.0
        fwd = mne.make_forward_solution(
            info, trans=trans, src=src,bem=bem, meg=False, eeg=True, mindist=mindist, n_jobs=4)
        mne.write_forward_solution(fwd_fname, fwd, overwrite=True, verbose=None)
        has_run = True
        return has_run

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['has_run'] = self.has_run
        return outputs
