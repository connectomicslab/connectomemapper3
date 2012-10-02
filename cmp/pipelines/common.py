
import os
from nipype.utils.filemanip import copyfile
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
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
	
def swap_and_reorient(base_directory,src_file, ref_file):
    mem = Memory(base_dir=os.path.join(base_directory,'NIPYPE'))
    
    fs_imageinfo = mem.cache(fs.utils.ImageInfo)
    fsl_orient = mem.cache(fsl.Orient)
    fsl_swapdim = mem.cache(fsl.SwapDimensions)
    
    src_orient = fs_imageinfo(in_file=src_file).outputs.orientation # "orientation" => 3 letter acronym defining orientation
    ref_orient = fs_imageinfo(in_file=ref_file).outputs.orientation
    src_conv = fsl_orient(in_file=src_file, get_orient=True).outputs.orient # "convention" => RADIOLOGICAL/NEUROLOGICAL
    ref_conv = fsl_orient(in_file=ref_file, get_orient=True).outputs.orient
    
    
    # if needed, match orientation to reference
    if src_orient == ref_orient:
        return True # no reorientation needed
    else:
        if src_conv != ref_conv:
            # if needed, match convention (radiological/neurological) to reference
            # copy src
            csrc = os.path.join(os.path.dirname(src_file),'orig-orient-' +  os.path.basename(src_file))
            tmpsrc = os.path.join(os.path.dirname(src_file), 'temp-' + os.path.basename(src_file))
            shutil.move(src_file, csrc)
        
            fsl_swapdim(in_file=csrc, new_dims='-x y z', out_file=tmpsrc)
        
            fsl_orient(in_file=tmpsrc, swap_orient=True)
        else:
            # If conventions match, just use the original source
            tmpsrc = src_file
    
    tmp2 = os.path.join(os.path.dirname(src), 'tmp.nii.gz')
    
    if ref_orient == 'LPS':
        fsl_swapdim(in_file=tmpsrc, new_dims='RL AP IS', out_file=tmp2)
    elif ref_orient == 'LPI':
        fsl_swapdim(in_file=tmpsrc, new_dims='RL AP SI', out_file=tmp2)
    else:
        return False
    
    shutil.move(tmp2, src)
    
    # Only remove the temporary file if the conventions did not match.  Otherwise,
    # we end up removing the output.
    if tmpsrc != src:
        os.remove(tmpsrc)
    return True 
	
