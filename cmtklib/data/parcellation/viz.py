# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions for plotting Lausanne parcellation files."""

import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from nilearn import plotting, datasets

from cmtklib.data.parcellation.util import (
    get_lausanne2018_parcellation_annot
)


def plot_lausanne2018_surface_ctx(
    roi_values, scale='scale1',
    cmap="Spectral",
    save_fig=False, output_dir="./", filename=None, fmt="png"
):
    """
    Plots a set of values on the cortical surface of a given Lausanne 2018 parcellation scale.

    Parameters
    ----------
    roi_values : numpy array
        The values to be plotted on the surface. The array should
        have as many values as regions of interest

    scale : {'scale1', 'scale2', 'scale3', 'scale4', 'scale5'}
        Scale of the Lausanne 2018 atlas to be used

    cmap : string
        Colormap to use for plotting, default "Spectral"

    save_fig : bool
        Whether to save the generated figures, default: `False`

    output_dir : string
        Directory to save the figure, only used when
        `save_fig == True`

    filename : string
        Filename of the saved figure (without the extension),
        only used when `save_fig == True`

    fmt : string
        Format the figure is saved
        (Default: "png", also
        accepted are "pdf", "svg", and others, depending
        on the backend used)

    """
    # Surface mesh
    fsaverage = datasets.fetch_surf_fsaverage(mesh="fsaverage")

    # File paths to the annot files
    annots = [get_lausanne2018_parcellation_annot(scale=f'{scale}', hemi='rh'),
              get_lausanne2018_parcellation_annot(scale=f'{scale}', hemi='lh')]

    # Read annot files
    annot_right = nib.freesurfer.read_annot(annots[0])
    annot_left = nib.freesurfer.read_annot(annots[1])

    # Create vector to store intensity values (one value per vertex)
    roi_vect_right = np.zeros_like(annot_right[0], dtype=float)
    roi_vect_left = np.zeros_like(annot_left[0], dtype=float)

    # Convert labels to strings, labels are the same as 2018 is symmetric
    labels = [str(elem, 'utf-8') for elem in annot_right[2]]

    # Create roi vectors
    for i in range(len(labels[1:])):  # skip 'unknown'
        ids_roi = np.where(annot_right[0] == i+1)[0]
        roi_vect_right[ids_roi] = roi_values[i]

    for i in range(len(labels[1:])):  # skip 'unknown'
        ids_roi = np.where(annot_left[0] == i+1)[0]
        roi_vect_left[ids_roi] = roi_values[i+len(labels)-1]

    # Get min and max values
    vmin = min(roi_values)
    vmax = max(roi_values)

    # Center around 0
    max_val = max([abs(vmin), vmax])
    vmax = max_val
    vmin = -max_val

    # Creation of list to allow iteration
    # and reduce duplication of plotting.plot_surf_roi()
    hemis = [
        'right', 'left', 'right', 'left',
        'right', 'left', 'right', 'left',
    ]
    views = [
        'lateral', 'lateral', 'medial', 'medial',
        'ventral', 'ventral', 'dorsal', 'dorsal'
    ]
    surfaces = [f'pial_{hemi}' for hemi in hemis]
    bg_maps = [f'sulc_{hemi}' for hemi in hemis]
    roi_vectors = [roi_vect_right, roi_vect_left]*4

    # Initial a figure with [2 x 4] subplots
    fig, axs = plt.subplots(nrows=2, ncols=4,
                            subplot_kw={'projection': '3d'},
                            figsize=(20, 10))
    axs = axs.flatten()

    # Iterate over the list of views to render
    for i, (hemi, surf, bg_map, view, vector, ax) in enumerate(
        zip(hemis, surfaces, bg_maps, views, roi_vectors, axs)
    ):
        plotting.plot_surf_roi(fsaverage[f'{surf}'], roi_map=vector,
                               hemi=hemi, view=view,
                               bg_map=fsaverage[f'{bg_map}'], bg_on_data=True,
                               darkness=.5,
                               cmap=cmap, vmin=vmin, vmax=vmax,
                               axes=ax)

    # Save the figure in the desired format if enabled
    if save_fig:
        if filename is None:
            filename = f'atlas-{scale}_projection'
        fig.savefig(f'{output_dir}/{filename}.{fmt}')
