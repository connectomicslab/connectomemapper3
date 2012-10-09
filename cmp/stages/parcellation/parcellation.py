
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
import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.cmtk as cmtk

# Own imports
from cmp.stages.common import CMP_Stage

class CMP_Parcellation_Config(HasTraits):
    parcellation_scheme = Enum('Lausanne2008',['NativeFreesurfer','Lausanne2008'])
    #parcellation = Property(List,depends_on='parcellation_scheme')
    parcellation_options_trait = List(['scale33', 'scale60', 'scale125', 'scale250', 'scale500'])
    parcellation = List(['scale33', 'scale60', 'scale125', 'scale250', 'scale500'],editor = CheckListEditor(name='parcellation_options_trait'))

    traits_view = View('parcellation_scheme',Item('parcellation',style='custom'),height=300)

    def _parcellation_scheme_changed(self, old, new):
        if new == 'NativeFreesurfer':
            self.parcellation_options_trait = ['freesurferaparc']
        if self.parcellation_scheme == 'Lausanne2008':
            self.parcellation_options_trait = ['scale33', 'scale60', 'scale125', 'scale250', 'scale500']

class Parcellation(CMP_Stage):
    name = 'Parcellation'
    display_color = 'lightyellow'
    position_x = 45
    position_y = 230
    config = CMP_Parcellation_Config()
    
    def create_workflow(self):
        flow = pe.Workflow(name="Parcellation_stage")
        
        inputnode = pe.Node(interface=util.IdentityInterface(fields=["subjects_dir","subject_id"]),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=["aseg_file","wm_mask_file","cmtk_cc_unknown_file",
                            "cmtk_ribbon_file","fs_roiv_file","cmtk_roi_files","cmtk_roiv_files"]),name="outputnode")
        flow.add_nodes([inputnode,outputnode])
        
        if self.config.parcellation_scheme == 'Lausanne2008':
            parc_node = pe.Node(interface=cmtk.Parcellate(scales=self.config.parcellation),name="cmtk_parcellation")
            flow.connect([
                            (inputnode,parc_node,[("subjects_dir","subjects_dir"),("subject_id","subject_id")]),
                            (parc_node,outputnode,[("aseg_file","aseg_file"),("cc_unknown_file","cmtk_cc_unknown_file"),
                                                   ("ribbon_file","cmtk_ribbon_file"),("white_matter_mask_file","wm_mask_file"),
                                                   ("roi_files","cmtk_roi_files"),("roi_files_in_structural_space","cmtk_roiv_files")])
                        ])

        return flow

