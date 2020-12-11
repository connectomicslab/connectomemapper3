# Copyright (C) 2017-2019, Brain Communication Pathways Sinergia Consortium, Switzerland
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
    from cmp.info import __version__, __url__, DOWNLOAD_URL

    bids_dir = os.path.abspath(bids_dir)
    deriv_dir = os.path.abspath(deriv_dir)

    if pipeline_name == 'cmp':
        desc = {
            'Name': 'CMP - Connectome Mapper processing workflow',
            'BIDSVersion': '1.1.1',
            'PipelineDescription': {
                'Name': 'Connectome Mapper',
                'Version': __version__,
                'CodeURL': DOWNLOAD_URL,
            },
            'CodeURL': __url__,
            'HowToAcknowledge':
                'Please cite our paper (https://doi.org/XXX), '
                'and include the generated citation boilerplate within the Methods '
                'section of the text.',
        }
    elif pipeline_name == 'freesurfer':
        desc = {
            'Name': 'CMP - Connectome Mapper processing workflow',
            'BIDSVersion': '1.1.1',
            'PipelineDescription': {
                'Name': 'Freesurfer v6.0.1 outputs of the Connectome Mapper',
                'Version': __version__,
                'CodeURL': DOWNLOAD_URL,
            },
            'CodeURL': __url__,
            'HowToAcknowledge':
                'Please cite our paper (https://doi.org/XXX), '
                'and include the generated citation boilerplate within the Methods '
                'section of the text.',
        }
    elif pipeline_name == 'nipype':
        desc = {
            'Name': 'CMP - Connectome Mapper processing workflow',
            'BIDSVersion': '1.1.1',
            'PipelineDescription': {
                'Name': 'Nipype outputs of the Connectome Mapper',
                'Version': __version__,
                'CodeURL': DOWNLOAD_URL,
            },
            'CodeURL': __url__,
            'HowToAcknowledge':
                'Please cite our paper (https://doi.org/XXX), '
                'and include the generated citation boilerplate within the Methods '
                'section of the text.',
        }
    # Keys that can only be set by environment
    if 'CMP_DOCKER_TAG' in os.environ:
        desc['DockerHubContainerTag'] = os.environ['CMP_DOCKER_TAG']
    if 'CMP_SINGULARITY_URL' in os.environ:
        singularity_url = os.environ['CMP_SINGULARITY_URL']
        desc['SingularityContainerURL'] = singularity_url

        singularity_md5 = _get_shub_version(singularity_url)
        if singularity_md5 and singularity_md5 is not NotImplemented:
            desc['SingularityContainerMD5'] = _get_shub_version(
                singularity_url)

    # Keys deriving from source dataset
    orig_desc = {}
    fname = os.path.join(bids_dir, 'dataset_description.json')
    if os.access(fname, os.R_OK):
        with open(fname, 'r') as fobj:
            orig_desc = json.load(fobj)

    if 'DatasetDOI' in orig_desc:
        desc['SourceDatasetsURLs'] = ['https://doi.org/{}'.format(
            orig_desc['DatasetDOI'])]
    if 'License' in orig_desc:
        desc['License'] = orig_desc['License']

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
