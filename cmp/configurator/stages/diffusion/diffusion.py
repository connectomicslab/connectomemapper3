# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Diffusion reconstruction and tractography
"""

# General imports
from traits.api import *
from traitsui.api import *
import gzip
import pickle

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

import nibabel as nib

# Own imports
from cmp.configurator.stages.common import Stage
from reconstruction import *
from tracking import *
from cmp.interfaces.misc import ExtractImageVoxelSizes, Tck2Trk


class DiffusionConfig(HasTraits):

    diffusion_imaging_model_editor = List(['DSI','DTI','HARDI'])
    diffusion_imaging_model = Str('DTI')
    # processing_tool_editor = List(['DTK','MRtrix','Camino','FSL','Gibbs'])
    # processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    dilate_rois = Bool(True)
    dilation_kernel = Enum(['Box','Gauss','Sphere'])
    dilation_radius = Enum([1,2,3,4])
    # processing_tool = Str('MRtrix')
    recon_processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    tracking_processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    recon_processing_tool = Str('MRtrix')
    tracking_processing_tool = Str('MRtrix')
    custom_track_file = File
    dtk_recon_config = Instance(HasTraits)
    dipy_recon_config = Instance(HasTraits)
    mrtrix_recon_config = Instance(HasTraits)
    camino_recon_config = Instance(HasTraits)
    fsl_recon_config = Instance(HasTraits)
    gibbs_recon_config = Instance(HasTraits)
    dtk_tracking_config = Instance(HasTraits)
    dtb_tracking_config = Instance(HasTraits)
    dipy_tracking_config = Instance(HasTraits)
    mrtrix_tracking_config = Instance(HasTraits)
    camino_tracking_config = Instance(HasTraits)
    fsl_tracking_config = Instance(HasTraits)
    gibbs_tracking_config = Instance(HasTraits)
    diffusion_model_editor = List(['Deterministic','Probabilistic'])
    diffusion_model = Str('Probabilistic')
    ## TODO import custom DWI and tractogram (need to register anatomical data to DWI to project parcellated ROIs onto the tractogram)

    traits_view = View(
                       Item('diffusion_imaging_model',style='readonly'),
                       HGroup(
                           Item('dilate_rois'),#,visible_when='processing_tool!="DTK"'),
                           Item('dilation_radius',visible_when='dilate_rois',label="radius")
                           ),
                       Group(Item('recon_processing_tool',label='Reconstruction processing tool',editor=EnumEditor(name='recon_processing_tool_editor')),
                             #Item('dtk_recon_config',style='custom',visible_when='processing_tool=="DTK"'),
                             Item('dipy_recon_config',style='custom',visible_when='recon_processing_tool=="Dipy"'),
			                 Item('mrtrix_recon_config',style='custom',visible_when='recon_processing_tool=="MRtrix"'),
			                 #Item('camino_recon_config',style='custom',visible_when='processing_tool=="Camino"'),
                             #Item('fsl_recon_config',style='custom',visible_when='processing_tool=="FSL"'),
                             #Item('gibbs_recon_config',style='custom',visible_when='processing_tool=="Gibbs"'),
                             label='Reconstruction', show_border=True, show_labels=False,visible_when='tracking_processing_tool!=Custom'),
                       Group(Item('tracking_processing_tool',label='Tracking processing tool',editor=EnumEditor(name='tracking_processing_tool_editor')),
                             Item('diffusion_model',editor=EnumEditor(name='diffusion_model_editor'),visible_when='tracking_processing_tool!="Custom"'),
                             #Item('dtb_tracking_config',style='custom',visible_when='processing_tool=="DTK"'),
                             Item('dipy_tracking_config',style='custom',visible_when='tracking_processing_tool=="Dipy"'),
			                 Item('mrtrix_tracking_config',style='custom',visible_when='tracking_processing_tool=="MRtrix"'),
			                 #Item('camino_tracking_config',style='custom',visible_when='processing_tool=="Camino"'),
                             #Item('fsl_tracking_config',style='custom',visible_when='processing_tool=="FSL"'),
                             #Item('gibbs_tracking_config',style='custom',visible_when='processing_tool=="Gibbs"'),
                             label='Tracking', show_border=True, show_labels=False),
                        Group(
                            Item('custom_track_file', style='simple'),
                            visible_when='tracking_processing_tool=="Custom"'),
                       )

    def __init__(self):
        self.dtk_recon_config = DTK_recon_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_recon_config = Dipy_recon_config(imaging_model=self.diffusion_imaging_model,recon_mode=self.diffusion_model,tracking_processing_tool=self.tracking_processing_tool)
        self.mrtrix_recon_config = MRtrix_recon_config(imaging_model=self.diffusion_imaging_model,recon_mode=self.diffusion_model)
        self.camino_recon_config = Camino_recon_config(imaging_model=self.diffusion_imaging_model)
        self.fsl_recon_config = FSL_recon_config()
        self.gibbs_recon_config = Gibbs_recon_config()
        self.dtk_tracking_config = DTK_tracking_config()
        self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_tracking_config = Dipy_tracking_config(imaging_model=self.diffusion_imaging_model,tracking_mode=self.diffusion_model,SD=self.mrtrix_recon_config.local_model)
        self.mrtrix_tracking_config = MRtrix_tracking_config(tracking_mode=self.diffusion_model,SD=self.mrtrix_recon_config.local_model)
        self.camino_tracking_config = Camino_tracking_config(imaging_model=self.diffusion_imaging_model,tracking_mode=self.diffusion_model)
        self.fsl_tracking_config = FSL_tracking_config()
        self.gibbs_tracking_config = Gibbs_tracking_config()

        self.mrtrix_recon_config.on_trait_change(self.update_mrtrix_tracking_SD,'local_model')
        self.dipy_recon_config.on_trait_change(self.update_dipy_tracking_SD,'local_model')
        self.dipy_recon_config.on_trait_change(self.update_dipy_tracking_sh_order,'lmax_order')

        self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'model_type')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'local_model')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'inversion')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'fallback_index')

    def _tracking_processing_tool_changed(self,new):
        if new == 'MRtrix':
            self.mrtrix_recon_config.tracking_processing_tool = new
        elif new == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = new

    def _diffusion_imaging_model_changed(self, new):
        self.dtk_recon_config.imaging_model = new
        self.mrtrix_recon_config.imaging_model = new
        self.dipy_recon_config.imaging_model = new
        self.dipy_tracking_config.imaging_model = new
        #self.camino_recon_config.diffusion_imaging_model = new
        self.dtk_tracking_config.imaging_model = new
        self.dtb_tracking_config.imaging_model = new
        # Remove MRtrix from recon and tracking methods and Probabilistic from diffusion model if diffusion_imaging_model is DSI
        if (new == 'DSI') and (self.recon_processing_tool != 'Custom'):
            self.recon_processing_tool = 'Dipy'
            self.recon_processing_tool_editor = ['Dipy','Custom']
            self.tracking_processing_tool_editor = ['Dipy','MRtrix','Custom']
            self.diffusion_model_editor = ['Deterministic','Probabilistic']
        else:
            # self.processing_tool_editor = ['DTK','MRtrix','Camino','FSL','Gibbs']
            #self.processing_tool_editor = ['Dipy','MRtrix']
            self.recon_processing_tool_editor = ['Dipy','MRtrix','Custom']
            self.tracking_processing_tool_editor = ['Dipy','MRtrix','Custom']

            if self.tracking_processing_tool == 'DTK':
                self.diffusion_model_editor = ['Deterministic']
            else:
                self.diffusion_model_editor = ['Deterministic','Probabilistic']

    def _recon_processing_tool_changed(self, new):
        print("recon_processing_tool_changed : %s"%new)
        #
        if new == 'Dipy' and self.diffusion_imaging_model != 'DSI':
            tracking_processing_tool = self.tracking_processing_tool
            self.tracking_processing_tool_editor = ['Dipy','MRtrix']
            if tracking_processing_tool == 'Dipy' or tracking_processing_tool == 'MRtrix':
                self.tracking_processing_tool = tracking_processing_tool
        elif new == 'Dipy' and self.diffusion_imaging_model == 'DSI':
            tracking_processing_tool = self.tracking_processing_tool
            self.tracking_processing_tool_editor = ['Dipy','MRtrix']
            if tracking_processing_tool == 'Dipy' or tracking_processing_tool == 'MRtrix':
                self.tracking_processing_tool = tracking_processing_tool
        elif new == 'MRtrix':
            self.tracking_processing_tool_editor = ['MRtrix']
        elif new == 'Custom':
            self.tracking_processing_tool_editor = ['Custom']

    def _tracking_processing_tool_changed(self, new):
        print("tracking_processing_tool changed: %s"%new)
        if new == 'Dipy' and self.recon_processing_tool == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = 'Dipy'
        elif new == 'MRtrix' and self.recon_processing_tool == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = 'MRtrix'

    def _diffusion_model_changed(self,new):
        # self.mrtrix_recon_config.recon_mode = new # Probabilistic tracking only available for Spherical Deconvoluted data
        self.mrtrix_tracking_config.tracking_mode = new
        self.dipy_tracking_config.tracking_mode = new
        self.camino_tracking_config.tracking_mode = new
        self.update_camino_tracking_model()

    def update_dipy_tracking_sh_order(self,new):
        if new != 'Auto':
            self.dipy_tracking_config.sh_order = new
        else:
            self.dipy_tracking_config.sh_order = 8

    def update_mrtrix_tracking_SD(self,new):
        self.mrtrix_tracking_config.SD = new

    def update_dipy_tracking_SD(self,new):
        self.dipy_tracking_config.SD = new

    def update_camino_tracking_model(self):
        if self.diffusion_model == 'Probabilistic':
            self.camino_tracking_config.tracking_model = 'pico'
        elif self.camino_recon_config.model_type == 'Single-Tensor' or self.camino_recon_config.local_model == 'restore' or self.camino_recon_config.local_model == 'adc':
            self.camino_tracking_config.tracking_model = 'dt'
        elif self.camino_recon_config.local_model == 'ball_stick':
            self.camino_tracking_config.tracking_model = 'ballstick'
        else:
            self.camino_tracking_config.tracking_model = 'multitensor'

    def update_camino_tracking_inversion(self):
        self.camino_tracking_config.inversion_index = self.camino_recon_config.inversion
        self.camino_tracking_config.fallback_index = self.camino_recon_config.fallback_index


def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')

class DiffusionStage(Stage):

    def __init__(self):
        self.name = 'diffusion_stage'
        self.config = DiffusionConfig()
        self.inputs = ["diffusion","partial_volumes","wm_mask_registered","brain_mask_registered","act_5tt_registered","gmwmi_registered","roi_volumes","grad","bvals","bvecs"]
        self.outputs = ["diffusion_model","track_file","fod_file","gFA","ADC","skewness","kurtosis","P0","roi_volumes","mapmri_maps"]

    def define_inspect_outputs(self):
        print "stage_dir : %s" % self.stage_dir

        ## RECON outputs
        # Dipy
        if self.config.dipy_recon_config.local_model or self.config.diffusion_imaging_model == 'DSI': # SHORE or CSD models

            if self.config.diffusion_imaging_model == 'DSI':
                recon_results_path = os.path.join(self.stage_dir,"reconstruction","dipy_SHORE","result_dipy_SHORE.pklz")
            else:
                recon_results_path = os.path.join(self.stage_dir,"reconstruction","dipy_CSD","result_dipy_CSD.pklz")

            if os.path.exists(recon_results_path):
                recon_results = pickle.load(gzip.open(recon_results_path))

                if self.config.diffusion_imaging_model == 'DSI':
                    gfa_res = recon_results.outputs.GFA
                    self.inspect_outputs_dict[self.config.recon_processing_tool + ' gFA image'] = ['mrview',gfa_res]
                    shm_coeff_res = recon_results.outputs.fod
                    self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH (SHORE) image'] = ['mrview',gfa_res,'-odf.load_sh',shm_coeff_res]

                else:
                    recon_tensor_results_path = os.path.join(self.stage_dir,"reconstruction","dipy_tensor","result_dipy_tensor.pklz")

                    if os.path.exists(recon_tensor_results_path):
                        recon_tensor_results = pickle.load(gzip.open(recon_tensor_results_path))

                        fa_res = recon_tensor_results.outputs.fa_file
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' FA image'] = ['mrview',fa_res]

                        shm_coeff_res = recon_results.outputs.out_shm_coeff
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH (CSD) image'] = ['mrview',fa_res,'-odf.load_sh',shm_coeff_res]
                    else:
                        shm_coeff_res = recon_results.outputs.out_shm_coeff
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH (CSD) image'] = ['mrview',shm_coeff_res,'-odf.load_sh',shm_coeff_res]



        # TODO: add Tensor image in case of DTI+Tensor modeling

        #MRtrix
        metrics_results_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_tensor_metrics","result_mrtrix_tensor_metrics.pklz")

        if os.path.exists(metrics_results_path):
            metrics_results = pickle.load(gzip.open(metrics_results_path))

            fa_res = metrics_results.outputs.out_fa
            self.inspect_outputs_dict[self.config.recon_processing_tool + ' FA image'] = ['mrview',fa_res]

            adc_res = metrics_results.outputs.out_adc
            self.inspect_outputs_dict[self.config.recon_processing_tool + ' ADC image'] = ['mrview',adc_res]


        if not self.config.mrtrix_recon_config.local_model: # Tensor model (DTI)
            recon_results_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_make_tensor","result_mrtrix_make_tensor.pklz")

            if os.path.exists(recon_results_path):
                recon_results = pickle.load(gzip.open(recon_results_path))

            tensor_res = recon_results.outputs.tensor
            self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH image'] = ['mrview',fa_res,'-odf.load_tensor',tensor_res]

        else: # CSD model

            RF_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_rf","result_mrtrix_rf.pklz")
            if(os.path.exists(RF_path)):
                RF_results = pickle.load(gzip.open(RF_path))
                self.inspect_outputs_dict['MRTRIX Response function'] = ['shview','-response',RF_results.outputs.response]

            recon_results_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_CSD","result_mrtrix_CSD.pklz")

            if os.path.exists(recon_results_path):
                recon_results = pickle.load(gzip.open(recon_results_path))
                shm_coeff_res = recon_results.outputs.spherical_harmonics_image
                self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH image'] = ['mrview',fa_res,'-odf.load_sh',shm_coeff_res]

        ## Tracking outputs
        # Dipy
        if self.config.dipy_recon_config.local_model or self.config.diffusion_imaging_model == 'DSI':

            if self.config.diffusion_model == 'Deterministic':
                diff_results_path = os.path.join(self.stage_dir,"tracking","dipy_deterministic_tracking","result_dipy_deterministic_tracking.pklz")
                if os.path.exists(diff_results_path):
                    diff_results = pickle.load(gzip.open(diff_results_path))
                    streamline_res = diff_results.outputs.tracks
                    self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]

            if self.config.diffusion_model == 'Probabilistic':
                diff_results_path = os.path.join(self.stage_dir,"tracking","dipy_probabilistic_tracking","result_dipy_probabilistic_tracking.pklz")
                if os.path.exists(diff_results_path):
                    diff_results = pickle.load(gzip.open(diff_results_path))
                    streamline_res = diff_results.outputs.tracks
                    self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]
        else:

            diff_results_path = os.path.join(self.stage_dir,"tracking","dipy_dtieudx_tracking","result_dipy_dtieudx_tracking.pklz")

            if os.path.exists(diff_results_path):
                diff_results = pickle.load(gzip.open(diff_results_path))
                streamline_res = diff_results.outputs.tracks
                self.inspect_outputs_dict[self.config.tracking_processing_tool + ' Tensor-based EuDX streamline'] = ['trackvis',streamline_res]

        #MRtrix
        if self.config.diffusion_model == 'Deterministic':
            diff_results_path = os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz")
            if os.path.exists(diff_results_path):
                diff_results = pickle.load(gzip.open(diff_results_path))
                streamline_res = diff_results.outputs.out_tracks
                print streamline_res
                self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]

        elif self.config.diffusion_model == 'Probabilistic':
            diff_results_path = os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz")
            print diff_results_path
            if os.path.exists(diff_results_path):
                diff_results = pickle.load(gzip.open(diff_results_path))
                streamline_res = diff_results.outputs.out_tracks
                print streamline_res
                self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]

            # if self.config.mrtrix_recon_config.local_model:
            #
            #     RF_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_rf","result_mrtrix_rf.pklz")
            #     if(os.path.exists(RF_path)):
            #         RF_results = pickle.load(gzip.open(RF_path))
            #         self.inspect_outputs_dict['MRTRIX Response function'] = ['shview','-response',RF_results.outputs.response]
            #
            #     CSD_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_CSD","result_mrtrix_CSD.pklz")
            #     tensor_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_make_tensor","result_mrtrix_make_tensor.pklz")
            #     if(os.path.exists(CSD_path) and os.path.exists(tensor_path)):
            #         CSD_results = pickle.load(gzip.open(CSD_path))
            #         self.inspect_outputs_dict['MRTrix Spherical Harmonics image'] = ['mrview',CSD_results.outputs.spherical_harmonics_image]
            #         Tensor_results = pickle.load(gzip.open(tensor_path))
            #         self.inspect_outputs_dict['MRTrix SH/tensor images'] = ['mrview',CSD_results.outputs.spherical_harmonics_image,'-odf.load_tensor',Tensor_results.outputs.tensor]
            #         self.inspect_outputs = self.inspect_outputs_dict.keys()
            #
            #     FA_path = os.path.join(self.stage_dir,"reconstruction","convert_FA","result_convert_FA.pklz")
            #     if(os.path.exists(FA_path)):
            #         FA_results = pickle.load(gzip.open(FA_path))
            #         self.inspect_outputs_dict['MRTrix FA'] = ['mrview',FA_results.outputs.converted]

        self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)


    def has_run(self):
        if self.config.tracking_processing_tool == 'Dipy':
            if self.config.diffusion_model == 'Deterministic':
                return os.path.exists(os.path.join(self.stage_dir,"tracking","dipy_deterministic_tracking","result_dipy_deterministic_tracking.pklz"))
            elif self.config.diffusion_model == 'Probabilistic':
                return os.path.exists(os.path.join(self.stage_dir,"tracking","dipy_probabilistic_tracking","result_dipy_probabilistic_tracking.pklz"))
        elif self.config.tracking_processing_tool == 'MRtrix':
            return os.path.exists(os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz"))
