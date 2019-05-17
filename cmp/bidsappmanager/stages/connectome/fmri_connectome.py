# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for building connectivity matrices and resulting CFF file
"""

# Global imports
import os
import pickle
import gzip

from traits.api import *
from traitsui.api import *
import subprocess

# Own imports
#from cmp.bidsappmanager.stages.common import Stage

from cmp.stages.connectome.fmri_connectome import ConnectomeConfig, ConnectomeStage

class ConnectomeConfigUI(ConnectomeConfig):
    
    output_types = List(['gPickle'], editor=CheckListEditor(values=['gPickle','mat','cff','graphml'],cols=4))

    traits_view = View(VGroup('apply_scrubbing',VGroup(Item('FD_thr',label='FD threshold'),Item('DVARS_thr',label='DVARS threshold'),visible_when="apply_scrubbing==True")),
                       Item('output_types',style='custom'))


class ConnectomeStageUI(ConnectomeStage):

    log_visualization = Bool(True)
    circular_layout = Bool(False)

    inspect_output_button = Button('View')

    inspect_outputs_view = View(Group(
                            Item('name',editor=TitleEditor(),show_label=False),
                            Group(
                                Item('log_visualization',label='Log scale'),
                                Item('circular_layout',label='Circular layout'),
                                label='Visualization', show_border=True
                                ),
                            Group(
                                Item('inspect_outputs_enum',show_label=False),
                                Item('inspect_output_button',enabled_when='inspect_outputs_enum!="Outputs not available"',show_label=False),
                                label = 'View outputs', show_border=True
                                )
                            ),
                            scrollable=True, resizable=True, kind='livemodal', title='Inspect stage outputs', buttons=['OK','Cancel']
                        )

    config_view = View(Group(
                            Item('name',editor=TitleEditor(),show_label=False),
                            Group(
                                Item('config',style='custom',show_label=False),
                                label = 'Configuration', show_border=True
                                ),
                            ),
                            scrollable=True, resizable=True, height=200, width=408, kind='livemodal', title='Edit stage configuration', buttons=['OK','Cancel']
                        )

    def __init__(self):
        ConnectomeStage.__init__(self)
        self.config = ConnectomeConfigUI()

    def _log_visualization_changed(self, new):
        self.config.log_visualization = new
        self.define_inspect_outputs()

    def _circular_layout_changed(self, new):
        self.config.circular_layout = new
        self.define_inspect_outputs()


    def _inspect_output_button_fired(self,info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
