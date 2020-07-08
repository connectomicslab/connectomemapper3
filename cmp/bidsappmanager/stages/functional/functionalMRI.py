# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license ModifFied BSD.

""" CMP Stage for Diffusion reconstruction and tractography
"""

# General imports

from traits.api import *
from traitsui.api import *

import subprocess

# Own imports
# from cmp.bidsappmanager.stages.common import Stage

from cmp.stages.functional.functionalMRI import FunctionalMRIConfig, FunctionalMRIStage


class FunctionalMRIConfigUI(FunctionalMRIConfig):
    traits_view = View(  # Item('smoothing'),
        # Item('discard_n_volumes'),
        HGroup(
            Item('detrending'), Item(
                'detrending_mode', visible_when='detrending'),
            label='Detrending', show_border=True
        ),
        HGroup(
            Item('global_nuisance', label="Global"),
            Item('csf'),
            Item('wm'),
            Item('motion'),
            label='Nuisance factors', show_border=True
        ),
        HGroup(
            Item('lowpass_filter', label='Low cutoff (volumes)'),
            Item('highpass_filter', label='High cutoff (volumes)'),
            label="Bandpass filtering", show_border=True
        )
    )


class FunctionalMRIStageUI(FunctionalMRIStage):
    inspect_output_button = Button('View')

    inspect_outputs_view = View(Group(
        Item('name', editor=TitleEditor(), show_label=False),
        Group(
            Item('inspect_outputs_enum', show_label=False),
            Item('inspect_output_button', enabled_when='inspect_outputs_enum!="Outputs not available"',
                 show_label=False),
            label='View outputs', show_border=True
        )
    ),
        scrollable=True, resizable=True, kind='livemodal', title='Inspect stage outputs', buttons=['OK', 'Cancel']
    )

    config_view = View(Group(
        Item('name', editor=TitleEditor(), show_label=False),
        Group(
            Item('config', style='custom', show_label=False),
            label='Configuration', show_border=True
        ),
    ),
        scrollable=True, resizable=True, height=528, width=608, kind='livemodal', title='Edit stage configuration',
        buttons=['OK', 'Cancel']
    )

    def __init__(self, bids_dir, output_dir):
        FunctionalMRIStage.__init__(self, bids_dir, output_dir)
        self.config = FunctionalMRIConfigUI()

    def _inspect_output_button_fired(self, info):
        subprocess.Popen(self.inspect_outputs_dict[self.inspect_outputs_enum])
