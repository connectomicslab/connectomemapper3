# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module defines the `showmatrix_gpickle` script that loads and displays a connectivity matrix."""

import sys
import os
from itertools import cycle

import networkx as nx
import numpy as np
import copy

import matplotlib.colors as colors

# import matplotlib
# matplotlib.use('Agg') # Must be before importing matplotlib.pyplot or pylab!
from matplotlib.pyplot import imshow, cm, show, figure, colorbar, hist
import matplotlib.pyplot as plt
import matplotlib.path as m_path
import matplotlib.patches as m_patches

from mne.viz.utils import plt_show


def _plot_connectivity_circle_onpick(
    event, fig=None, axes=None, indices=None, node_angles=None, ylim=[9, 10]
):
    """Isolate connections around a single node when user left clicks a node.

    On right click, resets all connections.
    """
    # Original Authors:
    #          Denis Engemann <denis.engemann@gmail.com>
    #          Martin Luessi <mluessi@nmr.mgh.harvard.edu>
    #          Alexandre Gramfort <alexandre.gramfort@telecom-paristech.fr>
    #
    # License: Simplified BSD
    #
    # Modified by:
    #          Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

    if event.inaxes != axes:
        return

    if event.button == 1:  # left click
        # click must be near node radius
        if not ylim[0] <= event.ydata <= ylim[1]:
            return

        # all angles in range [0, 2*pi]
        node_angles = node_angles % (np.pi * 2)
        node = np.argmin(np.abs(event.xdata - node_angles))

        patches = event.inaxes.patches
        for ii, (x, y) in enumerate(zip(indices[0], indices[1])):
            patches[ii].set_visible(node in [x, y])
        fig.canvas.draw()
    elif event.button == 3:  # right click
        patches = event.inaxes.patches
        for ii in range(np.size(indices, axis=1)):
            patches[ii].set_visible(True)
        fig.canvas.draw()


def plot_connectivity_circle(
    con,
    node_names,
    indices=None,
    n_lines=None,
    node_angles=None,
    node_width=None,
    node_colors=None,
    facecolor="black",
    textcolor="white",
    node_edgecolor="black",
    linewidth=1.5,
    colormap="hot",
    vmin=None,
    vmax=None,
    colorbar=True,
    title=None,
    colorbar_size=0.2,
    colorbar_pos=(-0.15, -0.05),
    fontsize_title=12,
    fontsize_names=10,
    fontsize_colorbar=10,
    padding=4.0,
    fig=None,
    subplot=111,
    interactive=True,
    node_linewidth=2.0,
    show=True,
):
    """Visualize connectivity as a circular graph.

    Note: This code is based on the circle graph example by Nicolas P. Rougier
    http://www.labri.fr/perso/nrougier/coding/.

    Parameters
    ----------
    con : numpy.array
        Connectivity scores. Can be a square matrix, or a 1D array. If a 1D
        array is provided, "indices" has to be used to define the connection
        indices.
    node_names : list of str
        Node names. The order corresponds to the order in con.
    indices : tuple of arrays | None
        Two arrays with indices of connections for which the connections
        strenghts are defined in con. Only needed if con is a 1D array.
    n_lines : int | None
        If not None, only the n_lines strongest connections (strength=abs(con))
        are drawn.
    node_angles : array, shape=(len(node_names,)) | None
        Array with node positions in degrees. If None, the nodes are equally
        spaced on the circle. See mne.viz.circular_layout.
    node_width : float | None
        Width of each node in degrees. If None, the minimum angle between any
        two nodes is used as the width.
    node_colors : list of tuples | list of str
        List with the color to use for each node. If fewer colors than nodes
        are provided, the colors will be repeated. Any color supported by
        matplotlib can be used, e.g., RGBA tuples, named colors.
    facecolor : str
        Color to use for background. See matplotlib.colors.
    textcolor : str
        Color to use for text. See matplotlib.colors.
    node_edgecolor : str
        Color to use for lines around nodes. See matplotlib.colors.
    linewidth : float
        Line width to use for connections.
    colormap : str
        Colormap to use for coloring the connections.
    vmin : float | None
        Minimum value for colormap. If None, it is determined automatically.
    vmax : float | None
        Maximum value for colormap. If None, it is determined automatically.
    colorbar : bool
        Display a colorbar or not.
    title : str
        The figure title.
    colorbar_size : float
        Size of the colorbar.
    colorbar_pos : 2-tuple
        Position of the colorbar.
    fontsize_title : int
        Font size to use for title.
    fontsize_names : int
        Font size to use for node names.
    fontsize_colorbar : int
        Font size to use for colorbar.
    padding : float
        Space to add around figure to accommodate long labels.
    fig : None | instance of matplotlib.pyplot.Figure
        The figure to use. If None, a new figure with the specified background
        color will be created.
    subplot : int | 3-tuple
        Location of the subplot when creating figures with multiple plots. E.g.
        121 or (1, 2, 1) for 1 row, 2 columns, plot 1. See
        matplotlib.pyplot.subplot.
    interactive : bool
        When enabled, left-click on a node to show only connections to that
        node. Right-click shows all connections.
    node_linewidth : float
        Line with for nodes.
    show : bool
        Show figure if True.

    Returns
    -------
    fig : instance of matplotlib.pyplot.Figure
        The figure handle.
    axes : instance of matplotlib.axes.PolarAxesSubplot
        The subplot handle.
    """
    n_nodes = len(node_names)

    if node_angles is not None:
        if len(node_angles) != n_nodes:
            raise ValueError("node_angles has to be the same length " "as node_names")
        # convert it to radians
        node_angles = node_angles * np.pi / 180
    else:
        # uniform layout on unit circle
        node_angles = np.linspace(0, 2 * np.pi, n_nodes, endpoint=False)

    if node_width is None:
        # widths correspond to the minimum angle between two nodes
        dist_mat = node_angles[None, :] - node_angles[:, None]
        dist_mat[np.diag_indices(n_nodes)] = 1e9
        node_width = np.min(np.abs(dist_mat))
    else:
        node_width = node_width * np.pi / 180

    if node_colors is not None:
        if len(node_colors) < n_nodes:
            node_colors = cycle(node_colors)
    else:
        # assign colors using colormap (plt.cmp.spectral -> plt.spectral)
        cmap = cm.get_cmap("hsv", n_nodes)  # 'Spectral'
        node_colors = [cmap(i / float(n_nodes)) for i in range(n_nodes)]

    # handle 1D and 2D connectivity information
    if con.ndim == 1:
        if indices is None:
            raise ValueError("indices has to be provided if con.ndim == 1")
    elif con.ndim == 2:
        print("Dimension: 2D")
        if con.shape[0] != n_nodes or con.shape[1] != n_nodes:
            raise ValueError("con has to be 1D or a square matrix")
        # we use the lower-triangular part
        print("Number_of_nodes : %i" % n_nodes)
        indices = np.tril_indices(n_nodes, -1)
        con = np.squeeze(con[indices])
    else:
        raise ValueError("con has to be 1D or a square matrix")

    con = np.squeeze(con.T)

    # get the colormap
    if isinstance(colormap, str):
        colormap = plt.get_cmap(colormap)

    # Make figure background the same colors as axes
    if fig is None:
        fig = plt.figure(figsize=(14, 11), facecolor=facecolor)

    # Use a polar axes
    if not isinstance(subplot, tuple):
        subplot = (subplot,)
    axes = plt.subplot(*subplot, polar=True)
    axes.set_facecolor(facecolor)

    # No ticks, we'll put our own
    plt.xticks([])
    plt.yticks([])

    # Set y axes limit, add additional space if requested
    plt.ylim(0, 10 + padding)

    # Remove the black axes border which may obscure the labels
    axes.spines["polar"].set_visible(False)

    # Draw lines between connected nodes, only draw the strongest connections
    if n_lines is not None and len(con) > n_lines:
        con_thresh = np.sort(np.abs(con).ravel())[-n_lines]
    else:
        con_thresh = 0.0

    # get the connections which we are drawing and sort by connection strength
    # this will allow us to draw the strongest connections first
    con_abs = np.abs(con)
    con_draw_idx = np.where(con_abs >= con_thresh)[1]

    con = np.squeeze(con[con_abs >= con_thresh].transpose())
    con_abs = np.squeeze(con_abs[con_abs >= con_thresh].transpose())
    indices = [np.squeeze(ind[con_draw_idx].transpose()) for ind in indices]

    # now sort them
    sort_idx = np.argsort(con_abs)

    # con_abs = con_abs[0, sort_idx]
    con = con[0, sort_idx]
    indices = [np.squeeze(ind[sort_idx].transpose()) for ind in indices]

    # Get vmin vmax for color scaling
    if vmin is None:
        vmin = np.min(con[np.abs(con) >= con_thresh])
    if vmax is None:
        vmax = np.max(con)
    vrange = vmax - vmin

    # We want to add some "noise" to the start and end position of the
    # edges: We modulate the noise with the number of connections of the
    # node and the connection strength, such that the strongest connections
    # are closer to the node center
    nodes_n_con = np.zeros((n_nodes), dtype=np.int)
    for i, j in zip(indices[0], indices[1]):
        # print "i : %i / j: %i" % (i,j)
        nodes_n_con[i] += 1
        nodes_n_con[j] += 1

    # initialize random number generator so plot is reproducible
    rng = np.random.mtrand.RandomState(seed=0)

    n_con = len(indices[0])
    noise_max = 0.25 * node_width
    start_noise = rng.uniform(-noise_max, noise_max, n_con)
    end_noise = rng.uniform(-noise_max, noise_max, n_con)

    nodes_n_con_seen = np.zeros_like(nodes_n_con)
    for i, (start, end) in enumerate(zip(indices[0], indices[1])):
        nodes_n_con_seen[start] += 1
        nodes_n_con_seen[end] += 1

        start_noise[i] *= (nodes_n_con[start] - nodes_n_con_seen[start]) / float(
            nodes_n_con[start]
        )
        end_noise[i] *= (nodes_n_con[end] - nodes_n_con_seen[end]) / float(
            nodes_n_con[end]
        )

    # scale connectivity for colormap (vmin<=>0, vmax<=>1)
    con_val_scaled = (con - vmin) / vrange

    # print("con_val_scaled.shape")
    con_val_scaled = np.squeeze(con_val_scaled.transpose())

    # Finally, we draw the connections
    for pos, (i, j) in enumerate(zip(indices[0], indices[1])):
        # Start point
        t0, r0 = node_angles[i], 10

        # End point
        t1, r1 = node_angles[j], 10

        # Some noise in start and end point
        t0 += start_noise[pos]
        t1 += end_noise[pos]

        verts = [(t0, r0), (t0, 5), (t1, 5), (t1, r1)]
        codes = [
            m_path.Path.MOVETO,
            m_path.Path.CURVE4,
            m_path.Path.CURVE4,
            m_path.Path.LINETO,
        ]
        path = m_path.Path(verts, codes)

        color = colormap(con_val_scaled[0, pos])

        # Actual line
        patch = m_patches.PathPatch(
            path, fill=False, edgecolor=color, linewidth=linewidth, alpha=1.0
        )
        axes.add_patch(patch)

    # Draw ring with colored nodes
    height = np.ones(n_nodes) * 1.0
    bars = axes.bar(
        node_angles,
        height,
        width=node_width,
        bottom=9,
        edgecolor=node_edgecolor,
        lw=node_linewidth,
        facecolor=".9",
        align="center",
    )

    for bar, color in zip(bars, node_colors):
        bar.set_facecolor(color)

    # Draw node labels
    angles_deg = 180 * node_angles / np.pi
    for name, angle_rad, angle_deg in zip(node_names, node_angles, angles_deg):
        if angle_deg >= 270 or angle_deg <= 90:
            ha = "left"
        else:
            # Flip the label, so text is always upright
            angle_deg += 180
            ha = "right"

        axes.text(
            angle_rad,
            10.4,
            name,
            size=fontsize_names,
            rotation=angle_deg,
            rotation_mode="anchor",
            horizontalalignment=ha,
            verticalalignment="center",
            color=textcolor,
        )

    if title is not None:
        plt.title(title, color=textcolor, fontsize=fontsize_title, axes=axes)

    if colorbar:
        sm = plt.cm.ScalarMappable(cmap=colormap, norm=plt.Normalize(vmin, vmax))
        sm.set_array(np.linspace(vmin, vmax))
        cb = plt.colorbar(
            sm, ax=axes, use_gridspec=False, shrink=colorbar_size, anchor=colorbar_pos
        )
        cb_yticks = plt.getp(cb.ax.axes, "yticklabels")
        cb.ax.tick_params(labelsize=fontsize_colorbar)
        plt.setp(cb_yticks, color=textcolor)

    from functools import partial

    # Add callback for interaction
    if interactive:
        callback = partial(
            _plot_connectivity_circle_onpick,
            fig=fig,
            axes=axes,
            indices=indices,
            n_nodes=n_nodes,
            node_angles=node_angles,
        )

        fig.canvas.mpl_connect("button_press_event", callback)

    plt_show(show)
    return fig, axes


def main():
    """Main function that load and display the specified connectivity matrix.

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    if len(sys.argv) == 5 and os.path.exists(sys.argv[2]):
        print("read %s" % sys.argv[2])
        a = nx.read_gpickle(sys.argv[2])
        print("open %s" % sys.argv[3])
        bb = nx.to_numpy_matrix(a, weight=sys.argv[3], dtype=np.float64)

        if sys.argv[4] == "True":
            c = np.zeros(bb.shape)
            c[bb > 0] = 1
            b = c
        else:
            b = bb

        if sys.argv[1] == "matrix":
            figure()
            imshow(
                b, interpolation="nearest", cmap=cm.inferno, vmin=b.min(), vmax=b.max()
            )
            figure()
            hist(b)
            show()
        elif sys.argv[1] == "circular":
            node_names = []
            for _, d_gml in a.nodes(data=True):
                # node_names.append(d_gml['dn_fsname'])
                node_names.append(d_gml["dn_name"])
            _, _ = plot_connectivity_circle(
                b, node_names, title="%s" % (sys.argv[3]), colormap="inferno"
            )

        else:
            print("Error: invalid layout mode ('matrix' or 'circular')")
            return 1

    elif len(sys.argv) == 6 and os.path.exists(sys.argv[2]):
        print("read %s" % sys.argv[2])
        a = nx.read_gpickle(sys.argv[2])
        print("open %s" % sys.argv[3])
        bb = nx.to_numpy_matrix(a, weight=sys.argv[3], dtype=np.float64)

        if sys.argv[4] == "True":
            c = np.zeros(bb.shape)
            c[bb > 0] = 1
            b = c
        else:
            b = bb

        if sys.argv[1] == "matrix":
            figure()
            if sys.argv[3] == "number_of_fibers":
                plt.title("%s (#fibers: %i)" % (sys.argv[5], int(0.5 * b.sum())))
            else:
                plt.title("%s" % (sys.argv[5]))
            imshow(
                b, interpolation="nearest", cmap=cm.inferno, vmin=b.min(), vmax=b.max()
            )
            show()
        elif sys.argv[1] == "circular":
            node_names = []
            for _, d_gml in a.nodes(data=True):
                # node_names.append(d_gml['dn_fsname'])
                node_names.append(d_gml["dn_name"])
            if sys.argv[3] == "number_of_fibers":
                title = "%s (#fibers: %i)" % (sys.argv[5], int(0.5 * b.sum()))
            else:
                title = "%s" % (sys.argv[5])
            _, _ = plot_connectivity_circle(
                b, node_names, title=title, colormap="inferno"
            )
        else:
            print("Error: invalid layout mode ('matrix' or 'circular')")
            return 1

    elif len(sys.argv) == 7 and os.path.exists(sys.argv[2]):
        print("read %s" % sys.argv[2])
        a = nx.read_gpickle(sys.argv[2])
        print("open %s" % sys.argv[3])
        bb = nx.to_numpy_matrix(a, weight=sys.argv[3], dtype=np.float64)

        if sys.argv[4] == "True":
            c = np.zeros(bb.shape)
            c[bb > 0] = 1
            b = c
        else:
            b = bb

        if sys.argv[1] == "matrix":
            figure()
            if sys.argv[3] == "number_of_fibers":
                plt.title("%s (#fibers: %i)" % (sys.argv[5], int(0.5 * b.sum())))
            else:
                plt.title("%s" % (sys.argv[5]))
            print("sys.argv[5]==%s" % sys.argv[6])
            if sys.argv[6] == "log":
                print("log scaling...")
                my_cmap = copy.copy(
                    cm.get_cmap("inferno")
                )  # copy the default cmap (0,0,0.5156)
                my_cmap.set_bad((0, 0, 0))
                imshow(b, interpolation="nearest", norm=colors.LogNorm(), cmap=my_cmap)
                colorbar()
            else:
                print("normal scaling...")
                imshow(
                    b,
                    interpolation="nearest",
                    norm=None,
                    cmap=cm.inferno,
                    vmin=b.min(),
                    vmax=b.max(),
                )
            show()
        elif sys.argv[1] == "circular":
            node_names = []
            for _, d_gml in a.nodes(data=True):
                # node_names.append(d_gml['dn_fsname'])
                node_names.append(d_gml["dn_name"])
            if sys.argv[3] == "number_of_fibers":
                title = "%s (#fibers: %i)" % (sys.argv[5], int(0.5 * b.sum()))
            else:
                title = "%s" % (sys.argv[5])
            print("sys.argv[5]==%s" % sys.argv[6])
            if sys.argv[6] == "log":
                print("Warning: log scale not employed as circular layout used")

            _, _ = plot_connectivity_circle(
                b, node_names, title=title, colormap="inferno"
            )
        else:
            print("Error: invalid layout mode ('matrix' or 'circular')")

    return 0


if __name__ == "__main__":
    sys.exit(main())
