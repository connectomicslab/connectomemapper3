# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper GUI
"""

# Libraries imports
from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView

# CMP imports
import project

global style_sheet
style_sheet = '''
            QLabel {
                font: 12pt "Verdana";
                margin-left: 25px;
            }
            QPushButton {
                border: 0px solid lightgray;
                border-radius: 6px;
                background-color: transparent;
                min-width: 80px;
                font: 12pt "Verdana";
                margin: 3px 3px 3px 3px;
                padding: 3px 3px;
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
            }
            QMainWindow::separator {
                background: yellow;
                width: 10px; /* when vertical */
                height: 10px; /* when horizontal */
            }
            QMainWindow::separator:hover {
                background: red;
            }
            QDockWidget {
                border: 1px solid lightgray;
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(undock.png);
            }

            QDockWidget::title {
                text-align: left; /* align the text to the left */
                background: lightgray;
                padding-left: 5px;
            }

            QDockWidget::close-button, QDockWidget::float-button {
                border: 1px solid transparent;
                background: darkgray;
                padding: 0px;
            }

            QDockWidget::close-button:hover, QDockWidget::float-button:hover {
                background: gray;
            }

            QDockWidget::close-button:pressed, QDockWidget::float-button:pressed {
                padding: 1px -1px -1px 1px;
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

class CMP_Project_Info(HasTraits):
    base_directory = Directory
    subjects = List(['sub-01','sub-02'])
    subject = Enum(values='subjects')
    #current_subj = Str()
    warning_msg = Str('\nWarning: selected directory is already configured.\n\nDo you want to reset the configuration to default parameters ?\n')
    config_error_msg = Str('')
    process_type = Enum('diffusion',['diffusion','fMRI'])
    diffusion_imaging_model = Enum('DSI',['DSI','DTI','HARDI'])
    config_to_load = Str()
    available_config = List()
    config_to_load_msg = Str('Several configuration files available.Select which one to load:\n')
    last_date_processed = Str('Not yet processed')
    last_stage_processed = Str('Not yet processed')
    stage_names = List
    custom_last_stage = Str

    create_view = QtView( Item('process_type',style='custom'),Item('diffusion_imaging_model',style='custom',visible_when='process_type=="diffusion"'),
                        Item('base_directory',label='BIDS dataset directory'),
                        title='Select type of pipeline, diffusion model (if diffusion) and BIDS base directory ',
                        kind='livemodal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    subject_view = QtView(Item('subject',label='Subject to be processed'),
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    warning_view = QtView( Item('warning_msg',style='readonly',show_label=False),
                        title='Warning',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    config_error_view = QtView( Item('config_error_msg', style='readonly',show_label=False),
                              title='Error',
                              kind = 'modal',
                              style_sheet=style_sheet,
                              buttons=['OK','Cancel'])

    open_view = QtView(Item('base_directory',label='BIDS dataset directory'),
                        title='Select BIDS directory with existing Connectome Data',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    select_config_to_load = QtView(Item('config_to_load_msg',style='readonly',show_label=False),
                                  Item('config_to_load',style='custom',editor=EnumEditor(name='available_config'),show_label=False),
                                  title='Select configuration',
                                  kind='modal',
                                  #style_sheet=style_sheet,
                                  buttons=['OK','Cancel'])

    custom_map_view = QtView(Item('custom_last_stage',editor=EnumEditor(name='stage_names'),style='custom',show_label=False),
                        title='Select until which stage to process.',
                        kind='modal',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

## Main window class of the ConnectomeMapper_Pipeline
#
class CMP_MainWindow(HasTraits):
    pipeline = Instance(HasTraits)
    project_info = Instance(CMP_Project_Info)

    new_project = Action(name='New Connectome data...',action='new_project')
    load_project = Action(name='Load Connectome data...',action='load_project')
    preprocessing = Action(name='Check BIDS dataset',action='check_input',enabled_when='handler.project_loaded==True')
    map_connectome = Action(name='Map Connectome!',action='map_connectome',enabled_when='handler.inputs_checked==True')
    map_custom = Action(name='Custom mapping...',action='map_custom',enabled_when='handler.inputs_checked==True')
    change_subject = Action(name='Change subject',action='change_subject',enabled_when='handler.project_loaded==True')
    save_config = Action(name='Save configuration as...',action='save_config_file',enabled_when='handler.project_loaded==True')
    load_config = Action(name='Load configuration...',action='load_config_file',enabled_when='handler.project_loaded==True')

    project_info.style_sheet = style_sheet

    traits_view = QtView(HGroup(
                            Item('pipeline',style='custom',enabled_when='handler.inputs_checked==True',show_label=False),
                            ),
                       title='Connectome Mapper 3',
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
                                   save_config,
                                   load_config,
                                name='Configuration'),
                               Menu(
                                   change_subject,
                                name='Subjects'),
                          ),
                       handler = project.ProjectHandler(),
                       style_sheet=style_sheet,
                       buttons = [preprocessing, map_connectome, map_custom],
                       width=0.5, height=0.8, scrollable=True, resizable=True
                   )
