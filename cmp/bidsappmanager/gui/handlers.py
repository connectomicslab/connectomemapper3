import multiprocessing
import os
import shutil

from bids import BIDSLayout
from pyface.constant import OK
from pyface.file_dialog import FileDialog
from traits.has_traits import HasTraits
from traits.trait_types import Bool, Instance
from traitsui.handler import Handler
from traitsui.message import error

# Own imports
from cmtklib.config import (
    anat_save_config, dmri_save_config, fmri_save_config, eeg_save_config,
    anat_load_config_json, dmri_load_config_json, eeg_load_config_json,
    fmri_load_config_json, convert_config_ini_2_json
)
from cmtklib.process import run
from cmtklib.util import (
    print_warning,
    print_blue
)

import cmp.bidsappmanager.project
from cmp.bidsappmanager.pipelines.anatomical import anatomical as anatomical_pipeline
from cmp.bidsappmanager.pipelines.diffusion import diffusion as diffusion_pipeline
from cmp.bidsappmanager.pipelines.functional import fMRI as fMRI_pipeline
from cmp.bidsappmanager.pipelines.functional import eeg as EEG_pipeline


class ConfigQualityWindowHandler(Handler):
    """Event handler of the Configurator and Inspector (Quality Control) windows.

    Attributes
    ----------
    project_loaded : traits.Bool
        Indicate if project has been successfully loaded
        (Default: False)

    anat_pipeline : Instance(HasTraits)
        Instance of :class:`AnatomicalPipelineUI` class

    anat_inputs_checked : traits.Bool
        Indicate if anatomical pipeline inputs are available
        (Default: False)

    anat_outputs_checked : traits.Bool
        Indicate if anatomical pipeline outputs are available
        (Default: False)

    anatomical_processed : traits.Bool
        Indicate if anatomical pipeline was run
        (Default: False)

    dmri_pipeline : Instance(HasTraits)
        Instance of :class:`DiffusionPipelineUI` class

    dmri_inputs_checked : traits.Bool
        Indicate if diffusion pipeline inputs are available
        (Default: False)

    dmri_processed : traits.Bool
        Indicate if diffusion pipeline was run
        (Default: False)

    fmri_pipeline : Instance(HasTraits)
        Instance of :class:`fMRIPipelineUI` class

    fmri_inputs_checked : traits.Bool
        Indicate if fMRI pipeline inputs are available
        (Default: False)

    fmri_processed : traits.Bool
        Indicate if fMRI pipeline was run
        (Default: False)

    eeg_pipeline : Instance(HasTraits)
        Instance of :class:`EEGPipelineUI` class

    eeg_inputs_checked : traits.Bool
        Indicate if EEG pipeline inputs are available
        (Default: False)

    eeg_processed : traits.Bool
        Indicate if EEG pipeline was run
        (Default: False)
    """

    project_loaded = Bool(False)

    anat_pipeline = Instance(HasTraits)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    anatomical_processed = Bool(False)

    dmri_pipeline = Instance(HasTraits)
    dmri_inputs_checked = Bool(False)
    dmri_processed = Bool(False)

    fmri_pipeline = Instance(HasTraits)
    fmri_inputs_checked = Bool(False)
    fmri_processed = Bool(False)

    eeg_pipeline = Instance(HasTraits)
    eeg_inputs_checked = Bool(False)
    eeg_processed = Bool(False)

    @classmethod
    def save_anat_config_file(self, ui_info):
        """Function that saves the anatomical pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print_blue("[Save anatomical pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_anatomical_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            anat_save_config(
                ui_info.ui.context["object"].anat_pipeline,
                ui_info.ui.context["object"].project_info.anat_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.anat_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.anat_config_file,
                    dialog.path,
                )

    def load_anat_config_file(self, ui_info):
        """Function that loads the anatomical pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*anatomical_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.anat_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.anat_config_file,
                )
            anat_load_config_json(
                self.anat_pipeline,
                ui_info.ui.context["object"].project_info.anat_config_file,
            )
            # TODO: load_config (anat_ or dmri_ ?)

    @classmethod
    def save_dmri_config_file(self, ui_info):
        """Function that saves the diffusion pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print_blue("[Save anatomical pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_diffusion_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            dmri_save_config(
                ui_info.ui.context["object"].dmri_pipeline,
                ui_info.ui.context["object"].project_info.dmri_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.dmri_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.dmri_config_file,
                    dialog.path,
                )

    def load_dmri_config_file(self, ui_info):
        """Function that loads the diffusion pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*diffusion_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.dmri_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.dmri_config_file,
                )
            dmri_load_config_json(
                self.dmri_pipeline,
                ui_info.ui.context["object"].project_info.dmri_config_file,
            )

    @classmethod
    def save_fmri_config_file(self, ui_info):
        """Function that saves the fMRI pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print_blue("[Save anatomical pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_fMRI_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            fmri_save_config(
                ui_info.ui.context["object"].fmri_pipeline,
                ui_info.ui.context["object"].project_info.fmri_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.fmri_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.fmri_config_file,
                    dialog.path,
                )

    def load_fmri_config_file(self, ui_info):
        """Function that loads the fMRI pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*fMRI_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.fmri_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.fmri_config_file,
                )
            fmri_load_config_json(
                self.fmri_pipeline,
                ui_info.ui.context["object"].project_info.fmri_config_file,
            )

    @classmethod
    def save_eeg_config_file(self, ui_info):
        """Function that saves the EEG pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        print_blue("[Save EEG pipeline configuration]")
        dialog = FileDialog(
            action="save as",
            default_filename=os.path.join(
                ui_info.ui.context["object"].project_info.base_directory,
                "code",
                "ref_EEG_config.json",
            ),
        )
        dialog.open()
        if dialog.return_code == OK:
            eeg_save_config(
                ui_info.ui.context["object"].eeg_pipeline,
                ui_info.ui.context["object"].project_info.eeg_config_file,
            )
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.eeg_config_file
            ):
                shutil.copy(
                    ui_info.ui.context["object"].project_info.eeg_config_file,
                    dialog.path,
                )

    def load_eeg_config_file(self, ui_info):
        """Function that loads the EEG pipeline configuration file.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``
        """
        dialog = FileDialog(action="open", wildcard="*EEG_config.json")
        dialog.open()
        if dialog.return_code == OK:
            if (
                dialog.path
                != ui_info.ui.context["object"].project_info.eeg_config_file
            ):
                shutil.copy(
                    dialog.path,
                    ui_info.ui.context["object"].project_info.eeg_config_file,
                )
            eeg_load_config_json(
                self.eeg_pipeline,
                ui_info.ui.context["object"].project_info.eeg_config_file,
            )


class MainWindowHandler(Handler):
    """Event handler of the main window.

    Attributes
    ----------
    project_loaded : traits.Bool
        Indicate if project has been successfully loaded
        (Default: False)

    anat_pipeline : Instance(HasTraits)
        Instance of :class:`AnatomicalPipelineUI` class

    anat_inputs_checked : traits.Bool
        Indicate if anatomical pipeline inputs are available
        (Default: False)

    anat_outputs_checked : traits.Bool
        Indicate if anatomical pipeline outputs are available
        (Default: False)

    anatomical_processed : traits.Bool
        Indicate if anatomical pipeline was run
        (Default: False)

    dmri_pipeline : Instance(HasTraits)
        Instance of :class:`DiffusionPipelineUI` class

    dmri_inputs_checked : traits.Bool
        Indicate if diffusion pipeline inputs are available
        (Default: False)

    dmri_processed : traits.Bool
        Indicate if diffusion pipeline was run
        (Default: False)

    fmri_pipeline : Instance(HasTraits)
        Instance of :class:`fMRIPipelineUI` class

    fmri_inputs_checked : traits.Bool
        Indicate if fMRI pipeline inputs are available
        (Default: False)

    fmri_processed : traits.Bool
        Indicate if fMRI pipeline was run
        (Default: False)

    eeg_pipeline : Instance(HasTraits)
        Instance of :class:`EEGPipelineUI` class

    eeg_inputs_checked : traits.Bool
        Indicate if EEG pipeline inputs are available
        (Default: False)

    eeg_processed : traits.Bool
        Indicate if EEG pipeline was run
        (Default: False)
    """

    project_loaded = Bool(False)

    anat_pipeline = Instance(HasTraits)
    anat_inputs_checked = Bool(False)
    anat_outputs_checked = Bool(False)
    anatomical_processed = Bool(False)

    dmri_pipeline = Instance(HasTraits)
    dmri_inputs_checked = Bool(False)
    dmri_processed = Bool(False)

    fmri_pipeline = Instance(HasTraits)
    fmri_inputs_checked = Bool(False)
    fmri_processed = Bool(False)

    eeg_pipeline = Instance(HasTraits)
    eeg_inputs_checked = Bool(False)
    eeg_processed = Bool(False)

    def load_dataset(self, ui_info, debug=False):
        """Function that creates a new :class:`ProjectInfoUI` instance from an existing project.

        Parameters
        ----------
        ui_info : QtView
            TraitsUI QtView associated with ``self``

        debug : bool
            If True, print more information for debugging
        """
        loaded_project = cmp.bidsappmanager.project.ProjectInfoUI()
        np_res = loaded_project.configure_traits(view="open_view")
        loaded_project.output_directory = os.path.join(
            loaded_project.base_directory, "derivatives"
        )

        if loaded_project.creation_mode == "Install Datalad BIDS dataset":
            datalad_is_available = cmp.bidsappmanager.project.is_tool("datalad")

            if datalad_is_available:
                print(">>> Datalad dataset installation...")
                if loaded_project.install_datalad_dataset_via_ssh:
                    if loaded_project.ssh_pwd != "":
                        os.environ["REMOTEUSERPWD"] = loaded_project.ssh_pwd
                        cmd = 'datalad install -D "Dataset {} (remote:{}) installed on {}" -s ssh://{}:$REMOTEUSERPWD@{}:{} {}'.format(
                            loaded_project.datalad_dataset_path,
                            loaded_project.ssh_remote,
                            loaded_project.base_directory,
                            loaded_project.ssh_user,
                            loaded_project.ssh_remote,
                            loaded_project.datalad_dataset_path,
                            loaded_project.base_directory,
                        )
                    else:
                        cmd = 'datalad install -D "Dataset {} (remote:{}) installed on {}" -s ssh://{}@{}:{} {}'.format(
                            loaded_project.datalad_dataset_path,
                            loaded_project.ssh_remote,
                            loaded_project.base_directory,
                            loaded_project.ssh_user,
                            loaded_project.ssh_remote,
                            loaded_project.datalad_dataset_path,
                            loaded_project.base_directory,
                        )
                    try:
                        print_blue("... cmd: {}".format(cmd))
                        run(
                            cmd,
                            env={},
                            cwd=os.path.abspath(loaded_project.base_directory),
                        )
                        del os.environ["REMOTEUSERPWD"]
                    except Exception:
                        print("    ERROR: Failed to install datalad dataset via ssh")
                        del os.environ["REMOTEUSERPWD"]
                else:
                    cmd = 'datalad install -D "Dataset {} installed on {}" -s {} {}'.format(
                        loaded_project.datalad_dataset_path,
                        loaded_project.base_directory,
                        loaded_project.datalad_dataset_path,
                        loaded_project.base_directory,
                    )
                    try:
                        print_blue("... cmd: {}".format(cmd))
                        run(
                            cmd,
                            env={},
                            cwd=os.path.abspath(loaded_project.base_directory),
                        )
                    except Exception:
                        print("    ERROR: Failed to install datalad dataset via ssh")
            else:
                print("    ERROR: Datalad is not installed!")

            # Install dataset via datalad
            # datalad install -s ssh://user@IP_ADDRESS:/remote/path/to/ds-example /local/path/to/ds-example
            #

        t1_available = False
        t2_available = False
        diffusion_available = False
        fmri_available = False
        eeg_available = False

        # print("Local BIDS dataset: %s" % loaded_project.base_directory)
        if np_res:
            try:
                bids_layout = BIDSLayout(loaded_project.base_directory)
                print(bids_layout)

                loaded_project.bids_layout = bids_layout

                loaded_project.subjects = []
                for subj in bids_layout.get_subjects():
                    if debug:  # pragma: no cover
                        print("sub: %s" % subj)
                    if "sub-" + str(subj) not in loaded_project.subjects:
                        loaded_project.subjects.append("sub-" + str(subj))
                # loaded_project.subjects = ['sub-'+str(subj) for subj in bids_layout.get_subjects()]
                loaded_project.subjects.sort()

                if debug:  # pragma: no cover
                    print("Available subjects : ")
                    print(loaded_project.subjects)
                loaded_project.number_of_subjects = len(loaded_project.subjects)

                loaded_project.subject = loaded_project.subjects[0]
                if debug:  # pragma: no cover
                    print(loaded_project.subject)

                subject = loaded_project.subject.split("-")[1]

                sessions = bids_layout.get(
                    target="session", return_type="id", subject=subject
                )

                if debug:  # pragma: no cover
                    print("Sessions: ")
                    print(sessions)

                if len(sessions) > 0:
                    loaded_project.subject_sessions = ["ses-{}".format(sessions[0])]
                    loaded_project.subject_session = "ses-{}".format(sessions[0])
                else:
                    loaded_project.subject_sessions = [""]
                    loaded_project.subject_session = ""

                if len(sessions) > 0:
                    print(
                        f"    ... Check for available input modalities for subject {subject} of session {sessions[0]}..."
                    )

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="bold",
                            extension=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available BOLD(s): {}".format(query_files))
                        fmri_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="T1w",
                            extension=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T1w(s): {}".format(query_files))
                        t1_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="T2w",
                            extension=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T2w(s): {}".format(query_files))
                        t2_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            suffix="dwi",
                            extension=["nii", "nii.gz"],
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available DWI(s): {}".format(query_files))
                        diffusion_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject,
                            session=sessions[0],
                            datatype="eeg",
                            suffix="eeg",
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available EEG data: {}".format(query_files))
                        eeg_available = True

                else:
                    print(
                        f"    ... Check for available input modalities for subject {subject}..."
                    )
                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="T1w", extension=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T1w(s): {}".format(query_files))
                        t1_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="T2w", extension=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available T2w(s): {}".format(query_files))
                        t2_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="dwi", extension=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available DWI(s): {}".format(query_files))
                        diffusion_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(
                            subject=subject, suffix="bold", extension=["nii", "nii.gz"]
                        )
                    ]
                    if len(query_files) > 0:
                        print("        * Available BOLD(s): {}".format(query_files))
                        fmri_available = True

                    query_files = [
                        f.filename
                        for f in bids_layout.get(subject=subject, datatype="eeg", suffix="eeg")
                    ]
                    if len(query_files) > 0:
                        print("        * Available EEG data: {}".format(query_files))
                        eeg_available = True
            except ValueError as e:
                msg = str(e)
                error(message=msg, title="BIDS error")
                return
            except Exception as e:
                error(
                    message="Invalid BIDS dataset. Please see documentation for more details.\n"
                            f"Exception traceback: {e.__traceback__}",
                    title="BIDS error"
                )
                return

            ui_info.ui.context["object"].project_info = loaded_project

            anat_inputs_checked = False
            if t1_available:
                anat_inputs_checked = True

            dmri_inputs_checked = False
            if t1_available and diffusion_available:
                dmri_inputs_checked = True

            if t2_available and debug:
                print("T2 available")

            fmri_inputs_checked = False
            if t1_available and fmri_available:
                fmri_inputs_checked = True
                if debug:  # pragma: no cover
                    print("fmri input check : {}".format(fmri_inputs_checked))

            eeg_inputs_checked = False
            if t1_available and eeg_available:
                eeg_inputs_checked = True
                if debug:  # pragma: no cover
                    print("eeg input check : {}".format(eeg_inputs_checked))

            self.anat_inputs_checked = anat_inputs_checked
            self.dmri_inputs_checked = dmri_inputs_checked
            self.fmri_inputs_checked = fmri_inputs_checked
            self.eeg_inputs_checked = eeg_inputs_checked

            if anat_inputs_checked:

                self.anat_pipeline = anatomical_pipeline.AnatomicalPipelineUI(
                    loaded_project
                )
                self.anat_pipeline.number_of_cores = loaded_project.number_of_cores

                code_directory = os.path.join(loaded_project.base_directory, "code")

                anat_config_file = os.path.join(
                    code_directory, "ref_anatomical_config.json"
                )

                # Check for old configuration file with INI format
                # when there is no existing json configuration file
                # and convert it to JSON format if so
                if not os.path.isfile(anat_config_file):
                    anat_config_ini_file = os.path.join(
                        code_directory, "ref_anatomical_config.ini"
                    )
                    if os.path.isfile(anat_config_ini_file):
                        anat_config_file = convert_config_ini_2_json(
                            anat_config_ini_file
                        )

                loaded_project.anat_config_file = anat_config_file

                if self.anat_pipeline is not None and not os.path.isfile(
                    anat_config_file
                ):
                    if not os.path.exists(code_directory):
                        try:
                            os.makedirs(code_directory)
                        except os.error:
                            print_warning("%s was already existing" % code_directory)
                        finally:
                            print("Created directory %s" % code_directory)

                    print(">> Create new reference anatomical config file...")
                    anat_save_config(
                        self.anat_pipeline, loaded_project.anat_config_file
                    )
                else:
                    print(">> Load reference anatomical config file...")
                    # if datalad_is_available:
                    #     print('... Datalad get anatomical config file : {}'.format(loaded_project.anat_config_file))
                    #     cmd = 'datalad run -m "Get reference anatomical config file" bash -c "datalad get code/ref_anatomical_config.json"'
                    #     try:
                    #         print('... cmd: {}'.format(cmd))
                    #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                    #     except Exception:
                    #         print("    ERROR: Failed to get file")

                    anat_load_config_json(
                        self.anat_pipeline, loaded_project.anat_config_file
                    )

                self.anat_pipeline.config_file = loaded_project.anat_config_file

                ui_info.ui.context["object"].anat_pipeline = self.anat_pipeline
                loaded_project.t1_available = self.anat_inputs_checked

                loaded_project.parcellation_scheme = self.anat_pipeline.stages[
                    "Parcellation"
                ].config.parcellation_scheme
                loaded_project.freesurfer_subjects_dir = self.anat_pipeline.stages[
                    "Segmentation"
                ].config.freesurfer_subjects_dir
                loaded_project.freesurfer_subject_id = self.anat_pipeline.stages[
                    "Segmentation"
                ].config.freesurfer_subject_id

                ui_info.ui.context["object"].project_info = loaded_project

                self.project_loaded = True

                if dmri_inputs_checked:
                    self.dmri_pipeline = diffusion_pipeline.DiffusionPipelineUI(
                        loaded_project
                    )
                    self.dmri_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.dmri_pipeline.parcellation_scheme = ui_info.ui.context[
                        "object"
                    ].project_info.parcellation_scheme

                    code_directory = os.path.join(loaded_project.base_directory, "code")
                    dmri_config_file = os.path.join(
                        code_directory, "ref_diffusion_config.json"
                    )

                    # Check for old configuration file with INI format
                    # when there is no existing json configuration file
                    # and convert it to JSON format if so
                    if not os.path.isfile(dmri_config_file):
                        dmri_config_ini_file = os.path.join(
                            code_directory, "ref_diffusion_config.ini"
                        )
                        if os.path.isfile(dmri_config_ini_file):
                            dmri_config_file = convert_config_ini_2_json(
                                dmri_config_ini_file
                            )

                    loaded_project.dmri_config_file = dmri_config_file
                    self.dmri_pipeline.config_file = dmri_config_file

                    if (
                        not os.path.isfile(dmri_config_file)
                        and self.dmri_pipeline is not None
                    ):

                        # Look for diffusion acquisition model information from filename (acq-*)
                        if loaded_project.subject_session != "":
                            session = loaded_project.subject_session.split("-")[1]
                            diffusion_imaging_models = [
                                i
                                for i in bids_layout.get(
                                    subject=subject,
                                    session=session,
                                    suffix="dwi",
                                    target="acquisition",
                                    return_type="id",
                                    extension=["nii", "nii.gz"],
                                )
                            ]
                            if debug:  # pragma: no cover
                                print(
                                    "DIFFUSION IMAGING MODELS : {}".format(
                                        diffusion_imaging_models
                                    )
                                )

                            if len(diffusion_imaging_models) > 0:
                                if len(diffusion_imaging_models) > 1:
                                    loaded_project.dmri_bids_acqs = (
                                        diffusion_imaging_models
                                    )
                                    loaded_project.configure_traits(
                                        view="dmri_bids_acq_view"
                                    )
                                else:
                                    loaded_project.dmri_bids_acqs = [
                                        "{}".format(diffusion_imaging_models[0])
                                    ]
                                    loaded_project.dmri_bids_acq = (
                                        diffusion_imaging_models[0]
                                    )

                                if ("dsi" in loaded_project.dmri_bids_acq) or (
                                    "DSI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DSI"
                                elif ("dti" in loaded_project.dmri_bids_acq) or (
                                    "DTI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DTI"
                                elif ("hardi" in loaded_project.dmri_bids_acq) or (
                                    "HARDI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "HARDI"
                                elif ("multishell" in loaded_project.dmri_bids_acq) or (
                                    "MULTISHELL" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = (
                                        "multishell"
                                    )
                                else:
                                    loaded_project.diffusion_imaging_model = "DTI"
                            else:
                                loaded_project.dmri_bids_acqs = [""]
                                loaded_project.dmri_bids_acq = ""
                                loaded_project.configure_traits(
                                    view="diffusion_imaging_model_select_view"
                                )

                            files = [
                                f.filename
                                for f in bids_layout.get(
                                    subject=subject,
                                    session=session,
                                    suffix="dwi",
                                    extension=["nii", "nii.gz"],
                                )
                            ]

                            if debug:  # pragma: no cover
                                print("****************************************")
                                print(files)
                                print("****************************************")

                            if loaded_project.dmri_bids_acq != "":
                                for file in files:
                                    if loaded_project.dmri_bids_acq in file:
                                        dwi_file = file
                                        if debug:  # pragma: no cover
                                            print(
                                                "Loaded DWI file: {}".format(dwi_file)
                                            )
                                        break
                            else:
                                dwi_file = files[0]
                        else:
                            diffusion_imaging_models = [
                                i
                                for i in bids_layout.get(
                                    subject=subject,
                                    suffix="dwi",
                                    target="acquisition",
                                    return_type="id",
                                    extension=["nii", "nii.gz"],
                                )
                            ]

                            if len(diffusion_imaging_models) > 0:
                                if len(diffusion_imaging_models) > 1:
                                    loaded_project.dmri_bids_acqs = (
                                        diffusion_imaging_models
                                    )
                                    loaded_project.configure_traits(
                                        view="dmri_bids_acq_view"
                                    )
                                else:
                                    loaded_project.dmri_bids_acq = (
                                        diffusion_imaging_models[0]
                                    )

                                if ("dsi" in loaded_project.dmri_bids_acq) or (
                                    "DSI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DSI"
                                elif ("dti" in loaded_project.dmri_bids_acq) or (
                                    "DTI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "DTI"
                                elif ("hardi" in loaded_project.dmri_bids_acq) or (
                                    "HARDI" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = "HARDI"
                                elif ("multishell" in loaded_project.dmri_bids_acq) or (
                                    "MULTISHELL" in loaded_project.dmri_bids_acq
                                ):
                                    loaded_project.diffusion_imaging_model = (
                                        "multishell"
                                    )
                                else:
                                    loaded_project.diffusion_imaging_model = "DTI"
                            else:
                                loaded_project.dmri_bids_acqs = [""]
                                loaded_project.dmri_bids_acq = ""
                                loaded_project.configure_traits(
                                    view="diffusion_imaging_model_select_view"
                                )

                        self.dmri_pipeline.diffusion_imaging_model = (
                            loaded_project.diffusion_imaging_model
                        )
                        self.dmri_pipeline.global_conf.diffusion_imaging_model = (
                            loaded_project.diffusion_imaging_model
                        )
                        self.dmri_pipeline.global_conf.dmri_bids_acq = (
                            loaded_project.dmri_bids_acq
                        )
                        self.dmri_pipeline.stages[
                            "Diffusion"
                        ].diffusion_imaging_model = (
                            loaded_project.diffusion_imaging_model
                        )
                        print(">> Create new reference diffusion config file...")
                        dmri_save_config(self.dmri_pipeline, dmri_config_file)
                    else:
                        print(">> Load reference diffusion config file...")

                        # if datalad_is_available:
                        #     print('... Datalad get reference diffusion config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference anatomical config file" bash -c "datalad get code/ref_diffusion_config.json"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        dmri_load_config_json(
                            self.dmri_pipeline, loaded_project.dmri_config_file
                        )
                        # TODO: check if diffusion imaging model (DSI/DTI/HARDI/multishell) is correct/valid.

                    ui_info.ui.context["object"].dmri_pipeline = self.dmri_pipeline
                    loaded_project.dmri_available = self.dmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True

                if fmri_inputs_checked:
                    self.fmri_pipeline = fMRI_pipeline.fMRIPipelineUI(loaded_project)
                    self.fmri_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.fmri_pipeline.parcellation_scheme = ui_info.ui.context[
                        "object"
                    ].project_info.parcellation_scheme

                    self.fmri_pipeline.stages["Registration"].pipeline_mode = "fMRI"
                    self.fmri_pipeline.stages[
                        "Registration"
                    ].registration_mode = "FSL (Linear)"
                    self.fmri_pipeline.stages[
                        "Registration"
                    ].registration_mode_trait = ["FSL (Linear)", "BBregister (FS)"]

                    code_directory = os.path.join(loaded_project.base_directory, "code")
                    fmri_config_file = os.path.join(
                        code_directory, "ref_fMRI_config.json"
                    )

                    # Check for old configuration file with INI format
                    # when there is no existing json configuration file
                    # and convert it to JSON format if so
                    if not os.path.isfile(fmri_config_file):
                        fmri_config_ini_file = os.path.join(
                            code_directory, "ref_fMRI_config.ini"
                        )
                        if os.path.isfile(fmri_config_ini_file):
                            fmri_config_file = convert_config_ini_2_json(
                                fmri_config_ini_file
                            )

                    loaded_project.fmri_config_file = fmri_config_file
                    self.fmri_pipeline.config_file = fmri_config_file

                    if (
                        not os.path.isfile(fmri_config_file)
                        and self.fmri_pipeline is not None
                    ):
                        print(">> Create new reference fMRI config file...")
                        fmri_save_config(self.fmri_pipeline, fmri_config_file)
                    else:
                        print(">> Load reference fMRI config file...")

                        # if datalad_is_available:
                        #     print('... Datalad get reference fMRI config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference fMRI config file" bash -c "datalad get code/ref_fMRI_config.json"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        fmri_load_config_json(
                            self.fmri_pipeline, loaded_project.fmri_config_file
                        )

                    ui_info.ui.context["object"].fmri_pipeline = self.fmri_pipeline
                    loaded_project.fmri_available = self.fmri_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True

                if eeg_inputs_checked:
                    self.eeg_pipeline = EEG_pipeline.EEGPipelineUI(loaded_project)
                    self.eeg_pipeline.number_of_cores = loaded_project.number_of_cores
                    self.eeg_pipeline.parcellation_scheme = \
                        ui_info.ui.context["object"].project_info.parcellation_scheme
                    code_directory = os.path.join(loaded_project.base_directory, "code")
                    eeg_config_file = os.path.join(
                        code_directory, "ref_EEG_config.json"
                    )

                    loaded_project.eeg_config_file = eeg_config_file
                    self.eeg_pipeline.config_file = eeg_config_file

                    if (
                        not os.path.isfile(eeg_config_file)
                        and self.eeg_pipeline is not None
                    ):
                        print(">> Create new reference EEG config file...")
                        eeg_save_config(self.eeg_pipeline, eeg_config_file)
                    else:
                        print(">> Load reference EEG config file...")

                        # if datalad_is_available:
                        #     print('... Datalad get reference fMRI config file : {}'.format(loaded_project.anat_config_file))
                        #     cmd = 'datalad run -m "Get reference fMRI config file" bash -c "datalad get code/ref_fMRI_config.json"'
                        #     try:
                        #         print('... cmd: {}'.format(cmd))
                        #         core.run( cmd, env={}, cwd=os.path.abspath(loaded_project.base_directory))
                        #     except Exception:
                        #         print("    ERROR: Failed to get file")

                        eeg_load_config_json(
                            self.eeg_pipeline, loaded_project.eeg_config_file
                        )

                    ui_info.ui.context["object"].eeg_pipeline = self.eeg_pipeline
                    loaded_project.eeg_available = self.eeg_inputs_checked

                    ui_info.ui.context["object"].project_info = loaded_project

                    self.project_loaded = True
