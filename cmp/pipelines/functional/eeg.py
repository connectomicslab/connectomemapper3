# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" EEG pipeline Class definition
"""

import datetime
import os
import glob
import shutil

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from nipype import config, logging

from traits.api import *

import cmp.pipelines.common as cmp_common
from cmp.pipelines.common import *
from cmp.stages.eeg.eeg_loader import EEGLoaderStage
from cmp.stages.eeg.eeg_preparer import EEGPreparerStage
from cmp.stages.eeg.eeg_inverse_solution import EEGInverseSolutionStage
from cmp.info import __version__
from cmtklib.bids.io import __nipype_directory__


class Global_Configuration(HasTraits):
    process_type = Str('EEG')
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str


class Check_Input_Notification(HasTraits):
    message = Str
    eeg_format_options = List(['set', 'fif'])
    eeg_format = Str
    eeg_format_message = Str(
        '\nMultiple EEG formats available. Please select desired EEG format.')

class EEGPipeline(Pipeline):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("EEG_pipeline")
    input_folders = ['anat', 'eeg']
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ['EEGPreparer',
                          'EEGLoader',
                          'InverseSolution']

    global_conf = Global_Configuration()
    config_file = Str
    parcellation_scheme = Str
    atlas_info = Dict()
    eeg_format = Str
    subjects_dir = Str

    flow = Instance(pe.Workflow)

    def __init__(self, project_info):

        self.subject = project_info.subject

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = project_info.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory = os.path.join(
                project_info.base_directory,
                project_info.subject,
                project_info.subject_session
            )
        else:
            self.global_conf.subject_session = ''
            self.subject_directory = os.path.join(
                project_info.base_directory,
                project_info.subject
            )

        self.derivatives_directory = os.path.abspath(project_info.output_directory)

        if project_info.output_directory is not None:
            self.output_directory = os.path.abspath(project_info.output_directory)
        else:
            self.output_directory = os.path.join(self.base_directory, "derivatives")

        self.stages = {
            'EEGPreparer': EEGPreparerStage(bids_dir=project_info.base_directory, output_dir=self.output_directory),
            'EEGLoader': EEGLoaderStage(bids_dir=project_info.base_directory, output_dir=self.output_directory),
            'EEGInverseSolution': EEGInverseSolutionStage(bids_dir=project_info.base_directory,
                                                          output_dir=self.output_directory),
        }

        cmp_common.Pipeline.__init__(self, project_info)

        cmp3_dir = os.path.join(self.derivatives_directory,f'cmp-{__version__}')
        self.stages['EEGPreparer'].config.cmp3_dir = cmp3_dir
        # removing the following three lines because these parameters are all set to default values at this point (the config file hasn't been read yet), so setting them with each other is pointless
        self.stages['EEGPreparer'].config.cartool_dir = os.path.join(self.derivatives_directory, 'Cartool-v3.80')
        # self.stages['EEGLoader'].config.eeg_format = self.stages['EEGPreparer'].config.eeg_format
        # self.stages['EEGLoader'].config.invsol_format = self.stages['EEGPreparer'].config.invsol_format

    # self.stages['EEGPreparer'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
    # self.stages['EEGLoader'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
    # self.stages['EEGInverseSolution'].config.on_trait_change(self.update_parcellation_scheme, 'parcellation_scheme')

    def check_config(self):
        raise NotImplementedError

    def check_input(self, layout, gui=True):
        """Check if input of the eeg pipeline are available.

        Parameters
        ----------
        layout : bids.BIDSLayout
            Instance of BIDSLayout

        gui : traits.Bool
            Boolean used to display different messages
            but not really meaningful anymore since the GUI
            components have been migrated to `cmp.bidsappmanager`

        Returns
        -------
        valid_inputs : traits.Bool
            True if inputs are available
        """
        print('**** Check Inputs is still not implemented ****')
        # eeg_available = False
        # epochs_available = False
        valid_inputs = True
        return valid_inputs

    def check_output(self):
        raise NotImplementedError

    def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):
        datasource = pe.Node(
            interface=util.IdentityInterface(
                fields=[
                    'base_directory',
                    'subject',
                    'cmp_deriv_subject_directory',
                    'nipype_deriv_subject_directory',
                ],
                mandatory_inputs=True
            ),
            name="datasource"
        )

        datasource.inputs.base_directory = self.base_directory
        datasource.inputs.subject = self.subject
        datasource.inputs.cmp_deriv_subject_directory = cmp_deriv_subject_directory
        datasource.inputs.nipype_deriv_subject_directory = nipype_deriv_subject_directory


        # Create common_flow
        eeg_flow = pe.Workflow(
            name='eeg_pipeline',
            base_dir=os.path.abspath(nipype_deriv_subject_directory)
        )

        # set a couple of config parameters that were read from the config file
        self.stages['EEGLoader'].config.eeg_format = self.stages['EEGPreparer'].config.eeg_format
        self.stages['EEGLoader'].config.invsol_format = self.stages['EEGPreparer'].config.invsol_format
        self.stages['EEGInverseSolution'].config.invsol_format = self.stages['EEGPreparer'].config.invsol_format

        # create stages (parameters specified in config file are read and set)
        preparer_flow = self.create_stage_flow("EEGPreparer")
        loader_flow = self.create_stage_flow("EEGLoader")
        invsol_flow = self.create_stage_flow("EEGInverseSolution")

        # read name of eeg file and determine format and derivatives folder name
        epochs_fname = self.stages['EEGPreparer'].config.epochs
        file_extension_start = epochs_fname.find('.')
        eeg_format = epochs_fname[file_extension_start:]
        if eeg_format=='.set':
            derivatives_folder = 'eeglab'
        elif eeg_format=='.fif':
            derivatives_folder = 'mne'
        else:
            pass # throw not implemented exception

        self.stages['EEGPreparer'].config.eeg_format = eeg_format

        datasource.inputs.epochs = [os.path.join(self.base_directory,'derivatives',derivatives_folder, self.subject,
                                                 'eeg', epochs_fname)]

        datasource.inputs.EEG_params = self.stages['EEGPreparer'].config.EEG_params

        # read name of parcellation and determine file name
        parcellation_label = self.stages['EEGPreparer'].config.parcellation['label']
        parcellation_desc = self.stages['EEGPreparer'].config.parcellation['desc']
        parcellation_suffix = self.stages['EEGPreparer'].config.parcellation['suffix']

        if self.stages['EEGPreparer'].config.eeg_format == '.set':
            # file with events/behavioral info
            expe_name = datasource.inputs.EEG_params['expe_name']
            datasource.inputs.behav_file = [
                os.path.join(
                    self.base_directory,
                    'derivatives',
                    'eeglab',
                    self.subject, 'eeg', self.subject + '_task-' + expe_name + '_desc-preproc_events.tsv'
                )
            ]

            # name of output file (EEG data source level)
            datasource.inputs.epochs_fif_fname = os.path.join(
                self.base_directory,
                'derivatives',
                f'cmp-{__version__}',
                self.subject, 'eeg', self.subject + '_epo.fif'
            )


        # name of output file (ROI time courses)
        datasource.inputs.roi_ts_file = os.path.join(
            self.base_directory,
            'derivatives',
            f'cmp-{__version__}',
            self.subject,
            'eeg',
            self.subject + '_rtc_epo.npy'
        )

        datasource.inputs.output_query = dict()

        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="eeg_sinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)

        # Clear previous outputs
        self.clear_stages_outputs()

        # fmt: off
        if self.stages['EEGPreparer'].config.invsol_format.split('-')[0] == "Cartool":
            # atlas image is required
            parcellation = self.subject + '_atlas-' +parcellation_label + '_res-' + parcellation_suffix + '_dseg.nii.gz'
            datasource.inputs.parcellation = os.path.join(self.base_directory, 'derivatives', f'cmp-{__version__}', self.subject,
                                                       'anat', parcellation)

            eeg_flow.connect(
                [
                    (datasource, preparer_flow, [('epochs', 'inputnode.epochs'),
                                                 ('subject', 'inputnode.subject'),
                                                 ('behav_file', 'inputnode.behav_file'),
                                                 ('parcellation', 'inputnode.parcellation'),
                                                 ('epochs_fif_fname', 'inputnode.epochs_fif_fname'),
                                                 ('EEG_params','inputnode.EEG_params'),
                                                 ('output_query', 'inputnode.output_query'),
                                                 ('base_directory','inputnode.bids_dir')]),
                    (datasource, loader_flow, [('base_directory', 'inputnode.base_directory'),
                                               ('subject', 'inputnode.subject')]),
                    (preparer_flow, loader_flow, [('outputnode.output_query', 'inputnode.output_query'),
                                                  ('outputnode.derivative_list', 'inputnode.derivative_list')]),
                    (loader_flow, invsol_flow, [('outputnode.EEG', 'inputnode.eeg_ts_file'),
                                                ('outputnode.rois', 'inputnode.rois_file'),
                                                ('outputnode.src', 'inputnode.src_file'),
                                                ('outputnode.invsol', 'inputnode.invsol_file')]),
                    (datasource, invsol_flow, [('roi_ts_file', 'inputnode.roi_ts_file')]),
                    (preparer_flow, invsol_flow, [('outputnode.invsol_params', 'inputnode.invsol_params')]),
                    (invsol_flow, sinker, [("outputnode.roi_ts_file", "eeg.@roi_ts_file")]),
                ]
            )
        elif self.stages['EEGPreparer'].config.invsol_format.split('-')[0] == 'mne':

            # Freesurfer annot files are required
            if parcellation_suffix=='':
                parcellation = parcellation_label # aparc
            else:
                parcellation = parcellation_label + '.' + parcellation_suffix # lausanne2008.scalex where x=1...5

            datasource.inputs.parcellation = parcellation

            # define names for MNE outputs
            datasource.inputs.noise_cov_fname = os.path.join(self.base_directory,
                                                             'derivatives',f'cmp-{__version__}',
                                                             self.subject,
                                                             'eeg',
                                                             self.subject + '_noisecov.fif')

            datasource.inputs.trans_fname = os.path.join(self.base_directory,
                                                         'derivatives',
                                                         f'cmp-{__version__}',
                                                         self.subject,
                                                         'eeg',
                                                         self.subject + '-trans.fif')

            datasource.inputs.fwd_fname = os.path.join(self.base_directory,
                                                         'derivatives',
                                                         f'cmp-{__version__}',
                                                         self.subject,
                                                         'eeg',
                                                         self.subject + '-fwd.fif')

            datasource.inputs.inv_fname = os.path.join(self.base_directory,
                                                        'derivatives',
                                                        f'cmp-{__version__}',
                                                         self.subject,
                                                         'eeg',
                                                         self.subject + '-inv.fif')

            ######
            # These two files come from cartool, which is non-standard, needs to be fixed!!
            datasource.inputs.electrode_positions_file = os.path.join(self.base_directory,
                                                                      'derivatives',
                                                                      'eeglab',
                                                                      self.subject,
                                                                      'eeg',
                                                                      self.subject + '.xyz')
            #######

            eeg_flow.connect(
                [
                    (datasource, preparer_flow, [('epochs', 'inputnode.epochs'),
                                                  ('subject', 'inputnode.subject'),
                                                  ('behav_file', 'inputnode.behav_file'),
                                                  ('parcellation', 'inputnode.parcellation'),
                                                  ('epochs_fif_fname', 'inputnode.epochs_fif_fname'),
                                                  ('electrode_positions_file','inputnode.electrode_positions_file'),
                                                  ('EEG_params','inputnode.EEG_params'),
                                                  ('output_query', 'inputnode.output_query'),
                                                  ('base_directory','inputnode.bids_dir')]),

                    (datasource, loader_flow, [('base_directory', 'inputnode.base_directory'),
                                                ('subject', 'inputnode.subject')]),

                    (preparer_flow, loader_flow, [('outputnode.output_query', 'inputnode.output_query'),
                                                  ('outputnode.derivative_list', 'inputnode.derivative_list')]),

                    (datasource, invsol_flow, [('subject', 'inputnode.subject'),
                                               ('base_directory','inputnode.bids_dir'),
                                               ('noise_cov_fname','inputnode.noise_cov_fname'),
                                               ('trans_fname','inputnode.trans_fname'),
                                               ('fwd_fname','inputnode.fwd_fname'),
                                               ('inv_fname','inputnode.inv_fname'),
                                               ('parcellation', 'inputnode.parcellation'),
                                               ('roi_ts_file', 'inputnode.roi_ts_file')]),

                    (preparer_flow, invsol_flow, [('outputnode.epochs_fif_fname','inputnode.epochs_fif_fname')]),

                    (loader_flow, invsol_flow, [('outputnode.src', 'inputnode.src_file'),
                                                ('outputnode.bem', 'inputnode.bem_file')]),

                    (invsol_flow, sinker, [("outputnode.roi_ts_file", "eeg.@roi_ts_file")]),
                ]
            )
        # fmt: on

        self.flow = eeg_flow
        return eeg_flow

    def process(self):
        """Executes the anatomical pipeline workflow and returns True if successful."""
        # Enable the use of the W3C PROV data model to capture and represent provenance in Nipype
        # config.enable_provenance()

        # Process time
        self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        if '_' in self.subject:
            self.subject = self.subject.split('_')[0]

        if self.global_conf.subject_session == '':
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory, f'cmp-{__version__}', self.subject
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, __nipype_directory__, self.subject
            )
        else:
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory, f'cmp-{__version__}', self.subject, self.global_conf.subject_session
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, __nipype_directory__, self.subject, self.global_conf.subject_session
            )

            self.subject = "_".join(
                (self.subject, self.global_conf.subject_session)
            )

        if not os.path.exists(os.path.join(nipype_deriv_subject_directory, "eeg_pipeline")):
            try:
                os.makedirs(
                    os.path.join(nipype_deriv_subject_directory, "eeg_pipeline")
                )
            except os.error:
                print(
                    "%s was already existing" % os.path.join(
                        nipype_deriv_subject_directory,
                        "eeg_pipeline"
                    )
                )

        # Initialization
        if os.path.isfile(os.path.join(nipype_deriv_subject_directory, "eeg_pipeline", "pypeline.log")):
            os.unlink(
                os.path.join(nipype_deriv_subject_directory, "eeg_pipeline", "pypeline.log"))
        config.update_config(
            {
                'logging': {
                    'log_directory': os.path.join(nipype_deriv_subject_directory, "eeg_pipeline"),
                    'log_to_file': True
                },
                'execution': {
                    'remove_unnecessary_outputs': False,
                    'stop_on_first_crash': True,
                    'stop_on_first_rerun': False,
                    'use_relative_paths': True,
                    'crashfile_format': "txt"
                }
            }
        )
        logging.update_logging(config)

        iflogger = logging.getLogger('nipype.interface')
        iflogger.info("**** Processing ****")

        eeg_flow = self.create_pipeline_flow(
            cmp_deriv_subject_directory=cmp_deriv_subject_directory,
            nipype_deriv_subject_directory=nipype_deriv_subject_directory
        )
        eeg_flow.write_graph(graph2use='colored', format='svg', simple_form=True)

        if self.number_of_cores != 1:
            eeg_flow.run(
                plugin='MultiProc',
                plugin_args={
                    'n_procs': self.number_of_cores
                }
            )
        else:
            eeg_flow.run()

        iflogger.info("**** Processing finished ****")

        return True
