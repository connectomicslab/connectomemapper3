"""This file contains cmp package information."""

_version_major = 3
_version_minor = 0
_version_micro = 0
_version_extra = '-RC2'
__release_date__ = '24.12.2020'

__minor_version__ = "%s.%s" % (_version_major,
                               _version_minor)

__version__ = "v%s.%s.%s%s" % (_version_major,
                               _version_minor,
                               _version_micro,
                               _version_extra)

# __current_year__ = datetime.datetime.now().strftime("%Y")
__current_year__ = '2020'

__author__ = 'The CMP3 developers'

__copyright__ = """Copyright (C) 2009-{}, Ecole Polytechnique Federale de Lausanne (EPFL)
                the University Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland,\n& Contributors\n
                All rights reserved.\n""".format(__current_year__)

__credits__ = ('Contributors: please check the ``.zenodo.json`` file at the top-level folder'
               'of the repository')
__license__ = '3-clause BSD'
__maintainer__ = 'Sebastien Tourbier'
__email__ = 'sebastien.tourbier@alumni.epfl.ch'
__status__ = 'Prototype'

__packagename__ = 'connectomemapper3'

__url__ = 'https://github.com/connectomicslab/{name}'.format(
    name=__packagename__)

DOWNLOAD_URL = (
    'https://github.com/connectomicslab/{name}/archive/{ver}.tar.gz'.format(
        name=__packagename__, ver=__version__))

# DOWNLOAD_URL = (
#     'https://bitbucket.org/sinergiaconsortium/{name}/get/{ver}.tar.gz'.format(
#         name=__packagename__, ver=__version__))
