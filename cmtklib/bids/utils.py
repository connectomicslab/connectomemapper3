# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This modules provides CMTK Utility functions to handle BIDS datasets."""

import os
import json


def write_derivative_description(bids_dir, deriv_dir, pipeline_name):
    """Write a dataset_description.json in each type of CMP derivatives.

    Parameters
    ----------
    bids_dir : string
        BIDS root directory

    deriv_dir : string
        Output/derivatives directory

    pipeline_name : string
        Type of derivatives (`['cmp', 'freesurfer', 'nipype']`)
    """
    from cmp.info import __version__, __url__, DOCKER_HUB

    bids_dir = os.path.abspath(bids_dir)
    deriv_dir = os.path.abspath(deriv_dir)

    if pipeline_name == 'cmp':
        desc = {
            'Name': 'CMP3 Outputs',
            'BIDSVersion': '1.4.0',
            'DatasetType': 'derivatives',
            'GeneratedBy': {
                    'Name': pipeline_name,
                    'Version': __version__,
                    'Container': {
                            'Type': 'docker',
                            'Tag': '{}:{}'.format(DOCKER_HUB, __version__)
                    },
                    'CodeURL': __url__
            },
            'HowToAcknowledge': 'Please cite ... ',
        }
    elif pipeline_name == 'freesurfer':
        desc = {
                'Name': 'Freesurfer Outputs of CMP3 ({})'.format(__version__),
                'BIDSVersion': '1.4.0',
                'DatasetType': 'derivatives',
                'GeneratedBy': {
                        'Name': 'freesurfer',
                        'Version': '6.0.1',
                        'Container': {
                                'Type': 'docker',
                                'Tag': '{}:{}'.format(DOCKER_HUB, __version__)
                        },
                        'CodeURL': __url__
                },
                'HowToAcknowledge': 'Please cite ... '
        }
    elif pipeline_name == 'nipype':
        from nipype import __version__ as nipype_version
        desc = {
                'Name': 'Nipype Outputs of CMP3 ({})'.format(__version__),
                'BIDSVersion': '1.4.0',
                'DatasetType': 'derivatives',
                'GeneratedBy': {
                        'Name': pipeline_name,
                        'Version': nipype_version,
                        'Container': {
                                'Type': 'docker',
                                'Tag': '{}:{}'.format(DOCKER_HUB, __version__)
                        },
                        'CodeURL': __url__
                },
                'HowToAcknowledge': 'Please cite ... '
        }

    # Keys that can only be set by environment
    # if 'CMP_DOCKER_TAG' in os.environ:
    #     desc['DockerHubContainerTag'] = os.environ['CMP_DOCKER_TAG']
    # if 'CMP_SINGULARITY_URL' in os.environ:
    #     singularity_url = os.environ['CMP_SINGULARITY_URL']
    #     desc['SingularityContainerURL'] = singularity_url

    #     singularity_md5 = _get_shub_version(singularity_url)
    #     if singularity_md5 and singularity_md5 is not NotImplemented:
    #         desc['SingularityContainerMD5'] = _get_shub_version(
    #             singularity_url)

    # Keys deriving from source dataset
    orig_desc = {}
    fname = os.path.join(bids_dir, 'dataset_description.json')
    if os.access(fname, os.R_OK):
        with open(fname, 'r') as fobj:
            orig_desc = json.load(fobj)

    if 'DatasetDOI' in orig_desc:
        desc['SourceDatasets']: [
            {
                'DOI': orig_desc['DatasetDOI'],
                'URL': 'https://doi.org/{}'.format(orig_desc['DatasetDOI']),
                'Version': 'TODO: To be updated'
            }
        ]
    else:
        desc['SourceDatasets']: [
            {
                'DOI': 'TODO: To be updated',
                'URL': 'TODO: To be updated',
                'Version': 'TODO: To be updated'
            }
        ]

    desc['License'] = 'TODO: To be updated (See https://creativecommons.org/about/cclicenses/)'

    with open(os.path.join(deriv_dir, pipeline_name, 'dataset_description.json'), 'w') as fobj:
        json.dump(desc, fobj, indent=4)


def _get_shub_version(singularity_url):
    """Get singularity_md5 from URL.

    .. note::
        Not implemented yet

    Parameters
    ----------
    singularity_url : url
        URL to image on singularity hub

    """
    return NotImplemented
