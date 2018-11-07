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
import multiprocessing
from subprocess import Popen
import pkg_resources

import gzip
import pickle
import string

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.api import ImageResource

from bids.grabbids import BIDSLayout

# CMP imports
import cmp.configurator.project as project

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
                min-width: 20px;
                icon-size: 240px;
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
                        buttons=['OK','Cancel'])

    subject_session_view = View(
                        Group(
                            Item('subject_session',label='Selected Session'),
                            ),
                        kind='modal',
                        title='Session selection (subject: %s)'% subject,
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    anat_warning_view = View(
                        Group(
                            Item('anat_warning_msg',style='readonly',show_label=False),
                            ),
                        title='Warning : Anatomical T1w data',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    anat_config_error_view = View(
                            Group(
                                Item('anat_config_error_msg', style='readonly',show_label=False),
                                ),
                            title='Error',
                            kind = 'modal',
                            #style_sheet=style_sheet,
                            buttons=['OK','Cancel'])

    dmri_warning_view = View(
                        Group(
                            Item('dmri_warning_msg',style='readonly',show_label=False),
                            ),
                        title='Warning : Diffusion MRI data',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    dmri_config_error_view = View(
                            Group(
                                Item('dmri_config_error_msg', style='readonly',show_label=False),
                                ),
                            title='Error',
                            kind = 'modal',
                            #style_sheet=style_sheet,
                            buttons=['OK','Cancel'])

    fmri_warning_view = View(
                        Group(
                            Item('fmri_warning_msg',style='readonly',show_label=False),
                            ),
                        title='Warning : fMRI data',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    fmri_config_error_view = View(
                            Group(
                                Item('fmri_config_error_msg', style='readonly',show_label=False),
                                ),
                            title='Error',
                            kind = 'modal',
                            #style_sheet=style_sheet,
                            buttons=['OK','Cancel'])

    open_view = View(
                    Group(
                        Item('base_directory',label='BIDS Dataset'),
                        ),
                    title='Data loading: BIDS dataset selection',
                    kind='modal',
                    #style_sheet=style_sheet,
                    buttons=['OK','Cancel'])

    anat_select_config_to_load = View(
                                  Group(
                                      Item('anat_config_to_load_msg',style='readonly',show_label=False),
                                      Item('anat_config_to_load',style='custom',editor=EnumEditor(name='anat_available_config'),show_label=False),
                                      ),
                                  title='Select configuration for anatomical pipeline',
                                  kind='modal',
                                  #style_sheet=style_sheet,
                                  buttons=['OK','Cancel'])

    anat_custom_map_view = View(
                        Group(
                            Item('anat_custom_last_stage',editor=EnumEditor(name='anat_stage_names'),style='custom',show_label=False),
                            ),
                        title='Select until which stage to process the anatomical pipeline.',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    diffusion_imaging_model_select_view = View(
                                                Group(
                                                    Item('diffusion_imaging_model',label='Diffusion MRI modality'),
                                                    ),
                                                title='Please select diffusion MRI modality',
                                                kind='modal',
                                                buttons=['OK','Cancel'])

    dmri_select_config_to_load = View(
                                Group(
                                    Item('dmri_config_to_load_msg',style='readonly',show_label=False),
                                    ),
                                Item('dmri_config_to_load',style='custom',editor=EnumEditor(name='dmri_available_config'),show_label=False),
                                title='Select configuration for diffusion pipeline',
                                kind='modal',
                                #style_sheet=style_sheet,
                                buttons=['OK','Cancel'])

    dmri_custom_map_view = View(
                        Group(
                            Item('dmri_custom_last_stage',editor=EnumEditor(name='dmri_stage_names'),style='custom',show_label=False),
                            ),
                        title='Select until which stage to process the diffusion pipeline.',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    fmri_select_config_to_load = View(
                                Group(
                                    Item('fmri_config_to_load_msg',style='readonly',show_label=False),
                                    ),
                                Item('fmri_config_to_load',style='custom',editor=EnumEditor(name='fmri_available_config'),show_label=False),
                                title='Select configuration for fMRI pipeline',
                                kind='modal',
                                #style_sheet=style_sheet,
                                buttons=['OK','Cancel'])

    fmri_custom_map_view = View(
                        Group(
                            Item('fmri_custom_last_stage',editor=EnumEditor(name='fmri_stage_names'),style='custom',show_label=False),
                            ),
                        title='Select until which stage to process the fMRI pipeline.',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    def _summary_view_button_fired(self):
        self.configure_traits(view='pipeline_processing_summary_view')


class CMP_BIDSAppWindow(HasTraits):

    project_info = Instance(CMP_Project_Info)

    bids_root = Directory()
    subjects = List(Str)

    # handler = Instance(project.CMP_BIDSAppWindowHandler)

    fs_license = File(os.path.join(os.environ['FREESURFER_HOME'],'license.txt'))
    fs_average = Directory(os.path.join(os.environ['FREESURFER_HOME'],'subjects','fsaverage'))

    list_of_subjects_to_be_processed = List(Str)

    anat_config = File()
    dmri_config = File()
    fmri_config = File()

    run_anat_pipeline = Bool(True)
    run_dmri_pipeline = Bool(True)
    run_fmri_pipeline = Bool(True)

    settings_checked = Bool(False)
    docker_running = Bool(False)

    # check = Action(name='Check settings!',action='check_settings',image=ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-check-settings.png'))))
    # start_bidsapp = Action(name='Start BIDS App!',action='start_bids_app',enabled_when='settings_checked==True and docker_running==False',image=ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-run.png'))))

    check = Button()
    start_bidsapp = Button()

    #stop_bidsapp = Action(name='Stop BIDS App!',action='stop_bids_app',enabled_when='handler.settings_checked and handler.docker_running')

    traits_view = QtView(Group(
                            Group(
                                Group(
                                    Item('bids_root', label='Base directory'),
                                label='BIDS dataset'),
                                Group(
                                    UItem('list_of_subjects_to_be_processed', editor=CheckListEditor(name='subjects'), style='custom', label='Selection'),
                                label='Participants to be processed'),
                                Group(
                                    Group(Item('anat_config',label='Configuration file',visible_when='run_anat_pipeline'), label='Anatomical pipeline'),
                                    Group(Item('run_dmri_pipeline',label='Run processing stages'),Item('dmri_config',label='Configuration file',visible_when='run_dmri_pipeline'), label='Diffusion pipeline'),
                                    Group(Item('run_fmri_pipeline',label='Run processing stages'),Item('fmri_config',label='Configuration file',visible_when='run_fmri_pipeline'), label='fMRI pipeline'),
                                    label='Configuration of processing pipelines'),
                                Group(
                                    Item('fs_license', label='LICENSE'),
                                    Item('fs_average', label='FSaverage directory'),
                                    label='Freesurfer configuration'),
                            orientation='vertical',springy=True),
                            spring,
                            HGroup(Item('check',style='custom',width=80,height=20,resizable=False,label='',show_label=False,
                                                editor_args={
                                                'image':ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-check-settings.png'))),'label':"",'label_value':""}
                                                ),
                                          Item('start_bidsapp',style='custom',width=80,height=20,resizable=False,label='',show_label=False,
                                                editor_args={
                                                'image':ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'bidsapp-run.png'))),'label':"",'label_value':""},
                                                enabled_when='settings_checked==True and docker_running==False'),
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

    def __init__(self, project_info=None, bids_root='', subjects=[''], list_of_subjects_to_be_processed=[''], anat_config='', dmri_config='', fmri_config=''):

        self.project_info = project_info
        self.bids_root = bids_root
        self.subjects = subjects
        # self.list_of_subjects_to_be_processed = list_of_subjects_to_be_processed
        self.anat_config = anat_config
        self.dmri_config = dmri_config
        self.fmri_config = fmri_config

        print(self.list_of_subjects_to_be_processed)
        print(self.bids_root)
        print(self.anat_config)
        print(self.dmri_config)
        print(self.fmri_config)
        print(self.fs_license)
        print(self.fs_average)

        #self.on_trait_change(self.update_run_anat_pipeline,'run_anat_pipeline')
        self.on_trait_change(self.update_run_dmri_pipeline,'run_dmri_pipeline')
        self.on_trait_change(self.update_run_fmri_pipeline,'run_fmri_pipeline')

    def update_run_anat_pipeline(self,new):
        print('Update run anat: %s'%new)
        print('Update run anat: %s'%self.run_anat_pipeline)
        if new == False:
            print('At least anatomical pipeline should be run!')
            self.run_anat_pipeline = True

    def update_run_dmri_pipeline(self,new):
        print('Update run diffusion: %s'%new)
        print('Update run diffusion: %s'%self.run_dmri_pipeline)
        self.run_anat_pipeline = True

    def update_run_fmri_pipeline(self,new):
        print('Update run fmri: %s'%new)
        print('Update run fmri: %s'%self.run_fmri_pipeline)
        self.run_anat_pipeline = True

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

        if os.path.isdir(self.fs_average):
            print("fsaverage directory : {}".format(self.fs_average))
        else:
            print("Error: fsaverage directory ({}) not existing!".format(self.fs_average))
            self.settings_checked = False

        print("Valid inputs for BIDS App : {}".format(self.settings_checked))
        print("Docker running ? {}".format(self.docker_running))
        return True

    def start_bidsapp_process(self, participant_label):
        cmd = ['docker','run','-it','--rm',
               '-v', '{}:/bids_dataset'.format(self.bids_root),
               '-v', '{}/derivatives:/outputs'.format(self.bids_root),
               '-v', '{}:/bids_dataset/derivatives/freesurfer/fsaverage'.format(self.fs_average),
               '-v', '{}:/opt/freesurfer/license.txt'.format(self.fs_license),
               '-v', '{}:/code/ref_anatomical_config.ini'.format(self.anat_config)]

        if self.run_dmri_pipeline:
            cmd.append('-v')
            cmd.append('{}:/code/ref_diffusion_config.ini'.format(self.dmri_config))

        if self.run_fmri_pipeline:
            cmd.append('-v')
            cmd.append('{}:/code/ref_fMRI_config.ini'.format(self.fmri_config))

        cmd.append('-u')
        cmd.append('{}:{}'.format(os.geteuid(),os.getegid()))

        cmd.append('sebastientourbier/connectomemapper-bidsapp:latest')
        cmd.append('/bids_dataset')
        cmd.append('/outputs')
        cmd.append('participant')

        cmd.append('--participant_label')
        cmd.append('{}'.format(participant_label))

        cmd.append('--anat_pipeline_config')
        cmd.append('/code/ref_anatomical_config.ini')

        if self.run_dmri_pipeline:
            cmd.append('--dwi_pipeline_config')
            cmd.append('/code/ref_diffusion_config.ini')

        if self.run_fmri_pipeline:
            cmd.append('--func_pipeline_config')
            cmd.append('/code/ref_fMRI_config.ini')


        print(cmd)

        log_filename = os.path.join(self.bids_root,'derivatives/cmp','sub-{}_log-cmpbidsapp.txt'.format(participant_label))

        with open(log_filename, 'w+') as log:
            proc = Popen(cmd, stdout=log, stderr=log)
            #docker_process.communicate()

        return proc

    def manage_bidsapp_procs(self, proclist):
        for proc in proclist:
            if proc.poll() is not None:
                proclist.remove(proc)

    def start_bids_app(self):
        print("Start BIDS App")

        maxprocs = multiprocessing.cpu_count()
        processes = []

        self.docker_running = True

        project.fix_dataset_directory_in_pickles(local_dir=self.bids_root,mode='bidsapp')

        for label in self.list_of_subjects_to_be_processed:
            while len(processes) == maxprocs:
                self.manage_bidsapp_procs(processes)

            proc = self.start_bidsapp_process(label)
            processes.append(proc)

        while len(processes) > 0:
            self.manage_bidsapp_procs(processes)

        project.fix_dataset_directory_in_pickles(local_dir=self.bids_root,mode='local')

        print('Processing with BIDS App Finished')

        self.docker_running = False

        # cmd = ['docke
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

    # anat_save_config = Action(name='Save anatomical pipeline configuration as...',action='save_anat_config_file')
    # dmri_save_config = Action(name='Save diffusion pipeline configuration as...',action='save_dmri_config_file')
    # fmri_save_config = Action(name='Save fMRI pipeline configuration as...',action='save_fmri_config_file')
    #
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
                        HGroup(Item('save_all_config',style='custom',width=160,height=20,resizable=False,label='',show_label=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('resources', os.path.join('buttons', 'configurator-saveall.png'))),'label':"",'label_value':""},
                                            enabled_when='anat_inputs_checked==True'),
                        show_labels=False,label=""),

                        title='Connectome Mapper 3 Configurator',
                        menubar=MenuBar(
                                    Menu(
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

        self.anat_pipeline.view_mode = 'config_view'
        self.dmri_pipeline.view_mode = 'config_view'
        self.fmri_pipeline.view_mode = 'config_view'

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        #self.on_trait_change(self.update_run_anat_pipeline,'run_anat_pipeline')

    def update_diffusion_imaging_model(self,new):
        self.dmri_pipeline.diffusion_imaging_model = new

    def _save_all_config_fired(self):
        print('Saving pipeline configuration files...')


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

    anat_save_config = Action(name='Save anatomical pipeline configuration as...',action='save_anat_config_file')
    dmri_save_config = Action(name='Save diffusion pipeline configuration as...',action='save_dmri_config_file')
    fmri_save_config = Action(name='Save fMRI pipeline configuration as...',action='save_fmri_config_file')

    anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file')
    dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='load_dmri_config_file')
    fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='load_fmri_config_file')

    traits_view = QtView(Group(
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
                       buttons = [anat_save_config, dmri_save_config, fmri_save_config,],
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

    def __init__(self, project_info=None, anat_pipeline=None, dmri_pipeline=None, fmri_pipeline=None, anat_inputs_checked=False, dmri_inputs_checked=False, fmri_inputs_checked=False):

        self.project_info = project_info

        self.anat_pipeline = anat_pipeline
        self.dmri_pipeline = dmri_pipeline
        self.fmri_pipeline = fmri_pipeline

        self.anat_pipeline.view_mode = 'inspect_outputs_view'
        self.dmri_pipeline.view_mode = 'inspect_outputs_view'
        self.fmri_pipeline.view_mode = 'inspect_outputs_view'

        self.anat_inputs_checked = anat_inputs_checked
        self.dmri_inputs_checked = dmri_inputs_checked
        self.fmri_inputs_checked = fmri_inputs_checked

        self.select_subject()

        #self.on_trait_change(self.update_run_anat_pipeline,'run_anat_pipeline')

    def select_subject(self):
        valid_selected_subject = False

        while not valid_selected_subject:

            #Select subject from BIDS dataset
            self.project_info.configure_traits(view='subject_view')
            self.anat_pipeline.subject = self.project_info.subject
            self.dmri_pipeline.subject = self.project_info.subject
            self.fmri_pipeline.subject = self.project_info.subject
            self.anat_pipeline.global_conf.ubject = self.project_info.subject
            self.dmri_pipeline.global_conf.subject = self.project_info.subject
            self.fmri_pipeline.global_conf.subject = self.project_info.subject

            print("Selected subject: %s" % self.project_info.subject)

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

                self.anat_pipeline.global_conf.subject_session = self.project_info.subject_session
                self.dmri_pipeline.global_conf.subject_session = self.project_info.subject_session
                self.fmri_pipeline.global_conf.subject_session = self.project_info.subject_session

                print("Selected session %s" % self.project_info.subject_session)
            else:
                self.anat_pipeline.global_conf.subject_session.subject_session = ''

                print("No session detected")

            self.anat_pipeline.fill_stages_outputs()
            self.dmri_pipeline.fill_stages_outputs()
            self.fmri_pipeline.fill_stages_outputs()

            # Check if available outputs
            output_anat_available = False
            output_dmri_available = False
            output_fmri_available = False

            for stage in self.anat_pipeline.stages.values():
                stage.define_inspect_outputs()
                print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                if len(stage.inspect_outputs) > 0:
                    output_anat_available = True

            print("Anatomical output(s) available : %s" % output_anat_available)

            for stage in self.dmri_pipeline.stages.values():
                stage.define_inspect_outputs()
                print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                if len(stage.inspect_outputs) > 0:
                    output_dmri_available = True

            print("Diffusion output(s) available : %s" % output_dmri_available)

            for stage in self.fmri_pipeline.stages.values():
                stage.define_inspect_outputs()
                print('Stage {}: {}'.format(stage.stage_dir, stage.inspect_outputs))
                if len(stage.inspect_outputs) > 0:
                    output_fmri_available = True

            print("fMRI output(s) available : %s" % output_fmri_available)

            if output_anat_available or output_dmri_available or output_fmri_available:
                valid_selected_subject = True
            else:
                self.error_msg = "No output available! Please select another subject (and session if any)!"
                self.configure_traits(view='error_view')

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
            print "update subject anat"
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
            print "update subject dmri"
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
            print "update subject fmri"
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
            print "update subject session anat"
            self = self.handler.update_subject_anat_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject anat"
            return

    def update_session_dmri_pipeline(self,new):
        try:
            print "update subject session dmri"
            self = self.handler.update_subject_dmri_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject dmri"
            return

    def update_session_fmri_pipeline(self,new):
        try:
            print "update subject session fmri"
            self = self.handler.update_subject_fmri_pipeline(self)
        except AttributeError:
            print "AttributeError: update subject fmri"
            return

    def show_bidsapp_interface(self):
        print("list_of_subjects_to_be_processed:")
        print(self.project_info.subjects)

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
                                            'image':ImageResource(pkg_resources.resource_filename('cmp', os.path.join('configurator/images', 'configurator.png'))),'label':"",'label_value':""}
                                            ),
                               show_labels=False,label=""),
                        spring,
                        HGroup(Item('bidsapp',style='custom',width=240,height=240,resizable=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('cmp', os.path.join('configurator/images', 'bidsapp.png'))),'label':""}
                                            ),
                               show_labels=False,label=""),
                        spring,
                        HGroup(Item('quality_control',style='custom',width=240,height=240,resizable=False,
                                            editor_args={
                                            'image':ImageResource(pkg_resources.resource_filename('cmp', os.path.join('configurator/images', 'qualitycontrol.png'))),'label':""}
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
                        title='Connectome Mapper 3 BIDS App Manager',
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
        print("list_of_subjects_to_be_processed:")
        print(self.project_info.subjects)

        bids_layout = BIDSLayout(self.project_info.base_directory)
        subjects = bids_layout.get_subjects()

        # anat_config = os.path.join(self.project_info.base_directory,'code/','ref_anatomical_config.ini')
        # dmri_config = os.path.join(self.project_info.base_directory,'code/','ref_diffusion_config.ini')
        # fmri_config = os.path.join(self.project_info.base_directory,'code/','ref_fMRI_config.ini')

        self.bidsapp_ui = CMP_BIDSAppWindow(project_info=self.project_info,
                                         bids_root=self.project_info.base_directory,
                                         subjects=subjects,
                                         list_of_subjects_to_be_processed=subjects,
                                         anat_config=self.project_info.anat_config_file,
                                         dmri_config=self.project_info.dmri_config_file,
                                         fmri_config=self.project_info.fmri_config_file
                                          # anat_config=anat_config,
                                          # dmri_config=dmri_config,
                                          # fmri_config=fmri_config
                                         )
        self.bidsapp_ui.configure_traits()

    def _configurator_fired(self):
        """ Callback of the "configurator" button. This displays the Configurator GUI.
        """
        if os.path.isfile(self.project_info.anat_config_file):
            print("Load anatomical config file %s"%self.project_info.anat_config_file)

        if os.path.isfile(self.project_info.dmri_config_file):
            print("Load diffusion config file %s"%self.project_info.dmri_config_file)

        if os.path.isfile(self.project_info.fmri_config_file):
            print("Load fMRI config file %s"%self.project_info.fmri_config_file)

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
        if os.path.isfile(self.project_info.anat_config_file):
            print("Load anatomical config file %s"%self.project_info.anat_config_file)

        if os.path.isfile(self.project_info.dmri_config_file):
            print("Load diffusion config file %s"%self.project_info.dmri_config_file)

        if os.path.isfile(self.project_info.fmri_config_file):
            print("Load fMRI config file %s"%self.project_info.fmri_config_file)

        print(self.anat_pipeline)
        print(self.dmri_pipeline)
        print(self.fmri_pipeline)

        print(self.project_info.t1_available)
        print(self.project_info.dmri_available)
        print(self.project_info.fmri_available)

        self.quality_control_ui = CMP_QualityControlWindow(project_info = self.project_info,
                                                    anat_pipeline=self.anat_pipeline,
                                                    dmri_pipeline=self.dmri_pipeline,
                                                    fmri_pipeline=self.fmri_pipeline,
                                                    anat_inputs_checked=self.project_info.t1_available,
                                                    dmri_inputs_checked=self.project_info.dmri_available,
                                                    fmri_inputs_checked=self.project_info.fmri_available
                                                    )

        self.quality_control_ui.configure_traits()

    def show_bidsapp_interface(self):
        print("list_of_subjects_to_be_processed:")
        print(self.project_info.subjects)

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
