#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""This module defines the `cmpbidsappmanager` script that launches the Graphical User Interface."""

import sys
import os

from traits.etsconfig.api import ETSConfig

# CMP imports
from cmp.bidsappmanager import gui
from cmp.info import __version__, __copyright__

# Setup Qt5 backend for traitsui
os.environ['ETS_TOOLKIT'] = 'qt4'
# os.environ['QT_API'] = 'pyqt5'
os.environ['QT_API'] = 'pyside2'
print("Graphical Backend : {}".format(ETSConfig.toolkit))


def info():
    """Print version and copyright information."""
    print("\nConnectome Mapper {} - BIDS App Manager ".format(__version__))
    print("""{}""".format(__copyright__ ))


def usage():
    """Display usage."""
    print("Usage : cmpbidsappmanager ")


# Check software dependencies. We call directly the functions instead
# of just checking existence in $PATH in order to handle missing libraries.
# Note that not all the commands give the awaited 1 exit code...
def dep_check():
    """Check if some dependencies are well installed."""
    nul = open(os.devnull, 'w')

    error = ""

    # TODO try import all dependencies

    if error != "":
        print(error)
        sys.exit(2)


def main():
    """Main function that launches CMP3 BIDS App Manager (GUI).

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    # check dependencies
    dep_check()

    # add current directory to the path, useful if DTB_ bins not installed
    os.environ["PATH"] += os.pathsep + os.path.dirname(sys.argv[0])

    # version and copyright message
    info()

    argc = len(sys.argv)
    if argc == 1:  # no args, launch the GUI
        mw = gui.CMP_MainWindow()
        mw_res = mw.configure_traits()
        exit_code = 0
    else:
        usage()
        exit_code = 2

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
