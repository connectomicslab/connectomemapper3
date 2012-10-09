
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
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.freesurfer as fs

# Own imports
from cmp.stages.common import CMP_Stage

class Segmentation_Config(HasTraits):
    freesurfer_subjects_dir = Str
    traits_view = View()
	
class Segmentation(CMP_Stage):
    # General and UI members
    name = 'Segmentation'
    display_color = 'lightyellow'
    position_x = 45
    position_y = 320
    config = Segmentation_Config()
	
    	
    def create_workflow(self):
        flow = pe.Workflow(name="Segmentation_stage")
        
        inputnode = pe.Node(interface=util.IdentityInterface(fields=["T1"]),name="inputnode")
        
        # Converting to .mgz format
        fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type="mgz",out_file="T1.mgz"),name="fs_mriconvert")
        
        # ReconAll => named outputnode as we don't want to select a specific output....
        fs_reconall = pe.Node(interface=fs.ReconAll(),name="outputnode")
        fs_reconall.inputs.subjects_dir = self.config.freesurfer_subjects_dir
        
        flow.connect([
                    (inputnode,fs_mriconvert,[('T1','in_file')]),
                    (fs_mriconvert,fs_reconall,[('out_file','T1_files')]),
                    ])
        
        return flow

	
