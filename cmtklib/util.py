# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMTK Utility functions
"""

import networkx as nx
import numpy as np
from os import path as op
from collections import OrderedDict
import warnings
from glob import glob
import os
import pickle
import gzip
import json

warnings.simplefilter("ignore")


class bcolors:
    """ Utility class for color unicode
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def load_graphs(output_dir, subjects, parcellation_scheme, weight):
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


def length(xyz, along=False):
    """
    Euclidean length of track line

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
    ''' magnitude of vector

    '''
    mag = np.sum(xyz ** 2, axis=1) ** 0.5
    imag = np.where(mag == 0)
    mag[imag] = np.finfo(float).eps

    if n > 1:
        return np.tile(mag, (n, 1)).T
    return mag.reshape(len(mag), 1)


def mean_curvature(xyz):
    ''' Calculates the mean curvature of a curve

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
    '''
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
    
    if codecs is None:
        codecs = ['utf8', 'latin-1']

    for codec in codecs:
        try:
            return string.decode(codec), codec
        except UnicodeDecodeError:
            pass

    print("ERROR: cannot decode pickle content %s" % ([string]))


def bidsapp_2_local_bids_dir(local_dir, path, debug=True):
    new_path = path.replace(
                        '/bids_dir', '{}'.format(local_dir))
    if debug:
        print(new_path)

    return new_path


def bidsapp_2_local_output_dir2(local_dir, path, debug=True):
    new_path = path.replace(
                        '/output_dir', '{}'.format(os.path.join(local_dir)))
    if debug:
        print(new_path)

    return new_path


def create_results_plkz_local(plkz_file, local_output_dir, encoding='latin-1', debug=True):
   
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
    ''' '''

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
    ''' '''

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
    ''' '''

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
    print("Dictionary of datasink outputs: {}".format(dict_outputs))
    return dict_outputs


def fix_dataset_directory_in_pickles(local_dir, mode='local', debug=False):
    #encoding=sys.getfilesystemencoding()
    
    # mode can be local or newlocal or bidsapp (local by default)

    # TODO: make fix more generalized by taking derivatives/output dir
    searchdir = os.path.join(local_dir, 'derivatives', 'nipype')

    for root, dirs, files in os.walk(searchdir):
        files = [fi for fi in files if (fi.endswith(
            ".pklz") and not fi.endswith("_new.pklz"))]

        if debug:
            print('----------------------------------------------------')

        for fi in files:
            if debug:
                print("Processing file {} {} {} (mode: {})".format(
                    root, dirs, fi, mode))

            pick = gzip.open(os.path.join(root, fi))
            cont = pick.read()
            
            if debug:
                print("local_dir : {} , cont.find('/bids_dir'): {}, cont.find('/output_dir'): {}  (mode: {})".format(
                    local_dir, cont.find(b'/bids_dir'), cont.find(b'/output_dir'), mode))

            # Change pickles: bids app dataset directory -> local dataset directory
            if (mode == 'local'):
                if debug:
                    print(' bids app dataset directory -> local dataset directory')
                new_cont = cont.replace(
                    b'/bids_dir', bytes('{}'.format(local_dir), 'utf-8'))
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)

                if debug:
                    print(
                        ' bids app output directory -> local dataset derivatives directory')
                new_cont = cont.replace(
                    b'/output_dir', bytes('{}'.format(os.path.join(local_dir, 'derivatives')), 'utf-8'))
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)

            elif (mode == 'newlocal'):
                if debug:
                    print(' old local dataset directory -> local dataset directory')

                old_dir = ''

                newpick = gzip.open(os.path.join(root, fi))

                # Retrieve current BIDS directory written in .pklz files
                # Suppose that the BIDS App output directory is directly in the root BIDS directory i.e /bids_dataset/derivatives
                line = newpick.readline()
                print(line)
                while line != '':
                    # print('Line: {}'.format(line))
                    if '/derivatives/' in line:
                        old_dir, _ = line.split('/derivatives/')
                        while old_dir[0] != '/':
                            old_dir = old_dir[1:]
                        break
                    line = newpick.readline()

                if debug:
                    print('Old dir : {}'.format(old_dir))
                    print('Current dir : {}'.format(local_dir))

                # Test if old_dir is valid (not empty) and different from the current BIDS root directory
                # In that case, update the path in the .pklz file
                if (old_dir != '') and (old_dir != local_dir):
                    new_cont = cont.replace(bytes('{}'.format(
                        old_dir), 'utf-8'), bytes('{}'.format(local_dir), 'utf-8'))

                    pref = fi.split(".")[0]
                    with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                        f.write(new_cont)

            # Change pickles: local dataset directory -> bids app dataset directory
            elif (mode == 'bidsapp'):
                if debug:
                    print(
                        ' local dataset derivatives directory -> bids app output directory')
                new_cont = cont.replace(bytes('{}'.format(
                                    os.path.join(local_dir, 'derivatives')), 'utf-8'), b'/output_dir')
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)

                if debug:
                    print(' local dataset directory -> bids app dataset directory')
                new_cont = cont.replace(
                    bytes('{}'.format(local_dir), 'utf-8'), b'/bids_dir')
                pref = fi.split(".")[0]
                with gzip.open(os.path.join(root, '{}.pklz'.format(pref)), 'wb') as f:
                    f.write(new_cont)

    return True


# def remove_aborded_interface_pickles(local_dir, debug=False):
#     searchdir = os.path.join(local_dir, 'derivatives/cmp')

#     for root, dirs, files in os.walk(searchdir):
#         files = [fi for fi in files if fi.endswith(".pklz")]

#         if debug:
#             print('----------------------------------------------------')

#         for fi in files:
#             if debug:
#                 print("Processing file {} {} {}".format(root, dirs, fi))
#             try:
#                 cont = pickle.load(gzip.open(os.path.join(root, fi)))
#             except Exception:
#                 # Remove pickle if unpickling error raised
#                 print('Unpickling Error: removed {}'.format(
#                     os.path.join(root, fi)))
#                 os.remove(os.path.join(root, fi))


# def remove_aborded_interface_pickles(local_dir, subject, session='', debug=False):
#     if session == '':
#         searchdir = os.path.join(local_dir, 'derivatives/cmp', subject, 'tmp')
#     else:
#         searchdir = os.path.join(
#             local_dir, 'derivatives/cmp', subject, session, 'tmp')

#     for root, dirs, files in os.walk(searchdir):
#         files = [fi for fi in files if fi.endswith(".pklz")]

#         if debug:
#             print('----------------------------------------------------')

#         for fi in files:
#             if debug:
#                 print("Processing file {} {} {}".format(root, dirs, fi))
#             try:
#                 cont = pickle.load(gzip.open(os.path.join(root, fi)))
#             except Exception:
#                 # Remove pickle if unpickling error raised
#                 print('Unpickling Error: removed {}'.format(
#                     os.path.join(root, fi)))
#                 os.remove(os.path.join(root, fi))
#             # except pickle.UnpicklingError as e:
#             #     # normal, somewhat expected
#             #     continue
#             # except (AttributeError,  EOFError, ImportError, IndexError) as e:
#             #     # secondary errors
#             #     print(traceback.format_exc(e))
#             #     continue