# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""EEG pipeline Class definition."""

import datetime

import nipype.interfaces.io as nio
from nipype import config, logging

import cmp.pipelines.common as cmp_common
from cmp.info import __version__
from cmp.pipelines.common import *
from cmp.stages.eeg.inverse_solution import EEGInverseSolutionStage
from cmp.stages.eeg.loader import EEGLoaderStage
from cmp.stages.eeg.preparer import EEGPreparerStage
from cmtklib.bids.io import (
    __cmp_directory__,
    __nipype_directory__,
    __cartool_directory__,
    __eeglab_directory__
)


class GlobalConfig(HasTraits):
    """Global EEG pipeline configurations.

    Attributes
    ----------
    process_type : 'EEG'
        Processing pipeline type

    subjects : traits.List
       List of subjects ID (in the form ``sub-XX``)

    subject : traits.Str
       Subject to be processed (in the form ``sub-XX``)

    subject_session : traits.Str
       Subject session to be processed (in the form ``ses-YY``)
    """

    process_type = Str("EEG")
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str


class EEGPipeline(Pipeline):
    """Class that extends a :class:`Pipeline` and represents the processing pipeline for EEG.

    It is composed of:
        * the EEG preparer stage that ...

        * the EEG loader stage that ...

        * the EEG inverse solution stage that ...

    See Also
    --------
    cmp.stages.eeg.preparer.EEGPreparerStage
    cmp.stages.eeg.loader.EEGLoaderStage
    cmp.stages.eeg.inverse_solution.EEGInverseSolutionStage
    """

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("EEG_pipeline")
    input_folders = ["anat", "eeg"]
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ["EEGPreparer", "EEGLoader", "InverseSolution"]

    global_conf = GlobalConfig()
    config_file = Str
    parcellation_scheme = Str
    atlas_info = Dict()
    eeg_format = Str
    subjects_dir = Str

    flow = Instance(pe.Workflow)

    def __init__(self, project_info):
        """Constructor of a `EEGPipeline` object.

        Parameters
        ----------
        project_info: cmp.project.ProjectInfo
            Instance of `CMP_Project_Info` object.

        See Also
        --------
        cmp.project.CMP_Project_Info
        """
        self.subject = project_info.subject

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = project_info.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory = os.path.join(
                project_info.base_directory, project_info.subject, project_info.subject_session
            )
        else:
            self.global_conf.subject_session = ""
            self.subject_directory = os.path.join(project_info.base_directory, project_info.subject)

        self.derivatives_directory = os.path.abspath(project_info.output_directory)

        if project_info.output_directory is not None:
            self.output_directory = os.path.abspath(project_info.output_directory)
        else:
            self.output_directory = os.path.join(self.base_directory, "derivatives")

        self.stages = {
            "EEGPreparer": EEGPreparerStage(bids_dir=project_info.base_directory, output_dir=self.output_directory),
            "EEGLoader": EEGLoaderStage(bids_dir=project_info.base_directory, output_dir=self.output_directory),
            "EEGInverseSolution": EEGInverseSolutionStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
        }

        cmp_common.Pipeline.__init__(self, project_info)

        cmp3_dir = os.path.join(self.derivatives_directory, f"cmp-{__version__}")
        self.stages["EEGPreparer"].config.cmp3_dir = cmp3_dir
        # Removing the following three lines because these parameters are all set to default
        # values at this point (the config file hasn't been read yet), so setting them with
        # each other is pointless
        self.stages["EEGPreparer"].config.cartool_dir = os.path.join(self.derivatives_directory, __cartool_directory__)
        # self.stages['EEGLoader'].config.eeg_format = self.stages['EEGPreparer'].config.eeg_format
        # self.stages['EEGLoader'].config.invsol_format = self.stages['EEGPreparer'].config.invsol_format

    # TODO: Re-integrate the lines below for integration in the GUI
    # self.stages['EEGPreparer'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
    # self.stages['EEGLoader'].config.on_trait_change(self.update_eeg_format, 'eeg_format')
    # self.stages['EEGInverseSolution'].config.on_trait_change(self.update_parcellation_scheme, 'parcellation_scheme')

    def check_config(self):
        # TODO: To Be Implemented if Necessary
        raise NotImplementedError

    def check_input(self, layout, gui=True):
        """Check if input of the eeg pipeline are available (Not available yet).

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
        print("**** Check Inputs is still not implemented ****")
        # TODO: To Be Implemented
        # eeg_available = False
        # epochs_available = False
        valid_inputs = True
        return valid_inputs

    # TODO: To Be Implemented if Necessary
    # def check_output(self):
    #     raise NotImplementedError

    def create_datagrabber_node(self, **kwargs):
        """Create the appropriate Nipype DataGrabber node depending on the `parcellation_scheme`

        Parameters
        ----------
        base_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        bids_atlas_label : string
            Parcellation atlas label

        Returns
        -------
        datasource : Output Nipype DataGrabber Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.DataGrabber` interface
        """
        # TODO: To Be Implemented
        print(kwargs)
        datasource = None
        return datasource

    def init_subject_derivatives_dirs(self):
        """Return the paths to Nipype and CMP derivatives folders of a given subject / session.

        Notes
        -----
        `self.subject` is updated to "sub-<participant_label>_ses-<session_label>"
        when subject has multiple sessions.
        """
        if "_" in self.subject:
            self.subject = self.subject.split("_")[0]

        if self.global_conf.subject_session == "":
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory, __cmp_directory__, self.subject
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, __nipype_directory__, self.subject
            )
        else:
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory,
                __cmp_directory__,
                self.subject,
                self.global_conf.subject_session,
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory,
                __nipype_directory__,
                self.subject,
                self.global_conf.subject_session,
            )

            self.subject = "_".join((self.subject, self.global_conf.subject_session))

        nipype_eeg_pipeline_subject_dir = os.path.join(nipype_deriv_subject_directory, "eeg_pipeline")
        if not os.path.exists(nipype_eeg_pipeline_subject_dir):
            try:
                os.makedirs(nipype_eeg_pipeline_subject_dir)
            except os.error:
                print(f"{nipype_eeg_pipeline_subject_dir} was already existing")

        return cmp_deriv_subject_directory, nipype_deriv_subject_directory, nipype_eeg_pipeline_subject_dir

    def create_pipeline_flow(self, cmp_deriv_subject_directory, nipype_deriv_subject_directory):
        """Create the workflow of the EEG pipeline.

        Parameters
        ----------
        cmp_deriv_subject_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        nipype_deriv_subject_directory : Directory
            Intermediate Nipype output directory of a subject
            e.g. ``/output_dir/nipype/sub-XX/(ses-YY)``

        Returns
        -------
        eeg_flow : nipype.pipeline.engine.Workflow
            An instance of :class:`nipype.pipeline.engine.Workflow`
        """
        datasource = pe.Node(
            interface=util.IdentityInterface(
                fields=[
                    "base_directory",
                    "subject",
                    "cmp_deriv_subject_directory",
                    "nipype_deriv_subject_directory",
                ],
                mandatory_inputs=True,
            ),
            name="datasource",
        )

        datasource.inputs.base_directory = self.base_directory
        datasource.inputs.subject = self.subject
        datasource.inputs.cmp_deriv_subject_directory = cmp_deriv_subject_directory
        datasource.inputs.nipype_deriv_subject_directory = nipype_deriv_subject_directory

        # Create common_flow
        eeg_flow = pe.Workflow(name="eeg_pipeline", base_dir=os.path.abspath(nipype_deriv_subject_directory))

        # Set a couple of config parameters that were read from the config file
        self.stages["EEGLoader"].config.eeg_format = self.stages["EEGPreparer"].config.eeg_format
        self.stages["EEGLoader"].config.invsol_format = self.stages["EEGPreparer"].config.invsol_format
        self.stages["EEGInverseSolution"].config.invsol_format = self.stages["EEGPreparer"].config.invsol_format

        # Create stages (parameters specified in config file are read and set)
        preparer_flow = self.create_stage_flow("EEGPreparer")
        loader_flow = self.create_stage_flow("EEGLoader")
        invsol_flow = self.create_stage_flow("EEGInverseSolution")

        # Read name of eeg file and determine format and derivatives folder name
        epochs_fname = self.stages["EEGPreparer"].config.epochs
        file_extension_start = epochs_fname.find(".")
        eeg_format = epochs_fname[file_extension_start:]
        if eeg_format == ".set":
            derivatives_folder = __eeglab_directory__
        elif eeg_format == ".fif":
            derivatives_folder = "mne"
        else:
            pass  # Throw not implemented exception (Dangerous! What happens is derivatives folder is not set!)

        # Define diverse EEG derivatives folder (TODO: Handle sessions)
        cmp_path_prefix_file = os.path.join(
            self.base_directory, 'derivatives', f'cmp-{__version__}', self.subject, 'eeg'
        )
        eeglab_path_prefix_file = os.path.join(
            self.base_directory, 'derivatives', __eeglab_directory__, self.subject, 'eeg'
        )
        derivatives_path_prefix_file = os.path.join(
            os.path.join(self.base_directory, "derivatives", derivatives_folder, self.subject, "eeg")
        )

        self.stages["EEGPreparer"].config.eeg_format = eeg_format

        datasource.inputs.epochs = [
            os.path.join(derivatives_path_prefix_file, epochs_fname)
        ]

        datasource.inputs.EEG_params = self.stages["EEGPreparer"].config.EEG_params

        # Read name of parcellation and determine file name
        parcellation_atlas = self.stages["EEGPreparer"].config.parcellation["atlas"]
        parcellation_resolution = self.stages["EEGPreparer"].config.parcellation["res"]
        
        print('Parcellation atlas: ', parcellation_atlas)
        print('Parcellation resolution: ', parcellation_resolution)
        
        if parcellation_atlas == 'lausanne2018':
            parcellation_atlas = 'L2018'

        if self.stages["EEGPreparer"].config.eeg_format == ".set":
            # File with events/behavioral info
            expe_name = datasource.inputs.EEG_params["expe_name"]
            datasource.inputs.behav_file = [
                os.path.join(
                    self.base_directory,
                    self.subject,
                    "eeg",
                    self.subject + "_task-" + expe_name + "_events.tsv",
                )
            ]

            # Name of output file (EEG data source level)
            datasource.inputs.epochs_fif_fname = os.path.join(
                cmp_path_prefix_file,  f"{self.subject}_epo.fif"
            )

        # Name of output file (ROI time courses)
        if parcellation_resolution is not None and parcellation_resolution != "":
            datasource.inputs.roi_ts_file = os.path.join(
                cmp_path_prefix_file,
                f"{self.subject}_atlas-{parcellation_atlas}_res-{parcellation_resolution}_desc-epo_timeseries.npy"
            )
        else:
            datasource.inputs.roi_ts_file = os.path.join(
                cmp_path_prefix_file,
                f"{self.subject}_atlas-{parcellation_atlas}_desc-epo_timeseries.npy"
            )

        datasource.inputs.output_query = dict()

        # Data sinker for output
        sinker = pe.Node(nio.DataSink(), name="eeg_datasinker")
        sinker.inputs.base_directory = os.path.abspath(cmp_deriv_subject_directory)

        # Clear previous outputs
        self.clear_stages_outputs()

        if "Cartool" in self.stages['EEGPreparer'].config.invsol_format:
            # atlas image is required
            parcellation = f'{self.subject}_atlas-{parcellation_atlas}_res-{parcellation_resolution}_dseg.nii.gz'
            datasource.inputs.parcellation = os.path.join(
                self.base_directory, 'derivatives', f'cmp-{__version__}',
                self.subject, 'anat', parcellation
            )
            # fmt: off
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
            # fmt: on
        elif 'mne' in self.stages['EEGPreparer'].config.invsol_format:

            # Freesurfer annot files are required
            if parcellation_resolution == '':
                parcellation = parcellation_atlas  # aparc
            else:
                parcellation = 'lausanne2018.' + parcellation_resolution

            datasource.inputs.parcellation = parcellation

            # Define names for MNE outputs
            datasource.inputs.noise_cov_fname = os.path.join(
                cmp_path_prefix_file, f'{self.subject}_noisecov.fif'
            )

            datasource.inputs.trans_fname = os.path.join(
                cmp_path_prefix_file, f'{self.subject}_trans.fif')

            datasource.inputs.fwd_fname = os.path.join(
                cmp_path_prefix_file, f'{self.subject}_fwd.fif'
            )

            datasource.inputs.inv_fname = os.path.join(
                cmp_path_prefix_file, f'{self.subject}_inv.fif'
            )

            # These two files come from cartool, which is non-standard, needs to be fixed!!
            datasource.inputs.electrode_positions_file = os.path.join(
                eeglab_path_prefix_file, f'{self.subject}_eeg.xyz'
            )

            # fmt: off
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

        cmp_deriv_subject_directory, nipype_deriv_subject_directory, nipype_eeg_pipeline_subject_dir = \
            self.init_subject_derivatives_dirs()

        # Initialization
        log_file = os.path.join(nipype_eeg_pipeline_subject_dir, "pypeline.log")
        if os.path.isfile(log_file):
            os.unlink(log_file)

        config.update_config(
            {
                "logging": {
                    "log_directory": os.path.join(nipype_deriv_subject_directory, "eeg_pipeline"),
                    "log_to_file": True,
                },
                "execution": {
                    "remove_unnecessary_outputs": False,
                    "stop_on_first_crash": True,
                    "stop_on_first_rerun": False,
                    "use_relative_paths": True,
                    "crashfile_format": "txt",
                },
            }
        )
        logging.update_logging(config)

        iflogger = logging.getLogger("nipype.interface")
        iflogger.info("**** Processing ****")

        eeg_flow = self.create_pipeline_flow(
            cmp_deriv_subject_directory=cmp_deriv_subject_directory,
            nipype_deriv_subject_directory=nipype_deriv_subject_directory,
        )
        eeg_flow.write_graph(graph2use="colored", format="svg", simple_form=True)

        # Create dictionary of arguments passed to plugin_args
        plugin_args = {
            'maxtasksperchild': 1,
            'n_procs': self.number_of_cores,
            'raise_insufficient': False,
        }
        eeg_flow.run(plugin="MultiProc", plugin_args=plugin_args)

        iflogger.info("**** Processing finished ****")

        return True
