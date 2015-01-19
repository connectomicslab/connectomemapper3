# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
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
import os

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, TraitedSpec, InputMultiPath

# Own imports
from cmp.stages.common import Stage

# Imports for processing
import nibabel as nib
import numpy as np
import scipy.io as sio
import statsmodels.api as sm
from scipy import signal

class FunctionalConfig(HasTraits):
    smoothing = Float(0.0)
    discard_n_volumes = Int(5)
    # Nuisance factors
    global_nuisance = Bool(False)
    csf = Bool(True)
    wm = Bool(True)
    motion = Bool(True)
    
    detrending = Bool(True)
    
    lowpass_filter = Int(3)
    highpass_filter = Int(25)
    
    scrubbing = Bool(True)
    
    traits_view = View(Item('smoothing'),
                       Item('discard_n_volumes'),
                       HGroup(
                            Item('global_nuisance',label="Global"),
                            Item('csf'),
                            Item('wm'),
                            Item('motion'),
                            label='Nuisance factors',show_border=True
                            ),
                        Item('detrending'),
                        HGroup(
                            Item('lowpass_filter',label='Low cutoff (volumes)'),
                            Item('highpass_filter',label='High cutoff (volumes)'),
                            label="Bandpass filtering",show_border=True
                            )
                       )
    
class discard_tp_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True,mandatory=True)
    n_discard = Int(mandatory=True)
    
class discard_tp_OutputSpec(TraitedSpec):
    out_file = File(exists = True)
    
class discard_tp(BaseInterface):
    input_spec = discard_tp_InputSpec
    output_spec = discard_tp_OutputSpec
    
    def _run_interface(self,runtime):
        dataimg = nib.load( self.inputs.in_file )
        data = dataimg.get_data()

        n_discard = float(self.inputs.n_discard) - 1

        new_data = data.copy()
        new_data = new_data[:,:,:,n_discard:-1]

        hd = dataimg.get_header()
        hd.set_data_shape([hd.get_data_shape()[0],hd.get_data_shape()[1],hd.get_data_shape()[2],hd.get_data_shape()[3]-n_discard-1])
        img = nib.Nifti1Image(new_data, dataimg.get_affine(), hd)
        nib.save(img, os.path.abspath('fMRI_discard.nii.gz'))
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_discard.nii.gz")
        return outputs
        
class nuisance_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True)
    brainfile = File(desc='Eroded brain mask registered to fMRI space')
    csf_file = File(desc='Eroded CSF mask registered to fMRI space')
    wm_file = File(desc='Eroded WM mask registered to fMRI space')
    motion_file = File(desc='motion nuisance effect')
    gm_file = InputMultiPath(File(),desc='GM atlas files registered to fMRI space')
    global_nuisance = Bool()
    csf_nuisance = Bool()
    wm_nuisance = Bool()
    motion_nuisance = Bool()
    n_discard = Int(desc='Number of volumes discarded from the fMRI sequence during preprocessing')    
    
class nuisance_OutputSpec(TraitedSpec):
    out_file = File(exists=True)
    averageGlobal_npy = File()
    averageCSF_npy = File()
    averageWM_npy = File()
    averageGlobal_mat = File()
    averageCSF_mat = File()
    averageWM_mat = File()
    
    
class nuisance_regression(BaseInterface):
    input_spec = nuisance_InputSpec
    output_spec = nuisance_OutputSpec
    
    def _run_interface(self,runtime):
        #regress out nuisance signals (WM, CSF, movements) through GLM
    
        # Output from previous preprocessing step
        ref_path = self.inputs.in_file
            
        # Extract whole brain average signal
        dataimg = nib.load( ref_path )
        data = dataimg.get_data()
        tp = data.shape[3]
        if self.inputs.global_nuisance:
            brainfile = self.inputs.brainfile # load eroded whole brain mask
            brain = nib.load( brainfile ).get_data().astype( np.uint32 )
            global_values = data[brain==1].mean( axis = 0 )
            global_values = global_values - np.mean(global_values)
            np.save( os.path.abspath('averageGlobal.npy'), global_values )
            sio.savemat( os.path.abspath('averageGlobal.mat' ), {'avgGlobal':global_values} )
    
        # Extract CSF average signal
        if self.inputs.csf_nuisance:
            csffile = self.inputs.csf_file # load eroded CSF mask
            csf = nib.load( csffile ).get_data().astype( np.uint32 )
            csf_values = data[csf==1].mean( axis = 0 )
            csf_values = csf_values - np.mean(csf_values)
            np.save( os.path.abspath('averageCSF.npy'), csf_values )
            sio.savemat( os.path.abspath('averageCSF.mat' ), {'avgCSF':csf_values} )
    
        # Extract WM average signal
        if self.inputs.wm_nuisance:
            WMfile = self.inputs.wm_file # load eroded WM mask
            WM = nib.load( WMfile ).get_data().astype( np.uint32 )
            wm_values = data[WM==1].mean( axis = 0 )
            wm_values = wm_values - np.mean(wm_values)
            np.save( os.path.abspath('averageWM.npy'), wm_values )
            sio.savemat( os.path.abspath('averageWM.mat' ), {'avgWM':wm_values} )
    
        # Import parameters from head motion estimation
        if self.inputs.motion_nuisance:
            move = np.genfromtxt( self.inputs.motion_file )
            move = move - np.mean(move,0)
    
        # GLM: regress out nuisance covariates
        new_data = data.copy()
        
        #s = gconf.parcellation.keys()[0]
        
        gm = nib.load(self.inputs.gm_file[0]).get_data().astype( np.uint32 )
        if float(self.inputs.n_discard) > 0:
            n_discard = float(self.inputs.n_discard) - 1
            if self.inputs.motion_nuisance:
                move = move[n_discard:-1,:]
    
        # build regressors matrix
        if self.inputs.global_nuisance:
            X = np.hstack(global_values.reshape(tp,1))
            print('Detrend global average signal')
            if self.inputs.csf_nuisance:    
                X = np.hstack((X.reshape(tp,1),csf_values.reshape(tp,1)))
                print('Detrend CSF average signal')
                if self.inputs.wm_nuisance:
                    X = np.hstack((X,wm_values.reshape(tp,1)))
                    print('Detrend WM average signal')
                    if self.inputs.motion_nuisance:
                        X = np.hstack((X,move))
                        print('Detrend motion average signals')
                elif self.inputs.motion_nuisance:
                    X = np.hstack((X,move))
                    print('Detrend motion average signals')
            elif self.inputs.wm_nuisance:
                X = np.hstack((X.reshape(tp,1),wm_values.reshape(tp,1)))
                print('Detrend WM average signal')
                if self.inputs.motion_nuisance:
                    X = np.hstack((X,move))
                    print('Detrend motion average signals')
            elif self.inputs.motion_nuisance:
                X = np.hstack((X.reshape(tp,1),move))
                print('Detrend motion average signals')
        elif self.inputs.csf_nuisance:    
            X = np.hstack((csf_values.reshape(tp,1)))
            print('Detrend CSF average signal')
            if self.inputs.wm_nuisance:
                X = np.hstack((X.reshape(tp,1),wm_values.reshape(tp,1)))
                print('Detrend WM average signal')
                if self.inputs.motion_nuisance:
                    X = np.hstack((X,move))
                    print('Detrend motion average signals')
            elif self.inputs.motion_nuisance:
                X = np.hstack((X.reshape(tp,1),move))
                print('Detrend motion average signals')
        elif self.inputs.wm_nuisance:    
            X = np.hstack((wm_values.reshape(tp,1)))
            print('Detrend WM average signal')
            if self.inputs.motion_nuisance:
                X = np.hstack((X.reshape(tp,1),move))
                print('Detrend motion average signals')
        elif self.inputs.motion_nuisance:
            X = move
            print('Detrend motion average signals')
    
        X = sm.add_constant(X)
        print('Shape X GLM')
        print(X.shape)
    
        # loop throughout all GM voxels
        for index,value in np.ndenumerate( gm ):
            Y = data[index[0],index[1],index[2],:].reshape(tp,1)
            gls_model = sm.GLS(Y,X)
            gls_results = gls_model.fit()
            #new_data[index[0],index[1],index[2],:] = gls_results.resid
            new_data[index[0],index[1],index[2],:] = gls_results.resid #+ gls_results.params[8]
    
        img = nib.Nifti1Image(new_data, dataimg.get_affine(), dataimg.get_header())
        nib.save(img, os.path.abspath('fMRI_nuisance.nii.gz'))
        
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_nuisance.nii.gz")
        if self.inputs.global_nuisance:
            outputs["averageGlobal_npy"] = os.path.abspath('averageGlobal.npy')
            outputs["averageGlobal_mat"] = os.path.abspath('averageGlobal.mat')
        if self.inputs.csf_nuisance:
            outputs["averageCSF_npy"] = os.path.abspath('averageCSF.npy')
            outputs["averageCSF_mat"] = os.path.abspath('averageCSF.mat')
        if self.inputs.wm_nuisance:
            outputs["averageWM_npy"] = os.path.abspath('averageWM.npy')
            outputs["averageWM_mat"] = os.path.abspath('averageWM.mat')
        return outputs
    
class detrending_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="fMRI volume to detrend")
    gm_file = InputMultiPath(File(exists=True), desc="ROI files registered to fMRI space")
    
class detrending_OutputSpec(TraitedSpec):
    out_file = File(exists=True)
    
class Detrending(BaseInterface):
    input_spec = detrending_InputSpec
    output_spec = detrending_OutputSpec
    
    def _run_interface(self,runtime):
        """ linear detrending
        """
        
        print("Linear detrending")
        print("=================")
    
        # Output from previous preprocessing step
        ref_path = self.inputs.in_file
    
        # Load data
        dataimg = nib.load( ref_path )
        data = dataimg.get_data()
        tp = data.shape[3]
    
        # GLM: regress out nuisance covariates
        new_data_det = data.copy()
        gm = nib.load(self.inputs.gm_file[0]).get_data().astype( np.uint32 )
    
        for index,value in np.ndenumerate( gm ):
            if value == 0:
                continue
    
            Ydet = signal.detrend(data[index[0],index[1],index[2],:].reshape(tp,1), axis=0)
            new_data_det[index[0],index[1],index[2],:] = Ydet[:,0]
    
        img = nib.Nifti1Image(new_data_det, dataimg.get_affine(), dataimg.get_header())
        nib.save(img, os.path.abspath('fMRI_detrending.nii.gz'))
    
        print("[ DONE ]") 
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_detrending.nii.gz")
        return outputs
    
class scrubbing_InputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="fMRI volume to scrubb")
    wm_mask = File(exists=True,desc='WM mask registered to fMRI space')
    gm_file = InputMultiPath(File(exists=True),desc='ROI volumes registered to fMRI space')
    motion_parameters = File(exists=True, desc='Motion parameters from preprocessing stage')
    
class scrubbing_OutputSpec(TraitedSpec):
    fd_mat = File(exists=True)
    dvars_mat = File(exists=True)
    fd_npy = File(exists=True)
    dvars_npy = File(exists=True)
    
class Scrubbing(BaseInterface):
    input_spec = scrubbing_InputSpec
    output_spec = scrubbing_OutputSpec
    
    def _run_interface(self,runtime):
        """ compute scrubbing parameters: FD and DVARS
        """
        print("Precompute FD and DVARS for scrubbing")
        print("=====================================")
    
        # Output from previous preprocessing step
        ref_path = self.inputs.in_file
    
        dataimg = nib.load( ref_path )
        data = dataimg.get_data()
        tp = data.shape[3]
        WMfile = self.inputs.wm_mask
        WM = nib.load( WMfile ).get_data().astype( np.uint32 )
        GM = nib.load(self.inputs.gm_file[0]).get_data().astype( np.uint32 )
        mask = WM + GM
        move = np.genfromtxt( self.inputs.motion_parameters )
    
        # initialize motion measures
        FD = np.zeros((tp-1,1))
        DVARS = np.zeros((tp-1,1))
    
        # loop throughout all the time points
        for i in xrange(0,tp-1):
            # FD
            move0 = move[i,:]
            move1 = move[i+1,:]
            this_move = move1 - move0
            this_move = np.absolute(this_move)
            FD[i] = this_move.sum()
    
            # DVARS
            # extract current and following time points
            temp0 = data[:,:,:,i]
            temp1 = data[:,:,:,i+1]
            temp = temp1 - temp0
            temp = np.power(temp,2)
            temp = temp[mask>0]
            DVARS[i] = np.power(temp.mean(),0.5)
    
        np.save( os.path.abspath('FD.npy'), FD )
        np.save( os.path.abspath('DVARS.npy'), DVARS )
        sio.savemat( os.path.abspath('FD.mat'), {'FD':FD} )
        sio.savemat( os.path.abspath('DVARS.mat'), {'DVARS':DVARS} )
    
        print("[ DONE ]")
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["fd_mat"] = os.path.abspath("FD.mat")
        outputs["dvars_mat"] = os.path.abspath("DVARS.mat")
        outputs["fd_npy"] = os.path.abspath("FD.npy")
        outputs["dvars_npy"] = os.path.abspath("DVARS.npy")
        return outputs

class FunctionalStage(Stage):
    
    def __init__(self):
        self.name = 'functional_stage'
        self.config = FunctionalConfig()
        self.inputs = ["preproc_file","motion_par_file","registered_roi_volumes","registered_wm","eroded_wm","eroded_csf","eroded_brain"]
        self.outputs = ["func_file","FD","DVARS"]


    def create_workflow(self, flow, inputnode, outputnode):

        smoothing_output = pe.Node(interface=util.IdentityInterface(fields=["smoothing_output"]),name="smoothing_output")
        if self.config.smoothing > 0.0:
            smoothing = pe.Node(interface=fsl.SpatialFilter(operation='mean',kernel_shape = 'gauss'),name="smoothing")
            smoothing.inputs.kernel_size = self.config.smoothing
            flow.connect([
                        (inputnode,smoothing,[("preproc_file","in_file")]),
                        (smoothing,smoothing_output,[("out_file","smoothing_output")])
                        ])
        else:
            flow.connect([
                        (inputnode,smoothing_output,[("preproc_file","smoothing_output")])
                        ])
        
        discard_output = pe.Node(interface=util.IdentityInterface(fields=["discard_output"]),name="discard_output")   
        if self.config.discard_n_volumes > 0:
            discard = pe.Node(interface=discard_tp(n_discard=self.config.discard_n_volumes),name='discard_volumes')
            flow.connect([
                        (smoothing_output,discard,[("smoothing_output","in_file")]),
                        (discard,discard_output,[("out_file","discard_output")])
                        ])
        else:
            flow.connect([
                        (smoothing_output,discard_output,[("smoothing_output","discard_output")])
                        ])
        
        nuisance_output = pe.Node(interface=util.IdentityInterface(fields=["nuisance_output"]),name="nuisance_output")      
        if self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            nuisance = pe.Node(interface=nuisance_regression(),name="nuisance_regression")
            nuisance.inputs.global_nuisance=self.config.global_nuisance
            nuisance.inputs.csf_nuisance=self.config.csf
            nuisance.inputs.wm_nuisance=self.config.wm
            nuisance.inputs.motion_nuisance=self.config.motion
            nuisance.inputs.n_discard=self.config.discard_n_volumes
            flow.connect([
                        (discard_output,nuisance,[("discard_output","in_file")]),
                        (inputnode,nuisance,[("eroded_brain","brainfile")]),
                        (inputnode,nuisance,[("eroded_csf","csf_file")]),
                        (inputnode,nuisance,[("eroded_wm","wm_file")]),
                        (inputnode,nuisance,[("motion_par_file","motion_file")]),
                        (inputnode,nuisance,[("registered_roi_volumes","gm_file")]),
                        (nuisance,nuisance_output,[("out_file","nuisance_output")])
                        ])
        else:
            flow.connect([
                        (discard_output,nuisance_output,[("discard_output","nuisance_output")])
                        ])
        
        detrending_output = pe.Node(interface=util.IdentityInterface(fields=["detrending_output"]),name="detrending_output")
        if self.config.detrending:
            detrending = pe.Node(interface=Detrending(),name='detrending')
            flow.connect([
                        (nuisance_output,detrending,[("nuisance_output","in_file")]),
                        (inputnode,detrending,[("registered_roi_volumes","gm_file")]),
                        (detrending,detrending_output,[("out_file","detrending_output")])
                        ])
        else:
            flow.connect([
                        (nuisance_output,detrending_output,[("nuisance_output","detrending_output")])
                        ])
        
        filter_output = pe.Node(interface=util.IdentityInterface(fields=["filter_output"]),name="filter_output")
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            filtering = pe.Node(interface=fsl.TemporalFilter(),name='temporal_filter')
            filtering.inputs.lowpass_sigma = self.config.lowpass_filter
            filtering.inputs.highpass_sigma = self.config.highpass_filter
            flow.connect([
                        (detrending_output,filtering,[("detrending_output","in_file")]),
                        (filtering,filter_output,[("out_file","filter_output")])
                        ])
        else:
            flow.connect([
                        (detrending_output,filter_output,[("detrending_output","filter_output")])
                        ])
                            
        if self.config.scrubbing:
            scrubbing = pe.Node(interface=Scrubbing(),name='scrubbing')
            flow.connect([
                        (filter_output,scrubbing,[("filter_output","in_file")]),
                        (inputnode,scrubbing,[("registered_wm","wm_mask")]),
                        (inputnode,scrubbing,[("registered_roi_volumes","gm_file")]),
                        (inputnode,scrubbing,[("motion_par_file","motion_parameters")]),
                        (scrubbing,outputnode,[("fd_npy","FD")]),
                        (scrubbing,outputnode,[("dvars_npy","DVARS")])
                        ])
        
        flow.connect([
                        (filter_output,outputnode,[("filter_output","func_file")])
                        ])


    def define_inspect_outputs(self):
        if self.config.smoothing > 0.0:
            res_path = os.path.join(self.stage_dir,"smoothing","result_smoothing.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Smoothed image'] = ['fslview',results.outputs.out_file]
        if self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            res_path = os.path.join(self.stage_dir,"nuisance_regression","result_nuisance_regression.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Regression output'] = ['fslview',results.outputs.out_file]
        if self.config.detrending:
            res_path = os.path.join(self.stage_dir,"detrending","result_detrending.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Detrending output'] = ['fslview',results.outputs.out_file]
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            res_path = os.path.join(self.stage_dir,"temporal_filter","result_temporal_filter.pklz")
            if(os.path.exists(res_path)):
                results = pickle.load(gzip.open(res_path))
                self.inspect_outputs_dict['Filter output'] = ['fslview',results.outputs.out_file]
        
        self.inspect_outputs = self.inspect_outputs_dict.keys()

            
    def has_run(self):
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            return os.path.exists(os.path.join(self.stage_dir,"temporal_filter","result_temporal_filter.pklz"))
        elif self.config.detrending:
            return os.path.exists(os.path.join(self.stage_dir,"detrending","result_detrending.pklz"))
        elif self.config.wm or self.config.global_nuisance or self.config.csf or self.config.motion:
            return os.path.exists(os.path.join(self.stage_dir,"nuisance_regression","result_nuisance_regression.pklz"))
        elif self.config.smoothing > 0.0:
            return os.path.exists(os.path.join(self.stage_dir,"smoothing","result_smoothing.pklz"))
        else:
            return True