# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMTK Connectome functions
""" 

import nibabel
import numpy as np
import networkx as nx
import scipy.io

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
        
        # Translate from mm to index
        endpoints[i,0,0] = int( endpoints[i,0,0] / float(voxelSize[0]))
        endpoints[i,0,1] = int( endpoints[i,0,1] / float(voxelSize[1]))
        endpoints[i,0,2] = int( endpoints[i,0,2] / float(voxelSize[2]))
        endpoints[i,1,0] = int( endpoints[i,1,0] / float(voxelSize[0]))
        endpoints[i,1,1] = int( endpoints[i,1,1] / float(voxelSize[1]))
        endpoints[i,1,2] = int( endpoints[i,1,2] / float(voxelSize[2]))
        
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

def cmat(intrk, roi_volumes, parcellation_scheme, compute_curvature=True, additional_maps={}, output_types=['gPickle'], atlas_info = {}): 
    """ Create the connection matrix for each resolution using fibers and ROIs. """
              
    # create the endpoints for each fibers
    en_fname  = 'endpoints.npy'
    en_fnamemm  = 'endpointsmm.npy'
    #ep_fname  = 'lengths.npy'
    curv_fname  = 'meancurvature.npy'
    #intrk = op.join(gconf.get_cmp_fibers(), 'streamline_filtered.trk')
    print('Opening file :' + intrk)
    fib, hdr    = nibabel.trackvis.read(intrk, False)
    
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
        
        
        print("Create the connection matrix")
        pc = -1
        for i in range(n):  # n: number of fibers

            # Percent counter
            pcN = int(round( float(100*i)/n ))
            if pcN > pc and pcN%1 == 0:
                pc = pcN
                print('%4.0f%%' % (pc))
    
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
            
            # additional measures
            # compute mean/std of fiber measure
            idx = np.where( (final_fiberlabels_array[:,0] == int(u)) & (final_fiberlabels_array[:,1] == int(v)) )[0]
            di['fiber_length_mean'] = float( np.mean(final_fiberlength_array[idx]) )
            di['fiber_length_std'] = float( np.std(final_fiberlength_array[idx]) )

            # this is indexed into the fibers that are valid in the sense of touching start
            # and end roi and not going out of the volume
            idx_valid = np.where( (fiberlabels[:,0] == int(u)) & (fiberlabels[:,1] == int(v)) )[0]
            for k,vv in mmapdata.items():
                val = []
                for i in idx_valid:
                    # retrieve indices
                    try:
                        idx2 = (h[i]/ vv[1] ).astype( np.uint32 )
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
