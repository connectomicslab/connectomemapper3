# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper GUI
"""

# Remove warnings visible whenever you import scipy (or another package) that was compiled against an older numpy than is installed.
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

# Libraries imports
import sys
import os
import glob
import time
import shutil
import multiprocessing
import subprocess
from subprocess import Popen
import pkg_resources

import gzip
import pickle
import string

from traits.api import *
from traitsui.api import *
from traitsui.tabular_adapter import TabularAdapter
from traitsui.qt4.extra.qt_view import QtView
from pyface.api import ImageResource

from bids import BIDSLayout

# CMP imports
from cmp.info import __version__
import cmp.bidsappmanager.project as project

global modal_width
modal_width = 300

global style_sheet
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
                min-width: 5px;
                icon-size: 415px;
                font: 12pt "Verdana";
                margin: 5px 5px 5px 5px;
                padding:1px 1px;
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
                width: 10px; /* when vertical */
                height: 10px; /* when horizontal */
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

# QDockWidget {
#     border: 1px solid lightgray;
#     titlebar-close-icon: url(close.png);
#     titlebar-normal-icon: url(undock.png);
# }
#
# QDockWidget::title {
#     text-align: left; /* align the text to the left */
#     background: lightgray;
#     padding-left: 5px;
# }
#
# QDockWidget::close-button, QDockWidget::float-button {
#     border: 1px solid transparent;
#     background: darkgray;
#     padding: 0px;
# }
#
# QDockWidget::close-button:hover, QDockWidget::float-button:hover {
#     background: gray;
# }
#
# QDockWidget::close-button:pressed, QDockWidget::float-button:pressed {
#     padding: 1px -1px -1px 1px;
# }

class CMP_Project_Info(HasTraits):
    base_directory = Directory

    bids_layout = Instance(BIDSLayout)
    subjects = List([])
    subject = Enum(values='subjects')

    number_of_subjects = Int()

    subject_sessions = List([])
    subject_session = Enum(values='subject_sessions')

    #current_subj = Str()
    anat_warning_msg = Str('\nWarning: selected directory is already configured for anatomical data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    dmri_warning_msg = Str('\nWarning: selected directory is already configured for diffusion data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    fmri_warning_msg = Str('\nWarning: selected directory is already configured for resting-state data processing.\n\nDo you want to reset the configuration to default parameters ?\n')

    #process_type = Enum('diffusion',['diffusion','fMRI'])
    diffusion_imaging_model = Enum('DTI',['DSI','DTI','HARDI'])
    dmri_bids_acqs = List()
    dmri_bids_acq = Enum(values='dmri_bids_acqs')

    anat_runs = List()
    anat_run = Enum(values='anat_runs')

    dmri_runs = List()
    dmri_run = Enum(values='dmri_runs')

    fmri_runs = List()
    fmri_run = Enum(values='fmri_runs')

    parcellation_scheme = Str('Lausanne2008')
    atlas_info = Dict()
    freesurfer_subjects_dir = Str('')
    freesurfer_subject_id = Str('')

    pipeline_processing_summary = List()

    t1_available = Bool(False)
    dmri_available = Bool(False)
    fmri_available = Bool(False)

    anat_config_error_msg = Str('')
    anat_config_to_load = Str()
    anat_available_config = List()
    anat_config_to_load_msg = Str('Several configuration files available. Select which one to load:\n')
    anat_last_date_processed = Str('Not yet processed')
    anat_last_stage_processed = Str('Not yet processed')

    anat_stage_names = List
    anat_custom_last_stage = Str

    dmri_config_error_msg = Str('')
    dmri_config_to_load = Str()
    dmri_available_config = List()
    dmri_config_to_load_msg = Str('Several configuration files available. Select which one to load:\n')
    dmri_last_date_processed = Str('Not yet processed')
    dmri_last_stage_processed = Str('Not yet processed')

    dmri_stage_names = List
    dmri_custom_last_stage = Str

    fmri_config_error_msg = Str('')
    fmri_config_to_load = Str()
    fmri_available_config = List()
    fmri_config_to_load_msg = Str('Several configuration files available. Select which one to load:\n')
    fmri_last_date_processed = Str('Not yet processed')
    fmri_last_stage_processed = Str('Not yet processed')

    fmri_stage_names = List
    fmri_custom_last_stage = Str

    number_of_cores = Enum(1,range(1,multiprocessing.cpu_count()+1))

    summary_view_button = Button('Pipeline processing summary')

    pipeline_processing_summary_view = VGroup(
                                            Item('pipeline_processing_summary'),
                                            )
    dataset_view = VGroup(
                        VGroup(
                            HGroup(
                                # '20',Item('base_directory',width=-0.3,height=-0.2, style='custom',show_label=False,resizable=True),
                                Item('base_directory',width=-0.3,style='readonly',label="",resizable=True),
                                Item('number_of_subjects',width=-0.3,style='readonly',label="Number of participants",resizable=True),
                                'summary_view_button',
                                ),
                            # HGroup(subj
                            #     '20',Item('root',editor=TreeEditor(editable=False, auto_open=1),show_label=False,resizable=True)
                            #     ),
                        label='BIDS Dataset',
                        ),
                        spring,
                        HGroup(
                            Group(
                            Item('subject',style='simple',show_label=True,resizable=True),
                            ),
                            Group(
                            Item('subject_session',style='simple',label="Session",resizable=True),
                            visible_when='subject_session!=""'),
                            springy = True
                        ),
                        spring,
                        Group(
                            Item('t1_available',style='readonly',label='T1',resizable=True),
                            HGroup(
                                Item('dmri_available',style='readonly',label='Diffusion',resizable=True),
                                Item('diffusion_imaging_model',label='Model',resizable=True,enabled_when='dmri_available'),
                                ),
                            Item('fmri_available',style='readonly',label='BOLD',resizable=True),
                            # Item('t1_available',style='readonly',label='T1',resizable=True),
                            label='Modalities'
                        ),
                        spring,
                        Group(

                            Item('anat_last_date_processed',label="Anatomical pipeline", style='readonly',resizable=True,enabled_when='t1_available'),

                            Item('dmri_last_date_processed',label="Diffusion pipeline",style='readonly',resizable=True,enabled_when='dmri_available'),

                            Item('fmri_last_date_processed',label="fMRI pipeline",style='readonly',resizable=True,enabled_when='fmri_available'),

                            label="Last date processed"
                        ),
                        spring,
                        Group(
                            Item('number_of_cores',resizable=True),
                            label='Processing configuration'
                        ),
                        '550',
                        spring,
                        springy=True)


    traits_view = QtView(Include('dataset_view'))

    create_view = View( #Item('process_type',style='custom'),Item('diffusion_imaging_model',style='custom',visible_when='process_type=="diffusion"'),
                        Group(
                            Item('base_directory',label='BIDS Dataset'),
                            ),
                        kind='livemodal',
                        title='Data creation: BIDS dataset selection',
                        #style_sheet=style_sheet,
                        width=modal_width,
                        buttons=['OK','Cancel'])

    subject_view = View(
                        Group(
                            Item('subject',label='Selected Subject'),
                            # Item('session',label='Session to be processed'),
                            # Item('diffusion_imaging_model',style='custom'),
                            ),
                        kind='modal',
                        title='Subject and session selection',
                        #style_sheet=style_sheet,
                        width=modal_width,
                        buttons=['OK','Cancel'])

    subject_session_view = View(
                        Group(
                            Item('subject_session',label='Selected Session'),
                            ),
                        kind='modal',
                        title='Session selection (subject: %s)'% subject,
                        #style_sheet=style_sheet,
                        width=modal_width,
                        buttons=['OK','Cancel'])

    dmri_bids_acq_view = View(
                        Group(
                            Item('dmri_bids_acq',label='Selected model'),
                            ),
                        kind='modal',
                        title='Selection of diffusion acquisition model',
                        #style_sheet=style_sheet,
                        width=modal_width,
                        buttons=['OK','Cancel'])

    anat_warning_view = View(
                        Group(
                            Item('anat_warning_msg',style='readonly',show_label=False),
                            ),
                        title='Warning : Anatomical T1w data',
                        kind='modal',
                        width=modal_width,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    anat_config_error_view = View(
                            Group(
                                Item('anat_config_error_msg', style='readonly',show_label=False),
                                ),
                            title='Error',
                            kind = 'modal',
                            width=modal_width,
                            #style_sheet=style_sheet,
                            buttons=['OK','Cancel'])

    dmri_warning_view = View(
                        Group(
                            Item('dmri_warning_msg',style='readonly',show_label=False),
                            ),
                        title='Warning : Diffusion MRI data',
                        kind='modal',
                        width=modal_width,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    dmri_config_error_view = View(
                            Group(
                                Item('dmri_config_error_msg', style='readonly',show_label=False),
                                ),
                            title='Error',
                            kind = 'modal',
                            width=modal_width,
                            #style_sheet=style_sheet,
                            buttons=['OK','Cancel'])

    fmri_warning_view = View(
                        Group(
                            Item('fmri_warning_msg',style='readonly',show_label=False),
                            ),
                        title='Warning : fMRI data',
                        kind='modal',
                        width=modal_width,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    fmri_config_error_view = View(
                            Group(
                                Item('fmri_config_error_msg', style='readonly',show_label=False),
                                ),
                            title='Error',
                            kind = 'modal',
                            width=modal_width,
                            #style_sheet=style_sheet,
                            buttons=['OK','Cancel'])

    open_view = View(
                    Group(
                        Item('base_directory',label='BIDS Dataset'),
                        ),
                    title='Data loading: BIDS dataset selection',
                    kind='modal',
                    width=modal_width,
                    #style_sheet=style_sheet,
                    buttons=['OK','Cancel'])

    anat_select_config_to_load = View(
                                  Group(
                                      Item('anat_config_to_load_msg',style='readonly',show_label=False),
                                      Item('anat_config_to_load',style='custom',editor=EnumEditor(name='anat_available_config'),show_label=False),
                                      ),
                                  title='Select configuration for anatomical pipeline',
                                  kind='modal',
                                  width=modal_width,
                                  #style_sheet=style_sheet,
                                  buttons=['OK','Cancel'])

    anat_custom_map_view = View(
                        Group(
                            Item('anat_custom_last_stage',editor=EnumEditor(name='anat_stage_names'),style='custom',show_label=False),
                            ),
                        title='Select until which stage to process the anatomical pipeline.',
                        kind='modal',
                        width=modal_width,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    diffusion_imaging_model_select_view = View(
                                                Group(
                                                    Item('diffusion_imaging_model',label='Diffusion MRI modality'),
                                                    ),
                                                title='Please select diffusion MRI modality',
                                                kind='modal',
                                                width=modal_width,
                                                buttons=['OK','Cancel'])

    dmri_select_config_to_load = View(
                                Group(
                                    Item('dmri_config_to_load_msg',style='readonly',show_label=False),
                                    ),
                                Item('dmri_config_to_load',style='custom',editor=EnumEditor(name='dmri_available_config'),show_label=False),
                                title='Select configuration for diffusion pipeline',
                                kind='modal',
                                width=modal_width,
                                #style_sheet=style_sheet,
                                buttons=['OK','Cancel'])

    dmri_custom_map_view = View(
                        Group(
                            Item('dmri_custom_last_stage',editor=EnumEditor(name='dmri_stage_names'),style='custom',show_label=False),
                            ),
                        title='Select until which stage to process the diffusion pipeline.',
                        kind='modal',
                        width=modal_width,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    fmri_select_config_to_load = View(
                                Group(
                                    Item('fmri_config_to_load_msg',style='readonly',show_label=False),
                                    ),
                                Item('fmri_config_to_load',style='custom',editor=EnumEditor(name='fmri_available_config'),show_label=False),
                                title='Select configuration for fMRI pipeline',
                                kind='modal',
                                width=modal_width,
                                #style_sheet=style_sheet,
                                buttons=['OK','Cancel'])

    fmri_custom_map_view = View(
                        Group(
                            Item('fmri_custom_last_stage',editor=EnumEditor(name='fmri_stage_names'),style='custom',show_label=False),
                            ),
                        title='Select until which stage to process the fMRI pipeline.',
                        kind='modal',
                        width=modal_width,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    def _summary_view_button_fired(self):
        self.configure_traits(view='pipeline_processing_summary_view')

class MultiSelectAdapter(TabularAdapter):
    """ This adapter is used by both the left and right tables
    """

    # Titles and column names for each column of a table.
    # In this example, each table has only one column.
    columns = [('', 'myvalue')]
    width = 100


    # Magically named trait which gives the display text of the column named
    # 'myvalue'. This is done using a Traits Property and its getter:
    myvalue_text = Property

    # The getter for Property 'myvalue_text' simply takes the value of the
    # corresponding item in the list being displayed in this table.
    # A more complicated example could format the item before displaying it.
    def _get_myvalue_text(self):
        return 'sub-%s'%self.item

class CMP_BIDSAppWindow(HasTraits):

    project_info = Instance(CMP_Project_Info)

    bids_root = Directory()
    subjects = List(Str)

    # handler = Instance(project.CMP_BIDSAppWindowHandler)

    fs_license = File()
    #fs_average = Directory(os.path.join(os.environ['FREESURFER_HOME'],'subjects','fsaverage'))

    list_of_subjects_to_be_processed = List(Str)

    list_of_processing_logfiles = List(File)

    anat_config = File()
    dmri_config = File()
    fmri_config = File()

    run_anat_pipeline = Bool(True)
    run_dmri_pipeline = Bool(True)
    run_fmri_pipeline = Bool(True)

    settings_checked = Bool(False)
    docker_running = Bool(False)

    bidsapp_tag = Enum('{}'.format(__version__),['latest','{}'.format(__version__)])

    data_provenance_tracking = Bool(False)
    datalad_update_environment = Bool(True)
    datalad_is_available = Bool(False)

    # check = Action(name='Check settings!',action='check_settings',image=ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-check-settings.png'))))
    # start_bidsapp = Action(name='Start BIDS App!',action='start_bids_app',enabled_when='settings_checked==True and docker_running==False',image=ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-run.png'))))

    update_selection = Button()
    check = Button()
    start_bidsapp = Button()

    #stop_bidsapp = Action(name='Stop BIDS App!',action='stop_bids_app',enabled_when='handler.settings_checked and handler.docker_running')

    traits_view = QtView(Group(
                            Group(
                                Group(
                                    Item('bids_root', style='readonly', label='Location'),
                                label='BIDS dataset'),
                                Group(
                                    HGroup(
                                    UItem('subjects',
                                        editor=TabularEditor(
                                        show_titles=True,
                                        selected='list_of_subjects_to_be_processed',
                                        editable=False,
                                        multi_select=True,
                                        adapter=MultiSelectAdapter(columns=[('Available labels','myvalue')]))
                                        ),
                                    UItem('list_of_subjects_to_be_processed',
                                        editor=TabularEditor(
                                        show_titles=True,
                                        editable=False,
                                        adapter=MultiSelectAdapter(columns=[('Labels to be processed','myvalue')]))
                                        ),
                                    ),
                                label='Participant labels to be processed'),
                                Group(
                                    Group(Item('anat_config',label='Configuration file',visible_when='run_anat_pipeline'), label='Anatomical pipeline'),
                                    Group(Item('run_dmri_pipeline',label='Run processing stages'),Item('dmri_config',label='Configuration file',visible_when='run_dmri_pipeline'), label='Diffusion pipeline'),
                                    Group(Item('run_fmri_pipeline',label='Run processing stages'),Item('fmri_config',label='Configuration file',visible_when='run_fmri_pipeline'), label='fMRI pipeline'),
                                    label='Configuration of processing pipelines'),
                                Group(
                                    Item('fs_license', label='LICENSE'),
                                    # Item('fs_average', label='FSaverage directory'),
                                    label='Freesurfer configuration'),
                            orientation='vertical',springy=True),
                            Group(
                                Item('bidsapp_tag', label='Release tag'),
                            label='BIDS App Version'),
                            Group(
                                Item('data_provenance_tracking', label='Use Datalad'),
                                Item('datalad_update_environment', visible_when='data_provenance_tracking', label='Update the computing environment (if existing)'),
                            label='Data Provenance Tracking / Data Lineage',
                            enabled_when='datalad_is_available'),
                            spring,
                            HGroup(spring,Item('check',style='custom',width=80,height=20,resizable=False,label='',show_label=False,
                                                editor_args={
                                                'image':ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-check-settings.png'))),'label':"",'label_value':""}
                                                ),
                                          spring,
                                          Item('start_bidsapp',style='custom',width=80,height=20,resizable=False,label='',show_label=False,
                                                editor_args={
                                                'image':ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-run.png'))),'label':"",'label_value':""},
                                                enabled_when='settings_checked==True and docker_running==False'),
                                          spring,
                            show_labels=False,label=""),
                        orientation='vertical',springy=True),

                        title='Connectome Mapper 3 BIDS App GUI',
                        # kind='modal',
                        handler=project.CMP_BIDSAppWindowHandler(),
                        style_sheet=style_sheet,
                        buttons = [],
                        # buttons = [check,start_bidsapp],
                        # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
                        #buttons = [preprocessing, map_connectome, map_custom],
                        width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                        icon=ImageResource('bidsapp.png')
                        )

    log_view = QtView(Group(
                            Item('list_of_processing_logfiles'),
                        orientation='vertical',springy=True),

                        title='Connectome Mapper 3 BIDS App Progress',
                        # kind='modal',
                        #handler=project.CMP_BIDSAppWindowHandler(),
                        style_sheet=style_sheet,
                        buttons = [],
                        # buttons = [check,start_bidsapp],
                        # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
                        #buttons = [preprocessing, map_connectome, map_custom],
                        width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                        icon=ImageResource('bidsapp.png')
                        )


    def __init__(self, project_info=None, bids_root='', subjects=[''], list_of_subjects_to_be_processed=[''], anat_config='', dmri_config='', fmri_config=''):

        self.project_info = project_info
        self.bids_root = bids_root
        self.subjects = subjects
        # self.list_of_subjects_to_be_processed = list_of_subjects_to_be_processed
        self.anat_config = anat_config
        self.dmri_config = dmri_config
        self.fmri_config = fmri_config

        if 'FREESURFER_HOME' in os.environ:
            self.fs_license = os.path.join(os.environ['FREESURFER_HOME'],'license.txt')
        else:
            print('Environment variable $FREESURFER_HOME not found')
            self.fs_license = ''
            print('Freesurfer license unset ({})'.format(self.fs_license))

        self.datalad_is_available = project.is_tool('datalad')

        # print(self.list_of_subjects_to_be_processed)
        # print(self.bids_root)
        # print(self.anat_config)
        # print(self.dmri_config)
        # print(self.fmri_config)
        # print(self.fs_license)
        #print(self.fs_average)

        #self.on_trait_change(self.update_run_anat_pipeline,'run_anat_pipeline')
        self.on_trait_change(self.update_run_dmri_pipeline,'run_dmri_pipeline')
        self.on_trait_change(self.update_run_fmri_pipeline,'run_fmri_pipeline')

        self.on_trait_change(self.update_checksettings, 'list_of_subjects_to_be_processed')
        self.on_trait_change(self.update_checksettings, 'anat_config')
        self.on_trait_change(self.update_checksettings, 'run_dmri_pipeline')
        self.on_trait_change(self.update_checksettings, 'dmri_config')
        self.on_trait_change(self.update_checksettings, 'run_fmri_pipeline')
        self.on_trait_change(self.update_checksettings, 'fmri_config')
        self.on_trait_change(self.update_checksettings, 'fs_license')
        #self.on_trait_change(self.update_checksettings, 'fs_average')

    def update_run_anat_pipeline(self,new):
        # print('Update run anat: %s'%new)
        # print('Update run anat: %s'%self.run_anat_pipeline)
        if new == False:
            print('At least anatomical pipeline should be run!')
            self.run_anat_pipeline = True

    def update_run_dmri_pipeline(self,new):
        # print('Update run diffusion: %s'%new)
        # print('Update run diffusion: %s'%self.run_dmri_pipeline)
        self.run_anat_pipeline = True

    def update_run_fmri_pipeline(self,new):
        # print('Update run fmri: %s'%new)
        # print('Update run fmri: %s'%self.run_fmri_pipeline)
        self.run_anat_pipeline = True

    def update_checksettings(self,new):
        # print("RESET Check BIDS App Settings")
        self.settings_checked = False

    def _update_selection_fired(self):
        self.configure_traits(view='select_subjects_to_be_processed_view')

    def _check_fired(self):
        self.check_settings()

    def _start_bidsapp_fired(self):
        self.start_bids_app()

    def check_settings(self):
        self.settings_checked = True

        if os.path.isdir(self.bids_root):
            print("BIDS root directory : {}".format(self.bids_root))
        else:
            print("Error: BIDS root invalid!")
            self.settings_checked = False

        if len(self.list_of_subjects_to_be_processed)>0:
            print("Participant labels to be processed : {}".format(self.list_of_subjects_to_be_processed))
        else:
            print("Error: At least one participant label to be processed should selected!")
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
        print("Data provenance tracking (datalad) : {}".format(self.data_provenance_tracking))
        print("Update computing environment (datalad) : {}".format(self.datalad_update_environment))

        return True

    def start_bidsapp_participant_level_process(self, bidsapp_tag, participant_labels):
        cmd = ['docker','run','-it','--rm',
               ##'-v', '{}:/bids_dataset'.format(self.bids_root),
               ##'-v', '{}/derivatives:/outputs'.format(self.bids_root),
               # '-v', '{}:/bids_dataset/derivatives/freesurfer/fsaverage'.format(self.fs_average),
               ##'-v', '{}:/opt/freesurfer/license.txt'.format(self.fs_license),
               ##'-v', '{}:/code/ref_anatomical_config.ini'.format(self.anat_config)
               '-v', '{}:/tmp'.format(self.bids_root),
               ]

        # if self.run_dmri_pipeline:
        #     cmd.append('-v')
        #     cmd.append('{}:/code/ref_diffusion_config.ini'.format(self.dmri_config))
        #
        # if self.run_fmri_pipeline:
        #     cmd.append('-v')
        #     cmd.append('{}:/code/ref_fMRI_config.ini'.format(self.fmri_config))

        cmd.append('-u')
        cmd.append('{}:{}'.format(os.geteuid(),os.getegid()))

        cmd.append('sebastientourbier/connectomemapper-bidsapp:{}'.format(bidsapp_tag))
        cmd.append('/tmp')
        cmd.append('/tmp/derivatives')
        cmd.append('participant')

        cmd.append('--participant_label')
        for label in participant_labels:
            cmd.append('{}'.format(label))

        cmd.append('--anat_pipeline_config')
        cmd.append('/tmp/code/ref_anatomical_config.ini')

        if self.run_dmri_pipeline:
            cmd.append('--dwi_pipeline_config')
            cmd.append('/tmp/code/ref_diffusion_config.ini')

        if self.run_fmri_pipeline:
            cmd.append('--func_pipeline_config')
            cmd.append('/tmp/code/ref_fMRI_config.ini')


        print('... Docker cmd : {}'.format(cmd))

        log_filename = os.path.join(self.bids_root,'derivatives','cmp','main_log-cmpbidsapp.txt')

        if not os.path.exists(os.path.join(self.bids_root,'derivatives','cmp')):
            os.makedirs(os.path.join(self.bids_root,'derivatives','cmp'))

        # with open(log_filename, 'w+') as log:
        #     proc = Popen(cmd, stdout=log, stderr=log)
        #     #docker_process.communicate()

        proc = Popen(cmd)
        # proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        return proc

    def start_bidsapp_participant_level_process_with_datalad(self, bidsapp_tag, participant_labels):
        cmd = ['datalad','containers-run',]

        cmd.append('--container-name')
        cmd.append('connectomemapper-bidsapp-{}'.format("-".join(bidsapp_tag.split("."))))

        cmd.append('-m')
        cmd.append('Processing with connectomemapper-bidsapp {}'.format(bidsapp_tag))

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
        cmd.append('/tmp/{{outputs[0]}}')
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

    def manage_bidsapp_procs(self, proclist):
        for proc in proclist:
            if proc.poll() is not None:
                proclist.remove(proc)

    def run(self, command, env={}, cwd=os.getcwd()):
        merged_env = os.environ
        merged_env.update(env)
        process = Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, shell=True,
                                   env=merged_env, cwd=cwd)
        while True:
            line = process.stdout.readline()
            line = str(line)[:-1]
            print(line)
            if line == '' and process.poll() != None:
                break
        if process.returncode != 0:
            raise Exception("Non zero return code: %d"%process.returncode)

    def start_bids_app(self):
        print("Start BIDS App")

        # Copy freesurfer license into dataset/code directory where the BIDS app
        # is looking for.
        print('> Copy FreeSurfer license (BIDS App Manager) ')
        print('... src : {}'.format(self.fs_license))
        print('... dst : {}'.format(os.path.join(self.bids_root,'code','license.txt')))
        shutil.copyfile(src=self.fs_license,dst=os.path.join(self.bids_root,'code','license.txt'))

        project.fix_dataset_directory_in_pickles(local_dir=self.bids_root,mode='bidsapp')


        print("> Datalad available: {}".format(self.datalad_is_available))

        # self.datalad_is_available = False

        if self.datalad_is_available and self.data_provenance_tracking:
            # Detect structure subject/session
            session_structure = False
            res = glob.glob(os.path.join(self.bids_root,'sub-*/*/anat'))
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
            if not os.path.isdir(os.path.join(self.bids_root,'.datalad')):
                cmd = 'datalad rev-create --force -D "Creation of datalad dataset to be processed by the connectome mapper bidsapp (tag:{})"'.format(self.bidsapp_tag)
                try:
                    print('... cmd: {}'.format(cmd))
                    self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
                except:
                    print("    ERROR: Failed to create the datalad dataset")
            else:
                print("    INFO: A datalad dataset already exists!")

            # log_filename = os.path.join(self.bids_root,'derivatives','cmp','main-datalad_log-cmpbidsapp.txt')
            #
            # if not os.path.exists(os.path.join(self.bids_root,'derivatives','cmp')):
            #     os.makedirs(os.path.join(self.bids_root,'derivatives','cmp'))

            #create an empty log file to be tracked by datalad
            # f = open(log_filename,"w+")
            # f.close()

            datalad_container = os.path.join(self.bids_root,'.datalad','environments','connectomemapper-bidsapp-{}'.format("-".join(self.bidsapp_tag.split("."))),'image')
            add_container = True
            if os.path.isdir(datalad_container):
                if self.datalad_update_environment:
                    print("    INFO: Container already listed in the datalad dataset and will be updated!")
                    shutil.rmtree(datalad_container)
                    add_container = True
                else:
                    add_container = False
                    print("    INFO: Container already listed in the datalad dataset and will NOT be updated!")
            else:
                add_container = True
                print("    INFO: Add a new computing environment (container image) to the datalad dataset!")

            if add_container:
                cmd = "datalad containers-add connectomemapper-bidsapp-{} --url dhub://sebastientourbier/connectomemapper-bidsapp:{}".format("-".join(self.bidsapp_tag.split(".")),self.bidsapp_tag)
                try:
                    print('... cmd: {}'.format(cmd))
                    self.run(cmd, env={}, cwd=os.path.join(self.bids_root))
                except:
                    print("   ERROR: Failed to link the container image to the datalad dataset")

            # Implementation with --upgrade available in latest version but not
            # in stable version of datalad_container

            # cmd = "datalad containers-add connectomemapper-bidsapp-{} --url dhub://sebastientourbier/connectomemapper-bidsapp:{} --update".format(self.bidsapp_tag,self.bidsapp_tag)
            #
            # try:
            #     print('... cmd: {}'.format(cmd))
            #     self.run(cmd, env={}, cwd=os.path.join(self.bids_root))
            # except:
            #     print("   ERROR: Failed to link the container image to the datalad dataset")

            datalad_get_list = []

            datalad_get_list.append('code/ref_anatomical_config.ini')

            if self.run_dmri_pipeline:
                datalad_get_list.append('code/ref_diffusion_config.ini')

            if self.run_dmri_pipeline:
                datalad_get_list.append('code/ref_fMRI_config.ini')

            if session_structure:
                for label in self.list_of_subjects_to_be_processed:
                    datalad_get_list.append('sub-{}/ses-*/anat/sub-{}*_T1w.*'.format(label,label))
                    datalad_get_list.append('derivatives/freesurfer/sub-{}*/*'.format(label))
                    if self.run_dmri_pipeline:
                        datalad_get_list.append('sub-{}/ses-*/dwi/sub-{}*_dwi.*'.format(label,label))
                    if self.run_fmri_pipeline:
                        datalad_get_list.append('sub-{}/ses-*/func/sub-{}*_bold.*'.format(label,label))
            else:
                for label in self.list_of_subjects_to_be_processed:
                    datalad_get_list.append('sub-{}/anat/sub-{}*_T1w.*'.format(label,label))
                    datalad_get_list.append('derivatives/freesurfer/sub-{}/*'.format(label))
                    if self.run_dmri_pipeline:
                        datalad_get_list.append('sub-{}/dwi/sub-{}*_dwi.*'.format(label,label))
                    if self.run_fmri_pipeline:
                        datalad_get_list.append('sub-{}/func/sub-{}*_bold.*'.format(label,label))

            cmd = 'datalad run -m "Get files for sub-{}" bash -c "datalad get {}"'.format(self.list_of_subjects_to_be_processed," ".join(datalad_get_list))
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
                print("    ERROR: Failed to get files (cmd: datalad get {})".format(" ".join(datalad_get_list)))


            cmd = 'datalad add --nosave -J {} .'.format(multiprocessing.cpu_count())
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
                print("    ERROR: Failed to add existing files to datalad")

            cmd = 'datalad save -m "Existing files tracked by datalad. Dataset ready for connectome mapping." --version-tag ready4analysis-{}'.format(time.strftime("%Y%m%d-%H%M%S"))
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
                print("    ERROR: Failed to commit to datalad dataset")

            cmd = 'datalad diff --revision HEAD~1'
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
                print("    ERROR: Failed to run datalad rev-status")

        maxprocs = multiprocessing.cpu_count()
        processes = []

        self.docker_running = True

        # for label in self.list_of_subjects_to_be_processed:
        #     while len(processes) == maxprocs:
        #         self.manage_bidsapp_procs(processes)
        #
        #     proc = self.start_bidsapp_participant_level_process(self.bidsapp_tag,label)
        #     processes.append(proc)
        #
        # while len(processes) > 0:
        #     self.manage_bidsapp_procs(processes)

        if self.datalad_is_available and self.data_provenance_tracking:

            proc = self.start_bidsapp_participant_level_process_with_datalad(self.bidsapp_tag,self.list_of_subjects_to_be_processed)

        else:
            proc = self.start_bidsapp_participant_level_process(self.bidsapp_tag,self.list_of_subjects_to_be_processed)

        processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        project.fix_dataset_directory_in_pickles(local_dir=self.bids_root,mode='local')

        if self.datalad_is_available and self.data_provenance_tracking:
            # Clean remaining cache files generated in tmp/ of the docker image
            project.clean_cache(self.bids_root)

            cmd = 'datalad add --nosave -J {} .'.format(multiprocessing.cpu_count())
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
                print("    ERROR: Failed to add changes to datalad dataset")

            cmd = 'datalad save -m "Dataset processed by the connectomemapper-bidsapp:{}" --version-tag processed-{}'.format(self.bidsapp_tag, time.strftime("%Y%m%d-%H%M%S"))
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
                print("    ERROR: Failed to commit derivatives to datalad dataset")

            cmd = 'datalad diff --revision HEAD~1'
            try:
                print('... cmd: {}'.format(cmd))
                self.run( cmd, env={}, cwd=os.path.abspath(self.bids_root))
            except:
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





    # def __init__(self,ui_info):
    #
    #     print ui_info.ui.context["object"].project_info
    #
    #     self.anat_config = ui_info.ui.context["object"].project_info.anat_config_to_load
    #
    #     if ui_info.ui.context["object"].project_info.dmri_config_to_load != None:
    #         self.dmri_config = ui_info.ui.context["object"].project_info.dmri_config_to_load
    #     if ui_info.ui.context["object"].project_info.fmri_config_to_load != None:
    #         self.fmri_config = ui_info.ui.context["object"].project_info.fmri_config_to_load
    #
    #     self.bids_root = ui_info.ui.context["object"].project_info.base_directory
    #     self.subjects = ui_info.ui.context["object"].project_info.subjects
    #     self.list_of_subjects_to_be_processed = ui_info.ui.context["object"].project_info.subjects


## Main window class of the ConnectomeMapper_Pipeline Configurator
#
class CMP_ConfiguratorWindow(HasTraits):
    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    project_info = Instance(CMP_Project_Info)

    anat_inputs_checked = Bool(False)
    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    anat_save_config = Action(name='Save anatomical pipeline configuration as...',action='save_anat_config_file')
    dmri_save_config = Action(name='Save diffusion pipeline configuration as...',action='save_dmri_config_file')
    fmri_save_config = Action(name='Save fMRI pipeline configuration as...',action='save_fmri_config_file')

    # anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file')
    # dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='load_dmri_config_file')
    # fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='load_fmri_config_file')

    save_all_config = Button('')

    traits_view = QtView(
                        Group(
                            # Group(
                            #     # Include('dataset_view'),label='Data manager',springy=True
                            #     Item('project_info',style='custom',show_label=False),label='Data manager',springy=True, dock='tab'
                            # ),
                            Group(
                                Item('anat_pipeline',style='custom',show_label=False),
                                label='Anatomical pipeline', dock='tab'
                            ),
                            Group(
                                Item('dmri_pipeline',style='custom',show_label=False, enabled_when='dmri_inputs_checked'),
                                label='Diffusion pipeline', dock='tab'
                            ),
                            Group(
                                Item('fmri_pipeline',style='custom',show_label=False, enabled_when='fmri_inputs_checked'),
                                label='fMRI pipeline', dock='tab'
                            ),
                        orientation='horizontal', layout='tabbed', springy=True, enabled_when='anat_inputs_checked'),
                        spring,
                        HGroup(spring,Item('save_all_config',style='custom',width=160,height=20,resizable=False,label='',show_label=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'configurator-saveall.png'))),'label':"",'label_value':""},
                                            enabled_when='anat_inputs_checked==True'),
                               spring,
                        show_labels=False,label=""),

                        title='Connectome Mapper 3 Configurator',
                        menubar=MenuBar(
                                    Menu(
                                        ActionGroup(
                                            anat_save_config,
                                            dmri_save_config,
                                            fmri_save_config,
                                        ),
                                        ActionGroup(
                                            Action(name='Quit',action='_on_close'),
                                        ),
                                        name='File'),
                                ),
                       handler = project.ProjectHandler(),
                       style_sheet=style_sheet,
                       # buttons = [anat_save_config, dmri_save_config, fmri_save_config,],
                       buttons = [],
                       #buttons = [preprocessing, map_connectome, map_custom],
                       width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                       icon=ImageResource('configurator.png')
                   )

    def __init__(self, project_info=None, anat_pipeline=None, dmri_pipeline=None, fmri_pipeline=None, anat_inputs_checked=False, dmri_inputs_checked=False, fmri_inputs_checked=False):

        self.project_info = project_info

        self.anat_pipeline = anat_pipeline
        self.dmri_pipeline = dmri_pipeline
        self.fmri_pipeline = fmri_pipeline

        if self.anat_pipeline != None:
            self.anat_pipeline.view_mode = 'config_view'

        if self.dmri_pipeline != None:
            self.dmri_pipeline.view_mode = 'config_view'

        if self.fmri_pipeline != None:
            self.fmri_pipeline.view_mode = 'config_view'

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        #self.on_trait_change(self.update_run_anat_pipeline,'run_anat_pipeline')

    def update_diffusion_imaging_model(self,new):
        self.dmri_pipeline.diffusion_imaging_model = new

    def _save_all_config_fired(self):
        print('Saving pipeline configuration files...')

        if self.anat_inputs_checked:
            anat_config_file = os.path.join(self.project_info.base_directory,'code','ref_anatomical_config.ini')
            project.anat_save_config(self.anat_pipeline, anat_config_file)
            print('Anatomical config saved as  {}'.format(anat_config_file))

        if self.dmri_inputs_checked:
            dmri_config_file = os.path.join(self.project_info.base_directory,'code','ref_diffusion_config.ini')
            project.dmri_save_config(self.dmri_pipeline, dmri_config_file)
            print('Diffusion config saved as  {}'.format(dmri_config_file))

        if self.fmri_inputs_checked:
            fmri_config_file = os.path.join(self.project_info.base_directory,'code','ref_fMRI_config.ini')
            project.fmri_save_config(self.fmri_pipeline, fmri_config_file)
            print('fMRI config saved as  {}'.format(fmri_config_file))


## Window class of the ConnectomeMapper_Pipeline Quality Inspector
#
class CMP_QualityControlWindow(HasTraits):
    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    project_info = Instance(CMP_Project_Info)

    anat_inputs_checked = Bool(False)
    dmri_inputs_checked = Bool(False)
    fmri_inputs_checked = Bool(False)

    output_anat_available = Bool(False)
    output_dmri_available = Bool(False)
    output_fmri_available = Bool(False)

    # anat_save_config = Action(name='Save anatomical pipeline configuration as...',action='save_anat_config_file')
    # dmri_save_config = Action(name='Save diffusion pipeline configuration as...',action='save_dmri_config_file')
    # fmri_save_config = Action(name='Save fMRI pipeline configuration as...',action='save_fmri_config_file')
    #
    # anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file')
    # dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='load_dmri_config_file')
    # fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='load_fmri_config_file')

    traits_view = QtView(Group(
                            # Group(
                            #     # Include('dataset_view'),label='Data manager',springy=True
                            #     Item('project_info',style='custom',show_label=False),label='Data manager',springy=True, dock='tab'
                            # ),
                            Group(
                                Item('anat_pipeline',style='custom',show_label=False), visible_when='output_anat_available',
                                label='Anatomical pipeline', dock='tab'
                            ),
                            Group(
                                Item('dmri_pipeline',style='custom',show_label=False, visible_when='output_dmri_available'),
                                label='Diffusion pipeline', dock='tab'
                            ),
                            Group(
                                Item('fmri_pipeline',style='custom',show_label=False, visible_when='output_fmri_available'),
                                label='fMRI pipeline', dock='tab'
                            ),
                            orientation='horizontal', layout='tabbed', springy=True, enabled_when='output_anat_available'),
                        title='Connectome Mapper 3 Quality Control',
                        menubar=MenuBar(
                                    Menu(
                                        ActionGroup(
                                            Action(name='Quit',action='_on_close'),
                                        ),
                                        name='File'),
                                ),
                       handler = project.ProjectHandler(),
                       style_sheet=style_sheet,
                       #buttons = [anat_save_config, dmri_save_config, fmri_save_config,],
                       #buttons = [preprocessing, map_connectome, map_custom],
                       width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                       icon=ImageResource('qualitycontrol.png')
                   )

    error_msg = Str('')
    error_view = View(
                    Group(
                        Item('error_msg', style='readonly',show_label=False),
                        ),
                    title='Error',
                    kind = 'modal',
                    #style_sheet=style_sheet,
                    buttons=['OK'])

    def __init__(self, project_info=None, anat_inputs_checked=False, dmri_inputs_checked=False, fmri_inputs_checked=False):

        self.project_info = project_info

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        print('Fix BIDS root directory to {}'.format(self.project_info.base_directory))
        project.fix_dataset_directory_in_pickles(local_dir=self.project_info.base_directory,mode='newlocal')

        aborded = self.select_subject()

        if aborded:
            raise Exception('ABORDED: The quality control window will not be displayed. Selection of subject/session was cancelled at initialization.')

        #self.on_trait_change(self.update_run_anat_pipeline,'run_anat_pipeline')

    def select_subject(self):
        valid_selected_subject = False
        select = True
        aborded = False

        while not valid_selected_subject and not aborded:

            #Select subject from BIDS dataset
            np_res = self.project_info.configure_traits(view='subject_view')

            if not np_res:
                aborded = True
                break

            print("Selected subject: {}".format(self.project_info.subject))

            # Select session if any
            bids_layout = BIDSLayout(self.project_info.base_directory)
            subject = self.project_info.subject.split('-')[1]

            sessions = bids_layout.get(target='session', return_type='id', subject=subject)

            if len(sessions) > 0:
                print("Detected sessions")
                print sessions

                self.project_info.subject_sessions = []

                for ses in sessions:
                    self.project_info.subject_sessions.append('ses-'+str(ses))

                np_res = self.project_info.configure_traits(view='subject_session_view')

                if not np_res:
                    aborded = True
                    break

                self.project_info.anat_config_file = os.path.join(self.project_info.base_directory,'derivatives','{}_{}_anatomical_config.ini'.format(self.project_info.subject,self.project_info.subject_session))
                if os.access(self.project_info.anat_config_file,os.F_OK):
                    self.anat_pipeline = project.init_anat_project(self.project_info,False)
                else:
                    self.anat_pipeline = None

                if self.dmri_inputs_checked:
                    self.project_info.dmri_config_file = os.path.join(self.project_info.base_directory,'derivatives','{}_{}_diffusion_config.ini'.format(self.project_info.subject,self.project_info.subject_session))
                    if os.access(self.project_info.dmri_config_file,os.F_OK):
                        dmri_valid_inputs, self.dmri_pipeline = project.init_dmri_project(self.project_info,bids_layout,False)
                    else:
                        self.dmri_pipeline = None

                    # self.dmri_pipeline.subject = self.project_info.subject
                    # self.dmri_pipeline.global_conf.subject = self.project_info.subject

                if self.fmri_inputs_checked:
                    self.project_info.fmri_config_file = os.path.join(self.project_info.base_directory,'derivatives','{}_{}_fMRI_config.ini'.format(self.project_info.subject,self.project_info.subject_session))
                    if os.access(self.project_info.fmri_config_file,os.F_OK):
                        fmri_valid_inputs, self.fmri_pipeline = project.init_fmri_project(self.project_info,bids_layout,False)
                    else:
                        self.fmri_pipeline = None

                    # self.fmri_pipeline.subject = self.project_info.subject
                    # self.fmri_pipeline.global_conf.subject = self.project_info.subject

                # self.anat_pipeline.global_conf.subject_session = self.project_info.subject_session

                # if self.dmri_pipeline != None:
                #     self.dmri_pipeline.global_conf.subject_session = self.project_info.subject_session
                #
                # if self.fmri_pipeline != None:
                #     self.fmri_pipeline.global_conf.subject_session = self.project_info.subject_session

                print("Selected session %s" % self.project_info.subject_session)
                if self.anat_pipeline != None:
                    self.anat_pipeline.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(self.project_info.base_directory,'derivatives','freesurfer','{}_{}'.format( self.project_info.subject, self.project_info.subject_session))
            else:
                print("No session detected")
                self.project_info.anat_config_file = os.path.join(self.project_info.base_directory,'derivatives','{}_anatomical_config.ini'.format(self.project_info.subject))
                if os.access(self.project_info.anat_config_file,os.F_OK):
                    self.anat_pipeline = project.init_anat_project(self.project_info,False)
                else:
                    self.anat_pipeline = None

                if self.dmri_inputs_checked:
                    self.project_info.dmri_config_file = os.path.join(self.project_info.base_directory,'derivatives','{}_diffusion_config.ini'.format(self.project_info.subject))
                    if os.access(self.project_info.dmri_config_file,os.F_OK):
                        dmri_valid_inputs, self.dmri_pipeline = project.init_dmri_project(self.project_info,bids_layout,False)
                    else:
                        self.dmri_pipeline = None

                    # self.dmri_pipeline.subject = self.project_info.subject
                    # self.dmri_pipeline.global_conf.subject = self.project_info.subject

                if self.fmri_inputs_checked:
                    self.project_info.fmri_config_file = os.path.join(self.project_info.base_directory,'derivatives','{}_fMRI_config.ini'.format(self.project_info.subject))
                    if os.access(self.project_info.fmri_config_file,os.F_OK):
                        fmri_valid_inputs, self.fmri_pipeline = project.init_fmri_project(self.project_info,bids_layout,False)
                    else:
                        self.fmri_pipeline = None

                    # self.fmri_pipeline.subject = self.project_info.subject
                    # self.fmri_pipeline.global_conf.subject = self.project_info.subject

                # self.anat_pipeline.global_conf.subject_session = ''
                if self.anat_pipeline != None:
                    self.anat_pipeline.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.project_info.base_directory,'derivatives','freesurfer','{}'.format(self.project_info.subject))

            if self.anat_pipeline != None:
                self.anat_pipeline.view_mode = 'inspect_outputs_view'
                for stage in self.anat_pipeline.stages.values():
                    stage.define_inspect_outputs()
                    print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (stage.inspect_outputs[0] != 'Outputs not available'):
                        self.output_anat_available = True

            if self.dmri_pipeline != None:
                self.dmri_pipeline.view_mode = 'inspect_outputs_view'
                for stage in self.dmri_pipeline.stages.values():
                    stage.define_inspect_outputs()
                    print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (stage.inspect_outputs[0] != 'Outputs not available'):
                        self.output_dmri_available = True

            if self.fmri_pipeline != None:
                self.fmri_pipeline.view_mode = 'inspect_outputs_view'
                for stage in self.fmri_pipeline.stages.values():
                    stage.define_inspect_outputs()
                    print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                    if (len(stage.inspect_outputs) > 0) and (stage.inspect_outputs[0] != 'Outputs not available'):
                        self.output_fmri_available = True

            print("Anatomical output(s) available : %s" % self.output_anat_available)
            print("Diffusion output(s) available : %s" % self.output_dmri_available)
            print("fMRI output(s) available : %s" % self.output_fmri_available)

            if self.output_anat_available or self.output_dmri_available or self.output_fmri_available:
                valid_selected_subject = True
            else:
                self.error_msg = "No output available! Please select another subject (and session if any)!"

                select = error(message=self.error_msg, title='Error', buttons=['OK', 'Cancel'])
                aborded = not select
                # self.configure_traits(view='error_view')

        return aborded

    def update_diffusion_imaging_model(self,new):
        self.dmri_pipeline.diffusion_imaging_model = new


## Main window class of the ConnectomeMapper_Pipeline
#
class CMP_MainWindow(HasTraits):
    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    project_info = Instance(CMP_Project_Info)

    bidsapp = Instance(CMP_BIDSAppWindow)

    handler = Instance(project.ProjectHandler)

    new_project = Action(name='Load BIDS Dataset (New)...',action='new_project')
    load_project = Action(name='Load BIDS Dataset (Processed)...',action='load_project')
    # process_anatomical = Action(name='Parcellate Brain!',action='process_anatomical',enabled_when='handler.anat_inputs_checked==True')
    # map_dmri_connectome = Action(name='Map Strutural Connectome!',action='map_dmri_connectome',enabled_when='handler.anat_outputs_checked and handler.dmri_inputs_checked')
    # map_fmri_connectome = Action(name='Map Functional Connectome!',action='map_fmri_connectome',enabled_when='handler.anat_outputs_checked and handler.fmri_inputs_checked')

    anat_save_config = Action(name='Save anatomical pipeline configuration as...',action='save_anat_config_file',enabled_when='handler.project_loaded==True')
    anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file',enabled_when='handler.project_loaded==True')

    dmri_save_config = Action(name='Save diffusion pipeline configuration as...',action='save_dmri_config_file',enabled_when='handler.project_loaded==True')
    dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='load_dmri_config_file',enabled_when='handler.project_loaded==True')

    fmri_save_config = Action(name='Save fMRI pipeline configuration as...',action='save_fmri_config_file',enabled_when='handler.project_loaded==True')
    fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='load_fmri_config_file',enabled_when='handler.project_loaded==True')

    show_bidsapp_window = Action(name='Show interface...',action='show_bidsapp_window',enabled_when='handler.project_loaded==True')

    project_info.style_sheet = style_sheet

    traits_view = QtView(Group(
                            Group(
                                # Include('dataset_view'),label='Data manager',springy=True
                                Item('project_info',style='custom',show_label=False),label='Data manager',springy=True, dock='tab'
                            ),
                            Group(
                                Item('anat_pipeline',style='custom',show_label=False),
                                label='Anatomical pipeline', dock='tab'
                            ),
                            Group(
                                Item('dmri_pipeline',style='custom',show_label=False, enabled_when='handler.anat_outputs_checked and handler.dmri_inputs_checked'),
                                label='Diffusion pipeline', dock='tab'
                            ),
                            Group(
                                Item('fmri_pipeline',style='custom',show_label=False, enabled_when='handler.anat_outputs_checked and handler.fmri_inputs_checked'),
                                label='fMRI pipeline', dock='tab'
                            ),
                            orientation='horizontal', layout='tabbed', springy=True, enabled_when='handler.anat_inputs_checked==True'),
                        title='Connectome Mapper 3 Configurator',
                        menubar=MenuBar(
                                    Menu(
                                        ActionGroup(
                                            new_project,
                                            load_project,
                                        ),
                                        ActionGroup(
                                            Action(name='Quit',action='_on_close'),
                                        ),
                                        name='File'),
                                    Menu(
                                        anat_save_config,
                                        dmri_save_config,
                                        fmri_save_config,
                                    name='Configuration'),
                                    Menu(
                                        show_bidsapp_window,
                                    name='BIDS App'),
                                    # Menu(
                                    #     change_subject,
                                    # name='Subjects'),
                                ),
                       handler = project.ProjectHandler(),
                       style_sheet=style_sheet,
                       # buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
                       #buttons = [preprocessing, map_connectome, map_custom],
                       width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                       icon=ImageResource('cmp.png')
                   )

    def update_diffusion_imaging_model(self,new):
        self.dmri_pipeline.diffusion_imaging_model = new

    def update_subject_anat_pipeline(self,new):
        try:
            # print "update subject anat"
            bids_layout = BIDSLayout(self.project_info.base_directory)
            self.project_info.subject_sessions = ["ses-%s"%s for s in bids_layout.get(target='session', return_type='id', subject=self.project_info.subject.split('-')[1])]
            if len(self.project_info.subject_sessions)>0:
                self.project_info.subject_session = self.project_info.subject_sessions[0]
            else:
                self.project_info.subject_session = ''
            self = self.handler.update_subject_anat_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject anat"
            return

    def update_subject_dmri_pipeline(self,new):
        try:
            # print "update subject dmri"
            bids_layout = BIDSLayout(self.project_info.base_directory)
            self.project_info.subject_sessions = ["ses-%s"%s for s in bids_layout.get(target='session', return_type='id', subject=self.project_info.subject.split('-')[1])]
            if len(self.project_info.subject_sessions)>0:
                self.project_info.subject_session = self.project_info.subject_sessions[0]
            else:
                self.project_info.subject_session = ''
            self = self.handler.update_subject_dmri_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject dmri"
            return

    def update_subject_fmri_pipeline(self,new):
        try:
            # print "update subject fmri"
            bids_layout = BIDSLayout(self.project_info.base_directory)
            self.project_info.subject_sessions = ["ses-%s"%s for s in bids_layout.get(target='session', return_type='id', subject=self.project_info.subject.split('-')[1])]
            if len(self.project_info.subject_sessions)>0:
                self.project_info.subject_session = self.project_info.subject_sessions[0]
            else:
                self.project_info.subject_session = ''
            self = self.handler.update_subject_fmri_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject fmri"
            return

    def update_session_anat_pipeline(self,new):
        try:
            # print "update subject session anat"
            self = self.handler.update_subject_anat_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject anat"
            return

    def update_session_dmri_pipeline(self,new):
        try:
            # print "update subject session dmri"
            self = self.handler.update_subject_dmri_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject dmri"
            return

    def update_session_fmri_pipeline(self,new):
        try:
            # print "update subject session fmri"
            self = self.handler.update_subject_fmri_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject fmri"
            return

    def show_bidsapp_interface(self):
        # print("list_of_subjects_to_be_processed:")
        # print(self.project_info.subjects)

        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        # anat_config = os.path.join(self.project_info.base_directory,'derivatives/','%s_anatomical_config.ini'%self.project_info.anat_config_to_load)
        # dmri_config = os.path.join(self.project_info.base_directory,'derivatives/','%s_diffusion_config.ini'%self.project_info.dmri_config_to_load)
        # fmri_config = os.path.join(self.project_info.base_directory,'derivatives/','%s_fMRI_config.ini'%self.project_info.fmri_config_to_load)

        anat_config = os.path.join(self.project_info.base_directory,'code/','ref_anatomical_config.ini')
        dmri_config = os.path.join(self.project_info.base_directory,'code/','ref_diffusion_config.ini')
        fmri_config = os.path.join(self.project_info.base_directory,'code/','ref_fMRI_config.ini')

        self.bidsapp = CMP_BIDSAppWindow(project_info=self.project_info,
                                         bids_root=self.project_info.base_directory,
                                         subjects=subjects,
                                         list_of_subjects_to_be_processed=subjects,
                                         anat_config=anat_config,
                                         dmri_config=dmri_config,
                                         fmri_config=fmri_config
                                         )
        self.bidsapp.configure_traits()

class CMP_MainWindowV2(HasTraits):
    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    project_info = Instance(CMP_Project_Info)

    # handler = project.ProjectHandlerV2()

    #configurator_ui = Instance(CMP_PipelineConfigurationWindow)
    bidsapp_ui = Instance(CMP_BIDSAppWindow)
    #quality_control_ui = Instance(CMP_QualityControlWindow)

    load_dataset = Action(name='Load BIDS Dataset...',action='load_dataset')

    # show_bidsapp_window = Action(name='Show interface...',action='show_bidsapp_window',enabled_when='handler.project_loaded==True')

    project_info.style_sheet = style_sheet

    configurator = Button('')
    bidsapp = Button('')
    quality_control = Button('')

    view_mode = 1

    manager_group = VGroup(
                    spring,
                        HGroup(
                        spring,
                        HGroup(Item('configurator',style='custom',width=240,height=240,resizable=False,label='',show_label=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('cmp', os.path.join('bidsappmanager/images', 'configurator.png'))),'label':"",'label_value':""}
                                            ),
                               show_labels=False,label=""),
                        spring,
                        HGroup(Item('bidsapp',style='custom',width=240,height=240,resizable=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('cmp', os.path.join('bidsappmanager/images', 'bidsapp.png'))),'label':""}
                                            ),
                               show_labels=False,label=""),
                        spring,
                        HGroup(Item('quality_control',style='custom',width=240,height=240,resizable=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('cmp', os.path.join('bidsappmanager/images', 'qualitycontrol.png'))),'label':""}
                                            ),
                               show_labels=False,label=""),
                        spring,
                        springy=True,visible_when='handler.project_loaded==True'),
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
                                             Action(name='Quit',action='_on_close'),
                                         ),
                                         name='File'),
                                 ),
                        handler = project.ProjectHandlerV2(),
                        style_sheet=style_sheet,
                        width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                        icon=ImageResource('cmp.png')
                         )

    def _bidsapp_fired(self):
        """ Callback of the "bidsapp" button. This displays the BIDS APP GUI.
        """
        # print("list_of_subjects_to_be_processed:")
        # print(self.project_info.subjects)

        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        anat_config = os.path.join(self.project_info.base_directory,'code/','ref_anatomical_config.ini')
        dmri_config = os.path.join(self.project_info.base_directory,'code/','ref_diffusion_config.ini')
        fmri_config = os.path.join(self.project_info.base_directory,'code/','ref_fMRI_config.ini')

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
        """ Callback of the "configurator" button. This displays the Configurator GUI.
        """
        if self.project_info.t1_available:
            if os.path.isfile(self.project_info.anat_config_file):
                print("Anatomical config file : %s"%self.project_info.anat_config_file)

        if self.project_info.dmri_available:
            if os.path.isfile(self.project_info.dmri_config_file):
                print("Diffusion config file : %s"%self.project_info.dmri_config_file)

        if self.project_info.fmri_available:
            if os.path.isfile(self.project_info.fmri_config_file):
                print("fMRI config file : %s"%self.project_info.fmri_config_file)

        print(self.anat_pipeline)
        print(self.dmri_pipeline)
        print(self.fmri_pipeline)

        print(self.project_info.t1_available)
        print(self.project_info.dmri_available)
        print(self.project_info.fmri_available)

        self.configurator_ui = CMP_ConfiguratorWindow(project_info = self.project_info,
                                                    anat_pipeline=self.anat_pipeline,
                                                    dmri_pipeline=self.dmri_pipeline,
                                                    fmri_pipeline=self.fmri_pipeline,
                                                    anat_inputs_checked=self.project_info.t1_available,
                                                    dmri_inputs_checked=self.project_info.dmri_available,
                                                    fmri_inputs_checked=self.project_info.fmri_available
                                                    )

        self.configurator_ui.configure_traits()

    def _quality_control_fired(self):
        """ Callback of the "configurator" button. This displays the Configurator GUI.
        """
        if self.project_info.t1_available:
            if os.path.isfile(self.project_info.anat_config_file):
                print("Anatomical config file : %s"%self.project_info.anat_config_file)

        if self.project_info.dmri_available:
            if os.path.isfile(self.project_info.dmri_config_file):
                print("Diffusion config file : %s"%self.project_info.dmri_config_file)

        if self.project_info.fmri_available:
            if os.path.isfile(self.project_info.fmri_config_file):
                print("fMRI config file : %s"%self.project_info.fmri_config_file)

        print(self.anat_pipeline)
        print(self.dmri_pipeline)
        print(self.fmri_pipeline)

        print(self.project_info.t1_available)
        print(self.project_info.dmri_available)
        print(self.project_info.fmri_available)

        try:
            self.quality_control_ui = CMP_QualityControlWindow(project_info = self.project_info,
                                                    anat_inputs_checked=self.project_info.t1_available,
                                                    dmri_inputs_checked=self.project_info.dmri_available,
                                                    fmri_inputs_checked=self.project_info.fmri_available
                                                    )
            self.quality_control_ui.configure_traits()
        except Exception as e:
            print(e)


    def show_bidsapp_interface(self):
        # print("list_of_subjects_to_be_processed:")
        # print(self.project_info.subjects)

        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        # anat_config = os.path.join(self.project_info.base_directory,'derivatives/','%s_anatomical_config.ini'%self.project_info.anat_config_to_load)
        # dmri_config = os.path.join(self.project_info.base_directory,'derivatives/','%s_diffusion_config.ini'%self.project_info.dmri_config_to_load)
        # fmri_config = os.path.join(self.project_info.base_directory,'derivatives/','%s_fMRI_config.ini'%self.project_info.fmri_config_to_load)

        anat_config = os.path.join(self.project_info.base_directory,'code/','ref_anatomical_config.ini')
        dmri_config = os.path.join(self.project_info.base_directory,'code/','ref_diffusion_config.ini')
        fmri_config = os.path.join(self.project_info.base_directory,'code/','ref_fMRI_config.ini')

        self.bidsapp = CMP_BIDSAppWindow(project_info=self.project_info,
                                         bids_root=self.project_info.base_directory,
                                         subjects=subjects,
                                         list_of_subjects_to_be_processed=subjects,
                                         anat_config=anat_config,
                                         dmri_config=dmri_config,
                                         fmri_config=fmri_config
                                         )
        #self.bidsapp.configure_traits()
