# Copyright (C) 2009-2014, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
    process_type = Enum('Diffusion',['Diffusion'])
    last_date_processed = Str('Not yet processed')
    last_stage_processed = Str('Not yet processed')
    stage_names = List
    custom_map_stages = List

    create_view = View( Item('process_type',style='custom'),
                        'base_directory',
                        title='Select type of pipeline and base directory for new Connectome Data',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])

    open_view = View('base_directory',
                        title='Select directory of existing Connectome Data',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])
                        
    custom_map_view = View(Item('custom_map_stages',editor=CheckListEditor(name='stage_names'),style='custom',show_label=False),
                        title='Select which stages to process.',
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
                            Item('pipeline',style='custom',enabled_when='handler.inputs_checked==True',show_label=False,width=800,height=710),
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
                   )




