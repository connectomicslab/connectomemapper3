# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK Utility functions."""

import os
from os import path as op

import warnings
from glob import glob

# import pickle
import gzip
import json

import networkx as nx
import numpy as np

warnings.simplefilter("ignore")


class BColors:
    """Utility class for color unicode."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def return_button_style_sheet(image, icon_size, verbose=False):
    """Return Qt style sheet for QPushButton with image

    Parameters
    ----------
    image : string
        Path to image to use as icon

    icon_size : int
        Image size

    verbose : Bool
        Print the style sheet if True
        Default: False

    Returns
    -------
    button_style_sheet : string
        Qt style sheet for QPushButton with image
    """
    button_style_sheet = f"""
        QPushButton {{
                border-radius: 2px;
                border-image: url({image}) 0 0 0 0;
                color: transparent;
                background-color: transparent;
                font: 12pt "Verdana";
                margin: 0px 0px 0px 0px;
                padding:0px 0px;
        }}
        QPushButton:pressed {{
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #dadbde, stop: 1 #f6f7fa);
        }}
        """
    if verbose:
        print(button_style_sheet)
    return button_style_sheet


def load_graphs(output_dir, subjects, parcellation_scheme, weight):
    """Return a dictionary of connectivity matrices (graph adjacency matrices).

    Still in development

    Parameters
    ----------
    output_dir : string
        Output/derivatives directory

    subjects : list
        List of subject

    parcellation_scheme : ['NativeFreesurfer','Lausanne2008','Lausanne2018']
        Parcellation scheme

    weight : ['number_of_fibers','fiber_density',...]
        Edge metric to extract from the graph

    Returns
    -------

    connmats: dict
        Dictionary of connectivity matrices

    """
    if parcellation_scheme == 'Lausanne2008':
        bids_atlas_label = 'L2008'
    elif parcellation_scheme == 'Lausanne2018':
        bids_atlas_label = 'L2018'
    elif parcellation_scheme == 'NativeFreesurfer':
        bids_atlas_label = 'Desikan'

    if parcellation_scheme == 'NativeFreesurfer':
        for subj in subjects:
            subj_dir = os.path.join(output_dir, subj)
            subj_session_dirs = glob(op.join(subj_dir, "ses-*"))
            subj_sessions = ['ses-{}'.format(subj_session_dir.split("-")[-1])
                             for subj_session_dir in subj_session_dirs]

            if len(subj_sessions) > 0:  # Session structure
                for subj_session in subj_sessions:
                    conn_derivatives_dir = op.join(
                        output_dir, 'cmp', subj, subj_session, 'connectivity')

                    # Extract the connectivity matrix
                    # self.subject+'_label-'+bids_atlas_label+'_desc-scale5_conndata-snetwork_connectivity'
                    connmat_fname = op.join(conn_derivatives_dir,
                                            '{}_{}_label-{}_conndata-snetwork_connectivity.gpickle'.format(subj,
                                                                                                           subj_session,
                                                                                                           bids_atlas_label))
                    connmat_gp = nx.read_gpickle(connmat_fname)
                    connmat = nx.to_numpy_matrix(
                        connmat_gp, weight=weight, dtype=np.float32)
    else:
        # For each parcellation scale
        for scale in np.arange(1, 6):
            for subj in subjects:
                subj_dir = os.path.join(output_dir, subj)
                subj_session_dirs = glob(op.join(subj_dir, "ses-*"))
                subj_sessions = ['ses-{}'.format(subj_session_dir.split("-")[-1]) for subj_session_dir in
                                 subj_session_dirs]

                if len(subj_sessions) > 0:  # Session structure
                    for subj_session in subj_sessions:
                        conn_derivatives_dir = op.join(
                            output_dir, 'cmp', subj, subj_session, 'connectivity')

                        # Extract the connectivity matrix
                        # self.subject+'_label-'+bids_atlas_label+'_desc-scale5_conndata-snetwork_connectivity'
                        connmat_fname = op.join(conn_derivatives_dir,
                                                '{}_{}_label-{}_desc-scale{}_conndata-snetwork_connectivity.gpickle'.format(
                                                    subj, subj_session, bids_atlas_label, scale))
                        connmat_gp = nx.read_gpickle(connmat_fname)
                        connmat = nx.to_numpy_matrix(
                            connmat_gp, weight=weight, dtype=np.float32)
                # TODO: finalize condition and append all conmat to a list
    return connmat


def length(xyz, along=False):
    """Euclidean length of track line.

    Parameters
    ----------
    xyz : array-like shape (N,3)
       array representing x,y,z of N points in a track

    along : bool, optional
       If True, return array giving cumulative length along track,
       otherwise (default) return scalar giving total length.

    Returns
    -------
    L : scalar or array shape (N-1,)
       scalar in case of `along` == False, giving total length, array if
       `along` == True, giving cumulative lengths.

    Examples
    --------
    >>> xyz = np.array([[1,1,1],[2,3,4],[0,0,0]])
    >>> expected_lens = np.sqrt([1+2**2+3**2, 2**2+3**2+4**2])
    >>> length(xyz) == expected_lens.sum()
    True
    >>> len_along = length(xyz, along=True)
    >>> np.allclose(len_along, expected_lens.cumsum())
    True
    >>> length([])
    0
    >>> length([[1, 2, 3]])
    0
    >>> length([], along=True)
    array([0])
    """
    xyz = np.asarray(xyz)
    if xyz.shape[0] < 2:
        if along:
            return np.array([0])
        return 0
    dists = np.sqrt((np.diff(xyz, axis=0) ** 2).sum(axis=1))
    if along:
        return np.cumsum(dists)
    return np.sum(dists)


def magn(xyz, n=1):
    """Returns the vector magnitude

    Parameters
    ----------
    xyz : vector
        Input vector

    n : int
        Tile by `n` if `n>1` before return
    """
    mag = np.sum(xyz ** 2, axis=1) ** 0.5
    imag = np.where(mag == 0)
    mag[imag] = np.finfo(float).eps

    if n > 1:
        return np.tile(mag, (n, 1)).T
    return mag.reshape(len(mag), 1)


def mean_curvature(xyz):
    """Calculates the mean curvature of a curve.

    Parameters
    ------------
    xyz : array-like shape (N,3)
       array representing x,y,z of N points in a curve

    Returns
    -----------
    m : float
        float representing the mean curvature

    Examples
    --------
    Create a straight line and a semi-circle and print their mean curvatures

    >>> from dipy.tracking import metrics as tm
    >>> import numpy as np
    >>> x=np.linspace(0,1,100)
    >>> y=0*x
    >>> z=0*x
    >>> xyz=np.vstack((x,y,z)).T
    >>> m=tm.mean_curvature(xyz) #mean curvature straight line
    >>> theta=np.pi*np.linspace(0,1,100)
    >>> x=np.cos(theta)
    >>> y=np.sin(theta)
    >>> z=0*x
    >>> xyz=np.vstack((x,y,z)).T
    >>> m=tm.mean_curvature(xyz) #mean curvature for semi-circle
    """
    xyz = np.asarray(xyz)
    n_pts = xyz.shape[0]
    if n_pts == 0:
        raise ValueError('xyz array cannot be empty')

    dxyz = np.gradient(xyz)[0]
    ddxyz = np.gradient(dxyz)[0]

    # Curvature
    k = magn(np.cross(dxyz, ddxyz), 1) / (magn(dxyz, 1) ** 3)

    return np.mean(k)


def force_decode(string, codecs=None):
    """Force decoding byte string with a specific codec.

    Parameters
    ----------
    string : bytes
        String in bytearray format to be decoded

    codecs : list
        List of codecs to try to decode the encoded string
    """
    if codecs is None:
        codecs = ['utf8', 'latin-1']

    for codec in codecs:
        try:
            return string.decode(codec), codec
        except UnicodeDecodeError:
            pass

    print("ERROR: cannot decode pickle content %s" % ([string]))


def bidsapp_2_local_bids_dir(local_dir, path, debug=True):
    """Replace all path prefixes /bids_dir by the real local directory path.

    Parameters
    ----------
    local_dir: string
        Local path to BIDS root directory

    path : string
        Path where the prefix should be replaced

    debug : Boolean
        If True, print the new path after replacement

    Returns
    -------
    new_path: string
        Output path with prefix replaced
    """
    new_path = path.replace(
                        '/bids_dir', '{}'.format(local_dir))
    if debug:
        print(new_path)

    return new_path


def bidsapp_2_local_output_dir2(local_dir, path, debug=True):
    """Replace all path prefixes /output_dir by the real local directory path.

    Parameters
    ----------
    local_dir: string
        Local path to output / derivatives directory

    path : string
        Path where the prefix should be replaced

    debug : Boolean
        If True, print the new path after replacement

    Returns
    -------
    new_path: string
        Output path with prefix replaced
    """
    new_path = path.replace(
                        '/output_dir', '{}'.format(os.path.join(local_dir)))
    if debug:
        print(new_path)

    return new_path


def create_results_plkz_local(plkz_file, local_output_dir, encoding='latin-1', debug=True):
    """Update path in pickle files generated by Nipype nodes.

    Parameters
    ----------
    plkz_file : zipped pickle
        Pickle file generated by Nipype node

    local_output_dir : string
        Local output / derivatives directory

    debug : Boolean
        If True, print extra information
    """
    if debug:
        print("Processing pickle {} ".format(plkz_file))

    pick = gzip.open(plkz_file,'rb')
    cont = pick.read()
    # cont = "".join( chr(x) for x in bytearray(cont))
    print(cont)

    # if debug:
    #     print("local_output_dir : {} , cont.find('/bids_dir'): {}, cont.find('/output_dir'): {} ".format(
    #         local_output_dir, cont.find('/bids_dir'), cont.find('/output_dir')))

    # if debug:
    #     print(
    #         ' bids app output directory -> local dataset derivatives directory')

    # new_cont = cont.replace('/output_dir', '{}'.format(local_output_dir))

    if debug:
        print("local_output_dir : {} , cont.find('/bids_dir'): {}, cont.find('/output_dir'): {} ".format(
            local_output_dir, cont.find(b'/bids_dir'), cont.find(b'/output_dir')))

    if debug:
        print(
            ' bids app output directory -> local dataset derivatives directory')

    new_cont = cont.replace(b'/output_dir', bytearray(local_output_dir, encoding="utf-8"))

    print(new_cont)

    root = os.path.dirname(plkz_file)
    base = os.path.basename(plkz_file)
    pref = os.path.splitext(base)[0]

    out_plkz_file = os.path.join(root, '{}_local.pklz'.format(pref))

    if os.path.exists(out_plkz_file):
        print('WARNING: remove existing local results pickle file')
        os.remove(out_plkz_file)

    print('New pickle: {} ({} , {} , {})'.format(out_plkz_file, root, base, pref))
    try:
        with gzip.open(out_plkz_file, 'wb') as f:
            f.write(new_cont)
    except Exception as e:
        print(e)

    print('Completed')

    return out_plkz_file


def extract_freesurfer_subject_dir(reconall_report, local_output_dir=None):
    """Extract Freesurfer subject directory from the report created by Nipype Freesurfer Recon-all node.

    Parameters
    ----------
    reconall_report : string
        Path to the recon-all report

    local_output_dir : string
        Local output / derivatives directory

    Returns
    -------
    fs_subject_dir : string
        Freesurfer subject directory
    """
    # Read rst report of a datasink node
    with open(reconall_report) as fp:
        line = fp.readline()
        cnt = 1
        while line:
            print("Line {}: {}".format(cnt, line.strip()))

            # Extract line containing listing of node outputs
            if "* subject_id : " in line:
                fs_subject_dir = line.strip()
                prefix = '* subject_id : '
                fs_subject_dir = str.replace(fs_subject_dir,prefix,"")
                print(fs_subject_dir)

                # Update from BIDS App /output_dir to local output directory
                # specified by local_output_dir
                if local_output_dir is not None:
                    fs_subject_dir = str.replace(fs_subject_dir,"/output_dir",local_output_dir)
                break

            line = fp.readline()
            cnt += 1

    return fs_subject_dir


def get_pipeline_dictionary_outputs(datasink_report, local_output_dir=None):
    """Read the Nipype datasink report and return a dictionary of pipeline outputs.

    Parameters
    ----------
    datasink_report : string
        Path to the datasink report

    local_output_dir : string
        Local output / derivatives directory

    Returns
    -------
    dict_outputs : dict
        Dictionary of pipeline outputs
    """
    # Read rst report of a datasink node
    with open(datasink_report) as fp:
        while True:
            line = fp.readline()
            if not line:
                break

            # Extract line containing listing of node outputs and stop
            if "_outputs :" in line:
                str_outputs = line.strip()
                prefix = '* _outputs : '
                str_outputs = str.replace(str_outputs,prefix,"")
                str_outputs = str.replace(str_outputs,"\'","\"")
                str_outputs = str.replace(str_outputs,"<undefined>","\"\"")

                # Update from BIDS App /output_dir to local output directory
                # specified by local_output_dir
                if local_output_dir is not None:
                    str_outputs = str.replace(str_outputs,"/output_dir",local_output_dir)
                break

    # Convert the extracted JSON-structured string to a dictionary
    dict_outputs = json.loads("{}".format(str_outputs))
    print("Dictionary of datasink outputs: {}".format(dict_outputs))
    return dict_outputs


def get_node_dictionary_outputs(node_report, local_output_dir=None):
    """Read the Nipype node report and return a dictionary of node outputs.

    Parameters
    ----------
    node_report : string
        Path to node report

    local_output_dir : string
        Local output / derivatives directory

    Returns
    -------
    dict_outputs : dict
        dictionary of outputs extracted from node execution report
    """
    # Read rst report of a datasink node
    with open(node_report) as fp:
        while True:
            line = fp.readline()
            if not line:
                break

            # Extract line containing listing of node outputs and stop
            if "_outputs :" in line:
                str_outputs = line.strip()
                prefix = '* _outputs : '
                str_outputs = str.replace(str_outputs,prefix,"")
                str_outputs = str.replace(str_outputs,"\'","\"")

                # Update from BIDS App /output_dir to local output directory
                # specified by local_output_dir
                if local_output_dir is not None:
                    str_outputs = str.replace(str_outputs,"/output_dir",local_output_dir)
                break

    # Convert the extracted JSON-structured string to a dictionary
    dict_outputs = json.loads("{}".format(str_outputs))
    print("Dictionary of node outputs: {}".format(dict_outputs))
    return dict_outputs
