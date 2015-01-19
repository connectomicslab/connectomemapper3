# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
import nipype.interfaces.diffusion_toolkit as dtk
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
from nipype.caching import Memory
from nipype.interfaces.base import BaseInterface, \
    BaseInterfaceInputSpec, File, TraitedSpec, isdefined
from nipype.utils.filemanip import split_filename

from traits.api import *
from traitsui.api import *

class ProgressWindow(HasTraits):
    main_status = Str("Processing launched...")
    stages_status = List([''])
    
    traits_view = View(Group(
                            Group(
                                Item('main_status',show_label=False,style='readonly'),
                                label = 'Main status', show_border=True),
                            Group(
                                Item('stages_status',show_label=False,editor=ListStrEditor(),enabled_when='2<1'),
                                label = 'Stages status', show_border=True),
                            ),
                       width=300,
                       height=400,
                       buttons=['OK','Cancel'],
                       title='Processing status',
                       kind='livemodal')
    
class ProgressThread(threading.Thread):
    stages = {}
    stage_names = []
    pw = Instance(ProgressWindow)
    
    def run(self):
        c=0
        
        while(c < len(self.stage_names)):
            time.sleep(5)
            c = 0
            statuses = []
            for stage in self.stage_names:
                if self.stages[stage].enabled:
                    if self.stages[stage].has_run():
                        statuses.append(stage+" stage finished!")
                        c = c+1
                    elif self.stages[stage].is_running():
                        statuses.append(stage+" stage running...")
                    else:
                        statuses.append(stage+" stage waiting...")
                else:
                    c = c+1
                    statuses.append(stage+" stage not selected for running!")
            self.pw.stages_status = statuses
        self.pw.main_status = "Processing finished!"
        self.pw.stages_status = ['All stages finished!']
                    
class ProcessThread(threading.Thread):
    pipeline = Instance(Any)
    
    def run(self):
        self.pipeline.process()
                      

class Pipeline(HasTraits):
    # informations common to project_info
    base_directory = Directory
    last_date_processed = Str
    last_stage_processed = Str
    
    # num core settings
    number_of_cores = Enum(1,range(1,multiprocessing.cpu_count()+1))
    
    traits_view = View(HGroup(
                        Include('pipeline_group'),
                        Group(
                            Group(
                                Item('base_directory',editor=TextEditor(),style='readonly',show_label=False,height=100),
                                label='Base directory',
                            ),
                            Group(
                                Item('pipeline_name',style='readonly'),
                                Item('last_date_processed',style='readonly'),
                                Item('last_stage_processed',style='readonly'),
                                label='Last processing'
                            ),
                            Group(
                                'number_of_cores',
                                label='Processing configuration'
                            ),
                            
                        ),
                        
                        ),kind = 'livemodal')
    
    def __init__(self, project_info):
        self.base_directory = project_info.base_directory
        self.last_date_processed = project_info.last_date_processed
        for stage in self.stages.keys():
            if self.stages[stage].name == 'segmentation_stage' or self.stages[stage].name == 'parcellation_stage':
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"NIPYPE",'common_stages',self.stages[stage].name)
            else:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"NIPYPE",self.pipeline_name,self.stages[stage].name)
                
    def check_config(self):
        if self.stages['Segmentation'].config.seg_tool ==  'Custom segmentation':
            if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\nCustom segmentation selected but no WM mask provided.\nPlease provide an existing WM mask file in the Segmentation configuration window.\n')
            if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
                return('\n\tCustom segmentation selected but no atlas provided.\nPlease specify an existing atlas file in the Parcellation configuration window.\t\n')
            if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
                return('\n\tCustom segmentation selected but no graphml info provided.\nPlease specify an existing graphml file in the Parcellation configuration window.\t\n')
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
    
    def create_common_flow(self):
        common_flow = pe.Workflow(name='common_stages')
        common_inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1"]),name="inputnode")
        common_outputnode = pe.Node(interface=util.IdentityInterface(fields=["subjects_dir","subject_id","wm_mask_file", "wm_eroded","brain_eroded","csf_eroded",
            "roi_volumes","parcellation_scheme","atlas_info"]),name="outputnode")
        common_flow.add_nodes([common_inputnode,common_outputnode])
        
        if self.stages['Segmentation'].enabled:
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                
                if self.stages['Segmentation'].config.use_existing_freesurfer_data == False:
                    self.stages['Segmentation'].config.freesurfer_subjects_dir = os.path.join(self.base_directory)
                    self.stages['Segmentation'].config.freesurfer_subject_id = os.path.join(self.base_directory,'FREESURFER')
                    
            seg_flow = self.create_stage_flow("Segmentation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                common_flow.connect([(common_inputnode,seg_flow, [('T1','inputnode.T1')])])
            
            common_flow.connect([
                                 (seg_flow,common_outputnode,[("outputnode.subjects_dir","subjects_dir"),
                                                              ("outputnode.subject_id","subject_id")])
                                ])
       
        if self.stages['Parcellation'].enabled:
            parc_flow = self.create_stage_flow("Parcellation")
            if self.stages['Segmentation'].config.seg_tool == "Freesurfer":
                common_flow.connect([(seg_flow,parc_flow, [('outputnode.subjects_dir','inputnode.subjects_dir'),
                                                           ('outputnode.subject_id','inputnode.subject_id')]),
                                     ])
            else:
                common_flow.connect([
                                     (seg_flow,parc_flow,[("outputnode.custom_wm_mask","inputnode.custom_wm_mask")])
                                     ])
            common_flow.connect([
                                 (parc_flow,common_outputnode,[("outputnode.wm_mask_file","wm_mask_file"),
                                                               ("outputnode.parcellation_scheme","parcellation_scheme"),
                                                               ("outputnode.atlas_info","atlas_info"),
                                                               ("outputnode.roi_volumes","roi_volumes"),
                                                               ("outputnode.wm_eroded","wm_eroded"),
                                                               ("outputnode.csf_eroded","csf_eroded"),
                                                               ("outputnode.brain_eroded","brain_eroded"),
                                                               ])
                                 ])
            
        return common_flow
        
    def fill_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.define_inspect_outputs()
                
    def clear_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.inspect_outputs_dict = {}
                stage.inspect_outputs = ['Outputs not available']
                # Remove result_*.pklz files to clear them from visualisation drop down list
                #stage_results = [os.path.join(dirpath, f)
                #                 for dirpath, dirnames, files in os.walk(stage.stage_dir)
                #                 for f in fnmatch.filter(files, 'result_*.pklz')]
                #for stage_res in stage_results:
                #    os.remove(stage_res)
                
    def launch_progress_window(self):
        pw = ProgressWindow()
        pt = ProgressThread()
        pt.pw = pw
        pt.stages = self.stages
        pt.stage_names = self.ordered_stage_list
        pt.start()
        pw.configure_traits()
        
    def launch_process(self):
        pt = ProcessThread()
        pt.pipeline = self
        pt.start()
               

def convert_rawdata(base_directory, input_dir, out_prefix):
    os.environ['UNPACK_MGH_DTI'] = '0'
    file_list = os.listdir(input_dir)

    # If RAWDATA folder contains one (and only one) gunzipped nifti file -> copy it
    first_file = os.path.join(input_dir, file_list[0])
    if len(file_list) == 1 and first_file.endswith('nii.gz'):
        copyfile(first_file, os.path.join(base_directory, 'NIFTI', out_prefix+'.nii.gz'), False, False, 'content') # intelligent copy looking at input's content
    else:
        mem = Memory(base_dir=os.path.join(base_directory,'NIPYPE'))
        mri_convert = mem.cache(fs.MRIConvert)
        res = mri_convert(in_file=first_file, out_file=os.path.join(base_directory, 'NIFTI', out_prefix + '.nii.gz'))
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

