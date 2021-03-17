import pycartool as cart
import pickle
import numpy as  np
import mne 
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec
import nipype.interfaces.io as nio


class EEGLoaderInputSpec(BaseInterfaceInputSpec):
    """Input specification for EEGLAB2fif. """

    base_directory = traits.Directory(
        exists=True, desc='BIDS data directory', mandatory=True)

    subject_id = traits.Str(
        desc='subject id', mandatory=True)

class EEGLoaderOutputSpec(TraitedSpec):
    """Input specification for EEGLAB2fif. """

    output_query = traits.Dict(
        desc='output query for BIDSDataGrabber', mandatory=True)
    
    base_directory = traits.Directory(
        exists=True, desc='BIDS data directory', mandatory=True)

    subject_id = traits.Str(
        desc='subject id', mandatory=True)

    EEG = traits.List(
            exists=True, desc='eeg * epochs in .set format', mandatory=True)
    events = traits.List(
            exists=True, desc='epochs metadata in _behav.txt', mandatory=True)
    src_file = traits.List(
            exists=True, desc='src (spi loaded with pycartool)', mandatory=True)
    invsol_file = traits.List(
            exists=True, desc='Inverse solution (.is file loaded with pycartool)', mandatory=True)
    parcellation = traits.List(
            exists=True, desc='parcellation scheme', mandatory=True)

class EEGLoader(BaseInterface):

    input_spec = EEGLoaderInputSpec
    output_spec = EEGLoaderOutputSpec
    
    def _run_interface(self, runtime):
        self.base_directory = self.inputs.base_directory
        self.subject_id = self.inputs.subject_id
        self._run_datagrabber()
        return runtime

    def _fill_query(self):
        output_query = {
                        'EEG': {
                                'scope': 'EEGLAB',
                                'suffix': 'eeg',
                                'task': 'FACES',
                                'desc': 'preproc',
                                'extensions': ['set']
                                },
                        'events': {'scope': 'EEGLAB',
                                'suffix': 'events',                                              
                                'extensions': ['txt']},
                        'src_file': {
                                'scope': 'Cartool',
                                'extensions': ['spi']
                                },
                        'invsol_file': {
                                'scope': 'Cartool',
                                'extensions': ['LAURA.is']
                                },
                        'parcellation': {
                                'scope': 'Connectome Mapper',
                                'suffix': 'atlas',
                                'label': 'L2008',
                                'desc': 'scale5',
                                'space': None,
                                },
                        }
        
        return output_query

    def _run_datagrabber(self):
        bidsdatagrabber = nio.BIDSDataGrabber(index_derivatives=True)
        bidsdatagrabber.inputs.base_dir = self.base_directory
        bidsdatagrabber.inputs.subject = self.subject_id
        bidsdatagrabber.inputs.output_query = self._fill_query()        
        self.results = bidsdatagrabber.run()
        
    

    def _list_outputs(self):        
        outputs = self._outputs().get()     
        
        for key, value in self.results.outputs.get().items():
            outputs[key] = value
        
        return outputs
