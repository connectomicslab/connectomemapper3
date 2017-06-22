# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common class for CMP Stages
""" 

# Libraries imports
from traits.api import *
from traitsui.api import *
import subprocess
import os

##  Stage master class, will be inherited by the various stage subclasses. Inherits from HasTraits.
#
class Stage(HasTraits):
    inspect_outputs = ['Outputs not available']
    inspect_outputs_enum = Enum(values='inspect_outputs')
    inspect_outputs_dict = Dict
    inspect_output_button = Button('View')
    enabled = True
    config = Instance(HasTraits)

    traits_view = View(Group(
                            Item('name',editor=TitleEditor(),show_label=False),
                            Group(
                                Item('config',style='custom',show_label=False),
                                label = 'Configuration', show_border=True
                                ),
                            Group(
                                Item('inspect_outputs_enum',show_label=False),Item('inspect_output_button',enabled_when='inspect_outputs_enum!="Outputs not available"',show_label=False),
                                label = 'View outputs', show_border=True
                                )
                            ),
                            scrollable=True, resizable=True, kind='livemodal', title='Edit stage configuration', buttons=['OK','Cancel']
                        )

    def _inspect_output_button_fired(self,info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
        
    def is_running(self):
        unfinished_files = [os.path.join(dirpath, f)
                                          for dirpath, dirnames, files in os.walk(self.stage_dir)
                                          for f in files if f.endswith('_unfinished.json')]
        return len(unfinished_files)



