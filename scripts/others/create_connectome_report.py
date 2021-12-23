#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Syntax :
%
Description
%
Input Parameters:
%
Output Parameters:
%
%
Related references:

See also:
__________________________________________________
Authors: Sébastien Tourbier
Radiology Department
CHUV, Lausanne
Created on %(date)s
Version $1.0

======================= Importing Libraries ==============================
"""
import sys
import os
import networkx as nx
import numpy as np
import copy

import io

# try:
#     from PIL import Image
# except ImportError:
#     print("PIL not available. Can not insert matplotlib figure inside the PDF. Please install it (conda install pil)")

try:
    import matplotlib.colors as colors
    # import matplotlib
    # matplotlib.use('Agg') # Must be before importing matplotlib.pyplot or pylab!
    from matplotlib.pyplot import title, suptitle, imshow, cm, figure, colorbar
except ImportError:
    print("matplotlib not available. Can not plot matrix")

try:
    from reportlab.pdfgen import canvas
    # from reportlab.lib.pagesizes import letter
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
except ImportError:
    print("reportlab not available. Can not generate PDF report")

try:
    from bids import BIDSLayout
except ImportError:
    print("BIDS not available. Can not read BIDS dataset")

from cmtklib.bids.io import __cmp_directory__

"""
====================End of Importing Libraries ===========================

"""


def main(bids_dir):
    """ Extract CMP3 connectome in a bids dataset and create PDF report"""

    # Read BIDS dataset
    try:
        bids_layout = BIDSLayout(bids_dir)
        print("BIDS: %s" % bids_layout)

        subjects = []
        for subj in bids_layout.get_subjects():
            subjects.append('sub-' + str(subj))

        print("Available subjects : ")
        print(subjects)

    except Exception:
        print(
            "BIDS ERROR: Invalid BIDS dataset. Please see documentation for more details.")
        sys.exit(1)

    c = canvas.Canvas(os.path.join(bids_dir, 'derivatives',
                                   __cmp_directory__, 'report.pdf'), pagesize=A4)
    width, height = A4

    print("Page size : %s x %s" % (width, height))

    startY = 841.89 - 50

    c.drawString(245, startY, 'Report')
    c.drawString(10, startY - 20, 'BIDS : %s ' % bids_dir)

    offset = 0
    for subj in bids_layout.get_subjects():
        print("Processing %s..." % subj)

        sessions = bids_layout.get(
            target='session', return_type='id', subject=subj)
        if len(sessions) > 0:
            print("Warning: multiple sessions")
            for ses in sessions:
                gpickle_fn = os.path.join(bids_dir, 'derivatives', __cmp_directory__, 'sub-' + str(subj), 'ses-' + str(ses), 'dwi',
                                          'sub-%s_ses-%s_label-L2008_res-scale1_conndata-snetwork_connectivity.gpickle' % (str(subj), str(ses)))
                if os.path.isfile(gpickle_fn):
                    # c.drawString(10,20+offset,'Subject: %s / Session: %s '%(str(subj),str(sess)))
                    G = nx.read_gpickle(gpickle_fn)
                    con_metric = 'number_of_fibers'
                    con = nx.to_numpy_matrix(
                        G, weight=con_metric, dtype=np.float64)

                    fig = figure(figsize=(8, 8))
                    suptitle('Subject: %s / Session: %s ' %
                             (str(subj), str(ses)), fontsize=11)
                    title('Connectivity metric: %s' % con_metric, fontsize=10)
                    # copy the default cmap (0,0,0.5156)
                    my_cmap = copy.copy(cm.get_cmap('inferno'))
                    my_cmap.set_bad((0, 0, 0))
                    imshow(con, interpolation='nearest',
                           norm=colors.LogNorm(), cmap=my_cmap)
                    colorbar()

                    imgdata = io.StringIO()
                    fig.savefig(imgdata, format='png')
                    imgdata.seek(0)  # rewind the data

                    Image = ImageReader(imgdata)
                    posY = startY - 20 - 4.5 * inch - offset
                    c.drawImage(Image, 10, posY, 4 * inch, 4 * inch)

                    offset += 4.5 * inch
                    if posY - offset < 0:
                        c.showPage()
                        offset = 0

        else:
            print("No session")
            gpickle_fn = os.path.join(bids_dir, 'derivatives', __cmp_directory__, 'sub-' + str(subj), 'connectivity',
                                      'sub-%s_label-L2008_res-scale1_conndata-snetwork_connectivity.gpickle' % (
                                          str(subj)))
            if os.path.isfile(gpickle_fn):
                # c.drawString(10,20+offset,'Subject : %s '%str(subj))
                G = nx.read_gpickle(gpickle_fn)
                con_metric = 'number_of_fibers'
                con = nx.to_numpy_matrix(
                    G, weight=con_metric, dtype=np.float64)

                fig = figure(figsize=(8, 8))
                suptitle('Subject: %s ' % (str(subj)), fontsize=11)
                title('Connectivity metric: %s' % con_metric, fontsize=10)
                # copy the default cmap (0,0,0.5156)
                my_cmap = copy.copy(cm.get_cmap('inferno'))
                my_cmap.set_bad((0, 0, 0))
                imshow(con, interpolation='nearest',
                       norm=colors.LogNorm(), cmap=my_cmap)
                colorbar()

                imgdata = io.StringIO()
                fig.savefig(imgdata, format='png')
                imgdata.seek(0)  # rewind the data

                Image = ImageReader(imgdata)
                posY = startY - 20 - 4.5 * inch - offset
                c.drawImage(Image, 10, posY, 4 * inch, 4 * inch)

                offset += 4.5 * inch
                if posY - offset < 0:
                    c.showPage()
                    offset = 0

    c.save()


if __name__ == "__main__":
    main(sys.argv[1])
