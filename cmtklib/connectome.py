# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK functions and Nipype interfaces for connectome mapping."""

from os import path as op
import csv
import glob
import os
import copy

from traits.api import *

import nibabel as nib
import numpy as np
import networkx as nx

import scipy.io as sio

from nipype.interfaces.base import traits, \
    File, TraitedSpec, BaseInterface, \
    BaseInterfaceInputSpec, isdefined, \
    InputMultiPath, OutputMultiPath
from nipype.interfaces import cmtk
from nipype.utils.filemanip import split_filename

from .util import mean_curvature, length
from .parcellation import get_parcellation


def group_analysis_sconn(output_dir, subjects_to_be_analyzed):
    """Perform group level analysis of structural connectivity matrices."""
    print("Perform group level analysis ...")


def compute_curvature_array(fib):
    """Computes the curvature array."""
    print("Compute curvature ...")

    n = len(fib)
    pc = -1
    meancurv = np.zeros((n, 1))
    for i, fi in enumerate(fib):
        # Percent counter
        pcN = int(round(float(100 * i) / n))
        if pcN > pc and pcN % 1 == 0:
            pc = pcN
            print('%4.0f%%' % pc)
        meancurv[i, 0] = mean_curvature(fi[0])

    return meancurv


def create_endpoints_array(fib, voxelSize, print_info):
    """Create the endpoints arrays for each fiber.

    Parameters
    ----------
    fib: the fibers data

    voxelSize: 3-tuple
        It contains the voxel size of the ROI image

    print_info : bool
        If True, print extra information

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
    n = len(fib)
    endpoints = np.zeros((n, 2, 3))
    endpointsmm = np.zeros((n, 2, 3))
    pc = -1

    # Computation for each fiber
    for i, fi in enumerate(fib):

        # Percent counter
        if print_info:
            pcN = int(round(float(100 * i) / n))
            if pcN > pc and pcN % 20 == 0:
                pc = pcN
                print('%4.0f%%' % pc)

        f = fi[0]

        # store startpoint
        endpoints[i, 0, :] = f[0, :]
        # store endpoint
        endpoints[i, 1, :] = f[-1, :]

        # store startpoint
        endpointsmm[i, 0, :] = f[0, :]
        # store endpoint
        endpointsmm[i, 1, :] = f[-1, :]

        # print 'endpoints (mm) : ',endpoints[i, 0, :],' ; ',endpoints[i, 1, :]

        # Translate from mm to index
        endpoints[i, 0, 0] = int(endpoints[i, 0, 0] / float(voxelSize[0]))
        endpoints[i, 0, 1] = int(endpoints[i, 0, 1] / float(voxelSize[1]))
        endpoints[i, 0, 2] = int(endpoints[i, 0, 2] / float(voxelSize[2]))
        endpoints[i, 1, 0] = int(endpoints[i, 1, 0] / float(voxelSize[0]))
        endpoints[i, 1, 1] = int(endpoints[i, 1, 1] / float(voxelSize[1]))
        endpoints[i, 1, 2] = int(endpoints[i, 1, 2] / float(voxelSize[2]))

        # print 'endpoints : ',endpoints[i, 0, :],' ; ',endpoints[i, 1, :]

    # Return the matrices
    return endpoints, endpointsmm


def save_fibers(oldhdr, oldfib, fname, indices):
    """Stores a new trackvis file fname using only given indices.

    Parameters
    ----------
    oldhdr : the tractogram header
        Tractogram header to use as reference

    oldfib : the fibers data
        Input fibers

    fname : string
        Output tractogram filename

    indices : list
        Indices of fibers included
    """

    hdrnew = oldhdr.copy()

    outstreams = []
    for i in indices:
        outstreams.append(oldfib[i])

    n_fib_out = len(outstreams)
    hdrnew['n_count'] = n_fib_out

    print("Writing final no orphan fibers: %s" % fname)
    nib.trackvis.write(fname, outstreams, hdrnew)


def cmat(intrk, roi_volumes, roi_graphmls, parcellation_scheme, compute_curvature=True, additional_maps={},
         output_types=['gPickle'], atlas_info={}):
    """Create the connection matrix for each resolution using fibers and ROIs.

    Parameters
    ----------
    intrk : TRK file
        Reconstructed tractogram

    roi_volumes : list
        List of parcellation files for a given parcellation scheme

    roi_graphmls : list
        List of graphmls files that describes parcellation nodes

    parcellation_scheme : ['NativeFreesurfer','Lausanne2008','Lausanne2018']

    compute_curvature : Boolean

    additional_maps : dict
        A dictionary of key/value for each additional map where the value
        is the path to the map

    output_types : ['gPickle','mat','graphml']

    atlas_info : dict
        Dictionary storing information such as path to files related to a
        parcellation atlas / scheme.
    """

    print("========================")
    print("> Creation of connectome maps")

    # create the endpoints for each fibers
    en_fname = 'endpoints.npy'
    en_fnamemm = 'endpointsmm.npy'
    # ep_fname  = 'lengths.npy'
    curv_fname = 'meancurvature.npy'
    # intrk = op.join(gconf.get_cmp_fibers(), 'streamline_filtered.trk')
    print('... tractogram :' + intrk)
    fib, hdr = nib.trackvis.read(intrk, False)

    # print "Header trackvis : ",hdr
    # print "Header trackvis id_string : ",hdr['id_string']
    # print "Fibers trackvis : ",fib

    print('... parcellation : %s' % parcellation_scheme)

    if parcellation_scheme != "Custom":
        if parcellation_scheme != "Lausanne2018":
            # print "get resolutions from parcellation_scheme"
            resolutions = get_parcellation(parcellation_scheme)
        else:
            resolutions = get_parcellation(parcellation_scheme)
            for parkey, parval in list(resolutions.items()):
                for vol, graphml in zip(roi_volumes, roi_graphmls):
                    # print parkey
                    if parkey in vol:
                        roi_fname = vol
                        # print roi_fname
                    if parkey in graphml:
                        roi_graphml_fname = graphml
                        # print roi_graphml_fname
                # roi_fname = roi_volumes[r]
                # r += 1
                roi = nib.load(roi_fname)
                roiData = roi.get_data()
                resolutions[parkey]['number_of_regions'] = roiData.max()
                resolutions[parkey]['node_information_graphml'] = op.abspath(
                    roi_graphml_fname)

            del roi, roiData
            # print("##################################################")
            # print("Atlas info (Lausanne2018) :")
            # print(resolutions)
            # print("##################################################")
    else:
        # print "get resolutions from atlas_info: "
        resolutions = atlas_info
        # print resolutions

    # print "resolutions : %s" % resolutions

    # Previously, load_endpoints_from_trk() used the voxel size stored
    # in the track hdr to transform the endpoints to ROI voxel space.
    # This only works if the ROI voxel size is the same as the DSI/DTI
    # voxel size.  In the case of DTI, it is not.
    # We do, however, assume that all of the ROI images have the same
    # voxel size, so this code just loads the first one to determine
    # what it should be
    firstROIFile = roi_volumes[0]
    firstROI = nib.load(firstROIFile)
    roiVoxelSize = firstROI.get_header().get_zooms()

    # print "roi Voxel Size",roiVoxelSize
    (endpoints, endpointsmm) = create_endpoints_array(fib, roiVoxelSize, True)
    np.save(en_fname, endpoints)
    np.save(en_fnamemm, endpointsmm)

    # only compute curvature if required
    if compute_curvature:
        meancurv = compute_curvature_array(fib)
        np.save(curv_fname, meancurv)

    print("========================")

    n = len(fib)

    # resolution = gconf.parcellation.keys()

    streamline_wrote = False
    for parkey, parval in list(resolutions.items()):
        # if parval['number_of_regions'] != 83:
        #    continue

        # print("Resolution = "+parkey)

        print("------------------------")
        print("Resolution = " + parkey)
        print("------------------------")

        # create empty fiber label array
        fiberlabels = np.zeros((n, 2))
        final_fiberlabels = []
        final_fibers_idx = []

        # Open the corresponding ROI (scale1 for lausanne2008/18) (first volume for nativefreesurfer)

        # print("Open the corresponding ROI")
        for vol in roi_volumes:
            # print parkey
            if (parkey in vol) or (len(roi_volumes) == 1):
                roi_fname = vol
                # print roi_fname
        # roi_fname = roi_volumes[r]
        # r += 1
        roi = nib.load(roi_fname)
        roiData = roi.get_data()

        # affine_vox_to_world = np.matrix(roi.affine[:3, :3])

        # print "roiData shape : %s " % roiData.shape
        # print "Affine Voxel 2 World transformation : ",affine_vox_to_world

        # affine_world_to_vox = np.linalg.inv(affine_vox_to_world)
        # origin = np.matrix(roi.affine[:3, 3]).T
        # print "Affine World 2 Voxel transformation : ",affine_world_to_vox

        # Create the matrix
        print("  >> Create the connection matrix (%s rois)" %
              parval['number_of_regions'])

        nROIs = parval['number_of_regions']
        G = nx.Graph()

        # add node information from parcellation
        gp = nx.read_graphml(parval['node_information_graphml'])
        n_nodes = len(gp)
        pc = -1
        cnt = -1

        thalamic_labels = []
        for u, d in gp.nodes(data=True):

            # Percent counter
            cnt += 1
            pcN = int(round(float(100 * cnt) / n_nodes))
            if pcN > pc and pcN % 10 == 0:
                pc = pcN
                print('%4.0f%%' % pc)

            G.add_node(int(u))
            for key in d:
                G.nodes[int(u)][key] = d[key]
            # compute a position for the node based on the mean position of the
            # ROI in voxel coordinates (segmentation volume )
            if parcellation_scheme != "Lausanne2018":
                G.nodes[int(u)]['dn_position'] = tuple(
                    np.mean(np.where(roiData == int(d["dn_correspondence_id"])), axis=1))
                G.nodes[int(u)]['roi_volume'] = np.sum(
                    roiData == int(d["dn_correspondence_id"]))
                # print "Add node %g - roi volume : %g " % (int(u),np.sum( roiData== int(d["dn_correspondence_id"]) ))
                # Store parcellation labels corresponding to thalamic nuclei
                # if gp.node[int(u)]['dn_fsname'] == 'thalamus':
                #     thalamic_labels.append(int(u))
            else:
                # if int(u) == 53:
                #    print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
                G.nodes[int(u)]['dn_position'] = tuple(
                    np.mean(np.where(roiData == int(d["dn_multiscaleID"])), axis=1))
                G.nodes[int(u)]['roi_volume'] = np.sum(
                    roiData == int(d["dn_multiscaleID"]))
                # if int(u) == 53:
                #    print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
                # print "Add node %g - roi volume (2018): %g " % (int(u),np.sum( roiData== int(d["dn_multiscaleID"]) ))
                # if int(u) == 53:
                #    print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")

        thalamic_labels = np.array(thalamic_labels)
        print("  ************************")
        print('  >> Labels of thalamic nuclei :')
        print('  {}'.format(thalamic_labels))
        print("  ************************")

        dis = 0

        # prepare: compute the measures
        t = [c[0] for c in fib]
        h = np.array(t, dtype=np.object)

        mmap = additional_maps
        mmapdata = {}
        print('  >> Maps to be processed :')
        for k, v in list(mmap.items()):
            print("     - %s map" % k)
            da = nib.load(v)
            mdata = da.get_data()
            print(mdata.max())
            mdata = np.nan_to_num(mdata)
            print(mdata.max())
            mmapdata[k] = (mdata, da.get_header().get_zooms())

        # print("mmapdata size : %g " % len(mmapdata.items()))

        print("  ************************")

        print("  >> Processing fibers and computing metrics (%s fibers)" % n)
        pc = -1
        for i in range(n):  # n: number of fibers

            # Percent counter
            pcN = int(round(float(100 * i) / n))
            if pcN > pc and pcN % 10 == 0:
                pc = pcN
                print('%4.0f%%' % pc)

            # ROI start => ROI end
            try:
                startvox = np.zeros((3, 1)).astype(int)
                startvox[0] = np.int(endpoints[i, 0, 0])
                startvox[1] = np.int(endpoints[i, 0, 1])
                startvox[2] = np.int(endpoints[i, 0, 2])

                endvox = np.zeros((3, 1)).astype(int)
                endvox[0] = np.int(endpoints[i, 1, 0])
                endvox[1] = np.int(endpoints[i, 1, 1])
                endvox[2] = np.int(endpoints[i, 1, 2])

                # print "start point : ",startvox
                # print "end point : ",endvox
                # print "roi data shape : ",roiData.shape

                # endpoints from create_endpoints_array
                startROI = int(roiData[startvox[0], startvox[1], startvox[2]])
                endROI = int(roiData[endvox[0], endvox[1], endvox[2]])

            except IndexError:
                print(
                    "... ERROR: An index error occured for fiber %s. This means that the fiber start or endpoint is outside the volume. Continue." % i)
                continue

            # Filter
            if startROI == 0 or endROI == 0:
                dis += 1
                fiberlabels[i, 0] = -1
                continue

            if startROI > nROIs or endROI > nROIs:
                #                print("Start or endpoint of fiber terminate in a voxel which is labeled higher")
                #                print("than is expected by the parcellation node information.")
                #                print("Start ROI: %i, End ROI: %i" % (startROI, endROI))
                #                print("This needs bugfixing!")
                continue

            # Switch the rois in order to enforce startROI < endROI
            if endROI < startROI:
                tmp = startROI
                startROI = endROI
                endROI = tmp

            # TODO: Refine fibers ending in thalamus
            # if (startROI in thalamic_labels) or (endROI in thalamic_labels):
            # Extract all thalamic nuclei the fiber is passing through

            # Refine start/endROI connecting to the most probable nucleus

            # Update fiber label
            fiberlabels[i, 0] = startROI
            fiberlabels[i, 1] = endROI

            final_fiberlabels.append([startROI, endROI])
            final_fibers_idx.append(i)

            # Add edge to graph
            if G.has_edge(startROI, endROI):
                G[startROI][endROI]['fiblist'].append(i)
            else:
                G.add_edge(startROI, endROI, fiblist=[i])

        print(
            "  ... INFO - Found %i (%f percent out of %i fibers) fibers that start or terminate in a voxel which is not labeled. (orphans)" % (
                dis, dis * 100.0 / n, n))
        print("  ... INFO - Valid fibers: %i (%f percent)" %
              (n - dis, 100 - dis * 100.0 / n))

        # print "roi : ",roi
        # print "roiData size : ",roiData.size
        # print "roiData shape : ",roiData.shape

        # create a final fiber length array
        finalfiberlength = []
        for idx in final_fibers_idx:
            # compute length of fiber
            # print('Fiber %i length: %d' % (idx, length(fib[idx][0])))
            finalfiberlength.append(length(fib[idx][0]))

        # convert to array
        final_fiberlength_array = np.array(finalfiberlength)

        # make final fiber labels as array
        final_fiberlabels_array = np.array(final_fiberlabels, dtype=np.int32)

        total_fibers = 0
        total_volume = 0
        u_old = -1
        for u, v, d in G.edges(data=True):
            total_fibers += len(d['fiblist'])
            if u != u_old:
                # print("Node %i"%int(u))
                # print(G.nodes[int(u)])
                total_volume += G.nodes[int(u)]['roi_volume']
            u_old = u

        G_out = copy.deepcopy(G)

        # update edges
        # measures to add here
        # FIXME treat case of self-connection that gives di['fiber_length_mean'] = 0.0
        for u, v, d in G.edges(data=True):
            # Check for diagonal elements that raise an error when the edge is visited a second time
            # print('({}, {}): {}'.format(u, v, list(G[u][v].keys())))
            G_out.remove_edge(u, v)

            # print("u / v : {} / {}".format(u,v))
            if len(list(G[u][v].keys())) == 1:
                di = {'number_of_fibers': len(G[u][v]['fiblist'])}

                # print("G[u][v]['fiblist'] : {}".format(G[u][v]['fiblist']))

                # additional measures
                # compute mean/std of fiber measure
                if u <= v:
                    idx = np.where((final_fiberlabels_array[:, 0] == int(u)) & (
                        final_fiberlabels_array[:, 1] == int(v)))[0]
                else:
                    idx = np.where((final_fiberlabels_array[:, 0] == int(v)) & (
                        final_fiberlabels_array[:, 1] == int(u)))[0]

                # print("idx : {}".format(idx))
                # print("final_fiberlength_array[idx] : {}".format(final_fiberlength_array[idx]))

                di['fiber_length_mean'] = float(
                    np.nanmean(final_fiberlength_array[idx]))
                di['fiber_length_median'] = float(
                    np.nanmedian(final_fiberlength_array[idx]))
                di['fiber_length_std'] = float(
                    np.nanstd(final_fiberlength_array[idx]))

                di['fiber_proportion'] = float(
                    100.0 * (di['number_of_fibers'] / float(total_fibers)))

                # Compute density
                # density = (#fibers / mean_fibers_length) * (2 / (area_roi_u + area_roi_v))

                # print "G.nodes[int(u)]['roi_volume'] : %i / G.nodes[int(v)]['roi_volume'] : %i"
                #   % (G.nodes[int(u)]['roi_volume'],G.nodes[int(v)]['roi_volume'])
                # print "di['number_of_fibers'] : %i / di['fiber_length_mean'] : %i" % (di['number_of_fibers'],di['fiber_length_mean'])

                if di['fiber_length_mean'] > 0.0:
                    di['fiber_density'] = float((float(di['number_of_fibers']) / float(di['fiber_length_mean'])) * float(
                        2.0 / (G.nodes[int(u)]['roi_volume'] + G.nodes[int(v)]['roi_volume'])))
                    di['normalized_fiber_density'] = float(
                        ((float(di['number_of_fibers']) / float(total_fibers)) / float(di['fiber_length_mean'])) * (
                            (2.0 * float(total_volume)) / (
                                G.nodes[int(u)]['roi_volume'] + G.nodes[int(v)]['roi_volume'])))
                else:
                    di['fiber_density'] = 0.0
                    di['normalized_fiber_density'] = 0.0
                # this is indexed into the fibers that are valid in the sense of touching start
                # and end roi and not going out of the volume
                if u <= v:
                    idx_valid = np.where((fiberlabels[:, 0] == int(u)) & (
                        fiberlabels[:, 1] == int(v)))[0]
                else:
                    idx_valid = np.where((fiberlabels[:, 0] == int(v)) & (
                        fiberlabels[:, 1] == int(u)))[0]

                for k, vv in list(mmapdata.items()):
                    val = []

                    # print("Processing %s map..." % k)
                    # print(vv[1])
                    for i in idx_valid:
                        # retrieve indices
                        try:
                            # print(h[i])
                            idx2 = (h[i] / vv[1]).astype(np.uint32)
                            # print "idx2 : ",idx2
                            val.append(vv[0][idx2[:, 0], idx2[:, 1], idx2[:, 2]])
                        except IndexError as e:
                            print(
                                "  ... ERROR - Index error occured when trying extract scalar values for measure", k)
                            print("  ... ERROR - Discard fiber with index",
                                  i, "Exception: ", e)

                    # print(k)
                    if len(val) > 0:
                        da = np.concatenate(val)
                        # print(da.max())
                        # print(np.median(da))

                        if k == 'shore_rtop':
                            di[k + '_mean'] = da.astype(np.float64).mean()
                            di[k + '_std'] = da.astype(np.float64).std()
                            di[k + '_median'] = np.median(da.astype(np.float64))
                        else:
                            di[k + '_mean'] = da.mean().astype(np.float)
                            di[k + '_std'] = da.std().astype(np.float)
                            di[k + '_median'] = np.median(da).astype(np.float)

                        # print(di[k + '_median'])
                        del da
                        del val

                G_out.add_edge(u, v)
                for key in di:
                    G_out[u][v][key] = di[key]

                # print('({}, {}): {}'.format(u, v, list(G[u][v].keys())))

        # print("  ************************************************************************")

        # for u, v, d in G.edges(data=True):

        #     print('({}, {}): {}'.format(u, v, list(d.keys())))
        #     if 'fiblist' in list(d.keys()):
        #         print(G[u][v]['fiblist'])

        del G

        print("  ************************************************")

        print("  >> Save connectome maps as :")

        # Get the edge attributes/keys/weights from the first edge and then break.
        # Change w.r.t networkx2
        edge_keys = []
        for u, v, d in G_out.edges(data=True):
            # print(list(d.keys()))
            edge_keys = list(d.keys())
            break

        # Storing network/graph in TSV format (by default to be BIDS compliant)
        print('    - connectome_%s.tsv' % parkey)
        # Write header fields
        with open('connectome_%s.tsv' % parkey, 'w') as out_file:
            tsv_writer = csv.writer(out_file, delimiter='\t')
            header = ['source', 'target']
            header = header + [key for key in edge_keys]
            tsv_writer.writerow(header)
        # Write list of graph edges with all connectivity metrics (edge_keys)
        with open('connectome_%s.tsv' % parkey, 'ab') as out_file:
            nx.write_edgelist(G_out,
                              out_file,
                              comments='#',
                              delimiter='\t',
                              data=edge_keys,
                              encoding='utf-8')

        # Storing network/graph in other formats that might be prefered by the user
        if 'gPickle' in output_types:
            print('    - connectome_%s.gpickle' % parkey)
            nx.write_gpickle(G_out, 'connectome_%s.gpickle' % parkey)
        if 'mat' in output_types:
            # edges
            # size_edges = (int(parval['number_of_regions']), int(
            #     parval['number_of_regions']))

            edge_struct = {}
            for edge_key in edge_keys:
                if edge_key != 'fiblist':
                    # print('edge key: %s ' % edge_key)
                    edge_struct[edge_key] = nx.to_numpy_matrix(G_out, weight=edge_key)

            # nodes
            size_nodes = int(parval['number_of_regions'])

            # Get the node attributes/keys from the first node and then break.
            # Change w.r.t networkx2
            for u, d in G_out.nodes(data=True):
                node_keys = list(d.keys())
                break

            # print "size_nodes : "
            # print size_nodes
            #
            # print "Number of nodes : %i" % len(G)

            node_struct = {}
            for node_key in node_keys:
                if node_key == 'dn_position':
                    node_arr = np.zeros([size_nodes, 3], dtype=np.float)
                else:
                    node_arr = np.zeros(size_nodes, dtype=np.object_)

                node_n = 0
                for _, node_data in G_out.nodes(data=True):
                    node_arr[node_n] = node_data[node_key]
                    # print " node_arr[%i]:" % node_n
                    # print node_arr[node_n]
                    node_n += 1
                # print('node key: %s ' % node_key)
                node_struct[node_key] = node_arr
            print('    - connectome_%s.mat' % parkey)
            sio.savemat('connectome_%s.mat' % parkey, long_field_names=True,
                        mdict={'sc': edge_struct,
                               'nodes': node_struct})
        if 'graphml' in output_types:
            g2 = nx.Graph()
            for u_gml, v_gml, d_gml in G_out.edges(data=True):
                g2.add_edge(u_gml, v_gml)
                for key in d_gml:
                    g2[u_gml][v_gml][key] = d_gml[key]
            for u_gml, d_gml in G_out.nodes(data=True):
                g2.add_node(u_gml)
                if parcellation_scheme != "Lausanne2018":
                    g2.nodes[u_gml]['dn_correspondence_id'] = d_gml['dn_correspondence_id']
                else:
                    g2.nodes[u_gml]['dn_multiscaleID'] = d_gml['dn_multiscaleID']
                g2.nodes[u_gml]['dn_fsname'] = d_gml['dn_fsname']
                g2.nodes[u_gml]['dn_hemisphere'] = d_gml['dn_hemisphere']
                g2.nodes[u_gml]['dn_name'] = d_gml['dn_name']
                g2.nodes[u_gml]['dn_position_x'] = d_gml['dn_position'][0]
                g2.nodes[u_gml]['dn_position_y'] = d_gml['dn_position'][1]
                g2.nodes[u_gml]['dn_position_z'] = d_gml['dn_position'][2]
                g2.nodes[u_gml]['dn_region'] = d_gml['dn_region']
                print('    - connectome_%s.graphml' % parkey)
            nx.write_graphml(g2, 'connectome_%s.graphml' % parkey)

        # print("Storing final fiber length array")
        fiberlabels_fname = 'final_fiberslength_%s.npy' % str(parkey)
        np.save(fiberlabels_fname, final_fiberlength_array)

        # print("Storing all fiber labels (with orphans)")
        fiberlabels_fname = 'filtered_fiberslabel_%s.npy' % str(parkey)
        np.save(fiberlabels_fname, np.array(fiberlabels, dtype=np.int32), )

        # print("Storing final fiber labels (no orphans)")
        fiberlabels_noorphans_fname = 'final_fiberlabels_%s.npy' % str(parkey)
        np.save(fiberlabels_noorphans_fname, final_fiberlabels_array)

        if not streamline_wrote:
            print("  > Filtering tractography - keeping only no orphan fibers")
            finalfibers_fname = 'streamline_final.trk'
            save_fibers(hdr, fib, finalfibers_fname, final_fibers_idx)

    print("Done.")
    print("========================")


class CMTK_cmatInputSpec(BaseInterfaceInputSpec):
    track_file = InputMultiPath(File(exists=True),
                                desc='Tractography result',
                                mandatory=True)
    roi_volumes = InputMultiPath(File(exists=True),
                                 desc='ROI volumes registered to diffusion space')
    parcellation_scheme = traits.Enum('Lausanne2008', ['Lausanne2008', 'Lausanne2018', 'NativeFreesurfer', 'Custom'],
                                      desc="Parcellation scheme",
                                      usedefault=True)
    roi_graphmls = InputMultiPath(File(exists=True),
                                  desc='GraphML description of ROI volumes (Lausanne2018)')

    atlas_info = Dict(mandatory=False, desc="custom atlas information")

    compute_curvature = traits.Bool(
        True, desc='Compute curvature', usedefault=True)

    additional_maps = traits.List(
        File, desc='Additional calculated maps (ADC, gFA, ...)')

    output_types = traits.List(
        Str, desc='Output types of the connectivity matrices')

    probtrackx = traits.Bool(False, desc="MUST be set to True if probtrackx was used (Not used anymore in CMP3)")

    voxel_connectivity = InputMultiPath(File(exists=True),
                                        desc="ProbtrackX connectivity matrices (# seed voxels x # target ROIs)")


class CMTK_cmatOutputSpec(TraitedSpec):
    endpoints_file = File(desc="Numpy files storing the list of fiber endpoint")

    endpoints_mm_file = File(desc="Numpy files storing the list of fiber endpoint in mm")

    final_fiberslength_files = OutputMultiPath(File(),
                                               desc="List of fiber length")

    filtered_fiberslabel_files = OutputMultiPath(File(), desc="List of fiber start end ROI parcellation label after filtering")

    final_fiberlabels_files = OutputMultiPath(File(), desc="List of fiber start end ROI parcellation label")

    streamline_final_file = File(desc="Final tractogram of fibers considered in the creation of connectivity matrices")

    connectivity_matrices = OutputMultiPath(File(), desc="Connectivity matrices")


class CMTK_cmat(BaseInterface):
    """Creates the structural connectivity matrices for a given parcellation scheme.

    Examples
    --------
    >>> from cmtklib.connectome import CMTK_cmat
    >>> cmat = CMTK_cmat()
    >>> cmat.inputs.base_dir = '/my_directory'
    >>> cmat.inputs.track_file = '/path/to/sub-01_tractogram.trk'
    >>> cmat.inputs.roi_volumes = ['/path/to/sub-01_space-DWI_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-DWI_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-DWI_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-DWI_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-DWI_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> cmat.inputs.roi_graphmls = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.graphml']
    >>> cmat.inputs.parcellation scheme = 'Lausanne2018'
    >>> cmat.inputs.output_types = ['gPickle','mat','graphml']
    >>> cmat.run() # doctest: +SKIP
    """

    input_spec = CMTK_cmatInputSpec
    output_spec = CMTK_cmatOutputSpec

    def _run_interface(self, runtime):
        if isdefined(self.inputs.additional_maps):
            additional_maps = dict(
                (split_filename(add_map)[1], add_map) for add_map in self.inputs.additional_maps if add_map != '')
        else:
            additional_maps = {}

        # if self.inputs.probtrackx:
        #     probtrackx_cmat(voxel_connectivity_files=self.inputs.track_file, roi_volumes=self.inputs.roi_volumes,
        #                     parcellation_scheme=self.inputs.parcellation_scheme, atlas_info=self.inputs.atlas_info,
        #                     output_types=self.inputs.output_types)
        # elif len(self.inputs.track_file) > 1:
        #     prob_cmat(intrk=self.inputs.track_file, roi_volumes=self.inputs.roi_volumes,
        #               parcellation_scheme=self.inputs.parcellation_scheme, atlas_info=self.inputs.atlas_info,
        #               output_types=self.inputs.output_types)
        # else:
        cmat(intrk=self.inputs.track_file[0], roi_volumes=self.inputs.roi_volumes,
             roi_graphmls=self.inputs.roi_graphmls,
             parcellation_scheme=self.inputs.parcellation_scheme, atlas_info=self.inputs.atlas_info,
             compute_curvature=self.inputs.compute_curvature,
             additional_maps=additional_maps,
             output_types=self.inputs.output_types)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['endpoints_file'] = os.path.abspath('endpoints.npy')
        outputs['endpoints_mm_file'] = os.path.abspath('endpointsmm.npy')
        outputs['final_fiberslength_files'] = glob.glob(
            os.path.abspath('final_fiberslength*'))
        outputs['filtered_fiberslabel_files'] = glob.glob(
            os.path.abspath('filtered_fiberslabel*'))
        outputs['final_fiberlabels_files'] = glob.glob(
            os.path.abspath('final_fiberlabels*'))
        outputs['streamline_final_file'] = os.path.abspath(
            'streamline_final.trk')
        outputs['connectivity_matrices'] = glob.glob(
            os.path.abspath('connectome*'))

        return outputs


class rsfmri_conmat_InputSpec(BaseInterfaceInputSpec):
    func_file = File(exists=True, mandatory=True, desc="fMRI volume")

    roi_volumes = InputMultiPath(File(exists=True),
                                 desc='ROI volumes registered to functional space')

    roi_graphmls = InputMultiPath(File(exists=True),
                                  desc='GraphML description file for ROI volumes (used only if parcellation_scheme == Lausanne2018)')

    parcellation_scheme = traits.Enum('Lausanne2008', ['Lausanne2008', 'Lausanne2018', 'NativeFreesurfer', 'Custom'],
                                      desc="Parcellation scheme",
                                      usedefault=True)

    atlas_info = Dict(mandatory=False, desc="custom atlas information")

    apply_scrubbing = Bool(False, desc="Apply scrubbing")

    FD = File(exists=True, desc="FD file if scrubbing is performed")

    FD_th = Float(desc="FD threshold")

    DVARS = File(exists=True, desc="DVARS file if scrubbing is performed")

    DVARS_th = Float(desc="DVARS threshold")

    output_types = traits.List(Str,
                               desc='Output types of the connectivity matrices')


class rsfmri_conmat_OutputSpec(TraitedSpec):
    avg_timeseries = OutputMultiPath(File(exists=True),
                                     desc="ROI average timeseries")

    scrubbed_idx = File(exists=True,
                        desc="Scrubbed indices")

    connectivity_matrices = OutputMultiPath(File(exists=True),
                                            desc="Functional connectivity matrices")


class rsfmri_conmat(BaseInterface):
    """Creates the functional connectivity matrices for a given parcellation scheme.

    It applies scrubbing (if enabled), computes the average GM ROI time-series and computes
    the Pearson's correlation coefficient between each GM ROI time-series poir.

    Examples
    --------
    >>> from cmtklib.connectome import rsfmri_conmat
    >>> cmat = rsfmri_conmat()
    >>> cmat.inputs.base_dir = '/my_directory'
    >>> cmat.inputs.func_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> cmat.inputs.roi_volumes = ['/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> cmat.inputs.roi_graphmls = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.graphml']
    >>> cmat.inputs.parcellation scheme = 'Lausanne2018'
    >>> cmat.inputs.apply_scrubbing = False
    >>> cmat.inputs.output_types = ['gPickle','mat','graphml']
    >>> cmat.run() # doctest: +SKIP
    """

    input_spec = rsfmri_conmat_InputSpec
    output_spec = rsfmri_conmat_OutputSpec

    def _run_interface(self, runtime):
        print("Compute average rs-fMRI signal for each cortical ROI")
        print("====================================================")

        fdata = nib.load(self.inputs.func_file).get_data()

        tp = fdata.shape[3]

        # OLD
        # if self.inputs.parcellation_scheme != "Custom":
        #     resolutions = get_parcellation(self.inputs.parcellation_scheme)
        # else:
        #     resolutions = self.inputs.atlas_info

        # NEW
        print('Parcellation_scheme : %s' % self.inputs.parcellation_scheme)

        if self.inputs.parcellation_scheme != "Custom":
            if self.inputs.parcellation_scheme != "Lausanne2018":
                print("get resolutions from parcellation_scheme")
                resolutions = get_parcellation(self.inputs.parcellation_scheme)
            else:
                resolutions = get_parcellation(self.inputs.parcellation_scheme)
                for parkey, parval in list(resolutions.items()):
                    for vol, graphml in zip(self.inputs.roi_volumes, self.inputs.roi_graphmls):
                        print(parkey)
                        if parkey in vol:
                            roi_fname = vol
                            print(roi_fname)
                        if parkey in graphml:
                            roi_graphml_fname = graphml
                            print(roi_graphml_fname)
                    # roi_fname = roi_volumes[r]
                    # r += 1
                    roi = nib.load(roi_fname)
                    roiData = roi.get_data()
                    resolutions[parkey]['number_of_regions'] = roiData.max()
                    resolutions[parkey]['node_information_graphml'] = os.path.abspath(
                        roi_graphml_fname)

                del roi, roiData
                print("##################################################")
                print("Atlas info (Lausanne2018) :")
                print(resolutions)
                print("##################################################")
        else:
            print("get resolutions from atlas_info: ")
            resolutions = self.inputs.atlas_info
            print(resolutions)

        index = np.linspace(0, tp - 1, tp).astype('int')

        # if self.inputs.apply_scrubbing:
        #     # load scrubbing FD and DVARS series
        #     FD = np.load( self.inputs.FD )
        #     DVARS = np.load( self.inputs.DVARS )
        #     # evaluate scrubbing mask
        #     FD_th = self.inputs.FD_th
        #     DVARS_th = self.inputs.DVARS_th
        #     FD_mask = np.array(np.nonzero(FD < FD_th))[0,:]
        #     DVARS_mask = np.array(np.nonzero(DVARS < DVARS_th))[0,:]
        #     index = np.sort(np.unique(np.concatenate((FD_mask,DVARS_mask)))) + 1
        #     index = np.concatenate(([0],index))
        #     log_scrubbing = "DISCARDED time points after scrubbing: " + str(FD.shape[0]-index.shape[0]+1) + " over " + str(FD.shape[0]+1)
        #     print(log_scrubbing)
        #     np.save( os.path.abspath( 'tp_after_scrubbing.npy'), index )
        #     sio.savemat( os.path.abspath('tp_after_scrubbing.mat'), {'index':index} )
        # else:
        #     index = np.linspace(0,tp-1,tp).astype('int')

        # loop throughout all the resolutions ('scale33', ..., 'scale500')
        for parkey, parval in list(resolutions.items()):
            print("Resolution = " + parkey)

            # Open the corresponding ROI
            print("Open the corresponding ROI")
            for vol in self.inputs.roi_volumes:
                if (parkey in vol) or (len(self.inputs.roi_volumes) == 1):
                    roi_fname = vol
                    print(roi_fname)

            roi = nib.load(roi_fname)
            mask = roi.get_data()

            # Compute average time-series
            # nROIs: number of ROIs for current resolution
            nROIs = parval['number_of_regions']

            # matrix number of rois vs timepoints
            ts = np.zeros((nROIs, tp), dtype=np.float32)

            # loop throughout all the ROIs (current resolution)
            for i in range(1, nROIs + 1):
                ts[i - 1, :] = fdata[mask == i].mean(axis=0)
            print("ts_shape:", ts.shape)

            np.save(os.path.abspath('averageTimeseries_%s.npy' % parkey), ts)
            sio.savemat(os.path.abspath(
                'averageTimeseries_%s.mat' % parkey), {'ts': ts})

        # Apply scrubbing (if enabled) and compute correlation
        # loop throughout all the resolutions ('scale33', ..., 'scale500')
        for parkey, parval in list(resolutions.items()):
            print("Resolution = " + parkey)

            # Open the corresponding ROI
            print("Open the corresponding ROI")
            for vol in self.inputs.roi_volumes:
                if parkey in vol:
                    roi_fname = vol
                    print(roi_fname)
            roi = nib.load(roi_fname)
            roiData = roi.get_data()

            # Average roi time-series
            ts = np.load(os.path.abspath('averageTimeseries_%s.npy' % parkey))

            # nROIs: number of ROIs for current resolution
            nROIs = parval['number_of_regions']

            # Create matrix, add node information from parcellation and recover ROI indexes
            print("Create the connection matrix (%s rois)" % nROIs)
            G = nx.Graph()
            gp = nx.read_graphml(parval['node_information_graphml'])
            ROI_idx = []
            for u, d in gp.nodes(data=True):
                G.add_node(int(u))
                for key in d:
                    G.nodes[int(u)][key] = d[key]
                # compute a position for the node based on the mean position of the
                # ROI in voxel coordinates (segmentation volume )
                if self.inputs.parcellation_scheme != "Lausanne2018":
                    G.nodes[int(u)]['dn_position'] = tuple(
                        np.mean(np.where(mask == int(d["dn_correspondence_id"])), axis=1))
                    ROI_idx.append(int(d["dn_correspondence_id"]))
                else:
                    G.nodes[int(u)]['dn_position'] = tuple(
                        np.mean(np.where(mask == int(d["dn_multiscaleID"])), axis=1))
                    ROI_idx.append(int(d["dn_multiscaleID"]))
            # # matrix number of rois vs timepoints
            # ts = np.zeros( (nROIs,tp), dtype = np.float32 )
            #
            # # loop throughout all the ROIs (current resolution)
            # roi_line = 0
            # for i in ROI_idx:
            #     ts[roi_line,:] = fdata[roiData==i].mean( axis = 0 )
            #     roi_line += 1
            #
            # np.save( os.path.abspath('averageTimeseries_%s.npy' % parkey), ts )
            # sio.savemat( os.path.abspath('averageTimeseries_%s.mat' % parkey), {'TCS':ts} )

            # Censoring time-series
            if self.inputs.apply_scrubbing:
                # load scrubbing FD and DVARS series
                FD = np.load(self.inputs.FD)
                DVARS = np.load(self.inputs.DVARS)
                # evaluate scrubbing mask
                FD_th = self.inputs.FD_th
                DVARS_th = self.inputs.DVARS_th
                FD_mask = np.array(np.nonzero(FD < FD_th))[0, :]
                DVARS_mask = np.array(np.nonzero(DVARS < DVARS_th))[0, :]
                index = np.sort(
                    np.unique(np.concatenate((FD_mask, DVARS_mask)))) + 1
                index = np.concatenate(([0], index))
                log_scrubbing = "DISCARDED time points after scrubbing: " + str(
                    FD.shape[0] - index.shape[0] + 1) + " over " + str(FD.shape[0] + 1)
                print(log_scrubbing)
                np.save(os.path.abspath('tp_after_scrubbing.npy'), index)
                sio.savemat(os.path.abspath(
                    'tp_after_scrubbing.mat'), {'index': index})
                ts_after_scrubbing = ts[:, index]
                np.save(os.path.abspath(
                    'averageTimeseries_%s_after_scrubbing.npy' % parkey), ts_after_scrubbing)
                sio.savemat(os.path.abspath('averageTimeseries_%s_after_scrubbing.mat' % parkey),
                            {'ts': ts_after_scrubbing})
                ts = ts_after_scrubbing
                print('ts.shape : ', ts.shape)

                # initialize connectivity matrix
                nnodes = ts.shape[0]
                i = -1
                for i_signal in ts:
                    i += 1
                    for j in range(i, nnodes):
                        j_signal = ts[j, :]
                        value = np.corrcoef(i_signal, j_signal)[0, 1]
                        G.add_edge(ROI_idx[i], ROI_idx[j])
                        G[ROI_idx[i]][ROI_idx[j]]['corr'] = value
                        # fmat[i,j] = value
                        # fmat[j,i] = value
                # np.save( op.join(gconf.get_timeseries(), 'fconnectome_%s_after_scrubbing.npy' % s), fmat )
                # sio.savemat( op.join(gconf.get_timeseries(),
                #    'fconnectome_%s_after_scrubbing.mat' % s), {'fmat':fmat} )
            else:
                nnodes = ts.shape[0]

                i = -1
                for i_signal in ts:
                    i += 1
                    for j in range(i, nnodes):
                        j_signal = ts[j, :]
                        value = np.corrcoef(i_signal, j_signal)[0, 1]
                        G.add_edge(ROI_idx[i], ROI_idx[j])
                        G[ROI_idx[i]][ROI_idx[j]]['corr'] = value
                        # fmat[i,j] = value
                        # fmat[j,i] = value
                # np.save( op.join(gconf.get_timeseries(), 'fconnectome_%s.npy' % s), fmat )
                # sio.savemat( op.join(gconf.get_timeseries(), 'fconnectome_%s.mat' % s), {'fmat':fmat} )

            # Get the edge attributes/keys/weights from the first edge and then break.
            # Change w.r.t networkx2
            edge_keys = []
            for _, _, d in G.edges(data=True):
                # print(list(d.keys()))
                edge_keys = list(d.keys())
                break

            print('    - connectome_%s.tsv' % parkey)

            with open('connectome_%s.tsv' % parkey, 'w') as out_file:
                tsv_writer = csv.writer(out_file, delimiter='\t')
                header = ['source', 'target']
                header = header + [key for key in edge_keys]
                tsv_writer.writerow(header)

            with open('connectome_%s.tsv' % parkey, 'ab') as out_file:
                nx.write_edgelist(G,
                                  out_file,
                                  comments='#',
                                  delimiter='\t',
                                  data=edge_keys,
                                  encoding='utf-8')

            # storing network
            if 'gPickle' in self.inputs.output_types:
                nx.write_gpickle(G, 'connectome_%s.gpickle' % parkey)
            if 'mat' in self.inputs.output_types:
                # edges
                # size_edges = (int(parval['number_of_regions']), int(
                #     parval['number_of_regions']))

                edge_struct = {}
                for edge_key in edge_keys:
                    edge_struct[edge_key] = nx.to_numpy_matrix(
                        G, weight=edge_key)

                # nodes
                size_nodes = int(parval['number_of_regions'])

                # Get the node attributes/keys from the first node and then break.
                # Change w.r.t networkx2
                for u, d in G.nodes(data=True):
                    node_keys = list(d.keys())
                    break

                node_struct = {}
                for node_key in node_keys:
                    if node_key == 'dn_position':
                        node_arr = np.zeros([size_nodes, 3], dtype=np.float)
                    else:
                        node_arr = np.zeros(size_nodes, dtype=np.object_)
                    node_n = 0
                    for _, node_data in G.nodes(data=True):
                        node_arr[node_n] = node_data[node_key]
                        node_n += 1
                    node_struct[node_key] = node_arr

                sio.savemat('connectome_%s.mat' % parkey, mdict={
                            'sc': edge_struct, 'nodes': node_struct})
            if 'graphml' in self.inputs.output_types:
                g2 = nx.Graph()

                for u_gml, d_gml in G.nodes(data=True):
                    g2.add_node(u_gml)
                    if self.inputs.parcellation_scheme != "Lausanne2018":
                        g2.nodes[u_gml]['dn_correspondence_id'] = d_gml['dn_correspondence_id']
                    else:
                        g2.nodes[u_gml]['dn_multiscaleID'] = d_gml['dn_multiscaleID']
                    g2.nodes[u_gml]['dn_fsname'] = d_gml['dn_fsname']
                    g2.nodes[u_gml]['dn_hemisphere'] = d_gml['dn_hemisphere']
                    g2.nodes[u_gml]['dn_name'] = d_gml['dn_name']
                    g2.nodes[u_gml]['dn_position_x'] = d_gml['dn_position'][0]
                    g2.nodes[u_gml]['dn_position_y'] = d_gml['dn_position'][1]
                    g2.nodes[u_gml]['dn_position_z'] = d_gml['dn_position'][2]
                    g2.nodes[u_gml]['dn_region'] = d_gml['dn_region']

                for u_gml, v_gml, d_gml in G.edges(data=True):
                    g2.add_edge(u_gml, v_gml, {'corr': float(d_gml['corr'])})
                nx.write_graphml(g2, 'connectome_%s.graphml' % parkey)

        print("[ DONE ]")
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['connectivity_matrices'] = glob.glob(
            os.path.abspath('connectome*'))
        outputs['avg_timeseries'] = glob.glob(
            os.path.abspath('averageTimeseries_*'))
        if self.inputs.apply_scrubbing:
            outputs['scrubbed_idx'] = os.path.abspath('tp_after_scrubbing.npy')
        return outputs


# OLD implementations

# class MRTrix3BaseInputSpec(CommandLineInputSpec):
#     nthreads = traits.Int(
#         argstr='-nthreads %d', desc='number of threads. if zero, the number'
#         ' of available cpus will be used', nohash=True)
#     # DW gradient table import options
#     grad_file = File(exists=True, argstr='-grad %s',
#                      desc='dw gradient scheme (MRTrix format')
#     grad_fsl = traits.Tuple(
#         File(exists=True), File(exists=True), argstr='-fslgrad %s %s',
#         desc='(bvecs, bvals) dw gradient scheme (FSL format')
#     bval_scale = traits.Enum(
#         'yes', 'no', argstr='-bvalue_scaling %s',
#         desc='specifies whether the b - values should be scaled by the square'
#         ' of the corresponding DW gradient norm, as often required for '
#         'multishell or DSI DW acquisition schemes. The default action '
#         'can also be set in the MRtrix config file, under the '
#         'BValueScaling entry. Valid choices are yes / no, true / '
#         'false, 0 / 1 (default: true).')

#     in_bvec = File(exists=True, argstr='-fslgrad %s %s',
#                    desc='bvecs file in FSL format')
#     in_bval = File(exists=True, desc='bvals file in FSL format')


# class MRTrix3Base(CommandLine):

#     def _format_arg(self, name, trait_spec, value):
#         if name == 'nthreads' and value == 0:
#             value = 1
#             try:
#                 from multiprocessing import cpu_count
#                 value = cpu_count()
#             except:
#                 logger.warn('Number of threads could not be computed')
#                 pass
#             return trait_spec.argstr % value

#         if name == 'in_bvec':
#             return trait_spec.argstr % (value, self.inputs.in_bval)

#         return super(MRTrix3Base, self)._format_arg(name, trait_spec, value)

#     def _parse_inputs(self, skip=None):
#         if skip is None:
#             skip = []

#         try:
#             if (isdefined(self.inputs.grad_file) or
#                     isdefined(self.inputs.grad_fsl)):
#                 skip += ['in_bvec', 'in_bval']

#             is_bvec = isdefined(self.inputs.in_bvec)
#             is_bval = isdefined(self.inputs.in_bval)
#             if is_bvec or is_bval:
#                 if not is_bvec or not is_bval:
#                     raise RuntimeError('If using bvecs and bvals inputs, both'
#                                        'should be defined')
#                 skip += ['in_bval']
#         except AttributeError:
#             pass

#         return super(MRTrix3Base, self)._parse_inputs(skip=skip)

# class BuildConnectomeInputSpec(CommandLineInputSpec):
#     in_file = File(exists=True, argstr='%s', mandatory=True, position=-3,
#                    desc='input tractography')
#     in_parc = File(exists=True, argstr='%s', position=-2,
#                    desc='parcellation file')
#     out_file = File(
#         'connectome.csv', argstr='%s', mandatory=True, position=-1,
#         usedefault=True, desc='output file after processing')

#     nthreads = traits.Int(
#         argstr='-nthreads %d', desc='number of threads. if zero, the number'
#         ' of available cpus will be used', nohash=True)

#     vox_lookup = traits.Bool(
#         argstr='-assignment_voxel_lookup',
#         desc='use a simple voxel lookup value at each streamline endpoint')
#     search_radius = traits.Float(
#         argstr='-assignment_radial_search %f',
#         desc='perform a radial search from each streamline endpoint to locate '
#         'the nearest node. Argument is the maximum radius in mm; if no node is'
#         ' found within this radius, the streamline endpoint is not assigned to'
#         ' any node.')
#     search_reverse = traits.Float(
#         argstr='-assignment_reverse_search %f',
#         desc='traverse from each streamline endpoint inwards along the '
#         'streamline, in search of the last node traversed by the streamline. '
#         'Argument is the maximum traversal length in mm (set to 0 to allow '
#         'search to continue to the streamline midpoint).')
#     search_forward = traits.Float(
#         argstr='-assignment_forward_search %f',
#         desc='project the streamline forwards from the endpoint in search of a'
#         'parcellation node voxel. Argument is the maximum traversal length in '
#         'mm.')

#     metric = traits.Enum(
#         'count', 'meanlength', 'invlength', 'invnodevolume', 'mean_scalar',
#         'invlength_invnodevolume', argstr='-metric %s', desc='specify the edge'
#         ' weight metric')

#     in_scalar = File(
#         exists=True, argstr='-image %s', desc='provide the associated image '
#         'for the mean_scalar metric')

#     in_weights = File(
#         exists=True, argstr='-tck_weights_in %s', desc='specify a text scalar '
#         'file containing the streamline weights')

#     keep_unassigned = traits.Bool(
#         argstr='-keep_unassigned', desc='By default, the program discards the'
#         ' information regarding those streamlines that are not successfully '
#         'assigned to a node pair. Set this option to keep these values (will '
#         'be the first row/column in the output matrix)')
#     zero_diagonal = traits.Bool(
#         argstr='-zero_diagonal', desc='set all diagonal entries in the matrix '
#         'to zero (these represent streamlines that connect to the same node at'
#         ' both ends)')


# class BuildConnectomeOutputSpec(TraitedSpec):
#     out_file = File(exists=True, desc='the output response file')


# class BuildConnectome(MRTrix3Base):

#     """
#     Generate a connectome matrix from a streamlines file and a node
#     parcellation image
#     Example
#     -------
#     >>> import nipype.interfaces.mrtrix3 as mrt
#     >>> mat = mrt.BuildConnectome()
#     >>> mat.inputs.in_file = 'tracks.tck'
#     >>> mat.inputs.in_parc = 'aparc+aseg.nii'
#     >>> mat.cmdline                               # doctest: +ELLIPSIS +ALLOW_UNICODE
#     'tck2connectome tracks.tck aparc+aseg.nii connectome.csv'
#     >>> mat.run()                                 # doctest: +SKIP
#     """

#     _cmd = 'tck2connectome'
#     input_spec = BuildConnectomeInputSpec
#     output_spec = BuildConnectomeOutputSpec

#     def _list_outputs(self):
#         outputs = self.output_spec().get()
#         outputs['out_file'] = op.abspath(self.inputs.out_file)
#         return outputs

# def mrtrixcmat(intck, fod_file, roi_volumes, parcellation_scheme, compute_curvature=True, additional_maps={},
#                output_types=['gPickle'], atlas_info={}):
#     """ Create the connection matrix using MRTrix fibers and Freesurfer ROIs. """
#     conflow = pe.Workflow(name='MRTRix_connectome_pipeline')
#     # connectome_inputnode = pe.Node(interface=util.IdentityInterface(fields=['intck','fod_file','roi_volumes']),name='inputnode')
#     # connectome_outputnode = pe.Node(interface=util.IdentityInterface(fields=['connectome']),name='outputnode')

#     print "INTCK : ", intck

#     fibers_filter = pe.Node(interface=FilterTractogram(), name='fibers_filter')
#     fibers_filter.inputs.in_tracks = op.intck
#     fibers_filter.inputs.in_fod = fod_file
#     fibers_filter.inputs.out_file = 'streamlines_weights.txt'

#     connectome_builder = pe.Node(interface=BuildConnectome(), name='connectome_builder')
#     connectome_builder.inputs.in_tracks = intck
#     connectome_builder.inputs.in_parc = roi_volumes
#     connectome_builder.inputs.zero_diagonal = True

#     conflow.connect([
#         (fibers_filter, connectome_builder, [('out_weights', 'in_weights')]),
#     ])

#     conflow.run()
