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
import multiprocessing

from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.api import ImageResource

from bids.grabbids import BIDSLayout

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
                icon-size: 450px;
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
                image: url("cmp3_icon.png");
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

    bids_layout = Instance(BIDSLayout)
    subjects = List([])
    subject = Enum(values='subjects')

    number_of_subjects = Int()

    subject_sessions = List([])
    subject_session = Enum(values='subject_sessions')

    #current_subj = Str()
    anat_warning_msg = Str('\nWarning: selected directory is already configured for anatomical data processing.\n\nDo you want to reset the configuration to default parameters ?\n')
    dmri_warning_msg = Str('\nWarning: selected directory is already configured for diffusion data processing.\n\nDo you want to reset the configuration to default parameters ?\n')

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
                            Item('subject',label='Subject to be processed'),
                            # Item('session',label='Session to be processed'),
                            # Item('diffusion_imaging_model',style='custom'),
                            ),
                        kind='modal',
                        title='Subject and session selection',
                        #style_sheet=style_sheet,
                        buttons=['OK','Cancel'])

    subject_session_view = View(
                        Group(
                            Item('subject_session',label='Session to be processed'),
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

## Main window class of the ConnectomeMapper_Pipeline
#
class CMP_MainWindow(HasTraits):
    anat_pipeline = Instance(HasTraits)
    dmri_pipeline = Instance(HasTraits)
    fmri_pipeline = Instance(HasTraits)

    project_info = Instance(CMP_Project_Info)

    handler = Instance(project.ProjectHandler)

    new_project = Action(name='Load BIDS Dataset (New)...',action='new_project')
    load_project = Action(name='Load BIDS Dataset (Processed)...',action='load_project')
    process_anatomical = Action(name='Parcellate Brain!',action='process_anatomical',enabled_when='handler.anat_inputs_checked==True')
    #preprocessing = Action(name='Check BIDS dataset',action='check_input',enabled_when='handler.project_loaded==True')
    map_dmri_connectome = Action(name='Map Strutural Connectome!',action='map_dmri_connectome',enabled_when='handler.anat_outputs_checked and handler.dmri_inputs_checked')
    map_fmri_connectome = Action(name='Map Functional Connectome!',action='map_fmri_connectome',enabled_when='handler.anat_outputs_checked and handler.fmri_inputs_checked')
    #map_custom = Action(name='Custom mapping...',action='map_custom',enabled_when='handler.inputs_checked==True')
    #change_subject = Action(name='Change subject',action='change_subject',enabled_when='handler.project_loaded==True')

    anat_save_config = Action(name='Save anatomical pipeline configuration as...',action='anat_save_config_file',enabled_when='handler.project_loaded==True')
    anat_load_config = Action(name='Load anatomical pipeline configuration...',action='anat_load_config_file',enabled_when='handler.project_loaded==True')

    dmri_save_config = Action(name='Save diffusion pipeline configuration as...',action='dmri_save_config_file',enabled_when='handler.project_loaded==True')
    dmri_load_config = Action(name='Load diffusion pipeline configuration...',action='dmri_load_config_file',enabled_when='handler.project_loaded==True')

    fmri_save_config = Action(name='Save fMRI pipeline configuration as...',action='fmri_save_config_file',enabled_when='handler.project_loaded==True')
    fmri_load_config = Action(name='Load fMRI pipeline configuration...',action='fmri_load_config_file',enabled_when='handler.project_loaded==True')

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
                                        anat_save_config,
                                        anat_load_config,
                                        dmri_save_config,
                                        dmri_load_config,
                                    name='Configuration'),
                                    # Menu(
                                    #     change_subject,
                                    # name='Subjects'),
                                ),
                       handler = project.ProjectHandler(),
                       style_sheet=style_sheet,
                       buttons = [process_anatomical,map_dmri_connectome,map_fmri_connectome],
                       #buttons = [preprocessing, map_connectome, map_custom],
                       width=0.5, height=0.8, resizable=True,#, scrollable=True, resizable=True
                       icon=ImageResource('cmp3_icon')
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
