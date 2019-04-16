""" This file contains cmp package information """

_version_major = 3
_version_minor = 0
_version_micro = 0
_version_extra = '-beta-singularity'

__release_date__ = '11.04.2017'

__minor_version__ = "%s.%s" % (_version_major,
                               _version_minor)

__version__ = "%s.%s.%s%s" % (_version_major,
                              _version_minor,
                              _version_micro,
                              _version_extra)


__author__ = 'The CMP3 developers'
__copyright__ = 'Copyright 2009-2019, Brain Communication Pathways Sinergia Consortium'
__credits__ = ('Contributors: please check the ``.zenodo.json`` file at the top-level folder'
               'of the repository')
__license__ = '3-clause BSD'
__maintainer__ = 'Sebastien Tourbier'
__email__ = 'sebastien.tourbier@alumni.epfl.ch'
__status__ = 'Prototype'
__url__ = 'https://bitbucket.org/sinergiaconsortium/connectomemapper3'
__packagename__ = 'connectomemapper3'

# DOWNLOAD_URL = (
#     'https://bitbucket.org/sinergiaconsortium/{name}/get/{ver}.tar.gz'.format(
#         name=__packagename__, ver=__version__))

DOWNLOAD_URL = (
    'https://bitbucket.org/sinergiaconsortium/{name}/get/{ver}.tar.gz'.format(
        name=__packagename__, ver=__version__))
