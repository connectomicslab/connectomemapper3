# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""The PyCartool module provides Nipype interfaces with Cartool using pycartool."""

# General imports
import os
import pickle
import nibabel
import numpy as np
import scipy.io as sio

# Nipype imports
from nipype.interfaces.base import (
    BaseInterface, BaseInterfaceInputSpec,
    TraitedSpec, traits
)

# EEG package imports
import mne
import pycartool as cart


class CartoolInverseSolutionROIExtractionInputSpec(BaseInterfaceInputSpec):
    epochs_file = traits.File(
        exists=True, desc='eeg * epochs in .set format', mandatory=True)

    invsol_file = traits.File(
        exists=True, desc='Inverse solution (.is file loaded with pycartool)', mandatory=True)

    mapping_spi_rois_file = traits.File(
        exists=True,
        desc='Cartool-reconstructed sources / parcellation ROI mapping file, loaded with pickle',
        mandatory=True
    )

    lamb = traits.Int(6, desc='Regularization weight')

    svd_toi_begin = traits.Float(0, desc='Start TOI for SVD projection')

    svd_toi_end = traits.Float(0.25, desc='End TOI for SVD projection')

    out_roi_ts_fname_prefix = traits.Str(
        exists=False,
        desc="Output name prefix (no extension) for rois * time series files",
        mandatory=True
    )


class CartoolInverseSolutionROIExtractionOutputSpec(TraitedSpec):
    roi_ts_npy_file = traits.File(desc="Path to output  ROI time series file in .npy format")
    roi_ts_mat_file = traits.File(desc="Path to output  ROI time series file in .mat format")


class CartoolInverseSolutionROIExtraction(BaseInterface):
    """Use Pycartool to load inverse solutions estimated by Cartool.

    Examples
    --------
    >>> from cmtklib.interfaces.pycartool import CartoolInverseSolutionROIExtraction
    >>> cartool_inv_sol = CartoolInverseSolutionROIExtraction()
    >>> cartool_inv_sol.inputs.epochs_file = 'sub-01_task-faces_desc-preproc_eeg.set'
    >>> cartool_inv_sol.inputs.invsol_file = 'sub-01_eeg.LORETA.is'
    >>> cartool_inv_sol.inputs.mapping_spi_rois_file = 'sub-01_atlas-L2018_res-scale1.pickle.rois'
    >>> cartool_inv_sol.inputs.lamd = 6
    >>> cartool_inv_sol.inputs.svd_toi_begin = 0
    >>> cartool_inv_sol.inputs.svd_toi_end = 0.25
    >>> cartool_inv_sol.inputs.out_roi_ts_fname_prefix = 'sub-01_task-faces_atlas-L2008_res-scale1_rec-LORETA_timeseries'
    >>> cartool_inv_sol.run()  # doctest: +SKIP

    References
    ----------
    - https://pycartool.readthedocs.io/en/latest/pycartool.io.html#module-pycartool.io.inverse_solution

    """

    input_spec = CartoolInverseSolutionROIExtractionInputSpec
    output_spec = CartoolInverseSolutionROIExtractionOutputSpec

    def _run_interface(self, runtime):
        svd_params = {
            "toi_begin": self.inputs.svd_toi_begin,
            "toi_end": self.inputs.svd_toi_end
        }
        roi_tcs = self.apply_inverse_epochs_cartool(
            self.inputs.epochs_file,
            self.inputs.invsol_file,
            self.inputs.lamb,
            self.inputs.mapping_spi_rois_file,
            svd_params
        )
        np.save(self._gen_output_filename_roi_ts(extension=".npy"), roi_tcs)
        sio.savemat(self._gen_output_filename_roi_ts(extension=".mat"), {"ts": roi_tcs})
        return runtime

    @staticmethod
    def apply_inverse_epochs_cartool(epochs_file, invsol_file, lamda, rois_file, svd_params):
        epochs = mne.read_epochs(epochs_file)
        invsol = cart.io.inverse_solution.read_is(invsol_file)
        pickle_in = open(rois_file, "rb")
        rois = pickle.load(pickle_in)
        print(f'  .. DEBUG: Invsol loaded = {invsol}')
        mat_k = invsol['regularisation_solutions'][lamda]
        n_rois = len(rois.names)
        times = epochs.times
        tstep = times[1] - times[0]
        roi_tcs = np.zeros((n_rois, len(times), len(epochs.events)))
        n_spi = np.zeros(n_rois, dtype=int)
        for r in range(n_rois):
            spis_this_roi = rois.groups_of_indexes[r]
            n_spi[r] = int(len(spis_this_roi))
            roi_stc = np.zeros((3, n_spi[r], len(times), len(epochs.events)))

            for k, e in enumerate(epochs):
                # logger.info('Processing epoch : %d%s' % (k + 1, total))
                roi_stc[0, :, :, k] = mat_k[0, spis_this_roi] @ e
                roi_stc[1, :, :, k] = mat_k[1, spis_this_roi] @ e
                roi_stc[2, :, :, k] = mat_k[2, spis_this_roi] @ e

            stim_onset = np.where(times == 0)[0][0]
            svd_t_begin = stim_onset + int(svd_params['toi_begin'] / tstep)
            svd_t_end = stim_onset + int(svd_params['toi_end'] / tstep)

            mean_roi_stc = np.mean(roi_stc[:, :, svd_t_begin:svd_t_end, :], axis=3)
            u1, _, _ = np.linalg.svd(mean_roi_stc.reshape(3, -1))

            tc_loc = np.zeros((len(times), n_spi[r], len(epochs.events)))

            for k in range(n_spi[r]):
                for e in range(len(epochs.events)):
                    tc_loc[:, k, e] = u1[:, 0].reshape(1, 3) @ roi_stc[:, k, :, e]

            roi_tcs[r, :, :] = np.mean(tc_loc, axis=1)

        return roi_tcs.transpose(2, 0, 1)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["roi_ts_npy_file"] = self._gen_output_filename_roi_ts(extension=".npy")
        outputs["roi_ts_mat_file"] = self._gen_output_filename_roi_ts(extension=".mat")
        return outputs

    def _gen_output_filename_roi_ts(self, extension):
        # Return the absolute path of the output ROI time series file
        return os.path.abspath(self.inputs.out_roi_ts_fname_prefix + extension)


class CreateSpiRoisMappingInputSpec(BaseInterfaceInputSpec):
    roi_volume_file = traits.File(exits=True, desc="Parcellation file in nifti format", mandatory=True)

    spi_file = traits.File(exits=True, desc="Cartool reconstructed sources file in spi format", mandatory=True)

    out_mapping_spi_rois_fname = traits.Str(
        desc="Name of output sources / parcellation ROI mapping file in .pickle.rois format",
        mandatory=True
    )


class CreateSpiRoisMappingOutputSpec(TraitedSpec):
    mapping_spi_rois_file = traits.File(
        desc="Path to output Cartool-reconstructed sources / parcellation ROI mapping file "
             "in .pickle.rois format"
    )


class CreateSpiRoisMapping(BaseInterface):
    """Create Cartool-reconstructed sources / parcellation ROI mapping file.

    Examples
    --------
    >>> from cmtklib.interfaces.pycartool import CreateSpiRoisMapping
    >>> createrois = CreateSpiRoisMapping()
    >>> createrois.inputs.roi_volume_file = '/path/to/sub-01_atlas-L2018_res-scale1_dseg.nii.gz'
    >>> createrois.inputs.spi_file = '/path/to/sub-01_eeg.spi'
    >>> createrois.inputs.out_mapping_spi_rois_fname = 'sub-01_atlas-L2018_res-scale1_eeg.pickle.rois'
    >>> createrois.run()  # doctest: +SKIP

    """

    input_spec = CreateSpiRoisMappingInputSpec
    output_spec = CreateSpiRoisMappingOutputSpec

    def _run_interface(self, runtime):
        mapping_spi_roi = self._create_mapping_spi_rois(
            self.inputs.roi_volume_file,
            self.inputs.spi_file
        )

        with open(self._gen_output_filename_mapping_spi_rois(), "wb") as f:
            pickle.dump(mapping_spi_roi, f)

        return runtime

    @staticmethod
    def _create_mapping_spi_rois(roi_volume_file, spi_file):
        # Load input parcellation and spi files
        source = cart.source_space.read_spi(spi_file)
        imdata = nibabel.load(roi_volume_file).get_fdata()

        x, y, z = np.where(imdata)
        center_brain = [np.mean(x), np.mean(y), np.mean(z)]
        source.coordinates[:, 0] = -source.coordinates[:, 0]
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

        mapping_spi_roi = cart.regions_of_interest.RegionsOfInterest(
            names=names, groups_of_indexes=groups_of_indexes, source_space=source
        )

        return mapping_spi_roi

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["mapping_spi_rois_file"] = self._gen_output_filename_mapping_spi_rois()
        return outputs

    def _gen_output_filename_mapping_spi_rois(self):
        # Return the absolute path of the output inverse operator file
        return os.path.abspath(self.inputs.out_mapping_spi_rois_fname)
