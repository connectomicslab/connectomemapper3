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

from cmp.stages.preprocessing.preprocessing import PreprocessingConfig, PreprocessingStage

class PreprocessingConfigUI(PreprocessingConfig):

    traits_view = View(
                    VGroup(
                        # VGroup(
                        # HGroup(
                        #     Item('start_vol',label='Vol'),
                        #     Item('end_vol',label='to'),
                        #     Item('max_str',style='readonly',show_label=False)
                        #     ),
                        #     label='Processed volumes'),
                        VGroup(
                        HGroup(
                            Item('denoising'),
                            Item('denoising_algo',label='Tool:',visible_when='denoising==True'),
                            Item('dipy_noise_model',label='Noise model (Dipy):',visible_when='denoising_algo=="Dipy (NLM)"')
                            ),
                        HGroup(
                            Item('bias_field_correction'),
                            Item('bias_field_algo',label='Tool:',visible_when='bias_field_correction==True')
                            ),
                        VGroup(
                        HGroup(
                            Item('eddy_current_and_motion_correction'),
                            Item('eddy_correction_algo',visible_when='eddy_current_and_motion_correction==True'),
                            ),
                            Item('eddy_correct_motion_correction',label='Motion correction',visible_when='eddy_current_and_motion_correction==True and eddy_correction_algo=="FSL eddy_correct"'),
                            Item('total_readout',label='Total readout time (s):',visible_when='eddy_current_and_motion_correction==True and eddy_correction_algo=="FSL eddy"')
                        ),
                        label='Preprocessing steps'),
                        VGroup(
                        VGroup(
                            Item('resampling',label='Voxel size (x,y,z)',editor=TupleEditor(cols=3)),
                            'interpolation'
                            ),
                        label='Final resampling')
                        ),
                    width=0.5,height=0.5)

    # def _max_vol_changed(self,new):
    #     self.max_str = '(max: %d)' % new
    #     #self.end_vol = new
    #
    # def _end_vol_changed(self,new):
    #     if new > self.max_vol:
    #         self.end_vol = self.max_vol
    #
    # def _start_vol_changed(self,new):
    #     if new < 0:
    #         self.start_vol = 0


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
                            scrollable=True, resizable=True, height=350, width=650, kind='livemodal', title='Edit stage configuration', buttons=['OK','Cancel']
                        )

    # General and UI members
    def __init__(self):
        PreprocessingStage.__init__(self)
        self.config = PreprocessingConfigUI()

    def _inspect_output_button_fired(self,info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
