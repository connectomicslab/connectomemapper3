# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for building connectivity matrices and resulting CFF file
"""

# Global imports
from traits.api import *
from traitsui.api import *
import glob
import os
import pickle
import gzip

# Nipype imports
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
# import nipype.interfaces.cmtk as cmtk
import cmtklib as cmtk
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec,\
    traits, File, TraitedSpec, InputMultiPath, OutputMultiPath, isdefined
from nipype.utils.filemanip import split_filename

# Own imports
from cmtklib.connectome import mrtrixcmat, cmat, prob_cmat, probtrackx_cmat
from nipype.interfaces.mrtrix3.connectivity import BuildConnectome
from cmp.interfaces.mrtrix3 import FilterTractogram
from cmp.configurator.stages.common import Stage

class ConnectomeConfig(HasTraits):
    #modality = List(['Deterministic','Probabilistic'])
    probtrackx = Bool(False)
    compute_curvature = Bool(False)
    output_types = List(['gPickle'], editor=CheckListEditor(values=['gPickle','mat','cff','graphml'],cols=4))
    connectivity_metrics = List(['Fiber number','Fiber length','Fiber density','Fiber proportion','Normalized fiber density','ADC','gFA'], editor=CheckListEditor(values=['Fiber number','Fiber length','Fiber density','Fiber proportion','Normalized fiber density','ADC','gFA'],cols=4))
    log_visualization = Bool(True)
    circular_layout = Bool(False)
    subject = Str

    traits_view = View(Item('output_types',style='custom'),
                        Group(
                            Item('connectivity_metrics',label='Metrics',style='custom'),
                            Item('compute_curvature'),
                            label='Connectivity matrix', show_border=True
                            ),
                        Group(
                            Item('log_visualization',label='Log scale'),
                            Item('circular_layout',label='Circular layout'),
                            label='Visualization'
                            ),
                        )

class ConnectomeStage(Stage):

    def __init__(self):
        self.name = 'connectome_stage'
        self.config = ConnectomeConfig()
        self.inputs = ["roi_volumes_registered","roi_graphMLs","track_file",
                  "parcellation_scheme","atlas_info","gFA","ADC","skewness","kurtosis","P0","mapmri_maps"]
        self.outputs = ["endpoints_file","endpoints_mm_file","final_fiberslength_files",
                   "filtered_fiberslabel_files","final_fiberlabels_files",
                   "streamline_final_file","connectivity_matrices"]

    def define_inspect_outputs(self):
        con_results_path = os.path.join(self.stage_dir,"compute_matrice","result_compute_matrice.pklz")
        print "Stage dir: %s" % self.stage_dir
        if(os.path.exists(con_results_path)):
            print "con_results_path : %s" % con_results_path
            con_results = pickle.load(gzip.open(con_results_path))
            self.inspect_outputs_dict['streamline_final'] = ['trackvis',con_results.outputs.streamline_final_file]
            mat = con_results.outputs.connectivity_matrices
            print "Conn. matrix : %s" % mat

            map_scale = "default"
            if self.config.log_visualization:
                map_scale = "log"

            if self.config.circular_layout:
                layout='circular'
            else:
                layout='matrix'

            if isinstance(mat, basestring):
                print "is str"
                if 'gpickle' in mat:
                    # 'Fiber number','Fiber length','Fiber density','ADC','gFA'
                    con_name = os.path.basename(mat).split(".")[0].split("_")[-1]
                    print "con_name:"
                    print con_name
                    if any('Fiber number' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - number of fibers'] = ["showmatrix_gpickle",layout,mat, "number_of_fibers", "False", self.config.subject+' - '+con_name+' - number of fibers', map_scale]
                    if any('Fiber length' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - fiber length mean'] = ["showmatrix_gpickle",layout,mat, "fiber_length_mean", "False", self.config.subject+' - '+con_name+' - fiber length mean', map_scale]
                        self.inspect_outputs_dict[con_name+' - fiber length median'] = ["showmatrix_gpickle",layout,mat, "fiber_length_median", "False", self.config.subject+' - '+con_name+' - fiber length median', map_scale]
                        self.inspect_outputs_dict[con_name+' - fiber length std'] = ["showmatrix_gpickle",layout,mat, "fiber_length_std", "False", self.config.subject+' - '+con_name+' - fiber length std', map_scale]
                    if any('Fiber density' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - fiber density'] = ["showmatrix_gpickle",layout,mat, "fiber_density", "False", self.config.subject+' - '+con_name+' - fiber density', map_scale]
                    if any('Fiber proportion' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - fiber proportion'] = ["showmatrix_gpickle",layout,mat, "fiber_proportion", "False", self.config.subject+' - '+con_name+' - fiber proportion', map_scale]
                    if any('Normalized fiber density' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - normalized fiber density'] = ["showmatrix_gpickle",layout,mat, "normalized_fiber_density", "False", self.config.subject+' - '+con_name+' - normalized fiber density', map_scale]
                    if any('gFA' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - gFA mean'] = ["showmatrix_gpickle",layout,mat, "FA_mean", "False", self.config.subject+' - '+con_name+' - gFA mean']
                        self.inspect_outputs_dict[con_name+' - gFA median'] = ["showmatrix_gpickle",layout,mat, "FA_median", "False",self.config.subject+' - '+con_name+' - gFA median']
                        self.inspect_outputs_dict[con_name+' - gFA std'] = ["showmatrix_gpickle",layout,mat, "FA_std", "False", self.config.subject+' - '+con_name+' - gFA std']
                    if any('ADC' in m for m in self.config.connectivity_metrics):
                        self.inspect_outputs_dict[con_name+' - ADC mean'] = ["showmatrix_gpickle",layout,mat, "ADC_mean", "False", self.config.subject+' - '+con_name+' - ADC mean']
                        self.inspect_outputs_dict[con_name+' - ADC median'] = ["showmatrix_gpickle",layout,mat, "ADC_median", "False", self.config.subject+' - '+con_name+' - ADC median']
                        self.inspect_outputs_dict[con_name+' - ADC std'] = ["showmatrix_gpickle",layout,mat, "ADC_std", "False", self.config.subject+' - '+con_name+' - ADC std']
            else:
                print "is list"
                for mat in con_results.outputs.connectivity_matrices:
                    print "mat : %s" % mat
                    if 'gpickle' in mat:
                        con_name = " ".join(os.path.basename(mat).split(".")[0].split("_"))
                        if any('Fiber number' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - number of fibers'] = ["showmatrix_gpickle",layout,mat, "number_of_fibers", "False", self.config.subject+' - '+con_name+' - number of fibers', map_scale]
                        if any('Fiber length' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - fiber length mean'] = ["showmatrix_gpickle",layout,mat, "fiber_length_mean", "False", self.config.subject+' - '+con_name+' - fiber length mean', map_scale]
                            self.inspect_outputs_dict[con_name+' - fiber length std'] = ["showmatrix_gpickle",layout,mat, "fiber_length_std", "False", self.config.subject+' - '+con_name+' - fiber length std', map_scale]
                            self.inspect_outputs_dict[con_name+' - fiber length median'] = ["showmatrix_gpickle",layout,mat, "fiber_length_median", "False", self.config.subject+' - '+con_name+' - fiber length median', map_scale]
                        if any('Fiber density' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - fiber density'] = ["showmatrix_gpickle",layout,mat, "fiber_density", "False", self.config.subject+' - '+con_name+' - fiber density', map_scale]
                        if any('Fiber proportion' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - fiber proportion'] = ["showmatrix_gpickle",layout,mat, "fiber_proportion", "False", self.config.subject+' - '+con_name+' - fiber proportion', map_scale]
                        if any('Normalized fiber density' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - normalized fiber density'] = ["showmatrix_gpickle",layout,mat, "normalized_fiber_density", "False", self.config.subject+' - '+con_name+' - normalized fiber density', map_scale]
                        if any('gFA' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - gFA mean'] = ["showmatrix_gpickle",layout,mat, "FA_mean", "False", self.config.subject+' - '+con_name+' - gFA mean']
                            self.inspect_outputs_dict[con_name+' - gFA std'] = ["showmatrix_gpickle",layout,mat, "FA_std", "False", self.config.subject+' - '+con_name+' - gFA std']
                            self.inspect_outputs_dict[con_name+' - gFA median'] = ["showmatrix_gpickle",layout,mat, "FA_mean", "False", self.config.subject+' - '+con_name+' - gFA median']
                        if any('ADC' in m for m in self.config.connectivity_metrics):
                            self.inspect_outputs_dict[con_name+' - ADC mean'] = ["showmatrix_gpickle",layout,mat, "ADC_mean", "False", self.config.subject+' - '+con_name+' - ADC mean']
                            self.inspect_outputs_dict[con_name+' - ADC std'] = ["showmatrix_gpickle",layout,mat, "ADC_std", "False", self.config.subject+' - '+con_name+' - ADC std']
                            self.inspect_outputs_dict[con_name+' - ADC median'] = ["showmatrix_gpickle",layout,mat, "ADC_median", "False", self.config.subject+' - '+con_name+' - ADC median']

            self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)
            #print self.inspect_outputs
