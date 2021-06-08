import os
import pandas as pd
import mne
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec


class EEGLAB2fifInputSpec(BaseInterfaceInputSpec):
    """Input specification for EEGLAB2fif. """

    eeg_ts_file = traits.List(
        exists=True, desc='eeg * epochs in .set format', mandatory=True)

    behav_file = traits.List(
        exists=True, desc='epochs metadata in _behav.txt', mandatory=True)

    epochs_fif_fname = traits.File(
        desc='eeg * epochs in .set format', mandatory=True)

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
        epochs_fif_fname = self.inputs.epochs_fif_fname
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query
        if not os.path.exists(epochs_fif_fname): 
            self._convert_eeglab2fif(epochs_file, behav_file, epochs_fif_fname)
        self.derivative_list.append('cmp')
        self.output_query['EEG'] = {
            'suffix': 'epo',
            'extensions': ['fif']
        }
        return runtime

    @staticmethod
    def _convert_eeglab2fif(epochs_file, behav_file, epochs_fif_fname):
        behav = pd.read_csv(behav_file, sep=",")
        behav = behav[behav.bad_trials == 0]
        epochs = mne.read_epochs_eeglab(epochs_file, events=None, event_id=None, eog=(), verbose=None,
                                        uint16_codec=None)
        epochs.events[:, 2] = list(behav.COND)
        epochs.event_id = {"Scrambled": 0, "Faces": 1}
        epochs.save(epochs_fif_fname, overwrite=True)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
