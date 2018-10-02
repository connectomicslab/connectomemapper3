# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common functions for CMP pipelines
"""

import os
import fnmatch
import shutil
import threading
import multiprocessing
import time
from nipype.utils.filemanip import copyfile
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.dcm2nii import Dcm2niix
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.mrtrix as mrt
from nipype.caching import Memory
from nipype.interfaces.base import CommandLineInputSpec, CommandLine, traits, BaseInterface, \
    BaseInterfaceInputSpec, File, TraitedSpec, isdefined, Directory, InputMultiPath
from nipype.utils.filemanip import split_filename

# Own import
import cmp.interfaces.fsl as cmp_fsl

from traits.api import *
from traitsui.api import *

import apptools.io.api as io

from pyface.qt.QtCore import *
from pyface.qt.QtGui import *
from traitsui.qt4.extra.qt_view import QtView

class Pipeline(HasTraits):
    # informations common to project_info
    base_directory = Directory
    root = Property
    subject = 'sub-01'
    last_date_processed = Str
    last_stage_processed = Str

    # num core settings
    number_of_cores = 1

    anat_flow = None

    traits_view = QtView(Include('pipeline_group'))

    #-- Traits Default Value Methods -----------------------------------------

    # def _base_directory_default(self):
    #     return getcwd()

    #-- Property Implementations ---------------------------------------------

    @property_depends_on('base_directory')
    def _get_root(self):
        return File(path=self.base_directory)

    def __init__(self, project_info):
        self.base_directory = project_info.base_directory
        self.subject = project_info.subject
        self.number_of_cores = project_info.number_of_cores

        for stage in self.stages.keys():
            if len(project_info.subject_sessions)>0:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,project_info.subject_session,'tmp',self.pipeline_name,self.stages[stage].name)
            else:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp',self.pipeline_name,self.stages[stage].name)
            # if self.stages[stage].name == 'segmentation_stage' or self.stages[stage].name == 'parcellation_stage':
            #     #self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'freesurfer',self.subject,self.stages[stage].name)
            #     self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp','nipype','common_stages',self.stages[stage].name)
            # else:
            #     self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp','nipype',self.pipeline_name,self.stages[stage].name)

    def check_config(self):
        if self.stages['Segmentation'].config.seg_tool ==  'Custom segmentation':
            if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\nCustom segmentation selected but no WM mask provided.\nPlease provide an existing WM mask file in the Segmentation configuration window.\n')
            if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
                return('\n\tCustom segmentation selected but no atlas provided.\nPlease specify an existing atlas file in the Parcellation configuration window.\t\n')
            if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
                return('\n\tCustom segmentation selected but no graphml info provided.\nPlease specify an existing graphml file in the Parcellation configuration window.\t\n')
        # if self.stages['MRTrixConnectome'].config.output_types == []:
        #     return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        if self.stages['Connectome'].config.output_types == []:
            return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        return ''

    def create_stage_flow(self, stage_name):
        stage = self.stages[stage_name]
        flow = pe.Workflow(name=stage.name)
        inputnode = pe.Node(interface=util.IdentityInterface(fields=stage.inputs),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=stage.outputs),name="outputnode")
        flow.add_nodes([inputnode,outputnode])
        stage.create_workflow(flow,inputnode,outputnode)
        return flow

    def fill_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.define_inspect_outputs()

    def clear_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.inspect_outputs_dict = {}
                stage.inspect_outputs = ['Outputs not available']



class SwapAndReorientInputSpec(BaseInterfaceInputSpec):
    src_file = File(desc='Source file to be reoriented.',exists=True,mandatory=True)
    ref_file = File(desc='Reference file, which orientation will be applied to src_file.',exists=True,mandatory=True)
    out_file = File(genfile=True, desc='Name of the reoriented file.')

class SwapAndReorientOutputSpec(TraitedSpec):
    out_file = File(desc='Reoriented file.')

class SwapAndReorient(BaseInterface):
    input_spec = SwapAndReorientInputSpec
    output_spec = SwapAndReorientOutputSpec

    def _gen_outfilename(self):
        out_file = self.inputs.out_file
        path,base,ext = split_filename(self.inputs.src_file)
        if not isdefined(self.inputs.out_file):
            out_file = os.path.join(path,base+'_reo'+ext)

        json_file = os.path.join(path,base+'.json')
        if os.path.isfile(json_file):
            path,base,ext = split_filename(self.inputs.out_file)
            out_json_file = os.path.join(path,base+'.json')
            shutil.copy(json_file,out_json_file)

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
        src_conv = cmp_fsl.Orient(in_file=src_file, get_orient=True).run().outputs.orient
        ref_conv = cmp_fsl.Orient(in_file=ref_file, get_orient=True).run().outputs.orient

        if src_orient == ref_orient:
            # no reorientation needed
            print "No reorientation needed for anatomical image; Copy only!"
            copyfile(src_file,out_file,False, False, 'content')
            return runtime
        else:
            if src_conv != ref_conv:
                # if needed, match convention (radiological/neurological) to reference
                tmpsrc = os.path.join(os.path.dirname(src_file), 'tmp_' + os.path.basename(src_file))

                fsl.SwapDimensions(in_file=src_file, new_dims=('-x','y','z'), out_file=tmpsrc).run()

                cmp_fsl.Orient(in_file=tmpsrc, swap_orient=True).run()
            else:
                # If conventions match, just use the original source
                tmpsrc = src_file

        tmp2 = os.path.join(os.path.dirname(src_file), 'tmp.nii.gz')
        map_orient = {'L':'RL','R':'LR','A':'PA','P':'AP','S':'IS','I':'SI'}
        fsl.SwapDimensions(in_file=tmpsrc, new_dims=(map_orient[ref_orient[0]],map_orient[ref_orient[1]],map_orient[ref_orient[2]]), out_file=tmp2).run()

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
