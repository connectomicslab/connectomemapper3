import os
import pandas as pd
import mne
import numpy as np
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec


class EEGLAB2fifInputSpec(BaseInterfaceInputSpec):
    """Input specification for EEGLAB2fif. """

    eeg_ts_file = traits.List(
        exists=True, desc='eeg * epochs in .set format', mandatory=True)

    behav_file = traits.List(
        exists=True, desc='epochs metadata in _behav.txt', mandatory=True)

    epochs_fif_fname = traits.File(
        desc='eeg * epochs in .set format', mandatory=True)
    
    ####
    electrode_positions_file = traits.File(
        exists=True, desc='positions of EEG electrodes in a txt file', mandatory=True)
    
    MRI_align_transform_file = traits.File(
        exists=True, desc='file containing transformation matrix to align electrode positions in electrode_positions_file with the MRI', mandatory=True)
    ####

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class EEGLAB2fifOutputSpec(TraitedSpec):
    """Output specification for EEGLAB2fif."""

    # fif_ts_file = traits.File(
    #	exists=True, desc='eeg * epochs in .fif format', mandatory=True)

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class EEGLAB2fif(BaseInterface):
    """Interface for roitimecourses.svd.
	Inputs
	------
	Outputs
	-------
	"""

    input_spec = EEGLAB2fifInputSpec
    output_spec = EEGLAB2fifOutputSpec

    def _run_interface(self, runtime):
        epochs_file = self.inputs.eeg_ts_file[0]
        behav_file = self.inputs.behav_file[0]
        
        ####
        montage_fname = self.inputs.electrode_positions_file
        dev_head_t_fname = self.inputs.MRI_align_transform_file
        ####
        
        epochs_fif_fname = self.inputs.epochs_fif_fname
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query
        if not os.path.exists(epochs_fif_fname): 
            self._convert_eeglab2fif(epochs_file, behav_file, epochs_fif_fname, montage_fname, dev_head_t_fname)
        self.derivative_list.append('cmp')
        self.output_query['EEG'] = {
            'suffix': 'epo',
            'extensions': ['fif']
        }
        return runtime

    @staticmethod
    def _convert_eeglab2fif(epochs_file, behav_file, epochs_fif_fname, montage_fname, dev_head_t_fname):
        behav = pd.read_csv(behav_file, sep=",")
        behav = behav[behav.bad_trials == 0]
        epochs = mne.read_epochs_eeglab(epochs_file, events=None, event_id=None, eog=(), verbose=None,
                                        uint16_codec=None)
        epochs.events[:, 2] = list(behav.COND)
        epochs.event_id = {"Scrambled": 0, "Faces": 1}
        
        ###
        # apply baseline, re-reference - should be user-defined (?)
        start_t = -0.2
        end_t = 0.6
        epochs.apply_baseline((start_t,0))
        epochs.set_eeg_reference(ref_channels='average',projection = True)
        epochs.crop(tmin=start_t,tmax=end_t)
        ###
        
        ###
        # create info object with information about electrode positions 
        # very specific to our dataset - adapt and make more generic!! 
        n = int(open(montage_fname).readline().lstrip().split(' ')[0])
        all_coord = np.loadtxt(montage_fname, skiprows=1, usecols=(0, 1, 2), max_rows=n)
        all_names = np.loadtxt(montage_fname, skiprows=1, usecols=3, max_rows=n,dtype=np.dtype(str)).tolist()
        all_coord = list(map(lambda x: x/1000,all_coord))
        ch_coord  = [all_coord[idx] for idx, chan in  enumerate(all_names) if chan not in ['lpa','rpa','nasion']]
        ch_names  = [all_names[idx] for idx, chan in  enumerate(all_names) if chan not in ['lpa','rpa','nasion']]    
        # create the montage object with the channel names and positions read from the file 
        montage = mne.channels.make_dig_montage(ch_pos=dict(zip(ch_names, ch_coord)),coord_frame='head')
        # align with MRI 
        dev_head_t = np.loadtxt(dev_head_t_fname)
        montage.dev_head_t = dev_head_t
    
        sfreq = 250. # sampling frequency 
        info = mne.create_info(ch_names, sfreq, 'eeg')
        info.set_montage(montage)
        epochs.info = info
        ###
        
        epochs.save(epochs_fif_fname, overwrite=True)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
