# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for building connectivity matrices and resulting CFF file
"""

# Global imports
import os
import pickle
import gzip

from traits.api import *
from traitsui.api import *

# Own imports
from cmp.bidsappmanager.stages.common import Stage

class ConnectomeConfig(HasTraits):
    subject = Str()

    apply_scrubbing = Bool(False)
    FD_thr = Float(0.2)
    DVARS_thr = Float(4.0)
    output_types = List(['gPickle'], editor=CheckListEditor(values=['gPickle','mat','cff','graphml'],cols=4))

    traits_view = View(VGroup('apply_scrubbing',VGroup(Item('FD_thr',label='FD threshold'),Item('DVARS_thr',label='DVARS threshold'),visible_when="apply_scrubbing==True")),
                       Item('output_types',style='custom'))

    
class ConnectomeStage(Stage):

    def __init__(self):
        self.name = 'connectome_stage'
        self.config = ConnectomeConfig()
        self.inputs = ["roi_volumes_registered","func_file", "FD","DVARS",
                  "parcellation_scheme","atlas_info","roi_graphMLs"]
        self.outputs = ["connectivity_matrices","avg_timeseries"]

    def define_inspect_outputs(self):
        con_results_path = os.path.join(self.stage_dir,"compute_matrice","result_compute_matrice.pklz")
        print('con_results_path : ',con_results_path)
        if(os.path.exists(con_results_path)):

            con_results = pickle.load(gzip.open(con_results_path))
            print(con_results)

            if isinstance(con_results.outputs.connectivity_matrices, basestring):
                mat = con_results.outputs.connectivity_matrices
                print(mat)
                if 'gpickle' in mat:
                    self.inspect_outputs_dict['ROI-average time-series correlation - Connectome %s'%os.path.basename(mat)] = ["showmatrix_gpickle",'matrix',mat, "corr", "False", self.config.subject+' - '+con_name+' - Correlation', "default"]
            else:
                for mat in con_results.outputs.connectivity_matrices:
                    print(mat)
                    if 'gpickle' in mat:
                        con_name = os.path.basename(mat).split(".")[0].split("_")[-1]
                        self.inspect_outputs_dict['ROI-average time-series correlation - Connectome %s'%con_name] = ["showmatrix_gpickle",'matrix',mat, "corr", "False", self.config.subject+' - '+con_name+' - Correlation', "default"]

            self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)

    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"compute_matrice","result_compute_matrice.pklz"))
