# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
"""

import os
import pickle
import gzip

from traits.api import *
from traitsui.api import *

import subprocess

#from cmp.bidsappmanager.stages.common import Stage

from cmp.stages.preprocessing.fmri_preprocessing import PreprocessingConfig, PreprocessingStage

class PreprocessingConfigUI(PreprocessingConfig):

    traits_view = View('discard_n_volumes','despiking','slice_timing',Item('repetition_time',visible_when='slice_timing!="none"'),'motion_correction')


class PreprocessingStageUI(PreprocessingStage):

    inspect_output_button = Button('View')

    inspect_outputs_view = View(Group(
                            Item('name',editor=TitleEditor(),show_label=False),
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
                            scrollable=True, resizable=True, height=280, width=350, kind='livemodal', title='Edit stage configuration', buttons=['OK','Cancel']
                        )

    # General and UI members
    def __init__(self):
        PreprocessingStage.__init__(self)
        self.config = PreprocessingConfigUI()

    def _inspect_output_button_fired(self,info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
