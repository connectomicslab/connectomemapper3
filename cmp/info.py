# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""This file contains cmp package information."""

_version_major = 3
_version_minor = 0
_version_micro = 1
_version_extra = ""
__release_date__ = "05.01.2022"

__minor_version__ = "%s.%s" % (_version_major, _version_minor)

__version__ = "v%s.%s.%s%s" % (
    _version_major,
    _version_minor,
    _version_micro,
    _version_extra,
)

# __current_year__ = datetime.datetime.now().strftime("%Y")
__current_year__ = "2021"

__author__ = "The CMP3 developers"

__copyright__ = (
    "Copyright (C) 2009-{}, ".format(__current_year__)
    + "Ecole Polytechnique Federale de Lausanne (EPFL) "
    + "the University Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, "
    + "and Contributors, All rights reserved."
)

__credits__ = (
    "Contributors: please check the ``.zenodo.json`` file at the top-level folder"
    "of the repository"
)
__license__ = "3-clause BSD"
__maintainer__ = "Sebastien Tourbier"
__email__ = "sebastien.tourbier@alumni.epfl.ch"
__status__ = "Prototype"

__packagename__ = "connectomemapper3"

__url__ = "https://github.com/connectomicslab/{name}/tree/{version}".format(
    name=__packagename__, version=__version__
)

DOWNLOAD_URL = "https://github.com/connectomicslab/{name}/archive/{ver}.tar.gz".format(
    name=__packagename__, ver=__version__
)

DOCKER_HUB = "sebastientourbier/connectomemapper-bidsapp"
