# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP preprocessing Stage (not used yet!)
"""

from traits.api import *
from traitsui.api import *

from nipype.interfaces.base import traits, BaseInterface, BaseInterfaceInputSpec, CommandLineInputSpec, CommandLine, InputMultiPath, OutputMultiPath, TraitedSpec, Interface, InterfaceResult, isdefined
import nipype.interfaces.utility as util

from cmp.configurator.stages.common import Stage

import os
import pickle
import gzip
import glob
import pkg_resources

import nipype.pipeline.engine as pe
import nipype.pipeline as pip
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.utility as util
import nipype.interfaces.mrtrix as mrt
import nipype.interfaces.ants as ants
import nipype.interfaces.dipy as dipy

import nibabel as nib

# from cmp.pipelines.common import MRThreshold, ExtractMRTrixGrad
from cmp.interfaces.mrtrix3 import DWIDenoise, DWIBiasCorrect, MRConvert, MRThreshold, ExtractFSLGrad, ExtractMRTrixGrad, Generate5tt, GenerateGMWMInterface
import cmp.interfaces.fsl as cmp_fsl
from cmp.interfaces.misc import ExtractPVEsFrom5TT

from nipype.interfaces.mrtrix3.preprocess import ResponseSD

class PreprocessingConfig(HasTraits):
    total_readout = Float(0.0)
    description = Str('description')
    denoising = Bool(False)
    denoising_algo =  Enum('MRtrix (MP-PCA)',['MRtrix (MP-PCA)','Dipy (NLM)'])
    dipy_noise_model = Enum('Rician',['Rician','Gaussian'])
    bias_field_correction = Bool(False)
    bias_field_algo = Enum('ANTS N4',['ANTS N4','FSL FAST'])
    eddy_current_and_motion_correction = Bool(True)
    eddy_correction_algo = Enum('FSL eddy_correct','FSL eddy')
    eddy_correct_motion_correction = Bool(True)
    start_vol = Int(0)
    end_vol = Int()
    max_vol = Int()
    max_str = Str
    partial_volume_estimation = Bool(True)
    fast_use_priors = Bool(True)

    # DWI resampling selection
    resampling = Tuple(1,1,1)
    interpolation = Enum(['interpolate','weighted','nearest','sinc','cubic'])

    traits_view = View(
                    VGroup(
                        VGroup(
                        HGroup(
                            Item('start_vol',label='Vol'),
                            Item('end_vol',label='to'),
                            Item('max_str',style='readonly',show_label=False)
                            ),
                            label='Processed volumes'),
                        VGroup(
                        HGroup(
                            Item('denoising'),
                            Item('denoising_algo',label='Tool:',visible_when='denoising==True'),
                            Item('dipy_noise_model',label='Noise model (Dipy):',visible_when='denoising_algo=="Dipy (NLM)"')
                            ),
                        HGroup(
                            Item('bias_field_correction'),
                            Item('bias_field_algo',label='Tool:',visible_when='bias_field_correction==True')
                            ),
                        VGroup(
                        HGroup(
                            Item('eddy_current_and_motion_correction'),
                            Item('eddy_correction_algo',visible_when='eddy_current_and_motion_correction==True'),
                            ),
                            Item('eddy_correct_motion_correction',label='Motion correction',visible_when='eddy_current_and_motion_correction==True and eddy_correction_algo=="FSL eddy_correct"'),
                            Item('total_readout',label='Total readout time (s):',visible_when='eddy_current_and_motion_correction==True and eddy_correction_algo=="FSL eddy"')
                        ),
                        label='Preprocessing steps'),
                        VGroup(
                        VGroup(
                            Item('resampling',label='Voxel size (x,y,z)',editor=TupleEditor(cols=3)),
                            'interpolation'
                            ),
                        label='Final resampling')
                        ),
                    width=0.5,height=0.5)

    def _max_vol_changed(self,new):
        self.max_str = '(max: %d)' % new
        #self.end_vol = new

    def _end_vol_changed(self,new):
        if new > self.max_vol:
            self.end_vol = self.max_vol

    def _start_vol_changed(self,new):
        if new < 0:
            self.start_vol = 0


class PreprocessingStage(Stage):
    # General and UI members
    def __init__(self):
        self.name = 'preprocessing_stage'
        self.config = PreprocessingConfig()
        self.inputs = ["diffusion","bvecs","bvals","T1","aseg","brain","brain_mask","wm_mask_file","roi_volumes"]
        self.outputs = ["diffusion_preproc","bvecs_rot","bvals","dwi_brain_mask","T1","act_5TT","gmwmi","brain","brain_mask","brain_mask_full","wm_mask_file","partial_volume_files","roi_volumes"]

    def define_inspect_outputs(self):
        print "stage_dir : %s" % self.stage_dir
        if self.config.denoising:
            denoising_results_path = os.path.join(self.stage_dir,"dwi_denoise","result_dwi_denoise.pklz")
            if(os.path.exists(denoising_results_path)):
                dwi_denoise_results = pickle.load(gzip.open(denoising_results_path))
                print dwi_denoise_results.outputs.out_file
                self.inspect_outputs_dict['DWI denoised image'] = ['mrview',dwi_denoise_results.outputs.out_file]
                if self.config.denoising_algo == "MRtrix (MP-PCA)":
                    print dwi_denoise_results.outputs.out_noisemap
                    self.inspect_outputs_dict['Noise map'] = ['mrview',dwi_denoise_results.outputs.out_noisemap]

        if self.config.bias_field_correction:
            bias_field_correction_results_path = os.path.join(self.stage_dir,"dwi_biascorrect","result_dwi_biascorrect.pklz")
            if(os.path.exists(bias_field_correction_results_path)):
                dwi_biascorrect_results = pickle.load(gzip.open(bias_field_correction_results_path))
                print dwi_biascorrect_results.outputs.out_file
                print dwi_biascorrect_results.outputs.out_bias
                self.inspect_outputs_dict['Bias field corrected image'] = ['mrview',dwi_biascorrect_results.outputs.out_file]
                self.inspect_outputs_dict['Bias field'] = ['mrview',dwi_biascorrect_results.outputs.out_bias]

        if self.config.eddy_current_and_motion_correction:
            if self.config.eddy_correction_algo == 'FSL eddy_correct':
                eddy_results_path = os.path.join(self.stage_dir,"eddy_correct","result_eddy_correct.pklz")
                if(os.path.exists(eddy_results_path)):
                    eddy_results = pickle.load(gzip.open(eddy_results_path))
                    self.inspect_outputs_dict['Eddy current corrected image'] = ['mrview',eddy_results.outputs.eddy_corrected]
            else:
                eddy_results_path = os.path.join(self.stage_dir,"eddy","result_eddy.pklz")
                if(os.path.exists(eddy_results_path)):
                    eddy_results = pickle.load(gzip.open(eddy_results_path))
                    self.inspect_outputs_dict['Eddy current corrected image'] = ['mrview',eddy_results.outputs.eddy_corrected]

        self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)


    def has_run(self):
        if not self.config.eddy_current_and_motion_correction:
            if not self.config.denoising and not self.config.bias_field_correction:
                return True
            else:
                return os.path.exists(os.path.join(self.stage_dir,"mr_convert_b","result_mr_convert_b.pklz"))
        else:
            return os.path.exists(os.path.join(self.stage_dir,"eddy","result_eddy.pklz"))
