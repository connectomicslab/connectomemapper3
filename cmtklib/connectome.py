# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMTK Connectome functions
""" 

from os import path as op
import nibabel
import numpy as np
import networkx as nx
import scipy.io

import nipype.pipeline.engine as pe
import nipype.interfaces.mrtrix as mrtrix

from nipype.interfaces.base import CommandLine, CommandLineInputSpec, traits, File, TraitedSpec, BaseInterface, BaseInterfaceInputSpec, isdefined


from util import mean_curvature, length
from parcellation import get_parcellation

def compute_curvature_array(fib):
    """ Computes the curvature array """
    print("Compute curvature ...")
    
    n = len(fib)
    pc        = -1
    meancurv = np.zeros( (n, 1) )
    for i, fi in enumerate(fib):
        # Percent counter
        pcN = int(round( float(100*i)/n ))
        if pcN > pc and pcN%1 == 0:    
            pc = pcN
            print('%4.0f%%' % (pc))
        meancurv[i,0] = mean_curvature(fi[0])

    return meancurv

def create_endpoints_array(fib, voxelSize, print_info):
    """ Create the endpoints arrays for each fiber
        
    Parameters
    ----------
    fib: the fibers data
    voxelSize: 3-tuple containing the voxel size of the ROI image
    
    Returns
    -------
    (endpoints: matrix of size [#fibers, 2, 3] containing for each fiber the
               index of its first and last point in the voxelSize volume
    endpointsmm) : endpoints in milimeter coordinates
    
    """
    if print_info:
        print("========================")
        print("create_endpoints_array")
    
    # Init
    n         = len(fib)
    endpoints = np.zeros( (n, 2, 3) )
    endpointsmm = np.zeros( (n, 2, 3) )
    pc        = -1

    # Computation for each fiber
    for i, fi in enumerate(fib):
    
        # Percent counter
        if print_info:
            pcN = int(round( float(100*i)/n ))
            if pcN > pc and pcN%20 == 0:    
                pc = pcN
                print('%4.0f%%' % (pc))

        f = fi[0]
    
        # store startpoint
        endpoints[i,0,:] = f[0,:]
        # store endpoint
        endpoints[i,1,:] = f[-1,:]
        
        # store startpoint
        endpointsmm[i,0,:] = f[0,:]
        # store endpoint
        endpointsmm[i,1,:] = f[-1,:]

        #print 'endpoints (mm) : ',endpoints[i, 0, :],' ; ',endpoints[i, 1, :]
        
        # Translate from mm to index
        endpoints[i,0,0] = int( endpoints[i,0,0] / float(voxelSize[0]))
        endpoints[i,0,1] = int( endpoints[i,0,1] / float(voxelSize[1]))
        endpoints[i,0,2] = int( endpoints[i,0,2] / float(voxelSize[2]))
        endpoints[i,1,0] = int( endpoints[i,1,0] / float(voxelSize[0]))
        endpoints[i,1,1] = int( endpoints[i,1,1] / float(voxelSize[1]))
        endpoints[i,1,2] = int( endpoints[i,1,2] / float(voxelSize[2]))

        #print 'endpoints : ',endpoints[i, 0, :],' ; ',endpoints[i, 1, :]
        
    # Return the matrices  
    return (endpoints, endpointsmm)


def save_fibers(oldhdr, oldfib, fname, indices):
    """ Stores a new trackvis file fname using only given indices """

    hdrnew = oldhdr.copy()

    outstreams = []
    for i in indices:
        outstreams.append( oldfib[i] )

    n_fib_out = len(outstreams)
    hdrnew['n_count'] = n_fib_out

    print("Writing final no orphan fibers: %s" % fname)
    nibabel.trackvis.write(fname, outstreams, hdrnew)
    
def probtrackx_cmat(voxel_connectivity_files, roi_volumes, parcellation_scheme, output_types=['gPickle'], atlas_info = {}): 

    print("Filling probabilistic connectivity matrices:")

    if parcellation_scheme != "Custom":
        resolutions = get_parcellation(parcellation_scheme)
    else:
        resolutions = atlas_info
        
    #firstROIFile = roi_volumes[0]
    #firstROI = nibabel.load(firstROIFile)
    #roiVoxelSize = firstROI.get_header().get_zooms()
    
    for parkey, parval in resolutions.items():            
        print("Resolution = "+parkey)
        
        # Open the corresponding ROI
        print("Open the corresponding ROI")
        for vol in roi_volumes:
            if parkey in vol:
                roi_fname = vol
                print roi_fname
        roi       = nibabel.load(roi_fname)
        roiData   = roi.get_data()
      
        # Create the matrix
        nROIs = parval['number_of_regions']
        print("Create the connection matrix (%s rois)" % nROIs)
        G     = nx.Graph()
        
        # Match ROI indexes to matrix indexes
        ROI_idx = np.unique(roiData[roiData != 0]).astype('int32')

        # add node information from parcellation
        gp = nx.read_graphml(parval['node_information_graphml'])
        for u,d in gp.nodes_iter(data=True):
            G.add_node(int(u), d)
            # compute a position for the node based on the mean position of the
            # ROI in voxel coordinates (segmentation volume )
            G.node[int(u)]['dn_position'] = tuple(np.mean( np.where(roiData== int(d["dn_correspondence_id"]) ) , axis = 1))

        tot_tracks = 0
        
        pc = -1
        
        for voxmat_i in range(0,len(voxel_connectivity_files)):
            pcN = int(round( float(100*voxmat_i)/len(voxel_connectivity_files) ))
            if pcN > pc and pcN%20 == 0:
                pc = pcN
                print('%4.0f%%' % (pc))
            #fib, hdr    = nibabel.trackvis.read(voxel_connectivity[voxmat_i], False)
            #(endpoints,endpointsmm) = create_endpoints_array(fib, roiVoxelSize, False)
            #n = len(fib)
            
            startROI = int(ROI_idx[voxmat_i])
                
            voxmat = np.loadtxt(voxel_connectivity_files[voxmat_i]).astype('int32')
            if len(voxmat.shape) > 1:
                ROImat = np.sum(voxmat,0)
            else:
                ROImat = voxmat
            
            for target in range(0,len(ROI_idx)):
                
                endROI = int(ROI_idx[target])

                if startROI != endROI: # Excludes loops (connections within the same ROI)
                    # Add edge to graph
                    if G.has_edge(startROI, endROI):
                        G.edge[startROI][endROI]['n_tracks'] += ROImat[target]
                    else:
                        G.add_edge(startROI, endROI, n_tracks  = ROImat[target])
                    
                    tot_tracks += ROImat[target]
                    
        for u,v,d in G.edges_iter(data=True):
            G.remove_edge(u,v)
            di = { 'number_of_fibers' : (float(d['n_tracks']) / tot_tracks.astype(float))}
            G.add_edge(u,v, di)
                
        # storing network
        if 'gPickle' in output_types:
            nx.write_gpickle(G, 'connectome_%s.gpickle' % parkey)
        if 'mat' in output_types:
            # edges
            size_edges = (parval['number_of_regions'],parval['number_of_regions'])
            edge_keys = G.edges(data=True)[0][2].keys()
            
            edge_struct = {}
            for edge_key in edge_keys:
                edge_struct[edge_key] = nx.to_numpy_matrix(G,weight=edge_key)
                
            # nodes
            size_nodes = parval['number_of_regions']
            node_keys = G.nodes(data=True)[0][1].keys()

            node_struct = {}
            for node_key in node_keys:
                if node_key == 'dn_position':
                    node_arr = np.zeros([size_nodes,3],dtype=np.float)
                else:
                    node_arr = np.zeros(size_nodes,dtype=np.object_)
                node_n = 0
                for _,node_data in G.nodes(data=True):
                    node_arr[node_n] = node_data[node_key]
                    node_n += 1
                node_struct[node_key] = node_arr
                
            scipy.io.savemat('connectome_%s.mat' % parkey, mdict={'sc':edge_struct,'nodes':node_struct})
        if 'graphml' in output_types:
            g2 = nx.Graph()
            for u_gml,v_gml,d_gml in G.edges_iter(data=True):
                g2.add_edge(u_gml,v_gml,d_gml)
            for u_gml,d_gml in G.nodes(data=True):
                g2.add_node(u_gml,{'dn_correspondence_id':d_gml['dn_correspondence_id'],
                               'dn_fsname':d_gml['dn_fsname'],
                               'dn_hemisphere':d_gml['dn_hemisphere'],
                               'dn_name':d_gml['dn_name'],
                               'dn_position_x':float(d_gml['dn_position'][0]),
                               'dn_position_y':float(d_gml['dn_position'][1]),
                               'dn_position_z':float(d_gml['dn_position'][2]),
                               'dn_region':d_gml['dn_region']})
            nx.write_graphml(g2,'connectome_%s.graphml' % parkey)
    
def prob_cmat(intrk, roi_volumes, parcellation_scheme, output_types=['gPickle'], atlas_info = {}): 

    print("Filling probabilistic connectivity matrices:")

    if parcellation_scheme != "Custom":
        resolutions = get_parcellation(parcellation_scheme)
    else:
        resolutions = atlas_info
        
    firstROIFile = roi_volumes[0]
    firstROI = nibabel.load(firstROIFile)
    roiVoxelSize = firstROI.get_header().get_zooms()
    
    for parkey, parval in resolutions.items():            
        print("Resolution = "+parkey)
        
        # Open the corresponding ROI
        print("Open the corresponding ROI")
        for vol in roi_volumes:
            if parkey in vol:
                roi_fname = vol
                print roi_fname
        roi       = nibabel.load(roi_fname)
        roiData   = roi.get_data()
      
        # Create the matrix
        nROIs = parval['number_of_regions']
        print("Create the connection matrix (%s rois)" % nROIs)
        G     = nx.Graph()

        # add node information from parcellation
        gp = nx.read_graphml(parval['node_information_graphml'])
        for u,d in gp.nodes_iter(data=True):
            G.add_node(int(u), d)
            # compute a position for the node based on the mean position of the
            # ROI in voxel coordinates (segmentation volume )
            G.node[int(u)]['dn_position'] = tuple(np.mean( np.where(roiData== int(d["dn_correspondence_id"]) ) , axis = 1))

        graph_matrix = np.zeros((nROIs,nROIs),dtype = int)
        
        pc = -1
        
        for intrk_i in range(0,len(intrk)):
            pcN = int(round( float(100*intrk_i)/len(intrk) ))
            if pcN > pc and pcN%20 == 0:
                pc = pcN
                print('%4.0f%%' % (pc))
            fib, hdr    = nibabel.trackvis.read(intrk[intrk_i], False)
            (endpoints,endpointsmm) = create_endpoints_array(fib, roiVoxelSize, False)
            n = len(fib)
                
            dis = 0
        
            pc = -1
            for i in range(n):  # n: number of fibers
        
                # ROI start => ROI end
                try:
                    startROI = int(roiData[endpoints[i, 0, 0], endpoints[i, 0, 1], endpoints[i, 0, 2]]) # endpoints from create_endpoints_array
                    endROI   = int(roiData[endpoints[i, 1, 0], endpoints[i, 1, 1], endpoints[i, 1, 2]])
                except IndexError:
                    print("An index error occured for fiber %s. This means that the fiber start or endpoint is outside the volume. Continue." % i)
                    continue
                
                # Filter
                if startROI == 0 or endROI == 0:
                    dis += 1
                    #fiberlabels[i,0] = -1
                    continue
                
                if startROI > nROIs or endROI > nROIs:
        #                print("Start or endpoint of fiber terminate in a voxel which is labeled higher")
        #                print("than is expected by the parcellation node information.")
        #                print("Start ROI: %i, End ROI: %i" % (startROI, endROI))
        #                print("This needs bugfixing!")
                    continue
                
                # Update fiber label
                # switch the rois in order to enforce startROI < endROI
                if endROI < startROI:
                    tmp = startROI
                    startROI = endROI
                    endROI = tmp
        
                # Add edge to graph
                if G.has_edge(startROI, endROI):
                    G.edge[startROI][endROI]['n_tracks'] += 1
                else:
                    G.add_edge(startROI, endROI, n_tracks  = 1)
                
                graph_matrix[startROI-1][endROI-1] +=1
                
        tot_tracks = graph_matrix.sum()
                    
        for u,v,d in G.edges_iter(data=True):
            G.remove_edge(u,v)
            di = { 'number_of_fibers' : (float(d['n_tracks']) / tot_tracks.astype(float))}
            G.add_edge(u,v, di)
                
        # storing network
        if 'gPickle' in output_types:
            nx.write_gpickle(G, 'connectome_%s.gpickle' % parkey)
        if 'mat' in output_types:
            # edges
            size_edges = (parval['number_of_regions'],parval['number_of_regions'])
            edge_keys = G.edges(data=True)[0][2].keys()
            
            edge_struct = {}
            for edge_key in edge_keys:
                edge_struct[edge_key] = nx.to_numpy_matrix(G,weight=edge_key)
                
            # nodes
            size_nodes = parval['number_of_regions']
            node_keys = G.nodes(data=True)[0][1].keys()

            node_struct = {}
            for node_key in node_keys:
                if node_key == 'dn_position':
                    node_arr = np.zeros([size_nodes,3],dtype=np.float)
                else:
                    node_arr = np.zeros(size_nodes,dtype=np.object_)
                node_n = 0
                for _,node_data in G.nodes(data=True):
                    node_arr[node_n] = node_data[node_key]
                    node_n += 1
                node_struct[node_key] = node_arr
                
            scipy.io.savemat('connectome_%s.mat' % parkey, mdict={'sc':edge_struct,'nodes':node_struct})
        if 'graphml' in output_types:
            g2 = nx.Graph()
            for u_gml,v_gml,d_gml in G.edges_iter(data=True):
                g2.add_edge(u_gml,v_gml,d_gml)
            for u_gml,d_gml in G.nodes(data=True):
                g2.add_node(u_gml,{'dn_correspondence_id':d_gml['dn_correspondence_id'],
                               'dn_fsname':d_gml['dn_fsname'],
                               'dn_hemisphere':d_gml['dn_hemisphere'],
                               'dn_name':d_gml['dn_name'],
                               'dn_position_x':float(d_gml['dn_position'][0]),
                               'dn_position_y':float(d_gml['dn_position'][1]),
                               'dn_position_z':float(d_gml['dn_position'][2]),
                               'dn_region':d_gml['dn_region']})
            nx.write_graphml(g2,'connectome_%s.graphml' % parkey)

class MRTrix3BaseInputSpec(CommandLineInputSpec):
    nthreads = traits.Int(
        argstr='-nthreads %d', desc='number of threads. if zero, the number'
        ' of available cpus will be used', nohash=True)
    # DW gradient table import options
    grad_file = File(exists=True, argstr='-grad %s',
                     desc='dw gradient scheme (MRTrix format')
    grad_fsl = traits.Tuple(
        File(exists=True), File(exists=True), argstr='-fslgrad %s %s',
        desc='(bvecs, bvals) dw gradient scheme (FSL format')
    bval_scale = traits.Enum(
        'yes', 'no', argstr='-bvalue_scaling %s',
        desc='specifies whether the b - values should be scaled by the square'
        ' of the corresponding DW gradient norm, as often required for '
        'multishell or DSI DW acquisition schemes. The default action '
        'can also be set in the MRtrix config file, under the '
        'BValueScaling entry. Valid choices are yes / no, true / '
        'false, 0 / 1 (default: true).')

    in_bvec = File(exists=True, argstr='-fslgrad %s %s',
                   desc='bvecs file in FSL format')
    in_bval = File(exists=True, desc='bvals file in FSL format')


class MRTrix3Base(CommandLine):

    def _format_arg(self, name, trait_spec, value):
        if name == 'nthreads' and value == 0:
            value = 1
            try:
                from multiprocessing import cpu_count
                value = cpu_count()
            except:
                logger.warn('Number of threads could not be computed')
                pass
            return trait_spec.argstr % value

        if name == 'in_bvec':
            return trait_spec.argstr % (value, self.inputs.in_bval)

        return super(MRTrix3Base, self)._format_arg(name, trait_spec, value)

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        try:
            if (isdefined(self.inputs.grad_file) or
                    isdefined(self.inputs.grad_fsl)):
                skip += ['in_bvec', 'in_bval']

            is_bvec = isdefined(self.inputs.in_bvec)
            is_bval = isdefined(self.inputs.in_bval)
            if is_bvec or is_bval:
                if not is_bvec or not is_bval:
                    raise RuntimeError('If using bvecs and bvals inputs, both'
                                       'should be defined')
                skip += ['in_bval']
        except AttributeError:
            pass

        return super(MRTrix3Base, self)._parse_inputs(skip=skip)

class BuildConnectomeInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=-3,
                   desc='input tractography')
    in_parc = File(exists=True, argstr='%s', position=-2,
                   desc='parcellation file')
    out_file = File(
        'connectome.csv', argstr='%s', mandatory=True, position=-1,
        usedefault=True, desc='output file after processing')

    nthreads = traits.Int(
        argstr='-nthreads %d', desc='number of threads. if zero, the number'
        ' of available cpus will be used', nohash=True)

    vox_lookup = traits.Bool(
        argstr='-assignment_voxel_lookup',
        desc='use a simple voxel lookup value at each streamline endpoint')
    search_radius = traits.Float(
        argstr='-assignment_radial_search %f',
        desc='perform a radial search from each streamline endpoint to locate '
        'the nearest node. Argument is the maximum radius in mm; if no node is'
        ' found within this radius, the streamline endpoint is not assigned to'
        ' any node.')
    search_reverse = traits.Float(
        argstr='-assignment_reverse_search %f',
        desc='traverse from each streamline endpoint inwards along the '
        'streamline, in search of the last node traversed by the streamline. '
        'Argument is the maximum traversal length in mm (set to 0 to allow '
        'search to continue to the streamline midpoint).')
    search_forward = traits.Float(
        argstr='-assignment_forward_search %f',
        desc='project the streamline forwards from the endpoint in search of a'
        'parcellation node voxel. Argument is the maximum traversal length in '
        'mm.')

    metric = traits.Enum(
        'count', 'meanlength', 'invlength', 'invnodevolume', 'mean_scalar',
        'invlength_invnodevolume', argstr='-metric %s', desc='specify the edge'
        ' weight metric')

    in_scalar = File(
        exists=True, argstr='-image %s', desc='provide the associated image '
        'for the mean_scalar metric')

    in_weights = File(
        exists=True, argstr='-tck_weights_in %s', desc='specify a text scalar '
        'file containing the streamline weights')

    keep_unassigned = traits.Bool(
        argstr='-keep_unassigned', desc='By default, the program discards the'
        ' information regarding those streamlines that are not successfully '
        'assigned to a node pair. Set this option to keep these values (will '
        'be the first row/column in the output matrix)')
    zero_diagonal = traits.Bool(
        argstr='-zero_diagonal', desc='set all diagonal entries in the matrix '
        'to zero (these represent streamlines that connect to the same node at'
        ' both ends)')


class BuildConnectomeOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='the output response file')


class BuildConnectome(MRTrix3Base):

    """
    Generate a connectome matrix from a streamlines file and a node
    parcellation image
    Example
    -------
    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> mat = mrt.BuildConnectome()
    >>> mat.inputs.in_file = 'tracks.tck'
    >>> mat.inputs.in_parc = 'aparc+aseg.nii'
    >>> mat.cmdline                               # doctest: +ELLIPSIS +ALLOW_UNICODE
    'tck2connectome tracks.tck aparc+aseg.nii connectome.csv'
    >>> mat.run()                                 # doctest: +SKIP
    """

    _cmd = 'tck2connectome'
    input_spec = BuildConnectomeInputSpec
    output_spec = BuildConnectomeOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = op.abspath(self.inputs.out_file)
        return outputs

class FilterTractogramInputSpec(CommandLineInputSpec):
    in_tracks = File(exists=True,mandatory=True,argstr='%s',position=-3,desc='Input track file')
    in_fod = File(exists=True,mandatory=True,argstr='%s',position=-2,desc='Input image containing the spherical harmonics of the fibre orientation distributions')
    out_file = File(argstr='%s',position=-1,desc='Output text file containing the weighting factor for each streamline')

class FilterTractogramOutputSpec(TraitedSpec):
    out_weights = File(exists=True,desc='Output text file containing the weighting factor for each streamline')

class FilterTractogram(MRTrix3Base):

    _cmd = 'tcksift2'
    input_spec = FilterTractogramInputSpec
    output_spec = FilterTractogramOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.out_file):
            outputs['out_weights'] = op.abspath('streamlines_weights.txt')
        else:
            outputs['out_weights'] = op.abspath(self.inputs.out_file)

        return outputs


def mrtrixcmat(intck, fod_file, roi_volumes, parcellation_scheme, compute_curvature=True, additional_maps={}, output_types=['gPickle'], atlas_info= {}):
    """ Create the connection matrix using MRTrix fibers and Freesurfer ROIs. """
    conflow = pe.Workflow(name='MRTRix_connectome_pipeline')
    #connectome_inputnode = pe.Node(interface=util.IdentityInterface(fields=['intck','fod_file','roi_volumes']),name='inputnode')
    #connectome_outputnode = pe.Node(interface=util.IdentityInterface(fields=['connectome']),name='outputnode')

    print "INTCK : ",intck 

    fibers_filter = pe.Node(interface=FilterTractogram(),name='fibers_filter')
    fibers_filter.inputs.in_tracks = op.intck
    fibers_filter.inputs.in_fod = fod_file
    fibers_filter.inputs.out_file = 'streamlines_weights.txt'

    connectome_builder = pe.Node(interface=BuildConnectome(),name='connectome_builder')
    connectome_builder.inputs.in_tracks = intck
    connectome_builder.inputs.in_parc = roi_volumes
    connectome_builder.inputs.zero_diagonal = True
   
    conflow.connect([
                (fibers_filter,connectome_builder,[('out_weights','in_weights')]),
                ])

    conflow.run()





def cmat(intrk, roi_volumes, parcellation_scheme, compute_curvature=True, additional_maps={}, output_types=['gPickle'], atlas_info = {}): 
    """ Create the connection matrix for each resolution using fibers and ROIs. """
              
    # create the endpoints for each fibers
    en_fname  = 'endpoints.npy'
    en_fnamemm  = 'endpointsmm.npy'
    #ep_fname  = 'lengths.npy'
    curv_fname  = 'meancurvature.npy'
    #intrk = op.join(gconf.get_cmp3_fibers(), 'streamline_filtered.trk')
    print('Opening file :' + intrk)
    fib, hdr    = nibabel.trackvis.read(intrk, False)
    
    print "Header trackvis : ",hdr
    #print "Fibers trackvis : ",fib

    if parcellation_scheme != "Custom":
        resolutions = get_parcellation(parcellation_scheme)
    else:
        resolutions = atlas_info
    
    # Previously, load_endpoints_from_trk() used the voxel size stored
    # in the track hdr to transform the endpoints to ROI voxel space.
    # This only works if the ROI voxel size is the same as the DSI/DTI
    # voxel size.  In the case of DTI, it is not.  
    # We do, however, assume that all of the ROI images have the same
    # voxel size, so this code just loads the first one to determine
    # what it should be
    firstROIFile = roi_volumes[0]
    firstROI = nibabel.load(firstROIFile)
    roiVoxelSize = firstROI.get_header().get_zooms()

    print "roi Voxel Size",roiVoxelSize
    (endpoints,endpointsmm) = create_endpoints_array(fib, roiVoxelSize, True)
    np.save(en_fname, endpoints)
    np.save(en_fnamemm, endpointsmm)

    # only compute curvature if required
    if compute_curvature:
        meancurv = compute_curvature_array(fib)
        np.save(curv_fname, meancurv)
    
    print("========================")
    
    n = len(fib)
    
    #resolution = gconf.parcellation.keys()

    streamline_wrote = False
    for parkey, parval in resolutions.items():
        #if parval['number_of_regions'] != 83:
        #    continue
            
        print("Resolution = "+parkey)

        print roi_volumes
        
        # create empty fiber label array
        fiberlabels = np.zeros( (n, 2) )
        final_fiberlabels = []
        final_fibers_idx = []
        
        # Open the corresponding ROI
        print("Open the corresponding ROI")
        for vol in roi_volumes:
            if parkey in vol:
                roi_fname = vol
                print roi_fname
        #roi_fname = roi_volumes[r]
        #r += 1
        roi       = nibabel.load(roi_fname)
        roiData   = roi.get_data()
        affine_vox_to_world = np.matrix(roi.affine[:3,:3])
        print "Affine Voxel 2 World transformation : ",affine_vox_to_world

        affine_world_to_vox = np.linalg.inv(affine_vox_to_world)
        print "Affine World 2 Voxel transformation : ",affine_world_to_vox

        origin = np.matrix(roi.affine[:3,3]).T
      
        # Create the matrix
        nROIs = parval['number_of_regions']
        print("Create the connection matrix (%s rois)" % nROIs)
        G     = nx.Graph()

        # add node information from parcellation
        gp = nx.read_graphml(parval['node_information_graphml'])
        for u,d in gp.nodes_iter(data=True):
            G.add_node(int(u), d)
            # compute a position for the node based on the mean position of the
            # ROI in voxel coordinates (segmentation volume )
            G.node[int(u)]['dn_position'] = tuple(np.mean( np.where(roiData== int(d["dn_correspondence_id"]) ) , axis = 1))

        dis = 0

        # prepare: compute the measures
        t = [c[0] for c in fib]
        h = np.array(t, dtype = np.object )
        
        mmap = additional_maps
        mmapdata = {}
        for k,v in mmap.items():
            da = nibabel.load(v)
            mmapdata[k] = (da.get_data(), da.get_header().get_zooms() )

        def voxmm2vox(x,y,z,affine_vox_to_world,origin):
            return np.rint( np.linalg.solve(affine_vox_to_world, (np.matrix([x,y,z]).T-origin) ) )

        def voxmm2vox2(x,y,z,affine_world_to_vox,origin):
            return np.rint( affine_world_to_vox * (np.matrix([x,y,z]).T) - origin )
        
        def voxmm2ras(x,y,z,affine_vox_to_world,origin):
            return np.rint( affine_vox_to_world * np.matrix([x,y,z]).T + origin)
        
        def voxmm2vox(x,y,z,voxelSize,origin):
           return np.rint( np.divide((np.matrix([x,y,z]).T-np.matrix(origin).T),np.matrix(voxelSize).T) ) 

        print("Create the connection matrix (%s fibers)" % n)
        pc = -1
        for i in range(n):  # n: number of fibers

            # Percent counter
            pcN = int(round( float(100*i)/n ))
            if pcN > pc and pcN%1 == 0:
                pc = pcN
                print('%4.0f%%' % (pc))
    
            # ROI start => ROI end
            try:
                # startvox = voxmm2vox2(endpointsmm[i, 0, 0], endpointsmm[i, 0, 1], endpointsmm[i, 0, 2], affine_vox_to_world, origin)
                # print "Start vox :",startvox
                # startROI = int(roiData[startvox[0], startvox[1], startvox[2]]) # endpoints from create_endpoints_array

                # endvox = voxmm2vox2(endpointsmm[i, 1, 0], endpointsmm[i, 1, 1], endpointsmm[i, 1, 2], affine_vox_to_world, origin)
                # print "End vox :",endvox
                # endROI   = int(roiData[endvox[0], endvox[1], endvox[2]])
                print "origin: ",origin[0],",",origin[1],",",origin[2]
                
                startvox = np.zeros((3,1))
                startvox[0]=np.int(endpointsmm[i, 0, 0])
                startvox[1]=np.int(endpointsmm[i, 0, 1])
                startvox[2]=np.int(endpointsmm[i, 0, 2])
                # startvox[0]=np.int(-(endpoints[i, 0, 0]+origin[0]))
                # startvox[1]=np.int(-(endpoints[i, 0, 1]+origin[1]))
                # startvox[2]=np.int(-endpoints[i, 0, 2]+origin[2])

                endvox = np.zeros((3,1))
                endvox[0]=np.int(endpointsmm[i, 1, 0])
                endvox[1]=np.int(endpointsmm[i, 1, 1])
                endvox[2]=np.int(endpointsmm[i, 1, 2])
                # endvox[0]=np.int(-(endpoints[i, 1, 0]+origin[0]))
                # endvox[1]=np.int(-(endpoints[i, 1, 1]+origin[1]))
                # endvox[2]=np.int(-endpoints[i, 1, 2]+origin[2])

                print "start point : ",startvox[0,0]," , ",startvox[1,0]," , ",startvox[2,0]
                print "end point : ",endvox[0,0]," , ",endvox[1,0]," , ",endvox[2,0]

                startROI = int(roiData[startvox[0,0],startvox[1,0],startvox[2,0]]) # endpoints from create_endpoints_array
                endROI   = int(roiData[endvox[0,0],endvox[1,0],endvox[2,0]])

                
                
            except IndexError:
                print("An index error occured for fiber %s. This means that the fiber start or endpoint is outside the volume. Continue." % i)
                continue
            
            # Filter
            if startROI == 0 or endROI == 0:
                dis += 1
                fiberlabels[i,0] = -1
                continue
            
            if startROI > nROIs or endROI > nROIs:
#                print("Start or endpoint of fiber terminate in a voxel which is labeled higher")
#                print("than is expected by the parcellation node information.")
#                print("Start ROI: %i, End ROI: %i" % (startROI, endROI))
#                print("This needs bugfixing!")
                continue
            
            # Update fiber label
            # switch the rois in order to enforce startROI < endROI
            if endROI < startROI:
                tmp = startROI
                startROI = endROI
                endROI = tmp

            fiberlabels[i,0] = startROI
            fiberlabels[i,1] = endROI

            final_fiberlabels.append( [ startROI, endROI ] )
            final_fibers_idx.append(i)

            # Add edge to graph
            if G.has_edge(startROI, endROI):
                G.edge[startROI][endROI]['fiblist'].append(i)
            else:
                G.add_edge(startROI, endROI, fiblist   = [i])
                
        print("Found %i (%f percent out of %i fibers) fibers that start or terminate in a voxel which is not labeled. (orphans)" % (dis, dis*100.0/n, n) )
        print("Valid fibers: %i (%f percent)" % (n-dis, 100 - dis*100.0/n) )

        print "roi : ",roi
        print "roiData size : ",roiData.size
        print "roiData shape : ",roiData.shape

        # create a final fiber length array
        finalfiberlength = []
        for idx in final_fibers_idx:
            # compute length of fiber
            finalfiberlength.append( length(fib[idx][0]) )

        # convert to array
        final_fiberlength_array = np.array( finalfiberlength )
        
        # make final fiber labels as array
        final_fiberlabels_array = np.array(final_fiberlabels, dtype = np.int32)

        # update edges
        # measures to add here
        for u,v,d in G.edges_iter(data=True):
            G.remove_edge(u,v)
            di = { 'number_of_fibers' : len(d['fiblist']), }

            print di
            
            # additional measures
            # compute mean/std of fiber measure
            idx = np.where( (final_fiberlabels_array[:,0] == int(u)) & (final_fiberlabels_array[:,1] == int(v)) )[0]

            print "idx : ",idx

            di['fiber_length_mean'] = float( np.mean(final_fiberlength_array[idx]) )
            di['fiber_length_std'] = float( np.std(final_fiberlength_array[idx]) )

            # this is indexed into the fibers that are valid in the sense of touching start
            # and end roi and not going out of the volume
            idx_valid = np.where( (fiberlabels[:,0] == int(u)) & (fiberlabels[:,1] == int(v)) )[0]
            for k,vv in mmapdata.items():
                val = []

                print "k, vv : ",k,", ",vv
                for i in idx_valid:
                    # retrieve indices
                    try:
                        idx2 = (h[i]/ vv[1] ).astype( np.uint32 )
                        print "idx2 : ",idx2
                        val.append( vv[0][idx2[:,0],idx2[:,1],idx2[:,2]] )
                    except IndexError, e:
                        print "Index error occured when trying extract scalar values for measure", k
                        print "--> Discard fiber with index", i, "Exception: ", e
                        print "----"

                da = np.concatenate( val )
                di[k + '_mean'] = float(da.mean())
                di[k + '_std'] = float(da.std())
                del da
                del val

            G.add_edge(u,v, di)

        # storing network
        if 'gPickle' in output_types:
            nx.write_gpickle(G, 'connectome_%s.gpickle' % parkey)
        if 'mat' in output_types:
            # edges
            size_edges = (parval['number_of_regions'],parval['number_of_regions'])
            edge_keys = G.edges(data=True)[0][2].keys()
            
            edge_struct = {}
            for edge_key in edge_keys:
                edge_struct[edge_key] = nx.to_numpy_matrix(G,weight=edge_key)
                
            # nodes
            size_nodes = parval['number_of_regions']
            node_keys = G.nodes(data=True)[0][1].keys()

            node_struct = {}
            for node_key in node_keys:
                if node_key == 'dn_position':
                    node_arr = np.zeros([size_nodes,3],dtype=np.float)
                else:
                    node_arr = np.zeros(size_nodes,dtype=np.object_)
                node_n = 0
                for _,node_data in G.nodes(data=True):
                    node_arr[node_n] = node_data[node_key]
                    node_n += 1
                node_struct[node_key] = node_arr
                
            scipy.io.savemat('connectome_%s.mat' % parkey, mdict={'sc':edge_struct,'nodes':node_struct})
        if 'graphml' in output_types:
            g2 = nx.Graph()
            for u_gml,v_gml,d_gml in G.edges_iter(data=True):
                g2.add_edge(u_gml,v_gml,d_gml)
            for u_gml,d_gml in G.nodes(data=True):
                g2.add_node(u_gml,{'dn_correspondence_id':d_gml['dn_correspondence_id'],
                               'dn_fsname':d_gml['dn_fsname'],
                               'dn_hemisphere':d_gml['dn_hemisphere'],
                               'dn_name':d_gml['dn_name'],
                               'dn_position_x':float(d_gml['dn_position'][0]),
                               'dn_position_y':float(d_gml['dn_position'][1]),
                               'dn_position_z':float(d_gml['dn_position'][2]),
                               'dn_region':d_gml['dn_region']})
            nx.write_graphml(g2,'connectome_%s.graphml' % parkey)

        print("Storing final fiber length array")
        fiberlabels_fname  = 'final_fiberslength_%s.npy' % str(parkey)
        np.save(fiberlabels_fname, final_fiberlength_array)

        print("Storing all fiber labels (with orphans)")
        fiberlabels_fname  = 'filtered_fiberslabel_%s.npy' % str(parkey)
        np.save(fiberlabels_fname, np.array(fiberlabels, dtype = np.int32), )

        print("Storing final fiber labels (no orphans)")
        fiberlabels_noorphans_fname  = 'final_fiberlabels_%s.npy' % str(parkey)
        np.save(fiberlabels_noorphans_fname, final_fiberlabels_array)

        if not streamline_wrote:
            print("Filtering tractography - keeping only no orphan fibers")
            finalfibers_fname = 'streamline_final.trk'
            save_fibers(hdr, fib, finalfibers_fname, final_fibers_idx)

    print("Done.")
    print("========================")
