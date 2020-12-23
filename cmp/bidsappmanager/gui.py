# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Connectome Mapper GUI."""

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
from traitsui.tabular_adapter import TabularAdapter
from traitsui.api import *
from traits.api import *

from bids import BIDSLayout

import warnings

# Own imports
import cmp.bidsappmanager.project as project
from cmp.project import CMP_Project_Info
from cmp.info import __version__

from cmp.pipelines.diffusion.diffusion import DiffusionPipeline
from cmp.pipelines.functional.fMRI import fMRIPipeline

from cmtklib.util import return_button_style_sheet

# Remove warnings visible whenever you import scipy (or another package) 
# that was compiled against an older numpy than is installed.
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

# global modal_width
modal_width = 400

# global style_sheet
style_sheet = '''
            QLabel {
                font: 12pt "Verdana";
                margin-left: 5px;
                background-color: transparent;
            }
            QPushButton {
                border: 0px solid lightgray;
                border-radius: 4px;
                color: transparent;
                background-color: transparent;
                min-width: 222px;
                icon-size: 222px;
                font: 12pt "Verdana";
                margin: 0px 0px 0px 0px;
                padding:0px 0px;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #dadbde, stop: 1 #f6f7fa);
            }
            QMenuBar {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #dadbde, stop: 1 #f6f7fa)
                font: 14pt "Verdana";
            }
            QMenuBar::item {
                spacing: 5px; /* spacing between menu bar items */
                padding: 5px 5px;
                background: transparent;
                border-radius: 4px;
            }
            QMenuBar::item:selected { /* when selected using mouse or keyboard */
                background: #a8a8a8;
            }
            QMenuBar::item:pressed {
                background: #888888;
            }
            QMainWindow {
                background-color: yellow;
                image: url("images/cmp.png");
            }
            QMainWindow::separator {
                background: yellow;
                width: 1px; /* when vertical */
                height: 1px; /* when horizontal */
            }
            QMainWindow::separator:hover {
                background: red;
            }

            QListView::item:selected {
                border: 1px solid #6a6ea9;
            }

            QListView::item:selected:!active {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #ABAFE5, stop: 1 #8588B2);
            }

            QListView::item:selected:active {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #6a6ea9, stop: 1 #888dd9);
            }

            QListView::item:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #FAFBFE, stop: 1 #DCDEF1);
            }
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
            }

            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 20px;
            }
            '''


def get_icon(path):
    """Return an instance of `ImageResource` or None is there is not graphical backend.

    Parameters
    ----------
    path : string
        Path to an image file

    Returns
    -------
    icon : ImageResource
        Return an instance of `ImageResource` or None is there is not graphical backend.
    """
    on_rtd = os.environ.get("READTHEDOCS") == "True"
    if on_rtd:
        print('READTHEDOCS: Return None for icon')
        icon = None
    else:
        icon = ImageResource(path)
    return icon


class CMP_Project_InfoUI(CMP_Project_Info):
    """Class that extends the :class:`CMP_Project_Info` with graphical components.

    It supports graphically the setting of all processing properties / attributes
    of an :class:`CMP_Project_Info` instance.

    Attributes
    -----------
    creation_mode : traits.Enum
        Mode for loading the dataset. Valid values are
        'Load BIDS dataset', 'Install Datalad BIDS dataset'

    install_datalad_dataset_via_ssh : traits.Bool
        If set to True install the datalad dataset from a remote server
        via ssh.(True by default)

    ssh_user : traits.Str
        Remote server username.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    ssh_pwd <traits.Password>
        Remote server password.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    ssh_remote : traits.Str
        Remote server IP or URL.
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    datalad_dataset_path : traits.Directory
        Path to the datalad dataset on the remote server. 
        (Required if ``install_datalad_dataset_via_ssh`` is True)

    summary_view_button : traits.ui.Button
        Button that shows the pipeline processing summary table

    pipeline_processing_summary_view : traits.ui.VGroup
        TraitsUI VGroup that contains ``Item('pipeline_processing_summary')``

    dataset_view : traits.ui.View
        TraitsUI View that shows a summary of project settings and
        modality available for a given subject

    traits_view : QtView
        TraitsUI QtView that includes the View 'dataset_view'

    create_view : traits.ui.View
        Dialog view to create a BIDS Dataset

    subject_view : traits.ui.View
        Dialog view to select of subject

    subject_session_view : traits.ui.View
        Dialog view to select the subject session

    dmri_bids_acq_view : traits.ui.View
        Dialog view to select the diffusion acquisition model

    anat_warning_view : traits.ui.View
        View that displays a warning message regarding
        the anatomical T1w data

    anat_config_error_view : traits.ui.View
        Error view that displays an error message regarding
        the configuration of the anatomical pipeline

    dmri_warning_view : traits.ui.View
        View that displays a warning message regarding
        the diffusion MRI data

    dmri_config_error_view : traits.ui.View
        View that displays an error message regarding
        the configuration of the diffusion pipeline

    fmri_warning_view : traits.ui.View
        View that displays a warning message regarding
        the functional MRI data

    fmri_config_error_view : traits.ui.View
        View that displays an error message regarding
        the configuration of the fMRI pipeline

    open_view : traits.ui.View
        Dialog view to load a BIDS Dataset

    anat_select_config_to_load : traits.ui.View
        Dialog view to load the configuration file of the anatomical pipeline

    diffusion_imaging_model_select_view : traits.ui.View
        Dialog view to select the diffusion acquisition model

    dmri_select_config_to_load : traits.ui.View
        Dialog view to load the configuration file of the diffusion MRI pipeline

    fmri_select_config_to_load : traits.ui.View
        Dialog view to load the configuration file of the fMRI pipeline
    """

    creation_mode = Enum('Load BIDS dataset', 'Install Datalad BIDS dataset')
    install_datalad_dataset_via_ssh = Bool(True)
    ssh_user = String('remote_username')
    ssh_pwd = Password('')
    ssh_remote = String('IP address/ Machine name')
    datalad_dataset_path = Directory(
        '/shared/path/to/existing/datalad/dataset')

    anat_runs = List()
    anat_run = Enum(values='anat_runs')

    dmri_runs = List()
    dmri_run = Enum(values='dmri_runs')

    fmri_runs = List()
    fmri_run = Enum(values='fmri_runs')

    summary_view_button = Button('Pipeline processing summary')

    pipeline_processing_summary_view = VGroup(Item('pipeline_processing_summary'))

    dataset_view = VGroup(
        VGroup(
            HGroup(
                Item('base_directory', width=-0.3,
                     style='readonly', label="", resizable=True),
                Item('number_of_subjects',
                     width=-0.3,
                     style='readonly',
                     label="Number of participants",
                     resizable=True),
                'summary_view_button'),
            label='BIDS Dataset'),
        spring,
        HGroup(
            Group(
                Item('subject', style='simple',
                     show_label=True, resizable=True)),
            Group(
                Item('subject_session', style='simple',
                     label="Session", resizable=True),
                visible_when='subject_session!=""'),
            springy=True),
        spring,
        Group(
            Item('t1_available', style='readonly', label='T1', resizable=True),
            HGroup(
                Item('dmri_available', style='readonly',
                     label='Diffusion', resizable=True),
                Item('diffusion_imaging_model', label='Model',
                     resizable=True, enabled_when='dmri_available')),
            Item('fmri_available', style='readonly',
                 label='BOLD', resizable=True),
            label='Modalities'),
        spring,
        Group(
            Item('anat_last_date_processed', label="Anatomical pipeline",
                 style='readonly', resizable=True,
                 enabled_when='t1_available'),
            Item('dmri_last_date_processed', label="Diffusion pipeline",
                 style='readonly', resizable=True,
                 enabled_when='dmri_available'),
            Item('fmri_last_date_processed', label="fMRI pipeline",
                 style='readonly', resizable=True,
                 enabled_when='fmri_available'),
            label="Last date processed"),
        spring,
        Group(
            Item('number_of_cores', resizable=True),
            label='Processing configuration'),
        '550',
        spring,
        springy=True)

    traits_view = QtView(Include('dataset_view'))

    create_view = View(
        Item('creation_mode', style='custom'),
        Group(
            Group(
                Item('base_directory', label='BIDS Dataset'),
                visible_when='creation_mode=="Load BIDS dataset"'),
            Group(
                Item('install_datalad_dataset_via_ssh'),
                visible_when='creation_mode=="Install Datalad/BIDS dataset"'),
            Group(
                Item('ssh_remote', label='Remote ssh server',
                     visible_when='install_datalad_dataset_via_ssh'),
                Item('ssh_user', label='Remote username',
                     visible_when='install_datalad_dataset_via_ssh'),
                Item('ssh_pwd', label='Remote password',
                     visible_when='install_datalad_dataset_via_ssh'),
                Item('datalad_dataset_path',
                     label='Datalad/BIDS Dataset Path/URL to be installed'),
                Item('base_directory', label='Installation directory'),
                visible_when='creation_mode=="Install Datalad/BIDS dataset"'),
        ),
        kind='livemodal',
        title='Data creation: BIDS dataset selection',
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=['OK', 'Cancel'])

    subject_view = View(
        Group(
            Item('subject', label='Selected Subject')
        ),
        kind='modal',
        title='Subject and session selection',
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=['OK', 'Cancel'])

    subject_session_view = View(
        Group(
            Item('subject', style='readonly', label='Selected Subject'),
            Item('subject_session', label='Selected Session'),
        ),
        kind='modal',
        title='Session selection',
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=['OK', 'Cancel'])

    dmri_bids_acq_view = View(
        Group(
            Item('dmri_bids_acq', label='Selected model'),
        ),
        kind='modal',
        title='Selection of diffusion acquisition model',
        # style_sheet=style_sheet,
        width=modal_width,
        buttons=['OK', 'Cancel'])

    anat_warning_view = View(
        Group(
            Item('anat_warning_msg', style='readonly', show_label=False),
        ),
        title='Warning : Anatomical T1w data',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    anat_config_error_view = View(
        Group(
            Item('anat_config_error_msg', style='readonly', show_label=False),
        ),
        title='Error',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    dmri_warning_view = View(
        Group(
            Item('dmri_warning_msg', style='readonly', show_label=False),
        ),
        title='Warning : Diffusion MRI data',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    dmri_config_error_view = View(
        Group(
            Item('dmri_config_error_msg', style='readonly', show_label=False),
        ),
        title='Error',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    fmri_warning_view = View(
        Group(
            Item('fmri_warning_msg', style='readonly', show_label=False),
        ),
        title='Warning : fMRI data',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    fmri_config_error_view = View(
        Group(
            Item('fmri_config_error_msg', style='readonly', show_label=False),
        ),
        title='Error',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    open_view = View(
        Item('creation_mode', label='Mode'),
        Group(
            Item('install_datalad_dataset_via_ssh'),
            Item('ssh_remote', label='Remote ssh server',
                 visible_when='install_datalad_dataset_via_ssh'),
            Item('ssh_user', label='Remote username',
                 visible_when='install_datalad_dataset_via_ssh'),
            Item('ssh_pwd', label='Remote password',
                 visible_when='install_datalad_dataset_via_ssh'),
            Item('datalad_dataset_path',
                 label='Datalad/BIDS Dataset Path/URL to be installed'),
            Item('base_directory', label='Installation directory'),
            visible_when='creation_mode=="Install Datalad BIDS dataset"'),
        Group(
            Item('base_directory', label='BIDS Dataset'),
            visible_when='creation_mode=="Load BIDS dataset"'),
        kind='livemodal',
        title='BIDS Dataset Creation/Loading',
        # style_sheet=style_sheet,
        width=600,
        height=250,
        buttons=['OK', 'Cancel'])

    anat_select_config_to_load = View(
        Group(
            Item('anat_config_to_load_msg', style='readonly', show_label=False),
            Item('anat_config_to_load', style='custom', editor=EnumEditor(name='anat_available_config'),
                 show_label=False)
        ),
        title='Select configuration for anatomical pipeline',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    anat_custom_map_view = View(
        Group(
            Item('anat_custom_last_stage', editor=EnumEditor(name='anat_stage_names'), style='custom',
                 show_label=False),
        ),
        title='Select until which stage to process the anatomical pipeline.',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    diffusion_imaging_model_select_view = View(
        Group(
            Item('diffusion_imaging_model', label='Diffusion MRI modality'),
        ),
        title='Please select diffusion MRI modality',
        kind='modal',
        width=modal_width,
        buttons=['OK', 'Cancel'])

    dmri_select_config_to_load = View(
        Group(
            Item('dmri_config_to_load_msg', style='readonly', show_label=False),
        ),
        Item('dmri_config_to_load', style='custom', editor=EnumEditor(
            name='dmri_available_config'), show_label=False),
        title='Select configuration for diffusion pipeline',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    dmri_custom_map_view = View(
        Group(
            Item('dmri_custom_last_stage', editor=EnumEditor(name='dmri_stage_names'), style='custom',
                 show_label=False),
        ),
        title='Select until which stage to process the diffusion pipeline.',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    fmri_select_config_to_load = View(
        Group(
            Item('fmri_config_to_load_msg', style='readonly', show_label=False),
        ),
        Item('fmri_config_to_load', style='custom', editor=EnumEditor(
            name='fmri_available_config'), show_label=False),
        title='Select configuration for fMRI pipeline',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    fmri_custom_map_view = View(
        Group(
            Item('fmri_custom_last_stage', editor=EnumEditor(name='fmri_stage_names'), style='custom',
                 show_label=False),
        ),
        title='Select until which stage to process the fMRI pipeline.',
        kind='modal',
        width=modal_width,
        # style_sheet=style_sheet,
        buttons=['OK', 'Cancel'])

    def _summary_view_button_fired(self):
        self.configure_traits(view='pipeline_processing_summary_view')


class MultiSelectAdapter(TabularAdapter):
    """This adapter is used by both the left and right tables."""

    # Titles and column names for each column of a table.
    # In this example, each table has only one column.
    columns = [('', 'myvalue')]
    width = 100

    # Magically named trait which gives the display text of the column named
    # 'myvalue'. This is done using a Traits Property and its getter:
    myvalue_text = Property

    def _get_myvalue_text(self):
        """The getter for Property 'myvalue_text'.

        It simply takes the value of the corresponding item in the list
        being displayed in this table. A more complicated example could
        format the item before displaying it.
        """
        return 'sub-%s' % self.item


class CMP_BIDSAppWindow(HasTraits):
    """Class that defines the Window of the BIDS App Interface.

    Attributes
    ----------
    project_info : CMP_Project_Info
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

    project_info = Instance(CMP_Project_Info)

    bids_root = Directory()
    output_dir = Directory()
    subjects = List(Str)

    # multiproc_number_of_cores = Int(1)
    number_of_participants_processed_in_parallel = Range(low=1,
                                                         high=multiprocessing.cpu_count()-1,
                                                         desc='Number of participants to be processed in parallel')

    number_of_threads_max = Int(multiprocessing.cpu_count()-1)

    number_of_threads = Range(low=1,
                              high='number_of_threads_max',
                              mode='spinner',
                              desc='Number of OpenMP threads used by Dipy, FSL, MRtrix, '
                                   'and Freesurfer recon-all')

    fix_ants_random_seed = Bool(False, desc='Fix MRtrix3 random generator seed for tractography')
    ants_random_seed = Int(1234, desc='MRtrix random generator seed value')

    fix_mrtrix_random_seed = Bool(False, desc='Fix ANTs random generator seed for registration')
    mrtrix_random_seed = Int(1234, desc='ANTs random generator seed value')

    fix_ants_number_of_threads = Bool(False, desc='Fix independently number of threads used by ANTs registration')
    ants_number_of_threads = Range(low=1,
                                   high='number_of_threads_max',
                                   mode='spinner',
                                   desc='Number of ITK threads used by ANTs registration')

    fs_license = File(desc='Path to your FREESURFER license.txt')
    # fs_average = Directory(os.path.join(os.environ['FREESURFER_HOME'],'subjects','fsaverage'))

    list_of_subjects_to_be_processed = List(Str)

    list_of_processing_logfiles = List(File)

    anat_config = File(desc='Path to the configuration file of the anatomical pipeline')
    dmri_config = File(desc='Path to the configuration file of the diffusion pipeline')
    fmri_config = File(desc='Path to the configuration file of the fMRI pipeline')

    run_anat_pipeline = Bool(True, desc='Run the anatomical pipeline')
    run_dmri_pipeline = Bool(True, desc='Run the diffusion pipeline')
    run_fmri_pipeline = Bool(True, desc='Run the fMRI pipeline')

    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    settings_checked = Bool(False)
    docker_running = Bool(False)

    bidsapp_tag = Enum('{}'.format(__version__), [
                       'latest', '{}'.format(__version__)])

    data_provenance_tracking = Bool(False,
                                    desc='Use datalad to execute CMP3 and record dataset changes')

    datalad_update_environment = Bool(True,
                                      desc='Update the container if datalad run-container has been run already once')

    datalad_is_available = Bool(False,
                                desc='True if datalad is available')

    # check = Action(name='Check settings!',
    #                action='check_settings',
    #                image=get_icon(
    #                           pkg_resources.resource_filename('resources',
    #                               os.path.join('buttons', 'bidsapp-check-settings.png'))))
    # start_bidsapp = Action(name='Start BIDS App!',
    # action='start_bids_app',
    # enabled_when='settings_checked==True and docker_running==False',
    # image=get_icon(
    #         pkg_resources.resource_filename('resources',
    #             os.path.join('buttons', 'bidsapp-run.png'))))

    update_selection = Button()
    check = Button()
    start_bidsapp = Button()

    # stop_bidsapp = Action(name='Stop BIDS App!',action='stop_bids_app',enabled_when='handler.settings_checked and handler.docker_running')

    traits_view = QtView(Group(
        VGroup(
            VGroup(
                Item('bidsapp_tag', style='readonly', label='Tag'),
                label='BIDS App Version'),
            VGroup(
                Item('bids_root', style='readonly', label='Input directory'),
                Item('output_dir', style='simple', label='Output directory'),
                label='BIDS dataset'),
            VGroup(
                HGroup(
                    UItem('subjects',
                          editor=TabularEditor(
                              show_titles=True,
                              selected='list_of_subjects_to_be_processed',
                              editable=False,
                              multi_select=True,
                              adapter=MultiSelectAdapter(columns=[('Available labels', 'myvalue')]))
                          ),
                    UItem('list_of_subjects_to_be_processed',
                          editor=TabularEditor(
                              show_titles=True,
                              editable=False,
                              adapter=MultiSelectAdapter(columns=[('Labels to be processed', 'myvalue')]))
                          ),
                ),
                label='Participant labels to be processed'),
            HGroup(
                Item('number_of_participants_processed_in_parallel',
                     label='Number of participants processed in parallel'),
                label='Parallel processing'
            ),
            VGroup(
                HGroup(
                    VGroup(Item('number_of_threads',
                                label='Number of OpenMP threads'),
                           Item('fix_ants_number_of_threads',
                                label='Set number of threads used by ANTs'),
                           Item('ants_number_of_threads',
                                label='Number of ITK threads used by ANTs registration',
                                enabled_when='fix_ants_number_of_threads'),
                           label='Multithreading'),
                    VGroup(Item('fix_ants_random_seed',
                                label='Set seed of ANTS random number generator'),
                           Item('ants_random_seed',
                                label='Seed',
                                enabled_when='fix_ants_random_seed'),
                           Item('fix_mrtrix_random_seed',
                                label='Set seed of MRtrix random number generator'),
                           Item('mrtrix_random_seed',
                                label='Seed',
                                enabled_when='fix_mrtrix_random_seed'),
                           label='Random number generators'),
                ),
                label='Advanced execution settings for each participant process'
            ),
            VGroup(
                Group(Item('anat_config', label='Configuration file', visible_when='run_anat_pipeline'),
                      label='Anatomical pipeline'),
                Group(Item('run_dmri_pipeline', label='Run processing stages'),
                      Item('dmri_config', label='Configuration file',
                           visible_when='run_dmri_pipeline'),
                      label='Diffusion pipeline',
                      visible_when='dmri_inputs_checked==True'),
                Group(Item('run_fmri_pipeline', label='Run processing stages'),
                      Item('fmri_config', label='Configuration file',
                           visible_when='run_fmri_pipeline'),
                      label='fMRI pipeline',
                      visible_when='fmri_inputs_checked==True'),
                label='Configuration of processing pipelines'),
            VGroup(
                Item('fs_license', label='LICENSE'),
                # Item('fs_average', label='FSaverage directory'),
                label='Freesurfer configuration'),
            VGroup(
                Item('data_provenance_tracking', label='Use Datalad'),
                Item('datalad_update_environment', visible_when='data_provenance_tracking',
                     label='Update the computing environment (if existing)'),
                label='Data Provenance Tracking / Data Lineage',
                enabled_when='datalad_is_available'),
            orientation='vertical', springy=True),
        spring,
        HGroup(spring, Item('check', style='custom',
                            width=152, height=35, resizable=False,
                            label='', show_label=False,
                            style_sheet=return_button_style_sheet(
                                    ImageResource(
                                            pkg_resources.resource_filename(
                                                    'resources',
                                                    os.path.join('buttons', 'bidsapp-check-settings.png'))).absolute_path,
                                    152)
                            ),
               spring,
               Item('start_bidsapp', style='custom',
                    width=152, height=35, resizable=False,
                    label='', show_label=False,
                    style_sheet=return_button_style_sheet(
                            ImageResource(
                                    pkg_resources.resource_filename(
                                            'resources',
                                            os.path.join('buttons', 'bidsapp-run.png'))).absolute_path,
                            152),
                    enabled_when='settings_checked==True and docker_running==False'),
               spring,
               show_labels=False, label=""),
        orientation='vertical',
        springy=True),

        title='Connectome Mapper 3 BIDS App GUI',
        # kind='modal',
        handler=project.CMP_BIDSAppWindowHandler(),
        # style_sheet=style_sheet,
        buttons=[],
        # buttons = [check,start_bidsapp],
        # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
        # buttons = [preprocessing, map_connectome, map_custom],
        width=0.6, height=0.8, scrollable=True,  # , resizable=True
        icon=get_icon('bidsapp.png')
    )

    log_view = QtView(Group(
        Item('list_of_processing_logfiles'),
        orientation='vertical', springy=True),

        title='Connectome Mapper 3 BIDS App Progress',
        # kind='modal',
        # handler=project.CMP_BIDSAppWindowHandler(),
        # style_sheet=style_sheet,
        buttons=[],
        # buttons = [check,start_bidsapp],
        # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
        # buttons = [preprocessing, map_connectome, map_custom],
        width=0.5, height=0.8, resizable=True,  # , scrollable=True, resizable=True
        icon=get_icon('bidsapp.png')
    )

    def __init__(self, project_info=None, bids_root='', subjects=None, list_of_subjects_to_be_processed=None,
                 anat_config='', dmri_config='', fmri_config=''):
        """Constructor of an :class:``CMP_BIDSAppWindow`` instance.

        Parameters
        ----------
        project_info : cmp.project.CMP_Project_Info
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
        if multiprocessing.cpu_count() < 4:
            self.number_of_threads_max = multiprocessing.cpu_count()

        self.project_info = project_info
        self.bids_root = bids_root

        # Create a BIDSLayout for checking availability of dMRI and fMRI data
        try:
            bids_layout = BIDSLayout(self.bids_root)
        except Exception:
            print("Exception : Raised at BIDSLayout")
            sys.exit(1)

        # Check if dMRI data is available in the dataset
        dmri_pipeline = DiffusionPipeline(project_info)
        dmri_inputs_checked = dmri_pipeline.check_input(layout=bids_layout,
                                                        gui=False)

        if dmri_inputs_checked is not None:
            self.dmri_inputs_checked = dmri_inputs_checked
        else:
            self.dmri_inputs_checked = False

        # Check if fMRI data is available in the dataset
        fmri_pipeline = fMRIPipeline(project_info)
        fmri_inputs_checked = fmri_pipeline.check_input(layout=bids_layout,
                                                        gui=False,
                                                        debug=False)
        if fmri_inputs_checked is not None:
            self.fmri_inputs_checked = fmri_inputs_checked
        else:
            self.fmri_inputs_checked = False

        # Initialize output directory to be /bids_dir/derivatives
        self.output_dir = os.path.join(bids_root, 'derivatives')

        self.subjects = subjects
        # self.list_of_subjects_to_be_processed = list_of_subjects_to_be_processed
        self.anat_config = anat_config
        self.dmri_config = dmri_config
        self.fmri_config = fmri_config

        if 'FREESURFER_HOME' in os.environ:
            self.fs_license = os.path.join(
                os.environ['FREESURFER_HOME'], 'license.txt')
        else:
            print('Environment variable $FREESURFER_HOME not found')
            self.fs_license = ''
            print('Freesurfer license unset ({})'.format(self.fs_license))

        self.datalad_is_available = project.is_tool('datalad')

        self.on_trait_change(
            self.update_run_dmri_pipeline, 'run_dmri_pipeline')
        self.on_trait_change(
            self.update_run_fmri_pipeline, 'run_fmri_pipeline')

        self.on_trait_change(self.number_of_parallel_procs_updated,
                             'number_of_participants_processed_in_parallel')

        self.on_trait_change(self.update_checksettings,
                             'list_of_subjects_to_be_processed')
        self.on_trait_change(self.update_checksettings, 'anat_config')
        self.on_trait_change(self.update_checksettings, 'run_dmri_pipeline')
        self.on_trait_change(self.update_checksettings, 'dmri_config')
        self.on_trait_change(self.update_checksettings, 'run_fmri_pipeline')
        self.on_trait_change(self.update_checksettings, 'fmri_config')
        self.on_trait_change(self.update_checksettings, 'fs_license')
        # self.on_trait_change(self.update_checksettings, 'fs_average')

    def number_of_parallel_procs_updated(self, new):
        """Callback function when ``number_of_parallel_procs`` is updated."""
        number_of_threads_max = int((multiprocessing.cpu_count() - 1) / new)

        if number_of_threads_max > 4:
            self.number_of_threads_max = 4
        else:
            self.number_of_threads_max = number_of_threads_max

        print('Set number of threads max to : {}'.format(self.number_of_threads_max))

    def update_run_anat_pipeline(self, new):
        """Callback function when ``run_anat_pipeline`` is updated."""
        if new is False:
            print('At least anatomical pipeline should be run!')
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

    def _update_selection_fired(self):
        """Callback function when the list of selected subjects has been updated."""
        self.configure_traits(view='select_subjects_to_be_processed_view')

    def _check_fired(self):
        """Callback function when the Check Setting button is clicked."""
        self.check_settings()

    def _start_bidsapp_fired(self):
        """Callback function when the Run BIDS App button is clicked."""
        self.start_bids_app()

    def check_settings(self):
        """Checks if all the parameters of the BIDS App run are properly set before execution."""
        self.settings_checked = True

        if os.path.isdir(self.bids_root):
            print("BIDS root directory : {}".format(self.bids_root))
        else:
            print("Error: BIDS root invalid!")
            self.settings_checked = False

        if os.path.exists(os.path.join(self.output_dir, 'cmp')):
            print('Output directory (existing) : {}'.format(self.output_dir))
        else:
            os.makedirs(os.path.join(self.output_dir, 'cmp'))
            print('Output directory (created) : {}'.format(self.output_dir))

        if len(self.list_of_subjects_to_be_processed) > 0:
            print("Participant labels to be processed : {}".format(
                self.list_of_subjects_to_be_processed))
        else:
            print(
                "Error: At least one participant label to be processed should selected!")
            self.settings_checked = False
        # if not self.list_of_subjects_to_be_processed.empty():
        #     print("List of subjects to be processed : {}".format(self.list_of_subjects_to_be_processed))
        # else:
        #     print("Warning: List of subjects empty!")

        if os.path.isfile(self.anat_config):
            print("Anatomical configuration file : {}".format(self.anat_config))
        else:
            print("Error: Configuration file for anatomical pipeline not existing!")
            self.settings_checked = False

        if os.path.isfile(self.dmri_config):
            print("Diffusion configuration file : {}".format(self.dmri_config))
        else:
            print("Warning: Configuration file for diffusion pipeline not existing!")

        if os.path.isfile(self.fmri_config):
            print("fMRI configuration file : {}".format(self.fmri_config))
        else:
            print("Warning: Configuration file for fMRI pipeline not existing!")

        if os.path.isfile(self.fs_license):
            print("Freesurfer license : {}".format(self.fs_license))
        else:
            print("Error: Invalid Freesurfer license ({})!".format(self.fs_license))
            self.settings_checked = False

        # if os.path.isdir(self.fs_average):
        #     print("fsaverage directory : {}".format(self.fs_average))
        # else:
        #     print("Error: fsaverage directory ({}) not existing!".format(self.fs_average))
        #     self.settings_checked = False

        print("Valid inputs for BIDS App : {}".format(self.settings_checked))
        print("BIDS App Version Tag: {}".format(self.bidsapp_tag))
        print("Data provenance tracking (datalad) : {}".format(
            self.data_provenance_tracking))
        print("Update computing environment (datalad) : {}".format(
            self.datalad_update_environment))
        print("Number of participant processed in parallel : {}".format(
            self.number_of_participants_processed_in_parallel))
        print("Number of threads / participant : {}".format(self.number_of_threads))

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

        cmd = ['docker', 'run', '-it', '--rm',
               # '-v', '{}:/bids_dataset'.format(self.bids_root),
               # '-v', '{}/derivatives:/outputs'.format(self.bids_root),
               # '-v', '{}:/bids_dataset/derivatives/freesurfer/fsaverage'.format(self.fs_average),
               # '-v', '{}:/opt/freesurfer/license.txt'.format(self.fs_license),
               # '-v', '{}:/code/ref_anatomical_config.ini'.format(self.anat_config)
               '-v', '{}:/bids_dir'.format(self.bids_root),
               '-v', '{}:/output_dir'.format(self.output_dir),
               '-v', '{}:/bids_dir/code/license.txt'.format(self.fs_license),
               '-v', '{}:/code/ref_diffusion_config.ini'.format(self.anat_config),
               # '-v', '{}:/tmp/derivatives'.format(os.path.join(self.bids_root,'derivatives')),
               ]

        if self.run_dmri_pipeline:
            cmd.append('-v')
            cmd.append('{}:/code/ref_diffusion_config.ini'.format(self.dmri_config))

        if self.run_fmri_pipeline:
            cmd.append('-v')
            cmd.append('{}:/code/ref_fMRI_config.ini'.format(self.fmri_config))

        cmd.append('-u')
        cmd.append('{}:{}'.format(os.geteuid(), os.getegid()))

        cmd.append(
            'sebastientourbier/connectomemapper-bidsapp:{}'.format(bidsapp_tag))
        cmd.append('/bids_dir')
        cmd.append('/output_dir')
        cmd.append('participant')

        cmd.append('--participant_label')
        for label in participant_labels:
            cmd.append('{}'.format(label))

        cmd.append('--anat_pipeline_config')
        cmd.append('/bids_dir/code/ref_anatomical_config.ini')

        if self.run_dmri_pipeline:
            cmd.append('--dwi_pipeline_config')
            cmd.append('/bids_dir/code/ref_diffusion_config.ini')

        if self.run_fmri_pipeline:
            cmd.append('--func_pipeline_config')
            cmd.append('/bids_dir/code/ref_fMRI_config.ini')

        cmd.append('--fs_license')
        cmd.append('{}'.format('/bids_dir/code/license.txt'))

        cmd.append('--number_of_participants_processed_in_parallel')
        cmd.append('{}'.format(self.number_of_participants_processed_in_parallel))

        cmd.append('--number_of_threads')
        cmd.append('{}'.format(self.number_of_threads))

        if self.fix_ants_number_of_threads:
            cmd.append('--ants_number_of_threads')
            cmd.append('{}'.format(self.ants_number_of_threads))

        if self.fix_ants_random_seed:
            cmd.append('--ants_random_seed')
            cmd.append('{}'.format(self.ants_random_seed))

        if self.fix_mrtrix_random_seed:
            cmd.append('--mrtrix_random_seed')
            cmd.append('{}'.format(self.mrtrix_random_seed))

        print('... BIDS App execution command: {}'.format(cmd))

        # log_filename = os.path.join(
        #     self.bids_root, 'derivatives', 'cmp', 'main_log-cmpbidsapp.txt')

        # with open(log_filename, 'w+') as log:
        #     proc = Popen(cmd, stdout=log, stderr=log)
        #     #docker_process.communicate()

        proc = Popen(cmd)
        # proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        return proc

    def start_bidsapp_participant_level_process_with_datalad(self, bidsapp_tag, participant_labels):
        """Create and run the BIDS App command with Datalad.

        Parameters
        ----------
        bidsapp_tag : traits.Str
            Version tag of the CMP 3 BIDS App

        participant_labels : traits.List
            List of participants labels in the form ["01", "03", "04", ...]
        """
        cmd = ['datalad', 'containers-run', ]

        cmd.append('--container-name')
        cmd.append(
            'connectomemapper-bidsapp-{}'.format("-".join(bidsapp_tag.split("."))))

        cmd.append('-m')
        cmd.append(
            'Processing with connectomemapper-bidsapp {}'.format(bidsapp_tag))

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

        cmd.append('--input')
        cmd.append('code/ref_anatomical_config.ini')

        if self.run_dmri_pipeline:
            cmd.append('--input')
            cmd.append('code/ref_diffusion_config.ini')

        if self.run_fmri_pipeline:
            cmd.append('--input')
            cmd.append('code/ref_fMRI_config.ini')

        cmd.append('--output')
        cmd.append('derivatives')
        # for label in participant_labels:
        #     cmd.append('--input')
        #     cmd.append('{}'.format(label))

        cmd.append('/tmp')
        cmd.append('/tmp/derivatives')
        cmd.append('participant')

        cmd.append('--participant_label')
        for label in participant_labels:
            cmd.append('{}'.format(label))

        # Counter to track position of config file as --input
        i = 0
        cmd.append('--anat_pipeline_config')
        cmd.append('{{inputs[{}]}}'.format(i))
        i += 1
        if self.run_dmri_pipeline:
            cmd.append('--dwi_pipeline_config')
            cmd.append('{{inputs[{}]}}'.format(i))
            i += 1

        if self.run_fmri_pipeline:
            cmd.append('--func_pipeline_config')
            cmd.append('{{inputs[{}]}}'.format(i))

        print('... Datalad cmd : {}'.format(cmd))

        # log_filename = os.path.join(self.bids_root,'derivatives','cmp','main-datalad_log-cmpbidsapp.txt')

        # if not os.path.exists(os.path.join(self.bids_root,'derivatives','cmp')):
        #     os.makedirs(os.path.join(self.bids_root,'derivatives','cmp'))

        # with open(log_filename, 'a+') as log:
        #     proc = Popen(cmd, stdout=log, stderr=log, cwd=os.path.join(self.bids_root))
        #     #docker_process.communicate()

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
        process = Popen(command, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, shell=True,
                        env=merged_env, cwd=cwd)
        while True:
            line = process.stdout.readline()
            line = str(line)[:-1]
            print(line)
            if line == '' and process.poll() is not None:
                break
        if process.returncode != 0:
            raise Exception("Non zero return code: %d" % process.returncode)

    def start_bids_app(self):
        """Function executed when the Run BIDS App button is clicked.

        It implements all steps in the creation and execution of the BIDS App
        with or without datalad.
        """
        print("Start BIDS App")

        # Copy freesurfer license into dataset/code directory at the location
        # the BIDS app expects to find it.

        license_dst = os.path.join(self.bids_root, 'code', 'license.txt')

        if not os.access(license_dst, os.F_OK):
            dst = os.path.join(
                self.bids_root, 'code', 'license.txt')
            print('> Copy FreeSurfer license (BIDS App Manager) ')
            print('... src : {}'.format(self.fs_license))
            print('... dst : {}'.format(dst))
            shutil.copy2(src=self.fs_license, dst=dst)
        else:
            print(
                '> FreeSurfer license copy skipped as it already exists(BIDS App Manager) ')

        # project.fix_dataset_directory_in_pickles(
        #     local_dir=self.bids_root, mode='bidsapp')

        print("> Datalad available: {}".format(self.datalad_is_available))

        # self.datalad_is_available = False

        if self.datalad_is_available and self.data_provenance_tracking:
            # Detect structure subject/session
            session_structure = False
            res = glob.glob(os.path.join(self.bids_root, 'sub-*/*/anat'))
            # print(res)
            if len(res) > 0:
                session_structure = True
                print('    INFO : Subject/Session structure detected!')
            else:
                print('    INFO : Subject structure detected!')

            # Equivalent to:
            #    >> datalad create derivatives
            #    >> cd derivatives
            #    >> datalad containers-add connectomemapper-bidsapp-{} --url dhub://sebastientourbier/connectomemapper-bidsapp:{}
            if not os.path.isdir(os.path.join(self.bids_root, '.datalad')):
                cmd = 'datalad rev-create --force -D "Creation of datalad dataset to be processed by the connectome mapper bidsapp (tag:{})"'.format(
                    self.bidsapp_tag)
                try:
                    print('... cmd: {}'.format(cmd))
                    self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
                except Exception:
                    print("    DATALAD ERROR: Failed to create the datalad dataset")
            else:
                print("    INFO: A datalad dataset already exists!")

            # log_filename = os.path.join(self.bids_root,'derivatives','cmp','main-datalad_log-cmpbidsapp.txt')
            #
            # if not os.path.exists(os.path.join(self.bids_root,'derivatives','cmp')):
            #     os.makedirs(os.path.join(self.bids_root,'derivatives','cmp'))

            # create an empty log file to be tracked by datalad
            # f = open(log_filename,"w+")
            # f.close()

            cmd = 'datalad add -J {} -m "Modified configuration files tracked by datalad. Dataset ready to be linked with the BIDS App." .'.format(
                multiprocessing.cpu_count())
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    DATALAD ERROR: Failed to add changes to dataset")

            datalad_container = os.path.join(self.bids_root, '.datalad', 'environments',
                                             'connectomemapper-bidsapp-{}'.format(
                                                 "-".join(self.bidsapp_tag.split("."))), 'image')
            add_container = True
            if os.path.isdir(datalad_container):
                if self.datalad_update_environment:
                    print(
                        "    INFO: Container already listed in the datalad dataset and will be updated!")
                    shutil.rmtree(datalad_container)
                    add_container = True
                else:
                    add_container = False
                    print(
                        "    INFO: Container already listed in the datalad dataset and will NOT be updated!")
            else:
                add_container = True
                print(
                    "    INFO: Add a new computing environment (container image) to the datalad dataset!")

            if add_container:
                cmd = "datalad containers-add connectomemapper-bidsapp-{} --url dhub://sebastientourbier/connectomemapper-bidsapp:{}".format(
                    "-".join(self.bidsapp_tag.split(".")), self.bidsapp_tag)
                try:
                    print('... cmd: {}'.format(cmd))
                    self.run(cmd, env={}, cwd=os.path.join(self.bids_root))
                except Exception:
                    print(
                        "   DATALAD ERROR: Failed to link the container image to the dataset")

            # Implementation with --upgrade available in latest version but not
            # in stable version of datalad_container

            # cmd = "datalad containers-add connectomemapper-bidsapp-{}"
            # " --url dhub://sebastientourbier/connectomemapper-bidsapp:{} --update".format(
            #                                                                       self.bidsapp_tag,
            #                                                                       self.bidsapp_tag)
            #
            # try:
            #     print('... cmd: {}'.format(cmd))
            #     self.run(cmd, env={}, cwd=os.path.join(self.bids_root))
            # except Exception:
            #     print("   ERROR: Failed to link the container image to the datalad dataset")

            datalad_get_list = []

            datalad_get_list.append('code/ref_anatomical_config.ini')

            if self.run_dmri_pipeline:
                datalad_get_list.append('code/ref_diffusion_config.ini')

            if self.run_dmri_pipeline:
                datalad_get_list.append('code/ref_fMRI_config.ini')

            if session_structure:
                for label in self.list_of_subjects_to_be_processed:
                    datalad_get_list.append(
                        'sub-{}/ses-*/anat/sub-{}*_T1w.*'.format(label, label))
                    datalad_get_list.append(
                        'derivatives/freesurfer/sub-{}*/*'.format(label))
                    if self.run_dmri_pipeline:
                        datalad_get_list.append(
                            'sub-{}/ses-*/dwi/sub-{}*_dwi.*'.format(label, label))
                    if self.run_fmri_pipeline:
                        datalad_get_list.append(
                            'sub-{}/ses-*/func/sub-{}*_bold.*'.format(label, label))
            else:
                for label in self.list_of_subjects_to_be_processed:
                    datalad_get_list.append(
                        'sub-{}/anat/sub-{}*_T1w.*'.format(label, label))
                    datalad_get_list.append(
                        'derivatives/freesurfer/sub-{}/*'.format(label))
                    if self.run_dmri_pipeline:
                        datalad_get_list.append(
                            'sub-{}/dwi/sub-{}*_dwi.*'.format(label, label))
                    if self.run_fmri_pipeline:
                        datalad_get_list.append(
                            'sub-{}/func/sub-{}*_bold.*'.format(label, label))

            cmd = 'datalad add -J {} -m "Existing files tracked by datalad. Dataset ready for getting files via datalad run." .'.format(
                multiprocessing.cpu_count())
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    DATALAD ERROR: Failed to add existing files to dataset")

            cmd = 'datalad run -m "Get files for sub-{}" bash -c "datalad get {}"'.format(
                self.list_of_subjects_to_be_processed, " ".join(datalad_get_list))
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    DATALAD ERROR: Failed to get files (cmd: datalad get {})".format(
                    " ".join(datalad_get_list)))

            cmd = 'datalad add --nosave -J {} .'.format(
                multiprocessing.cpu_count())
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    DATALAD ERROR: Failed to add existing files to dataset")

            cmd = 'datalad save -m "Existing files tracked by datalad. Dataset ready for connectome mapping." --version-tag ready4analysis-{}'.format(
                time.strftime("%Y%m%d-%H%M%S"))
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    DATALAD ERROR: Failed to commit changes to dataset")

            # cmd = 'datalad diff --revision HEAD~1'
            # try:
            #     print('... cmd: {}'.format(cmd))
            #     self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            # except Exception:
            #     print("    DATALAD ERROR: Failed to run datalad diff --revision HEAD~1")

            cmd = 'datalad rev-status'
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    DATALAD ERROR: Failed to run datalad rev-status")

        # maxprocs = multiprocessing.cpu_count()
        processes = []

        self.docker_running = True

        if self.datalad_is_available and self.data_provenance_tracking:

            proc = self.start_bidsapp_participant_level_process_with_datalad(self.bidsapp_tag,
                                                                             self.list_of_subjects_to_be_processed)

        else:
            proc = self.start_bidsapp_participant_level_process(self.bidsapp_tag,
                                                                self.list_of_subjects_to_be_processed)

        processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        # project.fix_dataset_directory_in_pickles(
        #     local_dir=self.bids_root, mode='local')

        if self.datalad_is_available and self.data_provenance_tracking:
            # Clean remaining cache files generated in tmp/ of the docker image
            project.clean_cache(self.bids_root)

            cmd = 'datalad add --nosave -J {} .'.format(
                multiprocessing.cpu_count())
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    ERROR: Failed to add changes to datalad dataset")

            cmd = 'datalad save -m "Dataset processed by the connectomemapper-bidsapp:{}" --version-tag processed-{}'.format(
                self.bidsapp_tag, time.strftime("%Y%m%d-%H%M%S"))
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    ERROR: Failed to commit derivatives to datalad dataset")

            cmd = 'datalad diff --revision HEAD~1'
            try:
                print('... cmd: {}'.format(cmd))
                self.run(cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except Exception:
                print("    ERROR: Failed to run datalad diff --revision HEAD~1")

        print('Processing with BIDS App Finished')

        self.docker_running = False

        # cmd = ['docke datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return True

    # def stop_bids_app(self, ui_info):
    #     print("Stop BIDS App")
    #     #self.docker_process.kill()
    #     self.docker_running = False
    #     return True


class CMP_ConfiguratorWindow(HasTraits):
    """Class that defines the Configurator Window.

    Attributes
    ----------
    project_info : CMP_Project_Info
        Instance of :class:`CMP_Project_Info` that represents the processing project

    anat_pipeline : Instance(HasTraits)
        Instance of anatomical MRI pipeline UI

    dmri_pipeline : Instance(HasTraits)
        Instance of diffusion MRI pipeline UI

    fmri_pipeline : Instance(HasTraits)
        Instance of functional MRI pipeline UI

    anat_inputs_checked : traits.Bool
            Boolean that indicates if anatomical pipeline inputs are available
            (Default: False)

        dmri_inputs_checked = : traits.Bool
            Boolean that indicates if diffusion pipeline inputs are available
            (Default: False)

        fmri_inputs_checked : traits.Bool
            Boolean that indicates if functional pipeline inputs are available
            (Default: False)

    anat_save_config : traits.ui.Action
        TraitsUI Action to save the anatomical pipeline configuration

    dmri_save_config : traits.ui.Action
        TraitsUI Action to save the diffusion pipeline configuration

    fmri_save_config : traits.ui.Action
        TraitsUI Action to save the functional pipeline configuration

    save_all_config : traits.ui.Button
        Button to save all configuration files at once

    traits_view : QtView
        TraitsUI QtView that describes the content of the window
    """

    project_info = Instance(CMP_Project_Info)

    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    anat_inputs_checked = Bool(False)
    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    anat_save_config = Action(
        name='Save anatomical pipeline configuration as...', action='save_anat_config_file')
    dmri_save_config = Action(
        name='Save diffusion pipeline configuration as...', action='save_dmri_config_file')
    fmri_save_config = Action(
        name='Save fMRI pipeline configuration as...', action='save_fmri_config_file')

    # anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file')
    # dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='load_dmri_config_file')
    # fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='load_fmri_config_file')

    save_all_config = Button('')

    traits_view = QtView(
        Group(
            Group(
                Item('anat_pipeline', style='custom', show_label=False),
                label='Anatomical pipeline', dock='tab'),
            Group(
                Item('dmri_pipeline', style='custom', show_label=False,
                     enabled_when='dmri_inputs_checked', visible_when='dmri_inputs_checked'),
                label='Diffusion pipeline', dock='tab'),
            Group(
                Item('fmri_pipeline', style='custom', show_label=False,
                     enabled_when='fmri_inputs_checked', visible_when='fmri_inputs_checked'),
                label='fMRI pipeline', dock='tab'),
            orientation='horizontal', layout='tabbed',
            springy=True, enabled_when='anat_inputs_checked'),
        spring,
        HGroup(spring, Item('save_all_config',
                            style='custom',
                            width=315, height=35,
                            resizable=False,
                            label='',
                            show_label=False,
                            style_sheet=return_button_style_sheet(
                                ImageResource(
                                    pkg_resources.resource_filename(
                                        'resources',
                                        os.path.join('buttons', 'configurator-saveall.png'))).absolute_path,
                                315),
                            enabled_when='anat_inputs_checked==True'),
               spring,
               show_labels=False, label=""),
        title='Connectome Mapper 3 Configurator',
        menubar=MenuBar(
            Menu(
                ActionGroup(
                    anat_save_config,
                    dmri_save_config,
                    fmri_save_config),
                ActionGroup(
                    Action(name='Quit', action='_on_close')),
                name='File')),
        handler=project.CMP_ConfigQualityWindowHandler(),
        style_sheet=style_sheet,
        buttons=[],
        width=0.5, height=0.8, resizable=True,  # scrollable=True,
        icon=get_icon('configurator.png')
    )

    def __init__(self, project_info=None, anat_pipeline=None, dmri_pipeline=None, fmri_pipeline=None,
                 anat_inputs_checked=False, dmri_inputs_checked=False, fmri_inputs_checked=False):
        """Constructor of an :class:``CMP_ConfiguratorWindow`` instance.

        Parameters
        ----------
        project_info : cmp.project.CMP_Project_Info
            :class:`CMP_Project_Info` object (Default: None)

        anat_pipeline <cmp.bidsappmanager.pipelines.anatomical.AnatomicalPipelineUI>
            Instance of :class:`cmp.bidsappmanager.pipelines.anatomical.AnatomicalPipelineUI`
            (Default: None)

        dmri_pipeline <cmp.bidsappmanager.pipelines.diffusion.DiffusionPipelineUI>
            Instance of :class:`cmp.bidsappmanager.pipelines.diffusion.DiffusionPipelineUI`
            (Default: None)

        fmri_pipeline <cmp.bidsappmanager.pipelines.functional.fMRIPipelineUI>
            Instance of :class:`cmp.bidsappmanager.pipelines.functional.fMRIPipelineUI`
            (Default: None)

        anat_inputs_checked : traits.Bool
            Boolean that indicates if anatomical pipeline inputs are available
            (Default: False)

        dmri_inputs_checked = : traits.Bool
            Boolean that indicates if diffusion pipeline inputs are available
            (Default: False)

        fmri_inputs_checked : traits.Bool
            Boolean that indicates if functional pipeline inputs are available
            (Default: False)
        """
        self.project_info = project_info

        self.anat_pipeline = anat_pipeline
        self.dmri_pipeline = dmri_pipeline
        self.fmri_pipeline = fmri_pipeline

        if self.anat_pipeline is not None:
            self.anat_pipeline.view_mode = 'config_view'

        if self.dmri_pipeline is not None:
            self.dmri_pipeline.view_mode = 'config_view'

        if self.fmri_pipeline is not None:
            self.fmri_pipeline.view_mode = 'config_view'

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

    def update_diffusion_imaging_model(self, new):
        self.dmri_pipeline.diffusion_imaging_model = new

    def _save_all_config_fired(self):
        print('Saving pipeline configuration files...')

        if self.anat_inputs_checked:
            anat_config_file = os.path.join(
                self.project_info.base_directory, 'code', 'ref_anatomical_config.ini')
            project.anat_save_config(self.anat_pipeline, anat_config_file)
            print('Anatomical config saved as  {}'.format(anat_config_file))

        if self.dmri_inputs_checked:
            dmri_config_file = os.path.join(
                self.project_info.base_directory, 'code', 'ref_diffusion_config.ini')
            project.dmri_save_config(self.dmri_pipeline, dmri_config_file)
            print('Diffusion config saved as  {}'.format(dmri_config_file))

        if self.fmri_inputs_checked:
            fmri_config_file = os.path.join(
                self.project_info.base_directory, 'code', 'ref_fMRI_config.ini')
            project.fmri_save_config(self.fmri_pipeline, fmri_config_file)
            print('fMRI config saved as  {}'.format(fmri_config_file))


# Window class of the ConnectomeMapper_Pipeline Quality Inspector
#
class CMP_InspectorWindow(HasTraits):
    """Class that defines the Configurator Window.

    Attributes
    ----------
    project_info : CMP_Project_Info
        Instance of :class:`CMP_Project_Info` that represents the processing project

    anat_pipeline : Instance(HasTraits)
        Instance of anatomical MRI pipeline

    dmri_pipeline : Instance(HasTraits)
        Instance of diffusion MRI pipeline

    fmri_pipeline : Instance(HasTraits)
        Instance of functional MRI pipeline

    anat_inputs_checked : traits.Bool
        Indicates if inputs of anatomical pipeline are available 
        (Default: False)

    dmri_inputs_checked : traits.Bool
        Indicates if inputs of diffusion pipeline are available 
        (Default: False)

    fmri_inputs_checked : traits.Bool
        Indicates if inputs of functional pipeline are available 
        (Default: False)

    output_anat_available : traits.Bool
        Indicates if outputs of anatomical pipeline are available 
        (Default: False)

    output_dmri_available : traits.Bool
        Indicates if outputs of diffusion pipeline are available 
        (Default: False)

    output_fmri_available : traits.Bool
        Indicates if outputs of functional pipeline are available 
        (Default: False)

    traits_view : QtView
        TraitsUI QtView that describes the content of the window
    """

    project_info = Instance(CMP_Project_Info)

    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    anat_inputs_checked = Bool(False)
    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    output_anat_available = Bool(False)
    output_dmri_available = Bool(False)
    output_fmri_available = Bool(False)

    traits_view = QtView(Group(
        # Group(
        #     # Include('dataset_view'),label='Data manager',springy=True
        #     Item('project_info',style='custom',show_label=False),label='Data manager',springy=True, dock='tab'
        # ),
        Group(
            Item('anat_pipeline', style='custom', show_label=False), visible_when='output_anat_available',
            label='Anatomical pipeline', dock='tab'
        ),
        Group(
            Item('dmri_pipeline', style='custom', show_label=False,
                 visible_when='output_dmri_available'),
            label='Diffusion pipeline', dock='tab'
        ),
        Group(
            Item('fmri_pipeline', style='custom', show_label=False,
                 visible_when='output_fmri_available'),
            label='fMRI pipeline', dock='tab'
        ),
        orientation='horizontal', layout='tabbed', springy=True, enabled_when='output_anat_available'),
        title='Connectome Mapper 3 Inspector',
        menubar=MenuBar(
            Menu(
                ActionGroup(
                    Action(name='Quit', action='_on_close'),
                ),
                name='File'),
    ),
        handler=project.CMP_ConfigQualityWindowHandler(),
        style_sheet=style_sheet,
        width=0.5, height=0.8, resizable=True,  # scrollable=True,
        icon=get_icon('qualitycontrol.png')
    )

    error_msg = Str('')
    error_view = View(
        Group(
            Item('error_msg', style='readonly', show_label=False),
        ),
        title='Error',
        kind='modal',
        # style_sheet=style_sheet,
        buttons=['OK'])

    def __init__(self, project_info=None, anat_inputs_checked=False, dmri_inputs_checked=False,
                 fmri_inputs_checked=False):
        """Constructor of an :class:``CMP_ConfiguratorWindow`` instance.

        Parameters
        ----------
        project_info : cmp.project.CMP_Project_Info
            :class:`CMP_Project_Info` object (Default: None)

        anat_inputs_checked : traits.Bool
            Boolean that indicates if anatomical pipeline inputs are available
            (Default: False)

        dmri_inputs_checked = : traits.Bool
            Boolean that indicates if diffusion pipeline inputs are available
            (Default: False)

        fmri_inputs_checked : traits.Bool
            Boolean that indicates if functional pipeline inputs are available
            (Default: False)
        """
        self.project_info = project_info

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        print('Fix BIDS root directory to {}'.format(
            self.project_info.base_directory))

        # project.fix_dataset_directory_in_pickles(
        #     local_dir=self.project_info.base_directory, mode='newlocal')

        aborded = self.select_subject()

        if aborded:
            raise Exception(
                'ABORDED: The quality control window will not be displayed.'
                'Selection of subject/session was cancelled at initialization.')

    def select_subject(self):
        """Function to select the subject and session for which to inspect outputs."""
        valid_selected_subject = False
        select = True
        aborded = False

        while not valid_selected_subject and not aborded:

            # Select subject from BIDS dataset
            np_res = self.project_info.configure_traits(view='subject_view')

            if not np_res:
                aborded = True
                break

            print("Selected subject: {}".format(self.project_info.subject))

            # Select session if any
            bids_layout = BIDSLayout(self.project_info.base_directory)
            subject = self.project_info.subject.split('-')[1]

            sessions = bids_layout.get(
                target='session', return_type='id', subject=subject)

            if len(sessions) > 0:
                print("Detected sessions")
                print(sessions)

                self.project_info.subject_sessions = []

                for ses in sessions:
                    self.project_info.subject_sessions.append(
                        'ses-' + str(ses))

                np_res = self.project_info.configure_traits(
                    view='subject_session_view')

                if not np_res:
                    aborded = True
                    break

                self.project_info.anat_config_file = os.path.join(self.project_info.base_directory, 'derivatives',
                                                                  'cmp', '{}'.format(
                                                                      self.project_info.subject),
                                                                  '{}'.format(
                                                                      self.project_info.subject_session),
                                                                  '{}_{}_anatomical_config.ini'.format(
                                                                      self.project_info.subject,
                                                                      self.project_info.subject_session))
                if os.access(self.project_info.anat_config_file, os.F_OK):
                    print("> Initialize anatomical pipeline")
                    self.anat_pipeline = project.init_anat_project(
                        self.project_info, False)
                else:
                    self.anat_pipeline = None

                if self.dmri_inputs_checked:
                    self.project_info.dmri_config_file = os.path.join(self.project_info.base_directory, 'derivatives',
                                                                      'cmp', '{}'.format(
                                                                          self.project_info.subject),
                                                                      '{}'.format(
                                                                          self.project_info.subject_session),
                                                                      '{}_{}_diffusion_config.ini'.format(
                                                                          self.project_info.subject,
                                                                          self.project_info.subject_session))
                    if os.access(self.project_info.dmri_config_file, os.F_OK):
                        print("> Initialize diffusion pipeline")
                        dmri_valid_inputs, self.dmri_pipeline = project.init_dmri_project(self.project_info,
                                                                                          bids_layout, False)
                    else:
                        self.dmri_pipeline = None

                    # self.dmri_pipeline.subject = self.project_info.subject
                    # self.dmri_pipeline.global_conf.subject = self.project_info.subject

                if self.fmri_inputs_checked:
                    self.project_info.fmri_config_file = os.path.join(self.project_info.base_directory, 'derivatives',
                                                                      'cmp', '{}'.format(
                                                                          self.project_info.subject),
                                                                      '{}'.format(
                                                                          self.project_info.subject_session),
                                                                      '{}_{}_fMRI_config.ini'.format(
                                                                          self.project_info.subject,
                                                                          self.project_info.subject_session))
                    if os.access(self.project_info.fmri_config_file, os.F_OK):
                        print("> Initialize fMRI pipeline")
                        fmri_valid_inputs, self.fmri_pipeline = project.init_fmri_project(self.project_info,
                                                                                          bids_layout, False)
                    else:
                        self.fmri_pipeline = None

                    # self.fmri_pipeline.subject = self.project_info.subject
                    # self.fmri_pipeline.global_conf.subject = self.project_info.subject

                # self.anat_pipeline.global_conf.subject_session = self.project_info.subject_session

                # if self.dmri_pipeline is not None:
                #     self.dmri_pipeline.global_conf.subject_session = self.project_info.subject_session
                #
                # if self.fmri_pipeline is not None:
                #     self.fmri_pipeline.global_conf.subject_session = self.project_info.subject_session

                print("Selected session %s" %
                      self.project_info.subject_session)
                if self.anat_pipeline is not None:
                    self.anat_pipeline.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(
                        self.project_info.base_directory, 'derivatives', 'freesurfer',
                        '{}_{}'.format(self.project_info.subject, self.project_info.subject_session))
            else:
                print("No session detected")
                self.project_info.anat_config_file = os.path.join(self.project_info.base_directory, 'derivatives',
                                                                  'cmp', '{}'.format(
                                                                      self.project_info.subject),
                                                                  '{}_anatomical_config.ini'.format(
                                                                      self.project_info.subject))
                if os.access(self.project_info.anat_config_file, os.F_OK):
                    self.anat_pipeline = project.init_anat_project(
                        self.project_info, False)
                else:
                    self.anat_pipeline = None

                if self.dmri_inputs_checked:
                    self.project_info.dmri_config_file = os.path.join(self.project_info.base_directory, 'derivatives',
                                                                      'cmp', '{}'.format(
                                                                          self.project_info.subject),
                                                                      '{}_diffusion_config.ini'.format(
                                                                          self.project_info.subject))
                    if os.access(self.project_info.dmri_config_file, os.F_OK):
                        dmri_valid_inputs, self.dmri_pipeline = project.init_dmri_project(self.project_info,
                                                                                          bids_layout, False)
                    else:
                        self.dmri_pipeline = None

                    # self.dmri_pipeline.subject = self.project_info.subject
                    # self.dmri_pipeline.global_conf.subject = self.project_info.subject

                if self.fmri_inputs_checked:
                    self.project_info.fmri_config_file = os.path.join(self.project_info.base_directory, 'derivatives',
                                                                      'cmp', '{}'.format(
                                                                          self.project_info.subject),
                                                                      '{}_fMRI_config.ini'.format(
                                                                          self.project_info.subject))
                    if os.access(self.project_info.fmri_config_file, os.F_OK):
                        fmri_valid_inputs, self.fmri_pipeline = project.init_fmri_project(self.project_info,
                                                                                          bids_layout, False)
                    else:
                        self.fmri_pipeline = None

                    # self.fmri_pipeline.subject = self.project_info.subject
                    # self.fmri_pipeline.global_conf.subject = self.project_info.subject

                # self.anat_pipeline.global_conf.subject_session = ''
                if self.anat_pipeline is not None:
                    self.anat_pipeline.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(
                        self.project_info.base_directory, 'derivatives', 'freesurfer',
                        '{}'.format(self.project_info.subject))

            print("[PIPELINE INIT DONE]")

            if self.anat_pipeline is not None:
                print("> Anatomical pipeline output inspection")
                self.anat_pipeline.view_mode = 'inspect_outputs_view'
                for stage in list(self.anat_pipeline.stages.values()):
                    print("  ... Inspect stage {}".format(stage))
                    stage.define_inspect_outputs()
                    # print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (stage.inspect_outputs[0] != 'Outputs not available'):
                        self.output_anat_available = True

            if self.dmri_pipeline is not None:
                print("> Diffusion pipeline output inspection")
                self.dmri_pipeline.view_mode = 'inspect_outputs_view'
                for stage in list(self.dmri_pipeline.stages.values()):
                    print("  ... Inspect stage {}".format(stage))
                    stage.define_inspect_outputs()
                    # print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (stage.inspect_outputs[0] != 'Outputs not available'):
                        self.output_dmri_available = True

            if self.fmri_pipeline is not None:
                print("> fMRI pipeline output inspection")
                self.fmri_pipeline.view_mode = 'inspect_outputs_view'
                for stage in list(self.fmri_pipeline.stages.values()):
                    print("  ... Inspect stage {}".format(stage))
                    stage.define_inspect_outputs()
                    # print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (stage.inspect_outputs[0] != 'Outputs not available'):
                        self.output_fmri_available = True

            print("Anatomical output(s) available : %s" %
                  self.output_anat_available)
            print("Diffusion output(s) available : %s" %
                  self.output_dmri_available)
            print("fMRI output(s) available : %s" % self.output_fmri_available)

            if self.output_anat_available or self.output_dmri_available or self.output_fmri_available:
                valid_selected_subject = True
            else:
                self.error_msg = "No output available! Please select another subject (and session if any)!"

                select = error(message=self.error_msg,
                               title='Error', buttons=['OK', 'Cancel'])
                aborded = not select

        return aborded

    def update_diffusion_imaging_model(self, new):
        """Function called when ``diffusion_imaging_model`` is updated."""
        self.dmri_pipeline.diffusion_imaging_model = new


class CMP_MainWindow(HasTraits):
    """Class that defines the Main window of the Connectome Mapper 3 GUI.

    Attributes
    ----------
    project_info : CMP_Project_InfoUI
        Instance of :class:`CMP_Project_InfoUI` that represents the processing project

    anat_pipeline : Instance(HasTraits)
        Instance of anatomical MRI pipeline UI

    dmri_pipeline : Instance(HasTraits)
        Instance of diffusion MRI pipeline UI

    fmri_pipeline : Instance(HasTraits)
        Instance of functional MRI pipeline UI

    bidsapp_ui : CMP_Project_Info
        Instance of :class:`CMP_BIDSAppWindow`

    load_dataset : traits.ui.Action
        TraitsUI Action to load a BIDS dataset

    bidsapp : traits.ui.Button
        Button that displays the BIDS App Interface window

    configurator : traits.ui.Button
        Button thats displays the pipeline Configurator window

    quality_control : traits.ui.Button
        Button that displays the pipeline Quality Control / Inspector window

    manager_group : traits.ui.View
        TraitsUI View that describes the content of the main window

    traits_view : QtView
        TraitsUI QtView that includes ``manager_group`` and parameterize 
        the window with menu
    """

    project_info = Instance(CMP_Project_Info)

    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    # configurator_ui = Instance(CMP_PipelineConfigurationWindow)
    bidsapp_ui = Instance(CMP_BIDSAppWindow)
    # quality_control_ui = Instance(CMP_QualityControlWindow)

    load_dataset = Action(name='Load BIDS Dataset...', action='load_dataset')

    project_info.style_sheet = style_sheet

    configurator = Button('')
    bidsapp = Button('')
    quality_control = Button('')

    view_mode = 1

    manager_group = VGroup(
        spring,
        HGroup(
            spring,
            HGroup(
                Item('configurator', style='custom', width=200, height=200, resizable=False, label='', show_label=False,
                     # editor_args={
                     #     'image': get_icon(pkg_resources.resource_filename('cmp',
                     #                                                       os.path.join('bidsappmanager/images',
                     #                                                                    'configurator_200x200.png'))),
                     #     'label': "", 'label_value': ""},
                     style_sheet=return_button_style_sheet(
                             ImageResource(
                                     pkg_resources.resource_filename('cmp',
                                                                     os.path.join('bidsappmanager/images',
                                                                                  'configurator_200x200.png'))).absolute_path,
                             200)
                     ),
                show_labels=False, label=""),
            spring,
            HGroup(Item('bidsapp', style='custom', width=200, height=200, resizable=False,
                        style_sheet=return_button_style_sheet(
                                ImageResource(
                                        pkg_resources.resource_filename('cmp',
                                                                        os.path.join('bidsappmanager/images',
                                                                                     'bidsapp_200x200.png'))).absolute_path,
                                200)
                        ),
                   show_labels=False, label=""),
            spring,
            HGroup(Item('quality_control', style='custom', width=200, height=200, resizable=False,
                        style_sheet=return_button_style_sheet(
                                ImageResource(
                                        pkg_resources.resource_filename('cmp',
                                                                        os.path.join('bidsappmanager/images',
                                                                                     'qualitycontrol_200x200.png'))).absolute_path,
                                200)
                        ),
                   show_labels=False, label=""),
            spring,
            springy=True, visible_when='handler.project_loaded==True'),
        spring,
        springy=True)

    traits_view = QtView(
        HGroup(
            Include('manager_group'),
        ),
        title='Connectome Mapper {} - BIDS App Manager'.format(__version__),
        menubar=MenuBar(
            Menu(
                ActionGroup(
                    load_dataset,
                ),
                ActionGroup(
                    Action(name='Quit', action='_on_close'),
                ),
                name='File'),
        ),
        handler=project.CMP_MainWindowHandler(),
        style_sheet=style_sheet,
        width=0.5, height=0.8, resizable=True,  # , scrollable=True , resizable=True
        icon=get_icon('cmp.png')
    )

    def _bidsapp_fired(self):
        """ Callback of the "bidsapp" button. This displays the BIDS App Interface window."""
        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        anat_config = os.path.join(
            self.project_info.base_directory, 'code/', 'ref_anatomical_config.ini')
        dmri_config = os.path.join(
            self.project_info.base_directory, 'code/', 'ref_diffusion_config.ini')
        fmri_config = os.path.join(
            self.project_info.base_directory, 'code/', 'ref_fMRI_config.ini')

        self.bidsapp_ui = CMP_BIDSAppWindow(project_info=self.project_info,
                                            bids_root=self.project_info.base_directory,
                                            subjects=subjects,
                                            list_of_subjects_to_be_processed=subjects,
                                            # anat_config=self.project_info.anat_config_file,
                                            # dmri_config=self.project_info.dmri_config_file,
                                            # fmri_config=self.project_info.fmri_config_file
                                            anat_config=anat_config,
                                            dmri_config=dmri_config,
                                            fmri_config=fmri_config
                                            )
        self.bidsapp_ui.configure_traits()

    def _configurator_fired(self):
        """Callback of the "configurator" button. This displays the Configurator Window."""
        if self.project_info.t1_available:
            if os.path.isfile(self.project_info.anat_config_file):
                print("Anatomical config file : %s" %
                      self.project_info.anat_config_file)

        if self.project_info.dmri_available:
            if os.path.isfile(self.project_info.dmri_config_file):
                print("Diffusion config file : %s" %
                      self.project_info.dmri_config_file)

        if self.project_info.fmri_available:
            if os.path.isfile(self.project_info.fmri_config_file):
                print("fMRI config file : %s" %
                      self.project_info.fmri_config_file)

        self.configurator_ui = CMP_ConfiguratorWindow(project_info=self.project_info,
                                                      anat_pipeline=self.anat_pipeline,
                                                      dmri_pipeline=self.dmri_pipeline,
                                                      fmri_pipeline=self.fmri_pipeline,
                                                      anat_inputs_checked=self.project_info.t1_available,
                                                      dmri_inputs_checked=self.project_info.dmri_available,
                                                      fmri_inputs_checked=self.project_info.fmri_available
                                                      )

        self.configurator_ui.configure_traits()

    def _quality_control_fired(self):
        """Callback of the "Inspector" button. This displays the Quality Control (Inspector) Window."""
        if self.project_info.t1_available:
            if os.path.isfile(self.project_info.anat_config_file):
                print("Anatomical config file : %s" %
                      self.project_info.anat_config_file)

        if self.project_info.dmri_available:
            if os.path.isfile(self.project_info.dmri_config_file):
                print("Diffusion config file : %s" %
                      self.project_info.dmri_config_file)

        if self.project_info.fmri_available:
            if os.path.isfile(self.project_info.fmri_config_file):
                print("fMRI config file : %s" %
                      self.project_info.fmri_config_file)

        try:
            self.quality_control_ui = CMP_InspectorWindow(project_info=self.project_info,
                                                          anat_inputs_checked=self.project_info.t1_available,
                                                          dmri_inputs_checked=self.project_info.dmri_available,
                                                          fmri_inputs_checked=self.project_info.fmri_available
                                                          )
            self.quality_control_ui.configure_traits()
        except Exception as e:
            print(e)

    def show_bidsapp_interface(self):
        """Callback of the "BIDS App" button. This displays the BIDS App Interface Window."""
        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        anat_config = os.path.join(
            self.project_info.base_directory, 'code/', 'ref_anatomical_config.ini')
        dmri_config = os.path.join(
            self.project_info.base_directory, 'code/', 'ref_diffusion_config.ini')
        fmri_config = os.path.join(
            self.project_info.base_directory, 'code/', 'ref_fMRI_config.ini')

        self.bidsapp = CMP_BIDSAppWindow(project_info=self.project_info,
                                         bids_root=self.project_info.base_directory,
                                         subjects=subjects,
                                         list_of_subjects_to_be_processed=subjects,
                                         anat_config=anat_config,
                                         dmri_config=dmri_config,
                                         fmri_config=fmri_config
                                         )
        # self.bidsapp.configure_traits()
