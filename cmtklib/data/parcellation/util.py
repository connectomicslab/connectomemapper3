# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions for retrieving Lausanne parcellation files."""

import os
from pkg_resources import resource_filename

import pandas as pd


def get_lausanne2018_parcellation_mni_coords(scale='scale1'):
    """Return label regions cut coordinates in MNI space (mm).

    Parameters
    ----------
    scale : {'scale1', 'scale2', 'scale3', 'scale4', 'scale5'}
        Lausanne 2018 parcellation scale

    Returns
    -------
    coords : numpy.array
        Label regions cut coordinates in MNI space (mm)

    """
    query_csv_file = resource_filename(
        "cmtklib",
        os.path.join("data",
                     "parcellation",
                     "lausanne2018",
                     "mni-space",
                     f'atlas-L2018_res-{scale}_coords.csv')
    )
    return pd.read_csv(query_csv_file,
                       index_col=0).to_numpy()


def get_lausanne2018_parcellation_annot(scale='scale1', hemi='lh'):
    """Return the path of the Freesurfer ``.annot`` file corresponding to a specific scale and hemisphere.

    Parameters
    ----------
    scale : {'scale1', 'scale2', 'scale3', 'scale4', 'scale5'}
        Lausanne 2018 parcellation scale

    hemi : {'lh', 'rh'}
        Brain hemisphere

    Returns
    -------
    annot_file_path : string
        Absolute path to the queried ``.annot`` file

    """
    query_annot_file = resource_filename(
        "cmtklib",
        os.path.join("data",
                     "parcellation",
                     "lausanne2018",
                     f'{hemi}.lausanne2018.{scale}.annot')
    )
    return query_annot_file
