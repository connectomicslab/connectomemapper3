# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common class for CMP Stages
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

##  Stage master class, will be inherited by the various stage subclasses. Inherits from HasTraits.
#
class CMP_Stage(HasTraits):
    output_options = ['Stage not yet run']
    view_output_choice = Enum(values='output_options')
    view_output = Button('View')
    outputs = Dict
    config = Instance(HasTraits)
    description = Str('No description')
    enabled = True
    name = ''

    traits_view = View(Group(
                            Item('name',editor=TitleEditor(),show_label=False),
#                           Group(
#                               Item('description',style='custom',enabled_when='1>2',show_label=False),
#                               label = 'Description', show_border=True
#                               ),
                            Group(
                                Item('config',style='custom',show_label=False,visible_when='enabled=True'),
                                label = 'Configuration', show_border=True
                                ),
                            Group(
                                Item('view_output_choice'),Item('view_output',enabled_when='len(outputs)>0'),
                                label = 'View outputs', show_border=True
                                )
                            ),
                            spring, kind='livemodal', title='Edit stage configuration', buttons=['OK','Cancel']
                        )

    def _view_output_fired(self,info):
        choice = self.outputs[self.view_output_choice]
        if isinstance(choice,list):
            for c in choice:
                _,_,ext = split_filename(c)
                if ext == '.nii' or ext == '.nii.gz':
                    viewer_args = ['fslview',c]
                if ext == '.trk':
                    viewer_args = ['trackvis',c]
                if ext == '.bmp' or ext == '.png' or ext == '.jpg':
                    viewer_args = ['eog',c]
                if ext == '.mgz':
                    viewer_args = ['tkmedit -f',c]
                subprocess.Popen(viewer_args)
        else:
            _,_,ext = split_filename(choice)
            if ext == '.nii' or ext == '.nii.gz':
                viewer_args = ['fslview',choice]
            if ext == '.trk':
                viewer_args = ['trackvis',choice]
            if ext == '.bmp' or ext == '.png' or ext == '.jpg':
                viewer_args = ['eog',choice]
            if ext == '.mgz':
                viewer_args = ['tkmedit -f',choice]
            subprocess.Popen(viewer_args)


