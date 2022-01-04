# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK Utility functions."""

import os
import warnings
from pathlib import Path

import json
import numpy as np

warnings.simplefilter("ignore")


def unicode2str(text):
    """Convert a unicode to a string using system's encoding.

    Parameters
    ----------
    text : bytes
        Unicode bytes representation of a string

    Returns
    -------
    out_str : str
        Output string
    """
    out_str = str(text)
    return out_str


def isavailable(file):
    """Check if file is available and return the file if it is.

    Used for debugging.

    Parameters
    ----------
    file : File
        Input file

    Returns
    -------
    file : File
        Output file
    """
    return file


def get_basename(path):
    """Return ``os.path.basename()`` of a ``path``.

    Parameters
    ----------
    path : os.path
        Path to extract the containing directory

    Returns
    -------
    path : os.path
        Path to the containing directory
    """
    from os import path as op  # Important to be used as Nipype connect function
    return op.basename(path)


class BColors:
    """Utility class for color unicode."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_warning(message):
    """Print yellow-colored warning message

    Parameters
    ----------
    message : string
        The string of the message to be printed
    """
    print(BColors.WARNING + message + BColors.ENDC)


def print_error(message):
    """Print red-colored error message

    Parameters
    ----------
    message : string
        The string of the message to be printed
    """
    print(BColors.FAIL + message + BColors.ENDC)


def print_blue(message):
    """Print blue-colored message

    Parameters
    ----------
    message : string
        The string of the message to be printed
    """
    print(BColors.OKBLUE + message + BColors.ENDC)


def return_button_style_sheet(image, image_disabled=None, verbose=False):
    """Return Qt style sheet for QPushButton with image

    Parameters
    ----------
    image : string
        Path to image to use as icon when button is enabled

    image_disabled : string
        Path to image to use as icon when button is disabled

    verbose : Bool
        Print the style sheet if True
        Default: False

    Returns
    -------
    button_style_sheet : string
        Qt style sheet for QPushButton with image
    """
    if image_disabled is None:
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
    else:
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
                QPushButton:disabled {{
                        border-radius: 2px;
                        border-image: url({image_disabled}) 0 0 0 0;
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
    >>> m=tm.mean_curvature(xyz)  # mean curvature straight line
    >>> theta=np.pi*np.linspace(0,1,100)
    >>> x=np.cos(theta)
    >>> y=np.sin(theta)
    >>> z=0*x
    >>> xyz=np.vstack((x,y,z)).T
    >>> m=tm.mean_curvature(xyz)  # mean curvature for semi-circle
    """
    xyz = np.asarray(xyz)
    n_pts = xyz.shape[0]
    if n_pts == 0:
        raise ValueError("xyz array cannot be empty")

    dxyz = np.gradient(xyz)[0]
    ddxyz = np.gradient(dxyz)[0]

    # Curvature
    k = magn(np.cross(dxyz, ddxyz), 1) / (magn(dxyz, 1) ** 3)

    return np.mean(k)


def extract_freesurfer_subject_dir(reconall_report, local_output_dir=None, debug=False):
    """Extract Freesurfer subject directory from the report created by Nipype Freesurfer Recon-all node.

    Parameters
    ----------
    reconall_report : string
        Path to the recon-all report

    local_output_dir : string
        Local output / derivatives directory

    debug : bool
        If `True`, show printed outputs

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
            if debug:
                print("Line {}: {}".format(cnt, line.strip()))

            # Extract line containing listing of node outputs
            if "* subject_id : " in line:
                fs_subject_dir = line.strip()
                prefix = "* subject_id : "
                fs_subject_dir = str.replace(fs_subject_dir, prefix, "")
                if debug:
                    print(fs_subject_dir)

                # Update from BIDS App /output_dir to local output directory
                # specified by local_output_dir
                if local_output_dir is not None:
                    fs_subject_dir = str.replace(
                        fs_subject_dir, "/output_dir", local_output_dir
                    )
                break

            line = fp.readline()
            cnt += 1

    return fs_subject_dir


def get_freesurfer_subject_id(file):
    """Extract Freesurfer subject ID from file generated by recon-all.

    Parameters
    ----------
    file : str
        File generated by recon-all

    Returns
    -------
    out : str
        Freesurfer subject ID
    """
    out = file[:-18]
    return out


def extract_reconall_base_dir(file):
    """Extract Recon-all base directory from a file.

    Parameters
    ----------
    file : File
        File generated by Recon-all

    Returns
    -------
    out_path : string
        Recon-all base directory
    """
    # print("Extract reconall base dir : %s" % file[:-17])
    out_path = str(file[:-17])
    return out_path


def get_pipeline_dictionary_outputs(
    datasink_report, local_output_dir=None, debug=False
):
    """Read the Nipype datasink report and return a dictionary of pipeline outputs.

    Parameters
    ----------
    datasink_report : string
        Path to the datasink report

    local_output_dir : string
        Local output / derivatives directory

    debug : bool
        If `True`, print output dictionary

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
                prefix = "* _outputs : "
                str_outputs = str.replace(str_outputs, prefix, "")
                str_outputs = str.replace(str_outputs, "'", '"')
                str_outputs = str.replace(str_outputs, "<undefined>", '""')

                # Update from BIDS App /output_dir to local output directory
                # specified by local_output_dir
                if local_output_dir is not None:
                    str_outputs = str.replace(
                        str_outputs, "/output_dir", local_output_dir
                    )
                break

    # Convert the extracted JSON-structured string to a dictionary
    dict_outputs = json.loads("{}".format(str_outputs))
    if debug:
        print("Dictionary of datasink outputs: {}".format(dict_outputs))
    return dict_outputs


def get_node_dictionary_outputs(node_report, local_output_dir=None, debug=False):
    """Read the Nipype node report and return a dictionary of node outputs.

    Parameters
    ----------
    node_report : string
        Path to node report

    local_output_dir : string
        Local output / derivatives directory

    debug : bool
        If `True`, print output dictionary

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
                prefix = "* _outputs : "
                str_outputs = str.replace(str_outputs, prefix, "")
                str_outputs = str.replace(str_outputs, "'", '"')

                # Update from BIDS App /output_dir to local output directory
                # specified by local_output_dir
                if local_output_dir is not None:
                    str_outputs = str.replace(
                        str_outputs, "/output_dir", local_output_dir
                    )
                break

    # Convert the extracted JSON-structured string to a dictionary
    dict_outputs = json.loads("{}".format(str_outputs))
    if debug:
        print("Dictionary of node outputs: {}".format(dict_outputs))
    return dict_outputs


def convert_list_to_tuple(lists):
    """Convert list of files to tuple of files.

    (Duplicated with preprocessing, could be moved to utils in the future)

    Parameters
    ----------
    lists : [bvecs, bvals]
        List of files containing bvecs and bvals
    Returns
    -------
    out_tuple : (bvecs, bvals)
        Tuple of files containing bvecs and bvals
    """
    return tuple(lists)


def check_directory_exists(mandatory_dir):
    """Makes sure the mandatory directory exists.

    Raises
    ------
    FileNotFoundError
        Raised when the directory is not found.
    """
    f_path = Path(mandatory_dir)
    if not f_path.is_dir():
        raise FileNotFoundError(f"No directory is found at: {str(f_path)}")
