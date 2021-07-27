# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

import os 
import pickle
import numpy as  np
import mne 
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec

class MNEInverseSolutionInputSpec(BaseInterfaceInputSpec):
    """Input specification for InverseSolution."""
    
    subject = traits.Str(
        desc='subject', mandatory=True)

    bids_dir = traits.Str(
        desc='base directory', mandatory=True)
    
    epochs_fif_fname = traits.File(
        exists=True, desc='eeg * epochs in .set format', mandatory=True)

    src_file = traits.List(
        exists=True, desc='source space created with MNE', mandatory=True)

    bem_file = traits.List(
        exists=True, desc='surfaces for head model', mandatory=True)
  
    cov_has_run = traits.Bool(
        desc='indicates if covariance matrix has been produced', mandatory=True)
    
    noise_cov_fname = traits.File(
        exists=True, desc="noise covariance matrix in fif format", mandatory=True)
    
    fwd_has_run = traits.Bool(
        desc='indicates if forward solution has been produced')
    
    fwd_fname = traits.File(
        desc="forward solution in fif format", mandatory=True)
    
    parcellation = traits.Str(
        desc='parcellation scheme')
    
    roi_ts_file = traits.File(
        exists=False, desc="rois * time series in .npy format")
    
class MNEInverseSolutionOutputSpec(TraitedSpec):
    """Output specification for InverseSolution."""

    roi_ts_file = traits.File(
        exists=True, desc="rois * time series in .npy format")


class MNEInverseSolution(BaseInterface):
    """Interface for MNE inverse solution.
    Inputs
    ------
    Outputs
    -------
    """
    input_spec = MNEInverseSolutionInputSpec
    output_spec = MNEInverseSolutionOutputSpec

    def _run_interface(self, runtime):
        bids_dir = self.inputs.bids_dir
        subject = self.inputs.subject
        epochs_file = self.inputs.epochs_fif_fname   
        src_file = self.inputs.src_file[0]
        fwd_fname = self.inputs.fwd_fname
        noise_cov_fname = self.inputs.noise_cov_fname
        parcellation = self.inputs.parcellation
        self.roi_ts_file = self.inputs.roi_ts_file 
                
        if os.path.exists(self.roi_ts_file):
            roi_tcs = self._createInv_MNE(bids_dir, subject, epochs_file, fwd_fname, noise_cov_fname, src_file, parcellation)
            np.save(self.roi_ts_file, roi_tcs)
        
        return runtime


    def _createInv_MNE(self, bids_dir, subject, epochs_file, fwd_fname, noise_cov_fname, src_file, parcellation):  
        epochs = mne.read_epochs(epochs_file)
        fwd = mne.read_forward_solution(fwd_fname)
        noise_cov = mne.read_cov(noise_cov_fname)
        src = mne.read_source_spaces(src_file, patch_stats=False, verbose=None)
        # compute the inverse operator 
        inverse_operator = mne.minimum_norm.make_inverse_operator(epochs.info, fwd, noise_cov, loose=1, depth=None, fixed=False)
        # compute the time courses of the source points 
        # some parameters 
        method = "sLORETA" 
        snr = 3.
        lambda2 = 1. / snr ** 2
        evoked = epochs.average().pick('eeg')
        stcs = mne.minimum_norm.apply_inverse_epochs(epochs, inverse_operator, lambda2, method, pick_ori="normal", nave=evoked.nave,return_generator=False) 
        
        # get ROI time courses 
        # read the labels of the source points 
        subjects_dir = os.path.join(bids_dir,'derivatives','freesurfer','subjects')
        labels_parc = mne.read_labels_from_annot(subject, parc=parcellation, subjects_dir=subjects_dir)
        # get the ROI time courses 
        roi_tcs = mne.extract_label_time_course(stcs, labels_parc, src, mode='pca_flip', allow_empty=True,
        return_generator=False)
                
        return roi_tcs

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['roi_ts_file'] = self.roi_ts_file
        return outputs

