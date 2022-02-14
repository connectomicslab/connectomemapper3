# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions and Nipype interfaces for EEG."""
import os
import pickle

import nibabel
import numpy as np
from nipype import BaseInterface
from nipype.interfaces import io as nio
from nipype.interfaces.base import BaseInterfaceInputSpec, TraitedSpec, traits

from cmtklib.interfaces import pycartool as cart


class CreateRoisInputSpec(BaseInterfaceInputSpec):
    """Input specification for InverseSolution."""

    subject = traits.Str(
        desc='subject', mandatory=True)

    bids_dir = traits.Str(
        desc='base directory', mandatory=True)

    parcellation = traits.Str(
        desc='parcellation scheme', mandatory=True)

    cartool_dir = traits.Str(
        desc='Cartool directory', mandatory=True)

    cmp3_dir = traits.Str(
        desc='CMP3 directory', mandatory=True)

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateRoisOutputSpec(TraitedSpec):
    """Output specification for InverseSolution."""

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateRois(BaseInterface):
    input_spec = CreateRoisInputSpec
    output_spec = CreateRoisOutputSpec

    def _run_interface(self, runtime):
        subject = self.inputs.subject
        parcellation_image_path = self.inputs.parcellation
        parcellation_name = parcellation_image_path.split('/')[-1].split('.')[0]
        cartool_dir = os.path.join(self.inputs.bids_dir,'derivatives',self.inputs.cartool_dir)
        cmp3_dir = os.path.join(self.inputs.bids_dir,'derivatives',self.inputs.cmp3_dir)
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query

        self._create_roi_files(subject, parcellation_image_path, parcellation_name, cartool_dir, cmp3_dir)

        self.derivative_list.append(self.inputs.cartool_dir)

        self.output_query['rois'] = {
            # 'scope': 'cartool-v3.80',
            'extension': ['pickle.rois']
        }
        self.output_query['src'] = {
            # 'scope': 'cartool-v3.80',
            'extension': ['spi']
        }
        self.output_query['invsol'] = {
            # 'scope': 'cartool-v3.80',
            'extension': ['LAURA.is']
        }

        return runtime

    @staticmethod
    def _create_roi_files(subject, parcellation, parcellation_name, cartool_dir, cmp3_dir):
        spipath = os.path.join(cartool_dir, subject, 'eeg',subject + '_eeg.spi')
        source = cart.source_space.read_spi(spipath)

        impath = os.path.join(parcellation)
        im = nibabel.load(impath)
        imdata = im.get_fdata()
        x, y, z = np.where(imdata)
        center_brain = [np.mean(x), np.mean(y), np.mean(z)]
        source.coordinates[:, 0] = - source.coordinates[:, 0]
        source.coordinates = source.coordinates - source.coordinates.mean(0) + center_brain

        xyz = source.get_coordinates()
        xyz = np.round(xyz).astype(int)
        num_spi = len(xyz)

        # label positions
        rois_file = np.zeros(num_spi)
        x_roi, y_roi, z_roi = np.where((imdata > 0) & (imdata < np.unique(imdata)[-1]))

        # For each coordinate
        for spi_id, spi in enumerate(xyz):
            distances = ((spi.reshape(-1, 1) - [x_roi, y_roi, z_roi]) ** 2).sum(0)
            roi_id = np.argmin(distances)
            rois_file[spi_id] = imdata[x_roi[roi_id], y_roi[roi_id], z_roi[roi_id]]

        groups_of_indexes = [np.where(rois_file == roi)[0].tolist() for roi in np.unique(rois_file)]
        names = [str(int(i)) for i in np.unique(rois_file) if i != 0]

        rois_file_new = cart.regions_of_interest.RegionsOfInterest(names=names,
                                                                   groups_of_indexes=groups_of_indexes,
                                                                   source_space=source)

        rois_dir = os.path.join(cartool_dir, subject, 'eeg', 'Rois')
        if not os.path.isdir(rois_dir):
            os.mkdir(rois_dir)
        filename_pkl = os.path.join(rois_dir, parcellation_name + '.pickle.rois')
        filehandler = open(filename_pkl, 'wb')
        pickle.dump(rois_file_new, filehandler)
        filehandler.close()

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs


class EEGLoaderInputSpec(BaseInterfaceInputSpec):
    """Input specification for EEGLoader. """

    base_directory = traits.Directory(
        exists=True, desc='BIDS data directory', mandatory=True)

    subject = traits.Str(
        desc='subject', mandatory=True)

    invsol_format = traits.Enum('Cartool-LAURA', 'Cartool-LORETA', 'mne-sLORETA',
            desc='Cartool vs mne')

    output_query = traits.Dict(
        desc='output query for BIDSDataGrabber', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class EEGLoaderOutputSpec(TraitedSpec):
    """Input specification for EEGLAB2fif. """

    EEG = traits.List(
        exists=True, desc='eeg * epochs in .fif format', mandatory=True)
    src = traits.List(
        exists=True, desc='src (spi loaded with pycartool or source space created with MNE)', mandatory=True)
    invsol = traits.List(
        exists=True, desc='Inverse solution (.is file loaded with pycartool)', mandatory=False)
    rois = traits.List(
        exists=True, desc='parcellation scheme', mandatory=True)
    bem = traits.List(
        exists=True, desc='boundary surfaces for MNE head model', mandatory=False)


class EEGLoader(BaseInterface):
    input_spec = EEGLoaderInputSpec
    output_spec = EEGLoaderOutputSpec

    def _run_interface(self, runtime):
        self.base_directory = self.inputs.base_directory
        self.subject = self.inputs.subject
        self.derivative_list = self.inputs.derivative_list
        self._run_datagrabber()
        return runtime

    def _run_datagrabber(self):
        bidsdatagrabber = nio.BIDSDataGrabber(index_derivatives=False,
                                              extra_derivatives=[os.path.join(self.base_directory, 'derivatives', elem)
                                                                 for elem in self.derivative_list])
        bidsdatagrabber.inputs.base_dir = self.base_directory
        bidsdatagrabber.inputs.subject = self.subject.split('-')[1]
        bidsdatagrabber.inputs.output_query = self.inputs.output_query
        print(bidsdatagrabber.inputs.output_query)
        print(bidsdatagrabber.inputs.base_dir)
        print(bidsdatagrabber.inputs.subject)
        self.results = bidsdatagrabber.run()

    def _list_outputs(self):
        outputs = self._outputs().get()

        for key, value in self.results.outputs.get().items():
            outputs[key] = value

        return outputs