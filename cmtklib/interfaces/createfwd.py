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
    
    src = traits.List(
        exists=True, desc='source space created with MNE', mandatory=True)
    
    bem = traits.List(
        exists=True, desc='boundary surfaces for MNE head model', mandatory=True)
    
    trans_fname = traits.File(
        exists=True, desc='trans.fif file containing co-registration information (electrodes x MRI)')

class CreateFwdOutputSpec(TraitedSpec):
    """Output specification for creating MNE source space."""

    fwd = traits.List(
        exists=True, desc='forwards solution created with MNE')    


class CreateFwd(BaseInterface):
    input_spec = CreateFwdInputSpec
    output_spec = CreateFwdOutputSpec

    def _run_interface(self, runtime):

        src = self.inputs.src
        bem = self.inputs.bem
        trans = self.inputs.trans_fname
        fwd = self._create_Fwd(src, bem, trans)

        return runtime

    @staticmethod
    def _create_Fwd(src,bem,trans):
        fwd = mne.make_forward_solution(info, trans=trans, src=src,
                                    bem=bem, meg=False, eeg=True, mindist=5.0, n_jobs=4)
    
        mne.write_forward_solution(fwd_fname, fwd, overwrite=True, verbose=None)


    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
