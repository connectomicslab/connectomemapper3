# Libraries imports
try: 
	from traits.api import *
	from traitsui.api import *
except ImportError: 
	from enthought.traits.api import *
	from enthought.traits.ui.api import *

##	Stage master class, will be inherited by the various stage subclasses. Inherits from HasTraits.
#
class CMP_Stage(HasTraits):
	output_options = ['Stage not yet run']
	view_output_choice = Enum(values='output_options')
	view_output = Button('View')
	outputs = Dict
	config = Instance(HasTraits)
	description = Str('No description')
	enabled = True

	traits_view = View(Group(
							Group(
								Item('description',style='custom',enabled_when='1>2',show_label=False),
								label = 'Description', show_border=True
								),
							Group(
								Item('config',style='custom',show_label=False,visible_when='enabled=True'),
								label = 'Configuration', show_border=True
								),
							Group(
								Item('view_output_choice'),Item('view_output',enabled_when='len(outputs)>0'),
								label = 'View outputs', show_border=True
								)
							),
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

