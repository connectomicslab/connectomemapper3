# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""EEG pipeline Class definition."""

# General imports
import copy
import json
import os
import datetime
from traits.api import (
    HasTraits, Instance, Str, List,
    Directory, Enum
)

import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe
from nipype import config, logging

# Own imports
from cmp.pipelines.common import Pipeline
from cmp.stages.eeg.esi import EEGSourceImagingStage
from cmp.stages.eeg.preprocessing import EEGPreprocessingStage
from cmp.stages.connectome.eeg_connectome import EEGConnectomeStage
from cmtklib.bids.io import (
    __cmp_directory__,
    __nipype_directory__,
    CustomParcellationBIDSFile
)
from cmtklib.util import find_toolbox_derivatives_containing_file


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
        * the EEG preprocessing stage that loads the input preprocessed EGG Epochs files and convert them to the MNE fif format.

        * the EEG source imaging stage that takes care of all the steps necessary to extract the ROI time courses.

        * the EEG connectome stage that computes different frequency- and time-frequency-domain connectivity measures from the extracted ROI time courses.

    See Also
    --------
    cmp.stages.eeg.preprocessing.EEGPreprocessingStage
    cmp.stages.eeg.esi.EEGSourceImagingStage
    cmp.stages.connectome.eeg_connectome.EEGConnectomeStage
    """

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("eeg_pipeline")
    input_folders = ["anat", "eeg"]
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ["EEGPreparer", "EEGLoader", "InverseSolution"]

    parcellation_scheme = Enum("Lausanne2018", "NativeFreesurfer")

    global_conf = GlobalConfig()
    config_file = Str

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
            "EEGPreprocessing": EEGPreprocessingStage(
                subject=self.subject,
                session=self.global_conf.subject_session,
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory
            ),
            "EEGSourceImaging": EEGSourceImagingStage(
                subject=self.subject,
                session=self.global_conf.subject_session,
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory
            ),
            "EEGConnectome": EEGConnectomeStage(
                subject=self.subject,
                session=self.global_conf.subject_session,
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory
            ),
        }

        self.parcellation_scheme = project_info.parcellation_scheme
        self.parcellation_cmp_dir = self.stages["EEGSourceImaging"].config.parcellation_cmp_dir

        self.stages["EEGSourceImaging"].config.parcellation_scheme = self.parcellation_scheme
        self.stages["EEGSourceImaging"].config.task_label = self.stages["EEGPreprocessing"].config.task_label

        self.stages["EEGPreprocessing"].config.on_trait_change(self._update_task_label, 'task_label')

        self.stages["EEGSourceImaging"].config.on_trait_change(self._update_parcellation_scheme, 'parcellation_scheme')
        self.stages["EEGSourceImaging"].config.on_trait_change(self._update_lausanne2018_parcellation_res, 'lausanne2018_parcellation_res')
        self.stages["EEGSourceImaging"].config.on_trait_change(self._update_parcellation_cmp_dir, 'parcellation_cmp_dir')

        Pipeline.__init__(self, project_info)

    def _update_parcellation_scheme(self):
        self.parcellation_scheme = self.stages["EEGSourceImaging"].config.parcellation_scheme
        self.stages["EEGConnectome"].config.parcellation_scheme =\
            self.stages["EEGSourceImaging"].config.parcellation_scheme

    def _update_lausanne2018_parcellation_res(self):
        self.stages["EEGConnectome"].config.lausanne2018_parcellation_res =\
            self.stages["EEGSourceImaging"].config.lausanne2018_parcellation_res

    def _update_parcellation_cmp_dir(self):
        self.parcellation_cmp_dir = self.stages["EEGSourceImaging"].config.parcellation_cmp_dir

    def _update_task_label(self):
        self.stages["EEGSourceImaging"].config.task_label = self.stages["EEGPreprocessing"].config.task_label
        self.stages["EEGConnectome"].config.task_label = self.stages["EEGPreprocessing"].config.task_label

    def check_config(self):
        # TODO: To Be Implemented if Necessary
        raise NotImplementedError

    def check_input(self):
        """Check if input of the eeg pipeline are available (Not available yet).

        Returns
        -------
        valid_inputs : bool
            True if inputs are available
        """
        print("**** Check Inputs ****")
        valid_inputs = True
        print(f'Base dir: {self.get_nipype_eeg_pipeline_subject_dir()}')
        datasource = self.create_datagrabber_node(
            name="eeg_check_input",
            base_directory=self.get_nipype_eeg_pipeline_subject_dir()
        )
        res = datasource.run()
        outputs: dict = res.outputs.__dict__
        for key in outputs.keys():
            if not outputs[key]:
                valid_inputs = False
                print(
                    f'\t.. ERROR - Input file for "{key}" key not found (subject: {self.subject})'
                    f'\t\t* Corresponding output query: {res.inputs["output_query"][key]}\n'
                )
            else:
                print(f'\t.. Input file for "{key}" key: {outputs[key]}')
        return valid_inputs

    # TODO: To Be Implemented if Necessary
    # def check_output(self):
    #     raise NotImplementedError

    def create_datagrabber_node(self, name="eeg_datasource", base_directory=None, debug=False):
        """Create the appropriate Nipype BIDSDataGrabber node depending on the configuration of the different EEG pipeline stages.

        Parameters
        ----------
        name: str
            Name of the datagrabber node

        base_directory: str
            Path to the directory that store the check_input node output

        debug: bool
            Print extra debugging messages if `True`

        Returns
        -------
        datasource : Output Nipype BIDSDataGrabber Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.BIDSDataGrabber` interface
        """
        # Initialize dictionary query to be passed to the BIDSDataGrabber
        # for the different input files
        output_query = dict()

        # Extract configuration stage parameters to set the BIDSDataGrabber
        # to get the different input derivatives file

        # EEG inputs of the preprocessing stage
        input_files = [
            self.stages["EEGPreprocessing"].config.eeg_ts_file,
            self.stages["EEGPreprocessing"].config.events_file,
        ]
        output_query.update(
            {
                "eeg_ts_file": self.stages["EEGPreprocessing"].config.eeg_ts_file.get_query_dict(),
                "events_file": self.stages["EEGPreprocessing"].config.events_file.get_query_dict()
            }
        )

        if self.stages["EEGPreprocessing"].config.electrodes_file_fmt == "Cartool":
            if debug:  # pragma: no cover
                print('\t.. DEBUG: Use electrode file generated by Cartool '
                      f'\t\t\t* output_query: {self.stages["EEGPreprocessing"].config.cartool_electrodes_file.get_query_dict()}')
            input_files.append(self.stages["EEGPreprocessing"].config.cartool_electrodes_file)
            output_query.update(
                {"electrodes_file": self.stages["EEGPreprocessing"].config.cartool_electrodes_file.get_query_dict()}
            )
        else:  # BIDS _electrodes.tsv file
            if debug:  # pragma: no cover
                print('\t.. DEBUG: Use standard BIDS TSV electrode file.')
            input_files.append(self.stages["EEGPreprocessing"].config.bids_electrodes_file)
            output_query.update(
                {"electrodes_file": self.stages["EEGPreprocessing"].config.bids_electrodes_file.get_query_dict()}
            )

        if self.stages["EEGSourceImaging"].config.esi_tool == "MNE":
            if debug:  # pragma: no cover
                print('\t.. DEBUG: Perform ESI with MNE.')
            if self.stages["EEGSourceImaging"].config.mne_apply_electrode_transform:
                if debug:  # pragma: no cover
                    print('\t.. DEBUG: Apply electrode transform.')
                input_files.append(self.stages["EEGSourceImaging"].config.mne_electrode_transform_file)
                output_query.update(
                    {"trans_file": self.stages["EEGSourceImaging"].config.mne_electrode_transform_file.get_query_dict()}
                )
        else:  # ESI outputs precomputed with Cartool
            if debug:  # pragma: no cover
                print('\t.. DEBUG: Use ESI files precomputed with Cartool.')
            input_files.append(self.stages["EEGSourceImaging"].config.cartool_spi_file)
            input_files.append(self.stages["EEGSourceImaging"].config.cartool_invsol_file)
            output_query.update(
                {
                    "spi_file": self.stages["EEGSourceImaging"].config.cartool_spi_file.get_query_dict(),
                    "invsol_file": self.stages["EEGSourceImaging"].config.cartool_invsol_file.get_query_dict()
                }
            )

        # Parcellation input to ESI stage
        roi_volume_file = CustomParcellationBIDSFile()
        if self.parcellation_scheme == "Lausanne2018":
            roi_volume_file.atlas = "L2018"
            roi_volume_file.res = self.stages["EEGSourceImaging"].config.lausanne2018_parcellation_res
            roi_volume_file.get_filename(
                subject=self.global_conf.subject,
                session=self.global_conf.subject_session
            )
        else:  # Native freesurfer
            roi_volume_file.atlas = "Desikan"
            roi_volume_file.res = ""

        if base_directory is not None:  # self.parcellation_cmp_dir has not been updated yet
            roi_volume_file.toolbox_derivatives_dir = find_toolbox_derivatives_containing_file(
                bids_dir=self.base_directory,
                fname=roi_volume_file.get_filename(
                    subject=self.global_conf.subject,
                    session=self.global_conf.subject_session
                )
            )
        else:
            roi_volume_file.toolbox_derivatives_dir = self.parcellation_cmp_dir
        input_files.append(roi_volume_file)
        output_query.update(
            {"roi_volume_file": roi_volume_file.get_query_dict()}
        )
        if debug:  # pragma: no cover
            print(f'\t.. DEBUG: Use parcellation {roi_volume_file}.')

        # Handle parcellation tsv file
        roi_volume_tsv_file = copy.deepcopy(roi_volume_file)
        roi_volume_tsv_file.extension = "tsv"

        input_files.append(roi_volume_tsv_file)
        output_query.update(
            {"roi_volume_tsv_file": roi_volume_tsv_file.get_query_dict()}
        )
        if debug:  # pragma: no cover
            print(f'\t.. DEBUG: Use parcellation index/label mapping {roi_volume_tsv_file}.')

        output_query_json = json.loads(json.dumps(output_query))

        # Create a list of unique toolbox derivatives directories
        # where input files should be queried by the BIDSDataGrabber
        extra_derivatives = []
        for bids_file in input_files:
            toolbox_derivatives_dir = os.path.join(
                self.base_directory, "derivatives", bids_file.get_toolbox_derivatives_dir()
            )
            if (toolbox_derivatives_dir not in extra_derivatives and
                    bids_file.get_toolbox_derivatives_dir() != ''):

                extra_derivatives.append(toolbox_derivatives_dir)

        # Ensure all derivatives folder are available at initialization of a new peoject
        for tool_dir in os.listdir(os.path.join(self.base_directory, "derivatives")):
            if ('cartool' in tool_dir and
                    os.path.join(self.base_directory, "derivatives", tool_dir) not in extra_derivatives):
                extra_derivatives.append(os.path.join(self.base_directory, "derivatives", tool_dir))
            if ('eeglab' in tool_dir and
                    os.path.join(self.base_directory, "derivatives", tool_dir) not in extra_derivatives):
                extra_derivatives.append(os.path.join(self.base_directory, "derivatives", tool_dir))

        if debug:  # pragma: no cover
            print('\t.. DEBUG: BIDSDataGrabber info\n'
                  f'\t\t* Input toolbox derivatives: {extra_derivatives}\n'
                  f'\t\t* Output query: {output_query_json}\n')

        datasource = pe.Node(
            nio.BIDSDataGrabber(
                index_derivatives=False,
                extra_derivatives=extra_derivatives
            ),
            base_dir=base_directory,
            name=name
        )
        datasource.inputs.base_dir = self.base_directory
        datasource.inputs.subject = self.subject.split("-")[1]
        if (self.global_conf.subject_session != "" and
                self.global_conf.subject_session is not None):
            datasource.inputs.session = self.global_conf.subject_session.split("-")[1]

        datasource.inputs.output_query = output_query_json

        return datasource

    def create_datasinker_node(self, output_directory):
        """Create the appropriate Nipype DataSink node depending on EEG `task_label` and `parcellation_scheme`

        Parameters
        ----------
        output_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        Returns
        -------
        sinker : Output Nipype DataSink Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.DataSink` interface
        """
        sinker = pe.Node(nio.DataSink(), name="eeg_datasinker")
        sinker.inputs.base_directory = output_directory

        bids_task_label = self.stages["EEGPreprocessing"].config.task_label
        if self.parcellation_scheme == "NativeFreesurfer":
            bids_atlas_label = 'Desikan'
        else:
            bids_atlas_label = 'L2018'

        # fmt:off
        substitutions = [
            ("bem.fif", f"{self.subject}_task-{bids_task_label}_bem.fif"),
            ("epo.fif", f"{self.subject}_task-{bids_task_label}_epo.fif"),
            ("src.fif", f"{self.subject}_task-{bids_task_label}_src.fif"),
            ("fwd.fif", f"{self.subject}_task-{bids_task_label}_fwd.fif"),
            ("inv.fif", f"{self.subject}_task-{bids_task_label}_inv.fif"),
            ("noisecov.fif", f"{self.subject}_task-{bids_task_label}_noisecov.fif"),
        ]
        # fmt:on

        if self.parcellation_scheme == "NativeFreesurfer":
            # fmt:off
            substitutions += [
                (
                    "timeseries",
                    f"{self.subject}_task-{bids_task_label}_atlas-{bids_atlas_label}_timeseries"
                ),
                (
                    "conndata-network_connectivity",
                    f"{self.subject}_task-{bids_task_label}_atlas-{bids_atlas_label}_conndata-network_connectivity"
                ),
            ]
            # fmt:on
        else:  # Lausanne2018
            scale = self.stages["EEGSourceImaging"].config.lausanne2018_parcellation_res
            # fmt:off
            substitutions += [
                (
                    "timeseries",
                    f"{self.subject}_task-{bids_task_label}_atlas-{bids_atlas_label}_res-{scale}_timeseries"
                ),
                (
                    "conndata-network_connectivity",
                    f"{self.subject}_task-{bids_task_label}_atlas-{bids_atlas_label}_res-{scale}_conndata-network_connectivity"
                ),
            ]
            # fmt:on

        sinker.inputs.substitutions = substitutions

        return sinker

    def get_nipype_eeg_pipeline_subject_dir(self):
        """Return the path to Nipype eeg_pipeline folder of a given subject / session."""
        if "_" in self.subject:
            subject = self.subject.split("_")[0]

        if self.global_conf.subject_session == "":
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, __nipype_directory__,
                self.subject
            )
        else:
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, __nipype_directory__,
                subject, self.global_conf.subject_session,
            )

        nipype_eeg_pipeline_subject_dir = os.path.join(nipype_deriv_subject_directory, "eeg_pipeline")

        return nipype_eeg_pipeline_subject_dir

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
        datasource = self.create_datagrabber_node()

        # Create common_flow
        eeg_flow = pe.Workflow(
            name="eeg_pipeline",
            base_dir=os.path.abspath(nipype_deriv_subject_directory)
        )

        # Create stages
        preproc_flow = self.create_stage_flow("EEGPreprocessing")
        esi_flow = self.create_stage_flow("EEGSourceImaging")
        cmat_flow = self.create_stage_flow("EEGConnectome")

        # Data sinker for output
        sinker = self.create_datasinker_node(
            output_directory=os.path.abspath(cmp_deriv_subject_directory)
        )

        # Clear previous outputs
        self.clear_stages_outputs()

        # BIDSDataGrabber node "datasource" is returning a
        # list of file but the interfaces take only a file as input.
        # This function allow to extract only one file to connect
        # as input in the rest of the workflow.
        def extract_first_file_from_list(files):
            if len(files) > 1:
                print('\t.. WARNING: Multiple files detected by BIDSDataGrabber')
                print(f'\t\t\t* Extracting {sorted(files)[0]}')
                files = sorted(files)
            return files[0]

        # Create the flow
        # fmt: off
        eeg_flow.connect(
            [
                (datasource, preproc_flow, [(('eeg_ts_file', extract_first_file_from_list),  'inputnode.eeg_ts_file'),
                                            (('events_file', extract_first_file_from_list),  'inputnode.events_file'),
                                            (('electrodes_file', extract_first_file_from_list),  'inputnode.electrodes_file')]),
            ]
        )
        # fmt: on

        def extract_parcellation_native_space(roi_volume_files):
            """Utility function that returns the parcellation file in native T1w space.

            If diffusion pipeline is before, the BIDSDataGrabber also returns
            the co-registered parcellation in the DWI space, which needs
            to be filtered out.

            Parameters
            ----------
            roi_volume_files: list
                List of the parcellation files returned by the
                :obj:`~nipype.interfaces.io.BIDSDataGrabber`

            Returns
            -------
            roi_volume_file: str
                Path to single parcellation file in native T1w space
            """
            for roi_volume_file in roi_volume_files:
                if 'space-DWI' not in roi_volume_file:
                    return roi_volume_file

        if self.stages["EEGSourceImaging"].config.esi_tool == "Cartool":
            # fmt: off
            eeg_flow.connect(
                [
                    (datasource, esi_flow, [(('spi_file', extract_first_file_from_list), 'inputnode.spi_file'),
                                            (('invsol_file', extract_first_file_from_list),  'inputnode.invsol_file'),
                                            (('roi_volume_file', extract_parcellation_native_space), 'inputnode.roi_volume_file')]),
                    (preproc_flow, esi_flow, [('outputnode.epochs_file', 'inputnode.epochs_file')]),
                    (esi_flow, sinker, [("outputnode.mapping_spi_rois_file", "eeg.@mapping_spi_rois_file")])
                ]
            )
            # fmt: on
        else:  # MNE workflow
            # fmt: off
            eeg_flow.connect(
                [
                    (preproc_flow, esi_flow, [("outputnode.epochs_file", "inputnode.epochs_file")]),
                ]
            )
            # fmt: on
            if self.stages["EEGSourceImaging"].config.mne_apply_electrode_transform:
                # fmt: off
                eeg_flow.connect(
                    [
                        (datasource, esi_flow, [(("trans_file", extract_first_file_from_list),  "inputnode.trans_file")])
                    ]
                )
                # fmt: on
            # fmt: off
            eeg_flow.connect(
                [
                    (esi_flow, sinker, [("outputnode.bem_file", "eeg.@bem_file")]),
                    (esi_flow, sinker, [("outputnode.noise_cov_file", "eeg.@noise_cov_file")]),
                    (esi_flow, sinker, [("outputnode.src_file", "eeg.@src_file")]),
                    (esi_flow, sinker, [("outputnode.fwd_file", "eeg.@fwd_file")]),
                    (esi_flow, sinker, [("outputnode.inv_file", "eeg.@inv_file")]),
                ]
            )
            # fmt: on
        # fmt: off
        eeg_flow.connect(
            [
                (datasource, cmat_flow, [(("roi_volume_tsv_file", extract_first_file_from_list), "inputnode.roi_volume_tsv_file")]),
                (esi_flow, cmat_flow, [("outputnode.roi_ts_npy_file", "inputnode.roi_ts_file")]),
                (preproc_flow, cmat_flow, [("outputnode.epochs_file", "inputnode.epochs_file")]),
                (esi_flow, sinker, [("outputnode.roi_ts_npy_file", "eeg.@roi_ts_npy_file"),
                                    ("outputnode.roi_ts_mat_file", "eeg.@roi_ts_mat_file")]),
                (preproc_flow, sinker, [("outputnode.epochs_file", "eeg.@epochs_file")]),
                (cmat_flow, sinker, [("outputnode.connectivity_matrices", "eeg.@connectivity_matrices")]),
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
