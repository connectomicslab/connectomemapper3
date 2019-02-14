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
from cmp.stages.common import Stage

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


class MRTrixConnectomeConfig(HasTraits):
    #modality = List(['Deterministic','Probabilistic'])
    #probtrackx = Bool(False)
    fiber_filter = Bool(True)
    output_types = List(['gPickle'], editor=CheckListEditor(values=['gPickle','mat','cff','graphml'],cols=4))

    traits_view = View(Item('output_types',style='custom'),
                        Group(Item('fiber_filter',label='Spherical-deconvolution Informed Filtering of Tractograms (SIFT2)'),label='Connectivity matrix', show_border=True),
                        )


class CMTK_cmatInputSpec(BaseInterfaceInputSpec):
    track_file = InputMultiPath(File(exists=True),desc='Tractography result', mandatory=True)
    roi_volumes = InputMultiPath(File(exists=True), desc='ROI volumes registered to diffusion space')
    parcellation_scheme = traits.Enum('Lausanne2008',['Lausanne2008','Lausanne2018','NativeFreesurfer','Custom'], usedefault=True)
    roi_graphMLs = InputMultiPath(File(exists=True), desc='GraphML description of ROI volumes (Lausanne2018)')
    atlas_info = Dict(mandatory = False,desc="custom atlas information")
    compute_curvature = traits.Bool(True, desc='Compute curvature', usedefault=True)
    additional_maps = traits.List(File,desc='Additional calculated maps (ADC, gFA, ...)')
    output_types = traits.List(Str, desc='Output types of the connectivity matrices')
    probtrackx = traits.Bool(False)
    voxel_connectivity = InputMultiPath(File(exists=True),desc = "ProbtrackX connectivity matrices (# seed voxels x # target ROIs)")

class CMTK_cmatOutputSpec(TraitedSpec):
    endpoints_file = File()
    endpoints_mm_file = File()
    final_fiberslength_files = OutputMultiPath(File())
    filtered_fiberslabel_files = OutputMultiPath(File())
    final_fiberlabels_files = OutputMultiPath(File())
    streamline_final_file = File()
    connectivity_matrices = OutputMultiPath(File())


class CMTK_cmat(BaseInterface):
    input_spec = CMTK_cmatInputSpec
    output_spec = CMTK_cmatOutputSpec

    def _run_interface(self, runtime):
        if isdefined(self.inputs.additional_maps):
            additional_maps = dict( (split_filename(add_map)[1],add_map) for add_map in self.inputs.additional_maps if add_map != '')
        else:
            additional_maps = {}

        if self.inputs.probtrackx:
            probtrackx_cmat(voxel_connectivity_files = self.inputs.track_file, roi_volumes=self.inputs.roi_volumes,
                parcellation_scheme=self.inputs.parcellation_scheme, atlas_info=self.inputs.atlas_info,
                output_types = self.inputs.output_types)
        elif len(self.inputs.track_file) > 1:
            prob_cmat(intrk=self.inputs.track_file, roi_volumes=self.inputs.roi_volumes,
             parcellation_scheme=self.inputs.parcellation_scheme,atlas_info = self.inputs.atlas_info,
             output_types=self.inputs.output_types)
        else:
            cmat(intrk=self.inputs.track_file[0], roi_volumes=self.inputs.roi_volumes, roi_graphmls=self.inputs.roi_graphMLs,
             parcellation_scheme=self.inputs.parcellation_scheme,atlas_info = self.inputs.atlas_info,
             compute_curvature=self.inputs.compute_curvature,
             additional_maps=additional_maps,output_types=self.inputs.output_types)

            if 'cff' in self.inputs.output_types:
                cvt = cmtk.CFFConverter()
                cvt.inputs.title = 'Connectome mapper'
                cvt.inputs.nifti_volumes = self.inputs.roi_volumes
                cvt.inputs.tract_files = ['streamline_final.trk']
                cvt.inputs.gpickled_networks = glob.glob(os.path.abspath("connectome_*.gpickle"))
                cvt.run()

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['endpoints_file'] = os.path.abspath('endpoints.npy')
        outputs['endpoints_mm_file'] = os.path.abspath('endpointsmm.npy')
        outputs['final_fiberslength_files'] = glob.glob(os.path.abspath('final_fiberslength*'))
        outputs['filtered_fiberslabel_files'] = glob.glob(os.path.abspath('filtered_fiberslabel*'))
        outputs['final_fiberlabels_files'] = glob.glob(os.path.abspath('final_fiberlabels*'))
        outputs['streamline_final_file'] = os.path.abspath('streamline_final.trk')
        outputs['connectivity_matrices'] = glob.glob(os.path.abspath('connectome*'))

        return outputs

class CMTK_mrtrixcmatInputSpec(BaseInterfaceInputSpec):
    track_file = InputMultiPath(File(exists=True),desc='Tractography result', mandatory=True)
    fod_file = InputMultiPath(File(exists=True),desc='Input image containing the spherical harmonics of the fibre orientation distributions', mandatory=True)
    roi_volumes = InputMultiPath(File(exists=True), desc='ROI volumes ')
    parcellation_scheme = traits.Enum('Lausanne2008',['Lausanne2008','NativeFreesurfer','Custom'], usedefault=True)
    atlas_info = Dict(mandatory = False,desc="custom atlas information")
    compute_curvature = traits.Bool(True, desc='Compute curvature', usedefault=True)
    additional_maps = traits.List(File,desc='Additional calculated maps (ADC, gFA, ...)')
    output_types = traits.List(Str, desc='Output types of the connectivity matrices')
    #probtrackx = traits.Bool(False)
    #voxel_connectivity = InputMultiPath(File(exists=True),desc = "ProbtrackX connectivity matrices (# seed voxels x # target ROIs)")

class CMTK_mrtrixcmatOutputSpec(TraitedSpec):
    # endpoints_file = File()
    # endpoints_mm_file = File()
    # final_fiberslength_files = OutputMultiPath(File())
    # filtered_fiberslabel_files = OutputMultiPath(File())
    # final_fiberlabels_files = OutputMultiPath(File())
    streamline_final_file = File()
    connectivity_matrices = OutputMultiPath(File())


class CMTK_mrtrixcmat(BaseInterface):
    input_spec = CMTK_mrtrixcmatInputSpec
    output_spec = CMTK_mrtrixcmatOutputSpec

    def _run_interface(self, runtime):
        if isdefined(self.inputs.additional_maps):
            additional_maps = dict( (split_filename(add_map)[1],add_map) for add_map in self.inputs.additional_maps if add_map != '')
        else:
            additional_maps = {}

        mrtrixcmat(intck=self.inputs.track_file[0], fod_file=self.inputs.fod_file, roi_volumes=self.inputs.roi_volumes,
             parcellation_scheme=self.inputs.parcellation_scheme,atlas_info = self.inputs.atlas_info,
             compute_curvature=self.inputs.compute_curvature, additional_maps=additional_maps,output_types=self.inputs.output_types)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        # outputs['endpoints_file'] = os.path.abspath('endpoints.npy')
        # outputs['endpoints_mm_file'] = os.path.abspath('endpointsmm.npy')
        # outputs['final_fiberslength_files'] = glob.glob(os.path.abspath('final_fiberslength*'))
        # outputs['filtered_fiberslabel_files'] = glob.glob(os.path.abspath('filtered_fiberslabel*'))
        # outputs['final_fiberlabels_files'] = glob.glob(os.path.abspath('final_fiberlabels*'))
        outputs['streamline_final_file'] = os.path.abspath('streamline_final.tck')
        outputs['connectivity_matrices'] = glob.glob(os.path.abspath('connectome*'))

        return outputs

class ConnectomeStage(Stage):

    def __init__(self):
        self.name = 'connectome_stage'
        self.config = ConnectomeConfig()
        self.inputs = ["roi_volumes_registered","roi_graphMLs",
                       "track_file",
                       "parcellation_scheme","atlas_info",
                       "FA","ADC","AD","RD",
                       "skewness","kurtosis","P0",
                       "shore_maps","mapmri_maps"]
        self.outputs = ["endpoints_file","endpoints_mm_file","final_fiberslength_files",
                        "filtered_fiberslabel_files","final_fiberlabels_files",
                        "streamline_final_file","connectivity_matrices"]


    def create_workflow(self, flow, inputnode, outputnode):
        cmtk_cmat = pe.Node(interface=CMTK_cmat(),name="compute_matrice")
        cmtk_cmat.inputs.compute_curvature = self.config.compute_curvature
        cmtk_cmat.inputs.output_types = self.config.output_types
        cmtk_cmat.inputs.probtrackx = self.config.probtrackx

        # Additional maps
        map_merge = pe.Node(interface=util.Merge(9),name="merge_additional_maps")

        flow.connect([
                     (inputnode,map_merge, [('FA','in1'),
                                            ('ADC','in2'),
                                            ('AD','in3'),
                                            ('RD','in4'),
                                            ('skewness','in5'),
                                            ('kurtosis','in6'),
                                            ('P0','in7'),
                                            ('shore_maps','in8'),
                                            ('mapmri_maps','in9')]),
                     (map_merge,cmtk_cmat, [('out','additional_maps')])
                     ])

        flow.connect([
                     (inputnode,cmtk_cmat, [('track_file','track_file'),
                                            ('roi_graphMLs','roi_graphMLs'),
                                            ('parcellation_scheme','parcellation_scheme'),
                                            ('atlas_info','atlas_info'),
                                            ('roi_volumes_registered','roi_volumes')]),
                     (cmtk_cmat,outputnode, [('endpoints_file','endpoints_file'),
                                             ('endpoints_mm_file','endpoints_mm_file'),
                                             ('final_fiberslength_files','final_fiberslength_files'),
                                             ('filtered_fiberslabel_files','filtered_fiberslabel_files'),
                                             ('final_fiberlabels_files','final_fiberlabels_files'),
                                             ('streamline_final_file','streamline_final_file'),
                                             ('connectivity_matrices','connectivity_matrices')])
                     ])

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

    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir,"compute_matrice","result_compute_matrice.pklz"))


class MRTrixConnectomeStage(Stage):

    def __init__(self):
        self.name = 'connectome_stage'
        self.config = MRTrixConnectomeConfig()
        self.inputs = ["roi_volumes_registered","diffusion_model","track_file","fod_file",
                  "parcellation_scheme","atlas_info","gFA","skewness","kurtosis","P0"]
        self.outputs = ["streamline_final_file","connectivity_matrices"]

    def create_workflow(self, flow, inputnode, outputnode):

        #conflow = pe.Workflow(name='MRTRix_connectome_pipeline')
        #connectome_inputnode = pe.Node(interface=util.IdentityInterface(fields=['intck','fod_file','roi_volumes']),name='inputnode')
        #connectome_outputnode = pe.Node(interface=util.IdentityInterface(fields=['connectome']),name='outputnode')

        def get_first(output):
            return output[0]


        # Additional maps
        map_merge = pe.Node(interface=util.Merge(4),name="merge_additional_maps")
        flow.connect([
                     (inputnode,map_merge, [('gFA','in1'),('skewness','in2'),('kurtosis','in3'),('P0','in4')])
                     #(map_merge,cmtk_mrtrixcmat, [('out','additional_maps')]),
                    ])

        #print "INTCK : ",intck
        if self.config.fiber_filter:
            fibers_filter = pe.Node(interface=FilterTractogram(out_file='streamlines_weights.txt'),name='fibers_filter')

            flow.connect([
                            (inputnode,fibers_filter,[('track_file','in_tracks')])
                            ])

            # if inputnode.inputs.diffusion_model == 'Deterministic':
            #     flow.connect([
            #                 (inputnode,fibers_filter,[('track_file','in_tracks')])
            #                 ])
            # else:
            #     flow.connect([
            #                 (inputnode,fibers_filter,[(('track_file',get_first),'in_tracks')]),
            #                 ])
            flow.connect([
                        (inputnode,fibers_filter,[('fod_file','in_fod')])
                        ])

        connectome_builder = pe.Node(interface=BuildConnectome(),name='connectome_builder')
        #connectome_builder.inputs.zero_diagonal = True

        #Test if trackfile is a list of tracks filename (Probabilistic tracking) or only a filename (Deterministic tracking)

        flow.connect([
                        (inputnode,connectome_builder,[('track_file','in_file')])
                        ])

        # if inputnode.inputs.diffusion_model == 'Deterministic':
        #     print "Deterministic"
        #     flow.connect([
        #                 (inputnode,connectome_builder,[('track_file','in_file')])
        #                 ])
        # else:
        #     print "Probabilistic"
        #     flow.connect([
        #                 (inputnode,connectome_builder,[(('track_file',get_first),'in_file')])
        #                 ])


        flow.connect([
                    (inputnode,connectome_builder,[(('roi_volumes_registered',get_first),'in_parc')]),
                    ])

        if self.config.fiber_filter:
            flow.connect([
                        (fibers_filter,connectome_builder,[('out_weights','in_weights')])
                        ])


        flow.connect([
                    (inputnode,outputnode, [('track_file','streamline_final_file')]),
                    (connectome_builder,outputnode, [('out_file','connectivity_matrices')])
                    ])


    def define_inspect_outputs(self):
        # print "stage_dir : %s" % self.stage_dir
        # con_results_path = os.path.join(self.stage_dir,"compute_matrice","result_compute_matrice.pklz")
        # if(os.path.exists(con_results_path)):
        #     con_results = pickle.load(gzip.open(con_results_path))
        #     self.inspect_outputs_dict['streamline_final'] = ['mrview',con_results.outputs.streamline_final_file]
        #     if type(con_results.outputs.connectivity_matrices) == str:
        #         mat = con_results.outputs.connectivity_matrices
        #         if 'gpickle' in mat:
        #             self.inspect_outputs_dict[os.path.basename(mat)] = ["showmatrix_gpickle",mat, "number_of_fibers", "False"]
        #     else:
        #         for mat in con_results.outputs.connectivity_matrices:
        #             if 'gpickle' in mat:
        #                 self.inspect_outputs_dict[os.path.basename(mat)] = ["showmatrix_gpickle",mat, "number_of_fibers", "False"]

        #     self.inspect_outputs = self.inspect_outputs_dict.keys()

        print "stage_dir : %s" % self.stage_dir
        con_results_path = os.path.join(self.stage_dir,"connectome_builder","result_connectome_builder.pklz")
        if(os.path.exists(con_results_path)):
            con_results = pickle.load(gzip.open(con_results_path))
            self.inspect_outputs_dict['streamline_final'] = ['mrview',con_results.inputs['in_file']]
            if type(con_results.outputs.out_file) == str:
                mat = con_results.outputs.out_file
                if 'gpickle' in mat:
                    self.inspect_outputs_dict[os.path.basename(mat)] = ["showmatrix_gpickle",mat, "number_of_fibers", "False"]
            else:
                for mat in con_results.outputs.out_file:
                    if 'gpickle' in mat:
                        self.inspect_outputs_dict[os.path.basename(mat)] = ["showmatrix_gpickle",mat, "number_of_fibers", "False"]

            self.inspect_outputs = self.inspect_outputs_dict.keys()

    def has_run(self):
        # return os.path.exists(os.path.join(self.stage_dir,"compute_matrice","result_compute_matrice.pklz"))
        return os.path.exists(os.path.join(self.stage_dir,"connectome_builder","result_connectome_builder.pklz"))
