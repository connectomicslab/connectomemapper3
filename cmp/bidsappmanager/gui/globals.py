# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Modules that defines multiple variables and functions used by the different windows of the GUI."""

import os
from pyface.api import ImageResource

# Remove warnings visible whenever you import scipy (or another package)
# that was compiled against an older numpy than is installed.
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


# global modal_width
modal_width = 400

# global style_sheet
style_sheet = """
        QLabel {
            font: 12pt "Verdana";
            margin-left: 5px;
            background-color: transparent;
        }
        QPushButton {
            border: 0px solid lightgray;
            border-radius: 4px;
            color: transparent;
            background-color: transparent;
            min-width: 222px;
            icon-size: 222px;
            font: 12pt "Verdana";
            margin: 0px 0px 0px 0px;
            padding:0px 0px;
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #dadbde, stop: 1 #f6f7fa);
        }
        QMenuBar {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #dadbde, stop: 1 #f6f7fa)
            font: 14pt "Verdana";
        }
        QMenuBar::item {
            spacing: 5px; /* spacing between menu bar items */
            padding: 5px 5px;
            background: transparent;
            border-radius: 4px;
        }
        QMenuBar::item:selected { /* when selected using mouse or keyboard */
            background: #a8a8a8;
        }
        QMenuBar::item:pressed {
            background: #888888;
        }
        QMainWindow {
            background-color: yellow;
            image: url("images/cmp.png");
        }
        QMainWindow::separator {
            background: yellow;
            width: 1px; /* when vertical */
            height: 1px; /* when horizontal */
        }
        QMainWindow::separator:hover {
            background: red;
        }

        QListView::item:selected {
            border: 1px solid #6a6ea9;
        }

        QListView::item:selected:!active {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #ABAFE5, stop: 1 #8588B2);
        }

        QListView::item:selected:active {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #6a6ea9, stop: 1 #888dd9);
        }

        QListView::item:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #FAFBFE, stop: 1 #DCDEF1);
        }
        QProgressBar {
            border: 2px solid grey;
            border-radius: 5px;
        }

        QProgressBar::chunk {
            background-color: #05B8CC;
            width: 20px;
        }
        """


def get_icon(path):
    """Return an instance of `ImageResource` or None is there is not graphical backend.

    Parameters
    ----------
    path : string
        Path to an image file

    Returns
    -------
    icon : ImageResource
        Return an instance of `ImageResource` or None is there is not graphical backend.
    """
    on_rtd = os.environ.get("READTHEDOCS") == "True"
    if on_rtd:
        print("READTHEDOCS: Return None for icon")
        icon = None
    else:
        icon = ImageResource(path)
    return icon
