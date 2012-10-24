# Copyright (C) 2009-2012, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP registration stage
""" 

# General imports
try: 
    from traits.api import *
except ImportError: 
    from enthought.traits.api import *
try: 
    from traitsui.api import *
except ImportError: 
    from enthought.traits.ui.api import *

# Nipype imports
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl

# Own imports
from cmp.stages.common import CMP_Stage

class Registration_Config(HasTraits):
    # Registration selection
    registration_mode = Enum('Linear (FSL)','Nonlinear (FSL)','BBregister (FS)')
    imaging_model = Str
    
    # FLIRT
    uses_qform = Bool(True)
    dof = Int(6)
    cost = Enum('mutualinfo',['mutualinfo','corratio','normcorr','normmi','leastsq','labeldiff'])
    no_search = Bool(True)
    
    # BBRegister
    init = Enum('header',['spm','fsl','header'])
    contrast_type = Enum('t2',['t1','t2'])
                
    traits_view = View('registration_mode',
                        Group('uses_qform','dof','cost','no_search',label='FLIRT',
                              show_border=True,visible_when='registration_mode=="Linear (FSL)"'),
                        Group('init','contrast_type',
                              show_border=True,visible_when='registration_mode=="BBregister (FS)"'),
                       kind='live',
                       )


class Registration(CMP_Stage):
    name = 'Registration'
    display_color = 'lightgreen'
    position_x = 70
    position_y = 240
    config = Registration_Config()

    def create_workflow(self):
        flow = pe.Workflow(name="Registration_Stage")

        inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1","diffusion","T2","subjects_dir","subject_id"]),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=["T1-TO-B0","T1-TO-B0_mat"]),name="outputnode")

        # Extract B0 and resample it to 1x1x1mm3
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(frame=0,out_file="diffusion_first.nii.gz",vox_size=(1,1,1)),name="fs_mriconvert")
        
        flow.connect([(inputnode, fs_mriconvert,[('diffusion','in_file')])])
        
        if self.config.registration_mode == 'Linear (FSL)':
            fsl_flirt = pe.Node(interface=fsl.FLIRT(out_file='T1-TO-B0.nii.gz',out_matrix_file='T1-TO-B0.mat'),name="fsl_flirt")
            fsl_flirt.inputs.uses_qform = self.config.uses_qform
            fsl_flirt.inputs.dof = self.config.dof
            fsl_flirt.inputs.cost = self.config.cost
            fsl_flirt.inputs.no_search = self.config.no_search
            
            flow.connect([
                        (inputnode, fsl_flirt, [('T1','in_file')]),
                        (fs_mriconvert, fsl_flirt, [('out_file','reference')]),
                        (fsl_flirt, outputnode, [('out_file','T1-TO-B0'),('out_matrix_file','T1-TO-B0_mat')]),
                        ])
        if self.config.registration_mode == 'BBregister (FS)':
            fs_bbregister = pe.Node(interface=fs.BBRegister(out_fsl_file=True),name="fs_bbregister")
            fs_bbregister.inputs.init = self.config.init
            fs_bbregister.inputs.contrast_type = self.config.contrast_type
            
            fsl_convertxfm = pe.Node(interface=fsl.ConvertXFM(invert_xfm=True),name="fsl_convertxfm")
            
            # TODO tkregister2 (+node), convertxfm, applyxfm
            
            flow.connect([
                        (inputnode, fs_bbregister, [('subjects_dir','subjects_dir'),('subject_id','subject_id')]),
                        (fs_mriconvert, fs_bbregister, [('out_file','source_file')]),
                        (fsl_flirt, outputnode, [('out_file','T1_TO_B0'),('out_matrix_file','T1_TO_B0_mat')]),
                        ])
       
       
        return flow

