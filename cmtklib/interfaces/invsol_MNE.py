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
    
    # base_directory = traits.Directory(
    #     exists=True, desc='BIDS data directory', mandatory=True)
    
    # subject = traits.Str(
    #     desc='subject', mandatory=True)
    
    epochs_fif_fname = traits.File(
        exists=True, desc='eeg * epochs in .set format', mandatory=True)

    src_file = traits.List(
        exists=True, desc='source space created with MNE', mandatory=True)

    bem_file = traits.List(
        exists=True, desc='surfaces for head model', mandatory=True)
  
    cov_has_run = traits.Bool(
        desc='indicates if covariance matrix has been produced')
    
    noise_cov_fname = traits.File(
        exists=True, desc="noise covariance matrix in fif format", mandatory=True)
    
    fwd_has_run = traits.Bool(
        desc='indicates if forward solution has been produced')
    
    fwd_fname = traits.File(
        desc="forward solution in fif format", mandatory=True)
    
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
        epochs_file = self.inputs.epochs_fif_fname   
#         src_file = self.inputs.src_file[0]
#         invsol_file = self.inputs.invsol_file[0]
#         lamda = self.inputs.lamda
#         rois_file = self.inputs.rois_file
#         svd_params = self.inputs.svd_params         
#         self.roi_ts_file = self.inputs.roi_ts_file
#         roi_tcs = self.apply_inverse_epochs_cartool(epochs_file, src_file, invsol_file, lamda, rois_file, svd_params)    
#         np.save(self.roi_ts_file,roi_tcs)

        import pdb
        pdb.set_trace()

        return runtime


    def apply_inverse_epochs_cartool(self, epochs_file, src_file, invsol_file, lamda,rois_file,svd_params):        
        epochs = mne.read_epochs(epochs_file)
        invsol = cart.io.inverse_solution.read_is(invsol_file)
        src = cart.source_space.read_spi(src_file)
        pickle_in = open(rois_file,"rb")
        rois = pickle.load(pickle_in)
        vertices_left  = np.array([idx for idx,coords in enumerate(src.coordinates) if coords[0]<0])
        vertices_right = np.array([idx for idx,coords in enumerate(src.coordinates) if coords[0]>=0])
        K = invsol['regularisation_solutions'][lamda]
        n_rois = len(rois.names)
        times = epochs.times
        tstep = times[1]-times[0]
        roi_tcs = np.zeros((n_rois, len(times),len(epochs.events))) 
        n_spi = np.zeros(n_rois,dtype = int);
        for r in range(n_rois):        
            spis_this_roi = rois.groups_of_indexes[r]
            n_spi[r] = int(len(spis_this_roi))
            roi_stc = np.zeros((3,n_spi[r],len(times),len(epochs.events)))        

            for k, e in enumerate(epochs):        
                #logger.info('Processing epoch : %d%s' % (k + 1, total)) 

                roi_stc[0,:,:,k] = K[0,spis_this_roi] @ e
                roi_stc[1,:,:,k] = K[1,spis_this_roi] @ e
                roi_stc[2,:,:,k] = K[2,spis_this_roi] @ e 

            stim_onset = np.where(times==0)[0][0]
            svd_t_begin = stim_onset+int(svd_params['toi_begin']/tstep)
            svd_t_end = stim_onset+int(svd_params['toi_end']/tstep)

            mean_roi_stc  = np.mean(roi_stc[:,:,svd_t_begin:svd_t_end,:],axis=3)
            u1,_,_ = np.linalg.svd(mean_roi_stc.reshape(3,-1))

            tc_loc = np.zeros((len(times),n_spi[r],len(epochs.events)))  

            for k in range(n_spi[r]):
                for e in range(len(epochs.events)):
                    tc_loc[:,k,e] = u1[:,0].reshape(1,3) @ roi_stc[:,k,:,e]            

            roi_tcs[r,:,:] = np.mean(tc_loc,axis=1)            

        return roi_tcs.transpose(2,0,1)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['roi_ts_file'] = self.roi_ts_file
        return outputs

