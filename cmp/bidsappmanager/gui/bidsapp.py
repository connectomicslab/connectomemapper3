# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper BIDS App Interface Window."""

# General imports
import os
import sys

import pkg_resources
from subprocess import Popen
import subprocess
import multiprocessing
import shutil
import time
import glob

from pyface.api import ImageResource
from traitsui.qt4.extra.qt_view import QtView
from traitsui.api import *
from traits.api import *

from bids import BIDSLayout

# Own imports
import cmp.project
from cmp.info import __version__

from cmtklib.bids.io import (
    __cmp_directory__, __freesurfer_directory__
)
from cmtklib.util import (
    return_button_style_sheet,
    BColors,
    print_blue,
    print_warning,
    print_error,
)

import cmp.bidsappmanager.gui.handlers
import cmp.bidsappmanager.project as project
from cmp.bidsappmanager.gui.traits import MultiSelectAdapter
from cmp.bidsappmanager.gui.globals import get_icon

# Remove warnings visible whenever you import scipy (or another package)
# that was compiled against an older numpy than is installed.
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


class BIDSAppInterfaceWindow(HasTraits):
    """Class that defines the Window of the BIDS App Interface.

    Attributes
    ----------
    project_info : ProjectInfo
        Instance of :class:`CMP_Project_Info` that represents the processing project

    bids_root : traits.Directory
        BIDS root dataset directory

    output_dir : traits.Directory
        Output directory

    subjects : traits.List
        List of subjects (in the form ``sub-XX``) present in the dataset

    number_of_participants_processed_in_parallel : traits.Range
        Number of participants / subjects to be processed in parallel that
        takes values in the [1, # of CPUs - 1] range

    number_threads_max : traits.Int
        Maximal number of threads to be used by OpenMP programs
        (4 by default)

    number_of_threads : traits.Range
        Number of threads to be used by OpenMP programs that takes values
        in the [1, ``number_threads_max``] range

    fs_file : traits.File
        Path to Freesurfer license file

    list_of_subjects_to_be_processed : List(Str)
        Selection of subjects to be processed from the ``subjects`` list

    dmri_inputs_checked : traits.Bool
        True if dMRI data is available in the dataset

    fmri_inputs_checked : traits.Bool
        rue if fMRI data is available in the dataset

    anat_config : traits.File
        Configuration file for the anatomical MRI pipeline

    dmri_config : traits.File
        Configuration file for the diffusion MRI pipeline

    fmri_config : traits.File
        Configuration file for the functional MRI pipeline

    run_anat_pipeline : traits.Bool
        If True, run the anatomical pipeline

    run_dmri_pipeline : traits.Bool
        If True, run the diffusion pipeline

    run_fmri_pipeline : traits.Bool
        If True, run the functional pipeline

    bidsapp_tag : traits.Enum
        Selection of BIDS App version to use

    data_provenance_tracking : traits.Bool
        If set and if ``datalad_is_available`` is True run the BIDS App
        using datalad (False by default)

    datalad_update_environment : traits.Bool
        If True and ``data_provenance_tracking`` is True, tell to datalad
        to update the BIDS App container image if there was a previous
        execution (True by default)

    datalad_is_available : traits.Bool
        Boolean used to store if datalad is available in the computing
        environment (False by default)

    check : traits.ui.Button
        Button to check if all parameters are properly set for execution
        of the BIDS App

    start_bidsapp : traits.ui.Button
        Button to run the BIDS App

    traits_view : QtView
        TraitsUI QtView that describes the content of the window
    """
    project_info = Instance(cmp.project.ProjectInfo)

    bids_root = Directory()
    output_dir = Directory()
    subjects = List(Str)

    # multiproc_number_of_cores = Int(1)
    number_of_participants_processed_in_parallel = Range(
        low=1,
        high=multiprocessing.cpu_count() - 1,
        desc="Number of participants to be processed in parallel",
    )

    number_of_threads_max = Int(multiprocessing.cpu_count() - 1)

    number_of_threads = Range(
        low=1,
        high="number_of_threads_max",
        mode="spinner",
        desc="Number of OpenMP threads used by Dipy, FSL, MRtrix, "
             "and Freesurfer recon-all",
    )

    fix_ants_random_seed = Bool(
        False, desc="Fix MRtrix3 random generator seed for tractography"
    )
    ants_random_seed = Int(1234, desc="MRtrix random generator seed value")

    fix_mrtrix_random_seed = Bool(
        False, desc="Fix ANTs random generator seed for registration"
    )
    mrtrix_random_seed = Int(1234, desc="ANTs random generator seed value")

    fix_ants_number_of_threads = Bool(
        False, desc="Fix independently number of threads used by ANTs registration"
    )
    ants_number_of_threads = Range(
        low=1,
        high="number_of_threads_max",
        mode="spinner",
        desc="Number of ITK threads used by ANTs registration",
    )

    fs_license = File(desc="Path to your FREESURFER license.txt")
    # fs_average = Directory(os.path.join(os.environ['FREESURFER_HOME'],'subjects','fsaverage'))

    list_of_subjects_to_be_processed = List(Str)

    list_of_processing_logfiles = List(File)

    anat_config = File(desc="Path to the configuration file of the anatomical pipeline")
    dmri_config = File(desc="Path to the configuration file of the diffusion pipeline")
    fmri_config = File(desc="Path to the configuration file of the fMRI pipeline")

    run_anat_pipeline = Bool(True, desc="Run the anatomical pipeline")
    run_dmri_pipeline = Bool(False, desc="Run the diffusion pipeline")
    run_fmri_pipeline = Bool(False, desc="Run the fMRI pipeline")

    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    settings_checked = Bool(False)
    docker_running = Bool(False)

    bidsapp_tag = Enum("{}".format(__version__), ["latest", "{}".format(__version__)])

    data_provenance_tracking = Bool(
        False, desc="Use datalad to execute CMP3 and record dataset changes"
    )

    datalad_update_environment = Bool(
        True,
        desc="Update the container if datalad run-container has been run already once",
    )

    datalad_is_available = Bool(False, desc="True if datalad is available")

    update_selection = Button()
    check = Button()
    start_bidsapp = Button()

    # stop_bidsapp = Action(name='Stop BIDS App!',action='stop_bids_app',enabled_when='handler.settings_checked and handler.docker_running')

    traits_view = QtView(
        Group(
            VGroup(
                VGroup(
                        Item("bidsapp_tag", style="readonly", label="Tag"),
                        label="BIDS App Version",
                ),
                VGroup(
                        Item("bids_root", style="readonly", label="Input directory"),
                        Item(
                                "output_dir",
                                style="simple",
                                label="Output directory",
                                enabled_when="not(data_provenance_tracking)",
                        ),
                        label="BIDS dataset",
                ),
                VGroup(
                    HGroup(
                        UItem(
                            "subjects",
                            editor=TabularEditor(
                                show_titles=True,
                                selected="list_of_subjects_to_be_processed",
                                editable=False,
                                multi_select=True,
                                adapter=MultiSelectAdapter(
                                        columns=[("Available labels", "myvalue")]
                                ),
                            ),
                        ),
                        UItem(
                            "list_of_subjects_to_be_processed",
                            editor=TabularEditor(
                                show_titles=True,
                                editable=False,
                                adapter=MultiSelectAdapter(
                                        columns=[("Labels to be processed", "myvalue")]
                                ),
                            ),
                        ),
                    ),
                    label="Participant labels to be processed",
                ),
                HGroup(
                    Item(
                        "number_of_participants_processed_in_parallel",
                        label="Number of participants processed in parallel",
                    ),
                    label="Parallel processing",
                ),
                VGroup(
                    HGroup(
                        VGroup(
                            Item("number_of_threads", label="Number of OpenMP threads"),
                            Item(
                                "fix_ants_number_of_threads",
                                label="Set number of threads used by ANTs",
                            ),
                            Item(
                                "ants_number_of_threads",
                                label="Number of ITK threads used by ANTs registration",
                                enabled_when="fix_ants_number_of_threads",
                            ),
                            label="Multithreading",
                        ),
                        VGroup(
                            Item(
                                "fix_ants_random_seed",
                                label="Set seed of ANTS random number generator",
                            ),
                            Item(
                                "ants_random_seed",
                                label="Seed",
                                enabled_when="fix_ants_random_seed",
                            ),
                            Item(
                                "fix_mrtrix_random_seed",
                                label="Set seed of MRtrix random number generator",
                            ),
                            Item(
                                "mrtrix_random_seed",
                                label="Seed",
                                enabled_when="fix_mrtrix_random_seed",
                            ),
                            label="Random number generators",
                        ),
                    ),
                    label="Advanced execution settings for each participant process",
                ),
                VGroup(
                    Group(
                        Item(
                            "anat_config",
                            editor=FileEditor(dialog_style="open"),
                            label="Configuration file",
                            visible_when="run_anat_pipeline",
                        ),
                        label="Anatomical pipeline",
                    ),
                    Group(
                        Item("run_dmri_pipeline", label="Run processing stages"),
                        Item(
                            "dmri_config",
                            editor=FileEditor(dialog_style="open"),
                            label="Configuration file",
                            visible_when="run_dmri_pipeline",
                        ),
                        label="Diffusion pipeline",
                        visible_when="dmri_inputs_checked==True",
                    ),
                    Group(
                        Item("run_fmri_pipeline", label="Run processing stages"),
                        Item(
                            "fmri_config",
                            editor=FileEditor(dialog_style="open"),
                            label="Configuration file",
                            visible_when="run_fmri_pipeline",
                        ),
                        label="fMRI pipeline",
                        visible_when="fmri_inputs_checked==True",
                    ),
                    label="Configuration of processing pipelines",
                ),
                VGroup(
                    Item(
                        "fs_license",
                        editor=FileEditor(dialog_style="open"),
                        label="LICENSE",
                    ),
                    # Item('fs_average', label='FSaverage directory'),
                    label="Freesurfer configuration",
                ),
                VGroup(
                    Item("data_provenance_tracking", label="Use Datalad"),
                    Item(
                        "datalad_update_environment",
                        visible_when="data_provenance_tracking",
                        label="Update the computing environment (if existing)",
                    ),
                    label="Data Provenance Tracking / Data Lineage",
                    enabled_when="datalad_is_available",
                ),
                orientation="vertical",
                springy=True,
            ),
            spring,
            HGroup(
                    spring,
                    Item(
                            "check",
                            style="custom",
                            width=152,
                            height=35,
                            resizable=False,
                            label="",
                            show_label=False,
                            style_sheet=return_button_style_sheet(
                                    ImageResource(
                                            pkg_resources.resource_filename(
                                                    "resources",
                                                    os.path.join("buttons", "bidsapp-check-settings.png"),
                                            )
                                    ).absolute_path
                            ),
                    ),
                    spring,
                    Item(
                            "start_bidsapp",
                            style="custom",
                            width=152,
                            height=35,
                            resizable=False,
                            label="",
                            show_label=False,
                            style_sheet=return_button_style_sheet(
                                    ImageResource(
                                            pkg_resources.resource_filename(
                                                    "resources", os.path.join("buttons", "bidsapp-run.png")
                                            )
                                    ).absolute_path,
                                    ImageResource(
                                            pkg_resources.resource_filename(
                                                    "resources",
                                                    os.path.join("buttons", "bidsapp-run-disabled.png"),
                                            )
                                    ).absolute_path,
                            ),
                            enabled_when="settings_checked==True and docker_running==False",
                    ),
                    spring,
                    show_labels=False,
                    label="",
            ),
            orientation="vertical",
            springy=True,
        ),
        title="Connectome Mapper 3 BIDS App GUI",
        # kind='modal',
        handler=cmp.bidsappmanager.gui.handlers.BIDSAppInterfaceWindowHandler(),
        # style_sheet=style_sheet,
        buttons=[],
        # buttons = [check,start_bidsapp],
        # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
        # buttons = [preprocessing, map_connectome, map_custom],
        width=0.6,
        height=0.8,
        scrollable=True,  # , resizable=True
        icon=get_icon("bidsapp.png"),
    )

    log_view = QtView(
            Group(
                    Item("list_of_processing_logfiles"), orientation="vertical", springy=True
            ),
            title="Connectome Mapper 3 BIDS App Progress",
            # kind='modal',
            # handler=project.BIDSAppInterfaceWindowHandler(),
            # style_sheet=style_sheet,
            buttons=[],
            # buttons = [check,start_bidsapp],
            # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
            # buttons = [preprocessing, map_connectome, map_custom],
            width=0.5,
            height=0.8,
            resizable=True,  # , scrollable=True, resizable=True
            icon=get_icon("bidsapp.png"),
    )

    def __init__(
            self,
            project_info=None,
            bids_root="",
            subjects=None,
            list_of_subjects_to_be_processed=None,
            anat_config="",
            dmri_config="",
            fmri_config="",
    ):
        """Constructor of an :class:``BIDSAppInterfaceWindow`` instance.

        Parameters
        ----------
        project_info : cmp.project.ProjectInfo
            :class:`CMP_Project_Info` object (Default: None)

        bids_root : traits.Directory
            BIDS dataset root directory (Default: \'\')

        subjects : List of string
            List of subjects in the dataset (Default: None)

        list_of_subjects_to_be_processed : List of string
            List of subjects to be processed (Default: None)

        anat_config : string
            Path to anatomical pipeline configuration file (Default: \'\')

        dmri_config : string
            Path to diffusion pipeline configuration file (Default: \'\')

        fmri_config : string
            Path to functional pipeline configuration file (Default: \'\')
        """
        print("> Initialize window...")
        if multiprocessing.cpu_count() < 4:
            self.number_of_threads_max = multiprocessing.cpu_count()

        self.project_info = project_info
        self.bids_root = bids_root

        # Create a BIDSLayout for checking availability of dMRI and fMRI data
        try:
            bids_layout = BIDSLayout(self.bids_root)
        except Exception:
            print_error("  .. Exception : Raised at BIDSLayout")
            sys.exit(1)

        # Check if sMRI data is available in the dataset
        smri_files = bids_layout.get(
                datatype="anat", suffix="T1w", extensions="nii.gz", return_type="file"
        )

        if not smri_files:
            anat_inputs_checked = False
        else:
            anat_inputs_checked = True

        print(f"  .. T1w available: {anat_inputs_checked}")

        # Check if dMRI data is available in the dataset
        dmri_files = bids_layout.get(
                datatype="dwi", suffix="dwi", extensions="nii.gz", return_type="file"
        )

        if not dmri_files:
            self.dmri_inputs_checked = False
            self.run_dmri_pipeline = False
        else:
            self.dmri_inputs_checked = True
            self.run_dmri_pipeline = True

        print(f"  .. DWI available: {self.dmri_inputs_checked}")

        # Check if fMRI data is available in the dataset
        fmri_files = bids_layout.get(
                task="rest",
                datatype="func",
                suffix="bold",
                extensions="nii.gz",
                return_type="file",
        )
        if not fmri_files:
            self.fmri_inputs_checked = False
            self.run_fmri_pipeline = False
        else:
            self.fmri_inputs_checked = True
            self.run_fmri_pipeline = True

        print(f"  .. rsfMRI available: {self.fmri_inputs_checked}")

        # Initialize output directory to be /bids_dir/derivatives
        self.output_dir = os.path.join(bids_root, "derivatives")

        self.subjects = subjects
        # self.list_of_subjects_to_be_processed = list_of_subjects_to_be_processed
        self.anat_config = anat_config
        self.dmri_config = dmri_config
        self.fmri_config = fmri_config

        if 'FREESURFER_HOME' in os.environ:
            self.fs_license = os.path.join(
                    os.environ['FREESURFER_HOME'], 'license.txt')
        elif os.path.isfile(os.path.join(bids_root, 'code', 'license.txt')):
            self.fs_license = os.path.join(bids_root, 'code', 'license.txt')
        else:
            print_error('.. ERROR: Environment variable $FREESURFER_HOME not found and no Freesurfer license file '
                        'found in local code-folder ')
            self.fs_license = ''
            print_warning('Freesurfer license unset ({})'.format(self.fs_license))

        self.datalad_is_available = project.is_tool("datalad")

        self.on_trait_change(self.update_run_dmri_pipeline, "run_dmri_pipeline")
        self.on_trait_change(self.update_run_fmri_pipeline, "run_fmri_pipeline")

        self.on_trait_change(
                self.number_of_parallel_procs_updated,
                "number_of_participants_processed_in_parallel",
        )

        self.on_trait_change(
                self.update_checksettings, "list_of_subjects_to_be_processed"
        )
        self.on_trait_change(self.update_checksettings, "anat_config")
        self.on_trait_change(self.update_checksettings, "run_dmri_pipeline")
        self.on_trait_change(self.update_checksettings, "dmri_config")
        self.on_trait_change(self.update_checksettings, "run_fmri_pipeline")
        self.on_trait_change(self.update_checksettings, "fmri_config")
        self.on_trait_change(self.update_checksettings, "fs_license")
        # self.on_trait_change(self.update_checksettings, 'fs_average')

    def number_of_parallel_procs_updated(self, new):
        """Callback function when ``number_of_parallel_procs`` is updated."""
        number_of_threads_max = int((multiprocessing.cpu_count() - 1) / new)

        if number_of_threads_max > 4:
            self.number_of_threads_max = 4
        else:
            self.number_of_threads_max = number_of_threads_max

        print(
                "  .. INFO : Update number of threads max to : {}".format(
                        self.number_of_threads_max
                )
        )

    def update_run_anat_pipeline(self, new):
        """Callback function when ``run_anat_pipeline`` is updated."""
        if new is False:
            print_warning("  .. WARNING: At least anatomical pipeline should be run!")
            self.run_anat_pipeline = True

    def update_run_dmri_pipeline(self, new):
        """Callback function when ``run_dmri_pipeline`` is updated."""
        self.run_anat_pipeline = True

    def update_run_fmri_pipeline(self, new):
        """Callback function when ``run_fmri_pipeline`` is updated."""
        self.run_anat_pipeline = True

    def update_checksettings(self, new):
        """Function that reset ``settings_checked`` attribute to False."""
        self.settings_checked = False

    def _data_provenance_tracking_changed(self, new):
        """Callback function `data_provenance_tracking` attribute is updated."""
        if new is True:
            self.output_dir = os.path.join(self.bids_root, "derivatives")
        self.data_provenance_tracking = new

    def _update_selection_fired(self):
        """Callback function when the list of selected subjects is updated."""
        self.configure_traits(view="select_subjects_to_be_processed_view")

    def _check_fired(self):
        """Callback function when the Check Setting button is clicked."""
        self.check_settings()

    def _start_bidsapp_fired(self):
        """Callback function when the Run BIDS App button is clicked."""
        self.start_bids_app()

    def check_settings(self):
        """Checks if all the parameters of the BIDS App run are properly set before execution."""
        print_warning("\n-----------------------------------------")
        print_warning("BIDS App execution settings check summary")
        print_warning("-----------------------------------------")

        self.settings_checked = True

        if os.path.isdir(self.bids_root):
            print(f"* BIDS root directory : {self.bids_root}")
        else:
            print_error("Error: BIDS root invalid!")
            self.settings_checked = False

        if os.path.exists(os.path.join(self.output_dir, __cmp_directory__)):
            print(f"* Output directory (existing) : {self.output_dir}")
        else:
            os.makedirs(os.path.join(self.output_dir, __cmp_directory__))
            print_warning(f"Output directory (created) : {self.output_dir}")

        if len(self.list_of_subjects_to_be_processed) > 0:
            print(
                    f"* Participant labels to be processed : {self.list_of_subjects_to_be_processed}"
            )
        else:
            print_error(
                    "Error: At least one participant label to be processed should selected!"
            )
            self.settings_checked = False
        # if not self.list_of_subjects_to_be_processed.empty():
        #     print("List of subjects to be processed : {}".format(self.list_of_subjects_to_be_processed))
        # else:
        #     print("Warning: List of subjects empty!")

        if os.path.isfile(self.anat_config):
            print(f"* Anatomical configuration file : {self.anat_config}")
        else:
            print_error(
                    "Error: Configuration file for anatomical pipeline not existing!"
            )
            self.settings_checked = False

        if os.path.isfile(self.dmri_config):
            print(f"* Diffusion configuration file : {self.dmri_config}")
        else:
            print_warning(
                    "Warning: Configuration file for diffusion pipeline not existing!"
            )

        if os.path.isfile(self.fmri_config):
            print(f"* fMRI configuration file : {self.fmri_config}")
        else:
            print_warning("Warning: Configuration file for fMRI pipeline not existing!")

        if os.path.isfile(self.fs_license):
            print(f"* Freesurfer license : {self.fs_license}")
        else:
            print_error(f"Error: Invalid Freesurfer license ({self.fs_license})!")
            self.settings_checked = False

        # if os.path.isdir(self.fs_average):
        #     print("fsaverage directory : {}".format(self.fs_average))
        # else:
        #     print("Error: fsaverage directory ({}) not existing!".format(self.fs_average))
        #     self.settings_checked = False

        print(f"Valid inputs for BIDS App : {self.settings_checked}")
        print(f"BIDS App Version Tag: {self.bidsapp_tag}")
        print(f"Data provenance tracking (datalad) : {self.data_provenance_tracking}")
        print(
                f"Update computing environment (datalad) : {self.datalad_update_environment}"
        )
        print(
                f"Number of participant processed in parallel : {self.number_of_participants_processed_in_parallel}"
        )
        print(f"Number of OpenMP threads / participant : {self.number_of_threads}")

        print(f"Fix number of ITK threads : {self.fix_ants_number_of_threads}")
        if self.fix_ants_number_of_threads:
            print(
                    f"Number of ITK threads (ANTs) / participant : {self.ants_number_of_threads}"
            )

        print(f"Fix seed in ANTS random number generator : {self.fix_ants_random_seed}")
        if self.fix_ants_random_seed:
            print(f"Seed value : {self.ants_random_seed}")

        print(
                f"Fix seed in MRtrix random number generator : {self.fix_mrtrix_random_seed}"
        )
        if self.fix_ants_random_seed:
            print(f"Seed value : {self.mrtrix_random_seed}")

        print("-----------------------------------------\n")

        return True

    def start_bidsapp_participant_level_process(self, bidsapp_tag, participant_labels):
        """Create and run the BIDS App command.

        Parameters
        ----------
        bidsapp_tag : traits.Str
            Version tag of the CMP 3 BIDS App

        participant_labels : traits.List
            List of participants labels in the form ["01", "03", "04", ...]
        """

        cmd = [
                "docker",
                "run",
                "-it",
                "--rm",
                "-v",
                "{}:/bids_dir".format(self.bids_root),
                "-v",
                "{}:/output_dir".format(self.output_dir),
                "-v",
                "{}:/bids_dir/code/license.txt".format(self.fs_license),
                "-v",
                "{}:/code/ref_anatomical_config.json".format(self.anat_config),
        ]

        if self.run_dmri_pipeline:
            cmd.append("-v")
            cmd.append("{}:/code/ref_diffusion_config.json".format(self.dmri_config))

        if self.run_fmri_pipeline:
            cmd.append("-v")
            cmd.append("{}:/code/ref_fMRI_config.json".format(self.fmri_config))

        cmd.append("-u")
        cmd.append("{}:{}".format(os.geteuid(), os.getegid()))

        cmd.append("sebastientourbier/connectomemapper-bidsapp:{}".format(bidsapp_tag))
        cmd.append("/bids_dir")
        cmd.append("/output_dir")
        cmd.append("participant")

        cmd.append("--participant_label")
        for label in participant_labels:
            cmd.append("{}".format(label))

        cmd.append("--anat_pipeline_config")
        cmd.append("/code/ref_anatomical_config.json")

        if self.run_dmri_pipeline:
            cmd.append("--dwi_pipeline_config")
            cmd.append("/code/ref_diffusion_config.json")

        if self.run_fmri_pipeline:
            cmd.append("--func_pipeline_config")
            cmd.append("/code/ref_fMRI_config.json")

        cmd.append("--fs_license")
        cmd.append("{}".format("/bids_dir/code/license.txt"))

        cmd.append("--number_of_participants_processed_in_parallel")
        cmd.append("{}".format(self.number_of_participants_processed_in_parallel))

        cmd.append("--number_of_threads")
        cmd.append("{}".format(self.number_of_threads))

        if self.fix_ants_number_of_threads:
            cmd.append("--ants_number_of_threads")
            cmd.append("{}".format(self.ants_number_of_threads))

        if self.fix_ants_random_seed:
            cmd.append("--ants_random_seed")
            cmd.append("{}".format(self.ants_random_seed))

        if self.fix_mrtrix_random_seed:
            cmd.append("--mrtrix_random_seed")
            cmd.append("{}".format(self.mrtrix_random_seed))

        print_blue("... BIDS App execution command: {}".format(" ".join(cmd)))

        proc = Popen(cmd)
        # proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        return proc

    def start_bidsapp_participant_level_process_with_datalad(
            self, bidsapp_tag, participant_labels
    ):
        """Create and run the BIDS App command with Datalad.

        Parameters
        ----------
        bidsapp_tag : traits.Str
            Version tag of the CMP 3 BIDS App

        participant_labels : traits.List
            List of participants labels in the form ["01", "03", "04", ...]
        """
        cmd = [
                "datalad",
                "containers-run",
                "--container-name",
                "connectomemapper-bidsapp-{}".format("-".join(bidsapp_tag.split("."))),
                "-m",
                "Processing with connectomemapper-bidsapp {}".format(bidsapp_tag),
                "--input",
                f"{self.anat_config}",
        ]

        # for label in participant_labels:
        #     cmd.append('--input')
        #     cmd.append('sub-{}/ses-*/anat/sub-*_T1w.*'.format(label))
        #
        #     cmd.append('--input')
        #     cmd.append('derivatives/freesurfer/sub-{}*/*'.format(label))
        #
        #     if self.run_dmri_pipeline:
        #         cmd.append('--input')
        #         cmd.append('sub-{}/ses-*/dwi/sub-*_dwi.*'.format(label))
        #
        #     if self.run_fmri_pipeline:
        #         cmd.append('--input')
        #         cmd.append('sub-{}/ses-*/func/sub-*_bold.*'.format(label))

        if self.run_dmri_pipeline:
            cmd.append("--input")
            cmd.append(f"{self.dmri_config}")

        if self.run_fmri_pipeline:
            cmd.append("--input")
            cmd.append(f"{self.fmri_config}")

        cmd.append("--output")
        cmd.append(f"{self.output_dir}")
        # for label in participant_labels:
        #     cmd.append('--input')
        #     cmd.append('{}'.format(label))

        cmd.append("/bids_dir")
        cmd.append("/output_dir")
        cmd.append("participant")

        cmd.append("--participant_label")
        for label in participant_labels:
            cmd.append("{}".format(label))

        # Counter to track position of config file as --input
        i = 0
        cmd.append("--anat_pipeline_config")
        cmd.append("/{{inputs[{}]}}".format(i))
        i += 1
        if self.run_dmri_pipeline:
            cmd.append("--dwi_pipeline_config")
            cmd.append("/{{inputs[{}]}}".format(i))
            i += 1

        if self.run_fmri_pipeline:
            cmd.append("--func_pipeline_config")
            cmd.append("/{{inputs[{}]}}".format(i))

        print_blue("... Datalad cmd : {}".format(" ".join(cmd)))

        proc = Popen(cmd, cwd=os.path.join(self.bids_root))
        # proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(self.bids_root,'derivatives'))

        return proc

    @classmethod
    def manage_bidsapp_procs(self, proclist):
        """Manage parallelized process at the participant level

        Parameters
        ----------
        proclist : List of subprocess.Popen
            List of Popen processes
        """
        for proc in proclist:
            if proc.poll() is not None:
                proclist.remove(proc)

    @classmethod
    def run(self, command, env=None, cwd=os.getcwd()):
        """Function to run datalad commands.

        It runs the command specified as input via ``subprocess.run()``.

        Parameters
        ----------
        command : string
            String containing the command to be executed (required)

        env : os.environ
            Specify a custom os.environ

        cwd : os.path
            Specify a custom current working directory

        Examples
        --------
        >>> cmd = 'datalad save -m my dataset change message'
        >>> run(cmd) # doctest: +SKIP
        """
        merged_env = os.environ
        if env is not None:
            merged_env.update(env)
        process = Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                env=merged_env,
                cwd=cwd,
        )
        while True:
            line = process.stdout.readline()
            # Remove the "b'" prefix and the "'" at the end return by datalad
            line = str(line)[2:-1]
            print(line)
            if line == "" and process.poll() is not None:
                break
        if process.returncode != 0:
            raise Exception(
                    BColors.FAIL
                    + f"Non zero return code: {process.returncode}"
                    + BColors.ENDC
            )

    def start_bids_app(self):
        """Function executed when the Run BIDS App button is clicked.

        It implements all steps in the creation and execution of the BIDS App
        with or without datalad.
        """
        print_blue("[Run BIDS App]")

        # Copy freesurfer license into dataset/code directory at the location
        # the BIDS app expects to find it.

        license_dst = os.path.join(self.bids_root, "code", "license.txt")

        if not os.access(license_dst, os.F_OK):
            dst = os.path.join(self.bids_root, "code", "license.txt")
            print("> Copy FreeSurfer license (BIDS App Manager) ")
            print("... src : {}".format(self.fs_license))
            print("... dst : {}".format(dst))
            shutil.copy2(src=self.fs_license, dst=dst)
        else:
            print_warning(
                    "> FreeSurfer license copy skipped as it already exists(BIDS App Manager) "
            )

        print("> Datalad available: {}".format(self.datalad_is_available))

        # self.datalad_is_available = False

        if self.datalad_is_available and self.data_provenance_tracking:
            # Detect structure subject/session
            session_structure = False
            res = glob.glob(os.path.join(self.bids_root, "sub-*/*/anat"))
            # print(res)
            if len(res) > 0:
                session_structure = True
                print("    INFO : Subject/Session structure detected!")
            else:
                print("    INFO : Subject structure detected!")

            # Equivalent to:
            #    >> datalad create derivatives
            #    >> cd derivatives
            #    >> datalad containers-add connectomemapper-bidsapp-{} --url dhub://sebastientourbier/connectomemapper-bidsapp:{}
            if not os.path.isdir(os.path.join(self.bids_root, ".datalad")):
                cmd = [
                        "datalad",
                        "create",
                        "--force",
                        "-D",
                        f'"Creation of datalad dataset to be processed by the connectome mapper bidsapp (tag:{self.bidsapp_tag})"',
                        "-c",
                        "text2git",
                        "-d",
                        f"{self.bids_root}",
                ]
                cmd = " ".join(cmd)
                try:
                    print_blue(f"... cmd: {cmd}")
                    self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
                    print(
                            "    INFO: A datalad dataset has been created with success at the root directory!"
                    )
                    msg = (
                            "Add all files to datalad. "
                            "Dataset ready to be linked with the BIDS App."
                    )

                except Exception:
                    msg = "Save state after error at datalad dataset creation"
                    print_error(
                            "    DATALAD ERROR: Failed to create the datalad dataset"
                    )
            else:
                msg = "Datalad dataset up-to-date and ready to be linked with the BIDS App."
                print("    INFO: A datalad dataset already exists!")

            # log_filename = os.path.join(self.bids_root,'derivatives','cmp','main-datalad_log-cmpbidsapp.txt')
            #
            # if not os.path.exists(os.path.join(self.bids_root,'derivatives','cmp')):
            #     os.makedirs(os.path.join(self.bids_root,'derivatives','cmp'))

            # create an empty log file to be tracked by datalad
            # f = open(log_filename,"w+")
            # f.close()

            cmd = f'datalad save -d . -m "{msg}"'
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error("    DATALAD ERROR: Failed to add changes to dataset")

            datalad_container = os.path.join(
                    self.bids_root,
                    ".datalad",
                    "environments",
                    "connectomemapper-bidsapp-{}".format(
                            "-".join(self.bidsapp_tag.split("."))
                    ),
                    "image",
            )
            add_container = True
            update_container = False
            if os.path.isdir(datalad_container):
                if self.datalad_update_environment:
                    print(
                            "    INFO: Container already listed in the datalad dataset and will be updated!"
                    )
                    shutil.rmtree(datalad_container)
                    add_container = True
                else:
                    add_container = False
                    print(
                            "    INFO: Container already listed in the datalad dataset and will NOT be updated!"
                    )
            else:
                add_container = True
                print(
                        "    INFO: Add a new computing environment (container image) to the datalad dataset!"
                )

            if add_container:
                # Define the docker run command executed by Datalad.
                # It makes the assumption that the license.txt and the configuration files
                # are located in the code/ directory.
                docker_cmd = [
                        "docker",
                        "run",
                        "--rm",
                        "-t",
                        "-v",
                        '"$(pwd)":/bids_dir',
                        "-v",
                        '"$(pwd)"/derivatives:/output_dir',
                        "-v",
                        '"$(pwd)"/code/license.txt:/bids_dir/code/license.txt',
                        "-v",
                        f'"$(pwd)"/code/{os.path.basename(self.anat_config)}:/code/ref_anatomical_config.json',
                ]

                if self.run_dmri_pipeline:
                    docker_cmd.append("-v")
                    docker_cmd.append(
                            f'"$(pwd)"/code/{os.path.basename(self.dmri_config)}:/code/ref_diffusion_config.json'
                    )

                if self.run_fmri_pipeline:
                    docker_cmd.append("-v")
                    docker_cmd.append(
                            f'"$(pwd)"/code/{os.path.basename(self.fmri_config)}:/code/ref_fMRI_config.json'
                    )

                docker_cmd.append("-u")
                docker_cmd.append("{}:{}".format(os.geteuid(), os.getegid()))

                docker_cmd.append(
                        f"sebastientourbier/connectomemapper-bidsapp:{self.bidsapp_tag}"
                )
                docker_cmd.append("{cmd}")

                # Define and run the command to add the container image to datalad
                version_tag = "-".join(self.bidsapp_tag.split("."))
                cmd = [
                        "datalad",
                        "containers-add",
                        f"connectomemapper-bidsapp-{version_tag}",
                        "--url",
                        f"dhub://sebastientourbier/connectomemapper-bidsapp:{self.bidsapp_tag}",
                        "-d",
                        ".",
                        "--call-fmt",
                ]

                cmd = " ".join(cmd)
                docker_cmd = " ".join(docker_cmd)
                cmd = f'{cmd} "{docker_cmd}"'

                if self.datalad_update_environment:
                    cmd = f"{cmd} --update"
                try:
                    print_blue(f"... cmd: {cmd}")
                    self.run(cmd, env={}, cwd=os.path.join(self.bids_root))
                    print(
                            "    INFO: Container image has been linked to dataset with success!"
                    )
                except Exception:
                    print_error(
                            "   DATALAD ERROR: Failed to link the container image to the dataset"
                    )

            # Create a list of files to be retrieved by datalad get
            datalad_get_list = [self.anat_config]

            if self.run_dmri_pipeline:
                datalad_get_list.append(self.dmri_config)

            if self.run_dmri_pipeline:
                datalad_get_list.append(self.fmri_config)

            if session_structure:
                for label in self.list_of_subjects_to_be_processed:
                    datalad_get_list.append(
                            "sub-{}/ses-*/anat/sub-{}*_T1w.*".format(label, label)
                    )
                    datalad_get_list.append(
                            "derivatives/{}/sub-{}*/*".format(__freesurfer_directory__, label)
                    )
                    if self.run_dmri_pipeline:
                        datalad_get_list.append(
                                "sub-{}/ses-*/dwi/sub-{}*_dwi.*".format(label, label)
                        )
                    if self.run_fmri_pipeline:
                        datalad_get_list.append(
                                "sub-{}/ses-*/func/sub-{}*_bold.*".format(label, label)
                        )
            else:
                for label in self.list_of_subjects_to_be_processed:
                    datalad_get_list.append(
                            "sub-{}/anat/sub-{}*_T1w.*".format(label, label)
                    )
                    datalad_get_list.append(
                            "derivatives/{}/sub-{}/*".format(__freesurfer_directory__, label)
                    )
                    if self.run_dmri_pipeline:
                        datalad_get_list.append(
                                "sub-{}/dwi/sub-{}*_dwi.*".format(label, label)
                        )
                    if self.run_fmri_pipeline:
                        datalad_get_list.append(
                                "sub-{}/func/sub-{}*_bold.*".format(label, label)
                        )

            cmd = (
                    'datalad save -d . -m "Dataset state after adding the container image. '
                    'Datasets ready to get files via datalad run."'
            )
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error(
                        "    DATALAD ERROR: Failed to add existing files to dataset"
                )

            cmd = 'datalad run -d . -m "Get files for sub-{}" bash -c "datalad get {}"'.format(
                    self.list_of_subjects_to_be_processed, " ".join(datalad_get_list)
            )
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error(
                        "    DATALAD ERROR: Failed to get files (cmd: datalad get {})".format(
                                " ".join(datalad_get_list)
                        )
                )

            cmd = (
                    'datalad save -d . -m "Dataset state after getting the files. Dataset ready for connectome mapping." '
                    "--version-tag ready4analysis-{}".format(time.strftime("%Y%m%d-%H%M%S"))
            )
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error("    DATALAD ERROR: Failed to commit changes to dataset")

            cmd = "datalad status -d ."
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error("    DATALAD ERROR: Failed to run datalad rev-status")

        # maxprocs = multiprocessing.cpu_count()
        processes = []

        self.docker_running = True

        if self.datalad_is_available and self.data_provenance_tracking:

            proc = self.start_bidsapp_participant_level_process_with_datalad(
                    self.bidsapp_tag, self.list_of_subjects_to_be_processed
            )

        else:
            proc = self.start_bidsapp_participant_level_process(
                    self.bidsapp_tag, self.list_of_subjects_to_be_processed
            )

        processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        if self.datalad_is_available and self.data_provenance_tracking:
            # Clean remaining cache files generated in tmp/ of the docker image
            # project.clean_cache(self.bids_root)

            cmd = 'datalad save -d . -m "Dataset processed by the connectomemapper-bidsapp:{}" --version-tag processed-{}'.format(
                    self.bidsapp_tag, time.strftime("%Y%m%d-%H%M%S")
            )
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error(
                        "    DATALAD ERROR: Failed to commit derivatives to datalad dataset"
                )

            cmd = "datalad diff -t HEAD~1"
            try:
                print_blue(f"... cmd: {cmd}")
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print_error("    DATALAD ERROR: Failed to run datalad diff -t HEAD~1")

        print("Processing with BIDS App Finished")
        self.docker_running = False
        return True

    # def stop_bids_app(self, ui_info):
    #     print("Stop BIDS App")
    #     #self.docker_process.kill()
    #     self.docker_running = False
    #     return True
