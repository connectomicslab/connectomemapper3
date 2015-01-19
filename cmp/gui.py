# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper GUI
""" 

# Libraries imports
from traits.api import *
from traitsui.api import *

# CMP imports
import project

class CMP_Project_Info(HasTraits):
    base_directory = Directory
    warning_msg = Str('\nWarning: selected directory is already configured.\n\nDo you want to reset the configuration to default parameters ?\n')
    config_error_msg = Str('')
    process_type = Enum('diffusion',['diffusion','fMRI'])
    config_to_load = Str()
    available_config = List()
    config_to_load_msg = Str('Several configuration files available.Select which one to load:\n')
    last_date_processed = Str('Not yet processed')
    last_stage_processed = Str('Not yet processed')
    stage_names = List
    custom_last_stage = Str

    create_view = View( Item('process_type',style='custom'),
                        'base_directory',
                        title='Select type of pipeline and base directory',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])
    
    warning_view = View( Item('warning_msg',style='readonly',show_label=False),
                        title='Warning',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])
    
    config_error_view = View( Item('config_error_msg', style='readonly',show_label=False),
                              title='Error',
                              kind = 'modal',
                              width=400,
                              buttons=['OK','Cancel'])

    open_view = View('base_directory',
                        title='Select directory of existing Connectome Data',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])
    
    select_config_to_load = View(Item('config_to_load_msg',style='readonly',show_label=False),
                                  Item('config_to_load',style='custom',editor=EnumEditor(name='available_config'),show_label=False),
                                  title='Select configuration',
                                  kind='modal',
                                  width=400,
                                  buttons=['OK','Cancel'])
                        
    custom_map_view = View(Item('custom_last_stage',editor=EnumEditor(name='stage_names'),style='custom',show_label=False),
                        title='Select until which stage to process.',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])

## Main window class of the ConnectomeMapper_Pipeline
#
class CMP_MainWindow(HasTraits):
    pipeline = Instance(HasTraits)
    project_info = Instance(CMP_Project_Info)
    
    new_project = Action(name='New Connectome data...',action='new_project')
    load_project = Action(name='Load Connectome data...',action='load_project')
    preprocessing = Action(name='Check input data',action='check_input',enabled_when='handler.project_loaded==True')
    map_connectome = Action(name='Map Connectome!',action='map_connectome',enabled_when='handler.inputs_checked==True')
    map_custom = Action(name='Custom mapping...',action='map_custom',enabled_when='handler.inputs_checked==True')
    save_config = Action(name='Save configuration as...',action='save_config_file',enabled_when='handler.project_loaded==True')
    load_config = Action(name='Load configuration...',action='load_config_file',enabled_when='handler.project_loaded==True')

    traits_view = View(HGroup(
                            Item('pipeline',style='custom',enabled_when='handler.inputs_checked==True',show_label=False,width=800,height=700),
                            ),
                       title='Connectome Mapper',
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
                          ),
                       handler = project.ProjectHandler(),
                       buttons = [preprocessing, map_connectome, map_custom],
                       height= 0.75, scrollable=True
                   )




