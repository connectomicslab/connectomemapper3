# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Connectome Mapper GUI
""" 

# Libraries imports
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

# CMP imports
import project

class CMP_Project_Info(HasTraits):
    base_directory = Directory
    process_type = Enum('Diffusion',['Diffusion'])
    last_date_processed = Str('Not yet processed')
    last_stage_processed = Str('Not yet processed')
    stage_names = List
    custom_map_stop = Str

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
                        
    custom_map_view = View(Item('custom_map_stop',editor=EnumEditor(name='stage_names')),
                        title='Select until which stage of the pipeline to process.',
                        kind='modal',
                        width=400,
                        buttons=['OK','Cancel'])
                        

    traits_view = View(Group(
                            Group(
                                Item('base_directory',enabled_when='1>2',show_label=False),
                                label='Base directory',
                            ),
                            Group(
                                Item('process_type',style='readonly'),
                                Item('last_date_processed',style='readonly'),
                                Item('last_stage_processed',style='readonly'),
                                label='Last processing'
                            ),
                        ),
                        #width=200,
                        )


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

    traits_view = View(HGroup(
                            Item('pipeline',style='custom',enabled_when='handler.inputs_checked==True',show_label=False,width=400,height=600),
                            Item('project_info',style='custom',show_label=False,width=400),
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
                                   Action(name='Save configuration as...',action='_save_config'),
                                   Action(name='Load configuration...',action='_load_config'),
                                name='Configuration'),
                          ),
                       handler = project.ProjectHandler(),
                       buttons = [preprocessing, map_connectome, map_custom],
                   )




