# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common functions for CMP pipelines
""" 

import os
import shutil
from nipype.utils.filemanip import copyfile
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
from nipype.caching import Memory
from nipype.interfaces.base import BaseInterface, \
    BaseInterfaceInputSpec, File, TraitedSpec, isdefined
from nipype.utils.filemanip import split_filename

def convert_rawdata(base_directory, input_dir, out_prefix):
    file_list = os.listdir(input_dir)

    # If RAWDATA folder contains one (and only one) nifti file -> copy it
    first_file = os.path.join(input_dir, file_list[0])
    if len(file_list) == 1 and first_file.endswith('nii.gz'):
        copyfile(first_file, os.path.join(base_directory, 'NIFTI', out_prefix+'nii.gz'), False, False, 'content') # intelligent copy looking at input's content
    else:
        mem = Memory(base_dir=os.path.join(base_directory,'NIPYPE'))
        dtk_diffunpack = mem.cache(dtk.DiffUnpack)
        res = dtk_diffunpack(input_dicom=first_file, out_prefix=os.path.join(base_directory, 'NIFTI', out_prefix), output_type='nii.gz')
        if len(res.outputs.get()) == 0:
            return False

    return True
    
class SwapAndReorientInputSpec(BaseInterfaceInputSpec):
    src_file = File(desc='Source file to be reoriented.',exists=True,mandatory=True)
    ref_file = File(desc='Reference file, which orientation will be applied to src_file.',exists=True,mandatory=True)
    out_file = File(desc='Name of the reoriented file.',genfile=True,hash_files=False)
    
class SwapAndReorientOutputSpec(TraitedSpec):
    out_file = File(desc='Reoriented file.',exists=True)

class SwapAndReorient(BaseInterface):
    input_spec = SwapAndReorientInputSpec
    output_spec = SwapAndReorientOutputSpec
    
    def _gen_outfilename(self):
        out_file = self.inputs.out_file
        path,base,ext = split_filename(self.inputs.src_file)
        if not isdefined(self.inputs.out_file):
            out_file = os.path.join(path,base+'_reoriented'+ext)

        return os.path.abspath(out_file)
    
    def _run_interface(self, runtime):
        out_file = self._gen_outfilename()
        src_file = self.inputs.src_file
        ref_file = self.inputs.ref_file
    
        # Collect orientation infos
        
        # "orientation" => 3 letter acronym defining orientation
        src_orient = fs.utils.ImageInfo(in_file=src_file).run().outputs.orientation
        ref_orient = fs.utils.ImageInfo(in_file=ref_file).run().outputs.orientation
        # "convention" => RADIOLOGICAL/NEUROLOGICAL
        src_conv = fsl.Orient(in_file=src_file, get_orient=True).run().outputs.orient
        ref_conv = fsl.Orient(in_file=ref_file, get_orient=True).run().outputs.orient
        
        if src_orient == ref_orient:
            # no reorientation needed
            copyfile(src_file,out_file,False, False, 'content')
            return runtime
        else:
            if src_conv != ref_conv:
                # if needed, match convention (radiological/neurological) to reference
                tmpsrc = os.path.join(os.path.dirname(src_file), 'tmp_' + os.path.basename(src_file))
        
                fsl.SwapDimensions(in_file=src_file, new_dims=('-x','y','z'), out_file=tmpsrc).run()
        
                fsl.Orient(in_file=tmpsrc, swap_orient=True).run()
            else:
                # If conventions match, just use the original source
                tmpsrc = src_file
                
        tmp2 = os.path.join(os.path.dirname(src_file), 'tmp.nii.gz')
        if ref_orient == 'LPS':
            fsl.SwapDimensions(in_file=tmpsrc, new_dims=('RL','AP','IS'), out_file=tmp2).run()
        elif ref_orient == 'LPI':
            fsl.SwapDimensions(in_file=tmpsrc, new_dims=('RL','AP','SI'), out_file=tmp2).run()
        else:
            self.raise_exception(runtime)
            
        shutil.move(tmp2, out_file)
    
        # Only remove the temporary file if the conventions did not match.  Otherwise,
        # we end up removing the output.
        if tmpsrc != src_file:
            os.remove(tmpsrc)
        return runtime
        
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename()
        return outputs

