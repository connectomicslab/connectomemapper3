# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
""" 

try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *
from cmp.stages.common import CMP_Stage

class Preprocessing_Config(HasTraits):
    description = Str('description')

class Preprocessing(CMP_Stage):
    # General and UI members
    name = 'Preprocessing'
    config = Preprocessing_Config()

