# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions for the EEG pipeline."""

import os
import copy
import csv
import networkx as nx
import numpy as np
import scipy.io as sio


def save_eeg_connectome_file(output_dir, output_basename, con_res, roi_labels, output_types=None):
    """Save a dictionary of connectivity matrices with corresponding keys to the metrics in the multiple formats of CMP3.

    Parameters
    ----------
    output_dir : str
        Output directory for the connectome file(s)

    output_basename : str
        Base name for the connectome file(s) i.e.,
        ``sub-01_atlas-L20018_res-scale1_conndata-network_connectivity``

    con_res : dict
        Dictionary of connectivity metric / matrix pairs
 
    roi_labels : list
        List of parcellation roi labels extracted from the epo.pkl file generated with MNE

    output_types : ['tsv', 'gpickle', 'mat', 'graphml']
        List of output format in which to save the connectome files.
        (Default: `None`)
    """
    if output_types is None:
        output_types = ['tsv']

    con_methods = list(con_res.keys())

    # Create a graph of n_nodes = shape of the connectivity matrix estimated by MNE
    G = nx.Graph(np.ones(con_res[con_methods[0]].shape))

    # Update node information
    for u, d in G.nodes(data=True):
        # compute a position for the node based on the mean position of the
        # ROI in voxel coordinates (segmentation volume )
        label_split = roi_labels[u].split(' ')
        label_name = f'ctx{label_split[1]}-{label_split[0]}'
        G.nodes[u]["dn_region"] = 'cortical'
        G.nodes[u]["dn_hemisphere"] = 'left' if "-lh" in roi_labels[u] else "right"
        G.nodes[u]["dn_fsname"] = label_name
        G.nodes[u]["dn_name"] = label_name
        # G.nodes[u]["dn_multiscaleID"] = int(u)
        G.nodes[u]["dn_mneID"] = int(u)
 
    # Update edge weights
    G_out = copy.deepcopy(G)
    for u, v, d in G.edges(data=True):
        G_out.remove_edge(u, v)

        edge = {}
        for method in con_methods:
            val = float(con_res[method][int(v), int(u)])
            edge[method] = val

        G_out.add_edge(u, v)
        for key in edge:
            G_out[u][v][key] = float(edge[key])

    # Change w.r.t networkx2
    edge_keys = []
    for u, v, d in G_out.edges(data=True):
        edge_keys = list(d.keys())
        break

    # Save the connectome file
    con_basepath = os.path.join(
        output_dir,
        output_basename
    )

    # In TSV format (by default to be BIDS compliant)
    print(f"Save {con_basepath}.tsv...")
    # Write header fields
    with open(f"{con_basepath}.tsv", "w") as out_file:
        tsv_writer = csv.writer(out_file, delimiter="\t")
        header = ["source", "target"]
        header = header + [key for key in edge_keys]
        tsv_writer.writerow(header)
    # Write list of graph edges with all connectivity metrics (edge_keys)
    with open(f"{con_basepath}.tsv", "ab") as out_file:
        nx.write_edgelist(
            G_out,
            out_file,
            comments="#",
            delimiter="\t",
            data=edge_keys,
            encoding="utf-8",
        )

    if "gpickle" in output_types:
        # Storing network/graph in gpickle that might be prefered by the user
        print(f"Save {con_basepath}.gpickle...")
        nx.write_gpickle(G_out, f"{con_basepath}.gpickle")

    if "mat" in output_types:
        edge_struct = {}
        for edge_key in edge_keys:
            edge_struct[edge_key] = nx.to_numpy_matrix(G_out, weight=edge_key)

        # nodes
        size_nodes = len(list(G_out.nodes(data=True)))

        # Get the node attributes/keys from the first node and then break.
        # Change w.r.t networkx2
        for u, d in G_out.nodes(data=True):
            node_keys = list(d.keys())
            break

        node_struct = {}
        for node_key in node_keys:
            if node_key == "dn_position":
                node_arr = np.zeros([size_nodes, 3], dtype=np.float)
            else:
                node_arr = np.zeros(size_nodes, dtype=np.object_)
                
                node_n = 0
                for _, node_data in G_out.nodes(data=True):
                    node_arr[node_n] = node_data[node_key]
                    node_n += 1
                node_struct[node_key] = node_arr
        
        print(f"Save {con_basepath}.mat...")
        sio.savemat(
            f"{con_basepath}.mat",
            long_field_names=True,
            mdict={"fc": edge_struct, "nodes": node_struct},
        )
    if "graphml" in output_types:
        g2 = nx.Graph()
        for u_gml, v_gml, d_gml in G_out.edges(data=True):
            g2.add_edge(u_gml, v_gml)
            for key in d_gml:
                g2[u_gml][v_gml][key] = d_gml[key]
        for u_gml, d_gml in G_out.nodes(data=True):
            g2.add_node(u_gml)
            # g2.nodes[u_gml]["dn_multiscaleID"] = d_gml["dn_multiscaleID"]
            g2.nodes[u_gml]["dn_mneID"] = d_gml["dn_mneID"]
            g2.nodes[u_gml]["dn_fsname"] = d_gml["dn_fsname"]
            g2.nodes[u_gml]["dn_hemisphere"] = d_gml["dn_hemisphere"]
            g2.nodes[u_gml]["dn_name"] = d_gml["dn_name"]
            g2.nodes[u_gml]["dn_region"] = d_gml["dn_region"]
        print(f"Save {con_basepath}.graphml...")
        nx.write_graphml(g2, f"{con_basepath}.graphml")
