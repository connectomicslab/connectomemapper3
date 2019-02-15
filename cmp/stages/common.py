# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common class for CMP Stages
"""

# Libraries imports
from traits.api import *
import subprocess
import os

##  Stage master class, will be inherited by the various stage subclasses. Inherits from HasTraits.
#
class Stage(HasTraits):
    inspect_outputs = ['Outputs not available']
    inspect_outputs_enum = Enum(values='inspect_outputs')
    inspect_outputs_dict = Dict
    enabled = True
    config = Instance(HasTraits)

    def is_running(self):
        unfinished_files = [os.path.join(dirpath, f)
                                          for dirpath, dirnames, files in os.walk(self.stage_dir)
                                          for f in files if f.endswith('_unfinished.json')]
        return len(unfinished_files)
