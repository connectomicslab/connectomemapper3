
import os
from nipype.utils.filemanip import copyfile
import nipype.interfaces.diffusion_toolkit as dtk
from nipype.caching import Memory

def convert_rawdata(base_directory, input_dir):
	file_list = os.listdir(input_dir)
	input_name = os.path.basename(input_dir)
	
	# If RAWDATA folder contains one (and only one) nifti file -> copy it
	first_file = os.path.join(input_dir, file_list[0])
	if len(file_list) == 1 and first_file.endswith('nii.gz'):
		copyfile(first_file, os.path.join(base_directory, 'NIFTI', input_name+'nii.gz'), False, False, 'content') # intelligent copy looking at input's content
	else:
		mem = Memory(base_dir=os.path.join(base_directory,'NIPYPE'))
		dtk_diffunpack = mem.cache(dtk.DiffUnpack)
		res = dtk_diffunpack(input_dicom=first_file, out_prefix=os.path.join(base_directory, 'NIFTI', input_name), output_type='nii.gz')
		if len(res.outputs.get()) == 0:
			return False
			
	return True
	
