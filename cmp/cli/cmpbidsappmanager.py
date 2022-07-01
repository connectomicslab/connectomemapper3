# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""This module defines the `cmpbidsappmanager` script that launches the Graphical User Interface."""

import platform
import os
import sys
import warnings
from distutils.version import StrictVersion
from pathlib import Path
import subprocess

# Setup Qt5 backend for traitsui
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = "qt"  # pylint: disable=E402 # noqa
os.environ["ETS_TOOLKIT"] = "qt"  # pylint: disable=E402 # noqa
os.environ['QT_API'] = 'pyqt5'  # pylint: disable=E402 # noqa

from PyQt5.QtCore import (
    QT_VERSION_STR,
    PYQT_VERSION_STR
)

# CMP imports
from cmp.info import __version__, __copyright__
from cmtklib.util import print_warning
import cmp.bidsappmanager.gui.principal


def _info():
    """Print version and copyright information."""
    print("\nConnectome Mapper {} - BIDS App Manager ".format(__version__))
    print_warning("------------------------------------------------------")
    print_warning("""{}""".format(__copyright__))
    print_warning("------------------------------------------------------")
    print("------------------------------------------------------")
    print(f"  .. INFO: Use {ETSConfig.toolkit} ({QT_VERSION_STR}) / "
          f"{os.environ['QT_API']} ({PYQT_VERSION_STR}) for graphical backend")
    print("------------------------------------------------------\n")


def _usage():
    """Display usage."""
    print("Usage : cmpbidsappmanager ")


# Check software dependencies. We call directly the functions instead
# of just checking existence in $PATH in order to handle missing libraries.
# Note that not all the commands give the awaited 1 exit code...
def _dep_check():
    """Check if some dependencies are well installed."""
    # nul = open(os.devnull, 'w')

    error = ""

    # TODO try import all dependencies

    if error != "":
        print(error)
        sys.exit(2)


def _run_pythonw(python_path):
    """Execute this script again through pythonw (MacOSX).

    This can be used to ensure we're using a framework
    build of Python on macOS, which fixes frozen menubar issues.

    Code adapted from BSD 3-clause license Napari project
    (https://github.com/napari/).

    Changes:

      * Imports were moved to beginning of file.

      * `cmd = [python_path, __file__]` instead of
        `cmd = [python_path, '-m', 'napari']`.

    Parameters
    ----------
    python_path : pathlib.Path
        Path to python framework build.

    References
    ----------
    * https://github.com/napari/napari/pull/1554/files
    """
    cwd = Path.cwd()
    cmd = [python_path, __file__]
    env = os.environ.copy()

    # Append command line arguments.
    if len(sys.argv) > 1:
        cmd.append(*sys.argv[1:])

    result = subprocess.run(cmd, env=env, cwd=cwd)
    sys.exit(result.returncode)


def main():
    """Main function that launches CMP3 BIDS App Manager (GUI).

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    # Ensure we're always using a "framework build" on the latest
    # macOS to ensure menubar works without needing to refocus cmpbidsappmanager.
    # This code is extracted from the BSD 3-clause licensed Napari project.
    # where they tried this for macOS later than the Catalina release
    # See https://github.com/napari/napari/pull/1554 and
    # https://github.com/napari/napari/issues/380#issuecomment-659656775
    # and https://github.com/ContinuumIO/anaconda-issues/issues/199
    _MACOS_LATEST = sys.platform == "darwin" and StrictVersion(
        platform.release()
    ) > StrictVersion('19.0.0')
    _RUNNING_CONDA = "CONDA_PREFIX" in os.environ
    _RUNNING_PYTHONW = "PYTHONEXECUTABLE" in os.environ

    if _MACOS_LATEST and _RUNNING_CONDA and not _RUNNING_PYTHONW:
        python_path = Path(sys.exec_prefix) / 'bin' / 'pythonw'

        if python_path.exists():
            # Required for macOS Big Sur: https://stackoverflow.com/a/64878899
            os.environ["QT_MAC_WANTS_LAYER"] = "1"
            # Running again with pythonw will exit this script
            # and use the framework build of python.
            _run_pythonw(python_path)
        else:
            msg = (
                'pythonw executable not found.\n'
                'To unfreeze the menubar on macOS, '
                'click away from cmpbidsappmanager window to another app, '
                'then reactivate cmpbidsappmanager. To avoid this problem, '
                'please install python.app in the py37cmp-gui conda environment using:\n'
                'conda install -c conda-forge python.app'
            )
            warnings.warn(msg)

    # Check dependencies
    _dep_check()

    # Add current directory to the path
    os.environ["PATH"] += os.pathsep + os.path.dirname(sys.argv[0])

    # Version and copyright message
    _info()

    argc = len(sys.argv)
    if argc == 1:  # No args, launch the GUI
        mw = cmp.bidsappmanager.gui.principal.MainWindow()
        _ = mw.configure_traits()
        exit_code = 0
    else:
        _usage()
        exit_code = 2

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
