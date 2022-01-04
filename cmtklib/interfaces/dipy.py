# -*- coding: utf-8 -*-
# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""The Dipy module provides Nipype interfaces to the algorithms in dipy."""

import os.path as op
from future import standard_library
import time
import gzip
import nibabel as nib
import numpy as np

from nipype.interfaces.dipy.base import DipyDiffusionInterface, DipyBaseInterface, DipyBaseInterfaceInputSpec
from nipype.interfaces.base import TraitedSpec, File, traits, isdefined, BaseInterfaceInputSpec, InputMultiPath
from nipype import logging


standard_library.install_aliases()
IFLOGGER = logging.getLogger('nipype.interface')


class DTIEstimateResponseSHInputSpec(DipyBaseInterfaceInputSpec):
    in_mask = File(
        exists=True, desc='input mask in which we find single fibers')
    fa_thresh = traits.Float(
        0.7, usedefault=True, desc='FA threshold')
    roi_radius = traits.Int(
        10, usedefault=True, desc='ROI radius to be used in auto_response')
    auto = traits.Bool(
        xor=['recursive'], desc='use the auto_response estimator from dipy')
    recursive = traits.Bool(
        xor=['auto'], desc='use the recursive response estimator from dipy')
    response = File(
        'response.txt', usedefault=True, desc='the output response file')
    out_mask = File('wm_mask.nii.gz', usedefault=True, desc='computed wm mask')


class DTIEstimateResponseSHOutputSpec(TraitedSpec):
    response = File(exists=True, desc='the response file')
    dti_model = File(exists=True, desc='DTI model object')
    out_mask = File(exists=True, desc='output wm mask')
    fa_file = File(exists=True)
    md_file = File(exists=True)
    rd_file = File(exists=True)
    ad_file = File(exists=True)


class DTIEstimateResponseSH(DipyDiffusionInterface):
    """Uses dipy to compute the single fiber response to be used by spherical deconvolution methods.

    The single fiber response is computed in a similar way to MRTrix's command
        ``estimate_response``.

    Example
    -------
    >>> from cmtklib.interfaces.dipy import DTIEstimateResponseSH
    >>> dti = DTIEstimateResponseSH()
    >>> dti.inputs.in_file = '4d_dwi.nii'
    >>> dti.inputs.in_bval = 'bvals'
    >>> dti.inputs.in_bvec = 'bvecs'
    >>> res = dti.run()  # doctest: +SKIP

    """

    input_spec = DTIEstimateResponseSHInputSpec
    output_spec = DTIEstimateResponseSHOutputSpec

    def _run_interface(self, runtime):
        # from dipy.core.gradients import GradientTable
        from dipy.reconst.dti import fractional_anisotropy, mean_diffusivity, TensorModel
        from dipy.reconst.csdeconv import recursive_response, auto_response

        import pickle as pickle

        img = nib.load(self.inputs.in_file)
        imref = nib.four_to_three(img)[0]
        affine = img.affine

        if isdefined(self.inputs.in_mask):
            msk = nib.load(self.inputs.in_mask).get_data()
            msk[msk > 0] = 1
            msk[msk < 0] = 0
        else:
            msk = np.ones(imref.shape)

        data = img.get_data().astype(np.float32)
        gtab = self._get_gradient_table()

        # Fit it
        tenmodel = TensorModel(gtab, fit_method='WLS')
        ten_fit = tenmodel.fit(data, msk)

        f = gzip.open(self._gen_filename('tenmodel', ext='.pklz'), 'wb')
        pickle.dump(tenmodel, f, -1)
        f.close()

        FA = np.nan_to_num(fractional_anisotropy(ten_fit.evals)) * msk
        indices = np.where(FA > self.inputs.fa_thresh)
        S0s = data[indices][:, np.nonzero(gtab.b0s_mask)[0]]
        S0 = np.mean(S0s)

        if self.inputs.auto:
            response, ratio = auto_response(gtab, data,
                                            roi_radius=self.inputs.roi_radius,
                                            fa_thr=self.inputs.fa_thresh)
            response = response[0].tolist() + [S0]
        elif self.inputs.recursive:
            MD = np.nan_to_num(mean_diffusivity(ten_fit.evals)) * msk
            indices = np.logical_or(
                FA >= 0.4, (np.logical_and(FA >= 0.15, MD >= 0.0011)))
            data = nib.load(self.inputs.in_file).get_data()
            response = recursive_response(gtab, data, mask=indices, sh_order=8,
                                          peak_thr=0.01, init_fa=0.08,
                                          init_trace=0.0021, iter=8,
                                          convergence=0.001,
                                          parallel=True)
            ratio = abs(response[1] / response[0])
        else:
            lambdas = ten_fit.evals[indices]
            l01 = np.sort(np.mean(lambdas, axis=0))

            response = np.array([l01[-1], l01[-2], l01[-2], S0])
            ratio = abs(response[1] / response[0])

        if ratio > 0.25:
            IFLOGGER.warn(('Estimated response is not prolate enough. '
                           'Ratio=%0.3f.') % ratio)
        elif ratio < 1.e-5 or np.any(np.isnan(response)):
            response = np.array([1.8e-3, 3.6e-4, 3.6e-4, S0])
            IFLOGGER.warn(
                    'Estimated response is not valid, using a default one')
        else:
            IFLOGGER.info('Estimated response: %s' % str(response[:3]))

        np.savetxt(op.abspath(self.inputs.response), response)

        wm_mask = np.zeros_like(FA)
        wm_mask[indices] = 1
        nib.Nifti1Image(
            wm_mask.astype(np.uint8), affine,
            None).to_filename(op.abspath(self.inputs.out_mask))

        IFLOGGER.info('Affine :')
        IFLOGGER.info(affine)

        # FA MD RD and AD
        for metric in ["fa", "md", "rd", "ad"]:

            if metric == "fa":
                data = FA.astype("float32")
            else:
                data = getattr(ten_fit, metric).astype("float32")

            out_name = self._gen_filename(metric)
            nib.Nifti1Image(data, affine).to_filename(out_name)
            IFLOGGER.info('DTI {metric} image saved as {i}'.format(
                i=out_name, metric=metric))
            IFLOGGER.info('Shape :')
            IFLOGGER.info(data.shape)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['response'] = op.abspath(self.inputs.response)
        outputs['dti_model'] = self._gen_filename('tenmodel', ext='.pklz')
        outputs['out_mask'] = op.abspath(self.inputs.out_mask)

        for metric in ["fa", "md", "rd", "ad"]:
            outputs["{}_file".format(metric)] = self._gen_filename(metric)
        return outputs


class CSDInputSpec(DipyBaseInterfaceInputSpec):
    in_mask = File(exists=True, desc='input mask in which compute tensors')
    response = File(exists=True, desc='single fiber estimated response')
    fa_thresh = traits.Float(0.7, usedefault=True,
                             desc='FA threshold used for response estimation')
    sh_order = traits.Int(8, usedefault=True,
                          desc='maximal shperical harmonics order')
    save_fods = traits.Bool(True, usedefault=True,
                            desc='save fODFs in file')
    save_shm_coeff = traits.Bool(True, usedefault=True,
                                 desc='save Spherical Harmonics Coefficients in file')
    tracking_processing_tool = traits.Enum("mrtrix", "dipy")
    out_fods = File(desc='fODFs output file name')
    out_shm_coeff = File(
        desc='Spherical Harmonics Coefficients output file name')


class CSDOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the CSD model fitted.')
    out_fods = File(desc='fODFs output file name')
    out_shm_coeff = File(
        desc='Spherical Harmonics Coefficients output file name')


class CSD(DipyDiffusionInterface):
    """Uses CSD [Tournier2007]_ to generate the fODF of DWIs.

    The interface uses :py:mod:`dipy`, as explained in
        `dipy's CSD example <http://nipy.org/dipy/examples_built/reconst_csd.html>`_.

    References
    ----------
    .. [Tournier2007] Tournier, J.D., et al. NeuroImage 2007.
      Robust determination of the fibre orientation distribution in diffusion
      MRI: Non-negativity constrained super-resolved spherical deconvolution

    Example
    -------
    >>> from cmtklib.interfaces.dipy import CSD
    >>> csd = CSD()
    >>> csd.inputs.in_file = '4d_dwi.nii'
    >>> csd.inputs.in_bval = 'bvals'
    >>> csd.inputs.in_bvec = 'bvecs'
    >>> res = csd.run()  # doctest: +SKIP

    """

    input_spec = CSDInputSpec
    output_spec = CSDOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst.csdeconv import ConstrainedSphericalDeconvModel, auto_response_ssst
        from dipy.data import get_sphere
        # import marshal as pickle
        import pickle as pickle
        # import gzip

        img = nib.load(self.inputs.in_file)
        imref = nib.four_to_three(img)[0]

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects around the edge of the image."""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.in_mask):
            msk = clipMask(
                nib.load(self.inputs.in_mask).get_data().astype('float32'))
        else:
            msk = clipMask(np.ones(imref.shape).astype('float32'))

        data = img.get_data().astype(np.float32)
        data[msk == 0] *= 0

        # hdr = imref.header.copy()

        gtab = self._get_gradient_table()

        if isdefined(self.inputs.response):
            resp_file = np.loadtxt(self.inputs.response)

            response = (np.array(resp_file[0:3]), resp_file[-1])
            ratio = response[0][1] / response[0][0]

            if abs(ratio - 0.2) > 0.1:
                IFLOGGER.warn(('Estimated response is not prolate enough. '
                               'Ratio=%0.3f.') % ratio)
        else:
            response, ratio = auto_response_ssst(gtab,
                                                         data,
                                                         roi_radii=10,
                                                         fa_thr=0.5)
            IFLOGGER.info("response: ")
            IFLOGGER.info(response)
            IFLOGGER.info("ratio: %g" % ratio)

            if abs(ratio - 0.2) > 0.1:
                IFLOGGER.warn(('Estimated response is not prolate enough. '
                               'Ratio=%0.3f.') % ratio)

        sphere = get_sphere('symmetric724')
        csd_model = ConstrainedSphericalDeconvModel(gtab,
                                                    response,
                                                    sh_order=self.inputs.sh_order,
                                                    reg_sphere=sphere,
                                                    lambda_=np.sqrt(1. / 2))
        # IFLOGGER.info('Fitting CSD model')
        # csd_fit = csd_model.fit(data, msk)

        if self.inputs.tracking_processing_tool == 'mrtrix':
            sh_basis_type = 'tournier07'
        elif self.inputs.tracking_processing_tool == 'dipy':
            sh_basis_type = 'descoteaux07'

        with gzip.open(self._gen_filename('csdmodel', ext='.pklz'), 'wb') as f:
            pickle.dump(csd_model, f, -1)

        if self.inputs.save_shm_coeff:
            # isphere = get_sphere('symmetric724')
            from dipy.direction import peaks_from_model
            IFLOGGER.info('Fitting CSD model')
            csd_peaks = peaks_from_model(model=csd_model,
                                         data=data,
                                         sphere=sphere,
                                         relative_peak_threshold=.5,
                                         min_separation_angle=25,
                                         mask=msk,
                                         sh_basis_type=sh_basis_type,
                                         return_sh=True,
                                         return_odf=False,
                                         normalize_peaks=True,
                                         npeaks=3,
                                         parallel=True,
                                         nbr_processes=None)
            # fods = csd_fit.odf(sphere)
            # IFLOGGER.info(fods)
            # IFLOGGER.info(fods.shape)
            IFLOGGER.info('Save Spherical Harmonics image')
            nib.Nifti1Image(csd_peaks.shm_coeff, img.affine, None).to_filename(self._gen_filename('shm_coeff'))

            # FIXME: dipy 1.1.0 and fury 0.5.1 with vtk 8.2.0 -> error:
            #
            #  from .vtkIOExodusPython import *
            #  ImportError: libnetcdf.so.13: cannot open shared object file: No such file or directory
            #
            # from dipy.viz import actor, window
            # ren = window.Renderer()
            # ren.add(actor.peak_slicer(csd_peaks.peak_dirs,
            #                           csd_peaks.peak_values,
            #                           colors=None))

            # window.record(ren, out_path=self._gen_filename(
            #     'csd_direction_field', ext='.png'), size=(900, 900))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['model'] = self._gen_filename('csdmodel', ext='.pklz')
        if self.inputs.save_fods:
            outputs['out_shm_coeff'] = self._gen_filename('shm_coeff')
        # if self.inputs.save_fods:
        #     outputs['out_fods'] = self._gen_filename('fods')
        return outputs


class SHOREInputSpec(DipyBaseInterfaceInputSpec):
    in_mask = File(exists=True, desc=(
        'input mask in which compute SHORE solution'))
    response = File(exists=True, desc='single fiber estimated response')
    radial_order = traits.Int(6, usedefault=True, desc=(
        'Even number that represents the order of the basis'))
    zeta = traits.Int(700, usedefault=True, desc='Scale factor')
    lambda_n = traits.Float(1e-8, usedefault=True,
                            desc='radial regularisation constant')
    lambda_l = traits.Float(1e-8, usedefault=True,
                            desc='angular regularisation constant')
    tau = traits.Float(0.025330295910584444, desc=(
        'Diffusion time. By default the value that makes q equal to the square root of the b-value.'))
    tracking_processing_tool = traits.Enum("mrtrix", "dipy")

    constrain_e0 = traits.Bool(False, usedefault=True, desc=(
        'Constrain the optimization such that E(0) = 1.'))
    positive_constraint = traits.Bool(False, usedefault=True, desc=(
        'Constrain the optimization such that E(0) = 1.'))


class SHOREOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the SHORE model fitted.')
    fodf = File(
        desc='Fiber Orientation Distribution Function output file name')
    dodf = File(
        desc='Fiber Orientation Distribution Function output file name')
    GFA = File(desc='Generalized Fractional Anisotropy output file name')
    MSD = File(desc='Mean Square Displacement output file name')
    RTOP = File(desc='Return To Origin Probability output file name')


class SHORE(DipyDiffusionInterface):
    """Uses SHORE [Merlet2013]_ to generate the fODF of DWIs.

    The interface uses :py:mod:`dipy`, as explained in
        `dipy's SHORE example <http://nipy.org/dipy/examples_built/reconst_shore.html#merlet2013>`_.

    References
    ----------
    .. [Merlet2013]	Merlet S. et. al, Medical Image Analysis, 2013.
        “Continuous diffusion signal, EAP and ODF estimation via Compressive Sensing in diffusion MRI”

    Example
    -------
    >>> from cmtklib.interfaces.dipy import SHORE
    >>> asm = SHORE(radial_order=6,zeta=700, lambda_n=1e-8, lambda_l=1e-8)
    >>> asm.inputs.in_file = '4d_dwi.nii'
    >>> asm.inputs.in_bval = 'bvals'
    >>> asm.inputs.in_bvec = 'bvecs'
    >>> res = asm.run()  # doctest: +SKIP

    """

    input_spec = SHOREInputSpec
    output_spec = SHOREOutputSpec

    def _run_interface(self, runtime):
        # import nibabel as nib

        import pickle as pickle

        from dipy.data import get_sphere
        from dipy.io import read_bvals_bvecs
        from dipy.core.gradients import gradient_table
        from dipy.reconst.shore import ShoreModel
        from dipy.reconst.odf import gfa
        from dipy.reconst.csdeconv import odf_sh_to_sharp
        from dipy.reconst.shm import sf_to_sh
        from dipy.core.ndindex import ndindex

        img = nib.load(self.inputs.in_file)
        imref = nib.four_to_three(img)[0]
        affine = img.affine

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects around the edge of the image."""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.in_mask):
            msk = clipMask(
                nib.load(self.inputs.in_mask).get_data().astype('float32'))
        else:
            msk = clipMask(np.ones(imref.shape).astype('float32'))

        data = img.get_data().astype(np.float32)
        data[msk == 0] *= 0

        # hdr = imref.header.copy()

        bvals, bvecs = read_bvals_bvecs(
            self.inputs.in_bval, self.inputs.in_bvec)
        bvecs = np.array([-bvecs[:, 0], bvecs[:, 1], bvecs[:, 2]]).transpose()
        gtab = gradient_table(bvals, bvecs)

        sphere = get_sphere('symmetric724')
        shore_model = ShoreModel(gtab, radial_order=self.inputs.radial_order, zeta=self.inputs.zeta,
                                 lambdaN=self.inputs.lambda_n, lambdaL=self.inputs.lambda_l)

        f = gzip.open(op.abspath('shoremodel.pklz'), 'wb')
        pickle.dump(shore_model, f, -1)
        f.close()

        lmax = self.inputs.radial_order
        datashape = data.shape
        dimsODF = list(datashape)
        dimsODF[3] = int((lmax + 1) * (lmax + 2) / 2)
        shODF = np.zeros(dimsODF)
        GFA = np.zeros(dimsODF[:3])
        RTOP = np.zeros(dimsODF[:3])
        MSD = np.zeros(dimsODF[:3])

        # Dipy >= 0.16 - basis : {None, ‘tournier07’, ‘descoteaux07’}
        if self.inputs.tracking_processing_tool == "mrtrix":
            basis = 'tournier07'
        else:
            basis = 'descoteaux07'

        # calculate odf per slice
        IFLOGGER.info('Fitting SHORE model')
        for i in ndindex(data.shape[:1]):
            print("Processing slice #%i " % i)
            start_time = time.time()
            shorefit = shore_model.fit(data[i])
            sliceODF = shorefit.odf(sphere)
            sliceGMSD = shorefit.msd()
            sliceRTOP = shorefit.rtop_signal()
            sliceGFA = gfa(sliceODF)
            shODF[i] = sf_to_sh(
                sliceODF, sphere, sh_order=lmax, basis_type=basis)
            GFA[i] = np.nan_to_num(sliceGFA)
            MSD[i] = np.nan_to_num(sliceGMSD)
            RTOP[i] = np.nan_to_num(sliceRTOP)
            print("Computation Time (slice %s): " %
                  str(i) + str(time.time() - start_time) + " seconds")

        shFODF = odf_sh_to_sharp(shODF, sphere, basis=basis, ratio=0.2, sh_order=lmax, lambda_=1.0, tau=0.1,
                                 r2_term=True)

        IFLOGGER.info('Save Spherical Harmonics / MSD / GFA images')

        nib.Nifti1Image(GFA, affine).to_filename(
            op.abspath('shore_gfa.nii.gz'))
        nib.Nifti1Image(MSD, affine).to_filename(
            op.abspath('shore_msd.nii.gz'))
        nib.Nifti1Image(RTOP, affine).to_filename(
            op.abspath('shore_rtop_signal.nii.gz'))
        nib.Nifti1Image(shODF, affine).to_filename(
            op.abspath('shore_dodf.nii.gz'))
        nib.Nifti1Image(shFODF, affine).to_filename(
            op.abspath('shore_fodf.nii.gz'))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['model'] = op.abspath('shoremodel.pklz')
        outputs['fodf'] = op.abspath('shore_fodf.nii.gz')
        outputs['dodf'] = op.abspath('shore_dodf.nii.gz')
        outputs['GFA'] = op.abspath('shore_gfa.nii.gz')
        outputs['MSD'] = op.abspath('shore_msd.nii.gz')
        outputs['RTOP'] = op.abspath('shore_rtop_signal.nii.gz')
        return outputs


class TensorInformedEudXTractographyInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc='input diffusion data')
    in_fa = File(exists=True, mandatory=True, desc='input FA')
    in_model = File(exists=True, mandatory=True, desc=(
        'input Tensor model extracted from.'))
    tracking_mask = File(exists=True, mandatory=True,
                         desc='input mask within which perform tracking')
    seed_mask = InputMultiPath(File(
        exists=True), mandatory=True, desc='ROI files registered to diffusion space')
    fa_thresh = traits.Float(0.2, mandatory=True, usedefault=True,
                             desc='FA threshold to build the tissue classifier')
    max_angle = traits.Float(25.0, mandatory=True, usedefault=True,
                             desc='Maximum angle')
    step_size = traits.Float(0.5, mandatory=True, usedefault=True,
                             desc='Step size')
    multiprocess = traits.Bool(True, mandatory=True, usedefault=True,
                               desc='use multiprocessing')
    save_seeds = traits.Bool(False, mandatory=True, usedefault=True,
                             desc='save seeding voxels coordinates')
    num_seeds = traits.Int(10000, mandatory=True, usedefault=True,
                           desc='desired number of tracks in tractography')
    out_prefix = traits.Str(desc='output prefix for file names')


class TensorInformedEudXTractographyOutputSpec(TraitedSpec):
    tracks = File(desc='TrackVis file containing extracted streamlines')
    out_seeds = File(desc=('file containing the (N,3) *voxel* coordinates used'
                           ' in seeding.'))


class TensorInformedEudXTractography(DipyBaseInterface):
    """Streamline tractography using Dipy Deterministic Maximum Direction Getter.

    Example
    -------
    >>> from cmtklib.interfaces import dipy as ndp
    >>> track = ndp.TensorInformedEudXTractography()
    >>> track.inputs.in_file = '4d_dwi.nii'
    >>> track.inputs.in_model = 'model.pklz'
    >>> track.inputs.tracking_mask = 'dilated_wm_mask.nii'
    >>> res = track.run()  # doctest: +SKIP

    """

    input_spec = TensorInformedEudXTractographyInputSpec
    output_spec = TensorInformedEudXTractographyOutputSpec

    def _run_interface(self, runtime):
        from dipy.tracking import utils
        from dipy.direction import peaks_from_model
        # from dipy.tracking.stopping_criterion import BinaryStoppingCriterion
        from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
        from dipy.tracking.local_tracking import LocalTracking
        from dipy.data import get_sphere
        from dipy.io.stateful_tractogram import Space, StatefulTractogram
        from dipy.io.streamline import save_trk
        # import marshal as pickle
        import pickle as pickle

        if not (isdefined(self.inputs.in_model)):
            raise RuntimeError("in_model should be supplied")

        img = nib.load(self.inputs.in_file)
        imref = nib.four_to_three(img)[0]
        affine = img.affine

        data = img.get_data().astype(np.float32)
        hdr = imref.header.copy()
        hdr.set_data_dtype(np.float32)
        hdr['data_type'] = 16

        trkhdr = nib.trackvis.empty_header()
        trkhdr['dim'] = imref.get_data().shape
        trkhdr['voxel_size'] = imref.get_header().get_zooms()[:3]
        trkhdr['voxel_order'] = 'ras'
        # trackvis_affine = utils.affine_for_trackvis(trkhdr['voxel_size'])

        sphere = get_sphere('symmetric724')

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects around the edge of the image."""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.tracking_mask):
            IFLOGGER.info('Loading Tracking Mask')
            tmsk = clipMask(nib.load(self.inputs.tracking_mask).get_data())
            tmsk[tmsk > 0] = 1
            tmsk[tmsk < 0] = 0
        else:
            tmsk = np.ones(imref.shape)

        seeds = self.inputs.num_seeds

        if isdefined(self.inputs.seed_mask[0]):
            IFLOGGER.info('Loading Seed Mask')
            seedmsk = nib.load(self.inputs.seed_mask[0]).get_data()
            IFLOGGER.info(f'  - Loaded Seed Mask Shape: {seedmsk.shape}')
            # seedmsk = clipMask(nib.load(self.inputs.seed_mask[0]).get_data())
            # assert (seedmsk.shape == data.shape[:3])
            seedmsk[seedmsk > 0] = 1
            seedmsk[seedmsk < 1] = 0
            seedps = np.array(np.where(seedmsk == 1), dtype=np.float32).T
            vseeds = seedps.shape[0]
            nsperv = (seeds // vseeds) + 1
            IFLOGGER.info(f'Seed mask is provided ({vseeds} voxels inside '
                          f'mask), computing seeds ({nsperv} seeds/voxel).')
            if nsperv > 1:
                IFLOGGER.info(f'Needed {nsperv} seeds per selected voxel (total {vseeds}).')
                seedps = np.vstack(np.array([seedps] * nsperv))
                voxcoord = seedps + np.random.uniform(-1, 1, size=seedps.shape)
                nseeds = voxcoord.shape[0]
                seeds = affine.dot(np.vstack((voxcoord.T, np.ones((1, nseeds)))))[:3, :].T

                if self.inputs.save_seeds:
                    np.savetxt(self._gen_filename('seeds', ext='.txt'), seeds)

            IFLOGGER.info(f'Create seeds for fiber tracking from the binary seed mask (density: {nsperv})')

            tseeds = utils.seeds_from_mask(seedmsk,
                                           affine=affine,
                                           density=[nsperv, nsperv, nsperv]  # FIXME: density should be customizable
                                           )

        IFLOGGER.info('Loading and masking FA')
        img_fa = nib.load(self.inputs.in_fa)
        fa = img_fa.get_data().astype(np.float32)
        fa = fa * tmsk

        IFLOGGER.info('Saving masked FA')
        hdr.set_data_shape(fa.shape)
        nib.Nifti1Image(fa.astype(np.float32), affine, hdr).to_filename(
            self._gen_filename('fa_masked'))

        IFLOGGER.info('Building Tissue Classifier')
        classifier = ThresholdStoppingCriterion(fa, self.inputs.fa_thresh)
        # classifier = BinaryStoppingCriterion(tmsk)

        IFLOGGER.info('Loading tensor model')
        f = gzip.open(self.inputs.in_model, 'rb')
        tensor_model = pickle.load(f)
        f.close()

        IFLOGGER.info('Generating peaks from tensor model')
        dti_peaks = peaks_from_model(model=tensor_model,
                                     data=data,
                                     sphere=sphere,
                                     relative_peak_threshold=.2,
                                     min_separation_angle=25,
                                     mask=tmsk,
                                     normalize_peaks=False,  # changed
                                     parallel=True)

        IFLOGGER.info('Performing tensor-informed EuDX tractography')
        streamlines = LocalTracking(dti_peaks,
                                    classifier,
                                    tseeds,
                                    affine,
                                    step_size=self.inputs.step_size,
                                    max_cross=1)

        IFLOGGER.info('Saving tracks')
        sft = StatefulTractogram(streamlines, imref, Space.RASMM)
        save_trk(sft, self._gen_filename('tracked', ext='.trk'))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['tracks'] = self._gen_filename('tracked', ext='.trk')
        if self.inputs.save_seeds:
            outputs['out_seeds'] = self._gen_filename('seeds', ext='.txt')

        return outputs

    def _gen_filename(self, name, ext=None):
        fname, fext = op.splitext(op.basename(self.inputs.in_file))
        if fext == '.gz':
            fname, fext2 = op.splitext(fname)
            fext = fext2 + fext

        if not isdefined(self.inputs.out_prefix):
            out_prefix = op.abspath(fname)
        else:
            out_prefix = self.inputs.out_prefix

        if ext is None:
            ext = fext

        return out_prefix + '_' + name + ext


class DirectionGetterTractographyInputSpec(BaseInterfaceInputSpec):
    algo = traits.Enum(["deterministic", "probabilistic"],
                       usedefault=True,
                       desc='Use either deterministic maximum (default) or probabilistic direction getter tractography')
    recon_model = traits.Enum(["CSD", "SHORE"],
                              usedefault=True,
                              desc='Use either fODFs from CSD (default) or SHORE models')
    recon_order = traits.Int(8,
                             desc='Spherical harmonics order')
    use_act = traits.Bool(False,
                          desc='Use FAST for partial volume estimation and '
                               'Anatomically-Constrained Tractography (ACT) tissue classifier')
    seed_from_gmwmi = traits.Bool(False,
                                  desc='Seed from the Gray Matter / White Matter interface')
    gmwmi_file = File(exists=True,
                      desc='input Gray Matter / White Matter interface image')
    # fast_number_of_classes = traits.Int(3, desc=('Number of tissue classes used by FAST for Anatomically-Constrained Tractography (ACT)'))
    in_file = File(exists=True, mandatory=True,
                   desc='input diffusion data')
    fod_file = File(exists=True,
                    desc='input fod file (if SHORE)')
    in_fa = File(exists=True, mandatory=True,
                 desc='input FA')
    in_partial_volume_files = InputMultiPath(File(exists=True),
                                             desc='Partial volume estimation result files (required if performing ACT)')
    # in_t1 = File(exists=True, desc=('input T1w (required if performing ACT)'))
    in_model = File(exists=True, mandatory=True,
                    desc='input f/d-ODF model extracted from.')
    tracking_mask = File(exists=True, mandatory=True,
                         desc='input mask within which perform tracking')
    seed_mask = InputMultiPath(File(exists=True), mandatory=True,
                               desc='ROI files registered to diffusion space')
    seed_density = traits.Float(1,
                                usedefault=True,
                                desc='Density of seeds')
    fa_thresh = traits.Float(0.2,
                             mandatory=True, usedefault=True,
                             desc='FA threshold to build the tissue classifier')
    max_angle = traits.Float(25.0,
                             mandatory=True, usedefault=True,
                             desc='Maximum angle')
    step_size = traits.Float(0.5,
                             mandatory=True, usedefault=True,
                             desc='Step size')
    multiprocess = traits.Bool(True,
                               mandatory=True, usedefault=True,
                               desc='use multiprocessing')
    save_seeds = traits.Bool(False,
                             mandatory=True, usedefault=True,
                             desc='save seeding voxels coordinates')
    num_seeds = traits.Int(10000,
                           mandatory=True, usedefault=True,
                           desc='desired number of tracks in tractography')
    out_prefix = traits.Str(desc='output prefix for file names')


class DirectionGetterTractographyOutputSpec(TraitedSpec):
    tracks = File(desc='TrackVis file containing extracted streamlines')
    tracks2 = File(desc='TrackVis file containing extracted streamlines')
    tracks3 = File(desc='TrackVis file containing extracted streamlines')
    out_seeds = File(desc=('file containing the (N,3) *voxel* coordinates used'
                           ' in seeding.'))
    streamlines = File(desc='Numpy array of streamlines')


class DirectionGetterTractography(DipyBaseInterface):
    """Streamline tractography using Dipy Deterministic Maximum Direction Getter.

    Example
    -------
    >>> from cmtklib.interfaces import dipy as ndp
    >>> track = ndp.DirectionGetterTractography()
    >>> track.inputs.in_file = '4d_dwi.nii'
    >>> track.inputs.in_model = 'model.pklz'
    >>> track.inputs.tracking_mask = 'dilated_wm_mask.nii'
    >>> res = track.run()  # doctest: +SKIP

    """

    input_spec = DirectionGetterTractographyInputSpec
    output_spec = DirectionGetterTractographyOutputSpec

    def _run_interface(self, runtime):
        from dipy.tracking import utils
        from dipy.direction import DeterministicMaximumDirectionGetter, ProbabilisticDirectionGetter
        # from dipy.tracking.local import ThresholdStoppingCriterion, ActStoppingCriterion
        from dipy.tracking.stopping_criterion import BinaryStoppingCriterion, CmcStoppingCriterion
        from dipy.tracking.local_tracking import LocalTracking, ParticleFilteringTracking
        from dipy.direction.peaks import peaks_from_model
        from dipy.data import get_sphere
        from dipy.tracking.streamline import Streamlines
        from dipy.io.stateful_tractogram import Space, StatefulTractogram
        from dipy.io.streamline import save_trk
        import pickle
        import gzip

        if not (isdefined(self.inputs.in_model)):
            raise RuntimeError('in_model should be supplied')

        img = nib.load(self.inputs.in_file)
        imref = nib.four_to_three(img)[0]
        affine = img.affine

        data = img.get_data().astype(np.float32)
        hdr = imref.header.copy()
        hdr.set_data_dtype(np.float32)
        hdr['data_type'] = 16

        sphere = get_sphere('symmetric724')

        def clipMask(mask):
            """This is a hack until Dipy fixes the behaviour of the tracking objects
            around the edge of the image"""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[tuple(idx)] = 0.
            return out

        if self.inputs.use_act:
            # from nipype.interfaces import fsl
            # # Run FAST for partial volume estimation (WM;GM;CSF)
            # fastr = pe.Node(interface=fsl.FAST(),name='fastr')
            # fastr.inputs.in_files = self.inputs.in_t1 # TODO: input T1w image to interface, diffusion and tracking stages
            # fastr.inputs.out_basename = 'fast_'
            # fastr.inputs.number_classes = self.inputs.fast_number_of_classes
            # IFLOGGER.info("Running FAST...")
            # out = fastr.run()  # doctest: +SKIP
            #
            # # Create the include_map and exclude_map for the partial volume files (FAST outputs)
            # IFLOGGER.info("partial_volume_files :")
            # IFLOGGER.info(fastr.outputs.partial_volume_files)

            img_pve_csf = nib.load(self.inputs.in_partial_volume_files[0])
            img_pve_gm = nib.load(self.inputs.in_partial_volume_files[1])
            img_pve_wm = nib.load(self.inputs.in_partial_volume_files[2])

            voxel_size = np.average(img_pve_wm.header['pixdim'][1:4])
            step_size = self.inputs.step_size

            IFLOGGER.info('Building CMC Tissue Classifier')

            cmc_classifier = CmcStoppingCriterion.from_pve(img_pve_wm.get_data(),
                                                           img_pve_gm.get_data(),
                                                           img_pve_csf.get_data(),
                                                           step_size=step_size,
                                                           average_voxel_size=voxel_size)

            if self.inputs.recon_model == 'CSD':
                IFLOGGER.info('Creating mask used by CSD model from partial volume maps of GM and WM')

                tmsk = img_pve_wm.get_data() + img_pve_gm.get_data()
                tmsk[tmsk > 0] = 1
                tmsk[tmsk < 0] = 0

            # background = np.ones(imref.shape)
            # pve_sum = np.zeros(imref.shape)
            # for pve_file in self.inputs.in_partial_volume_files:
            #     pve_img = nib.load(pve_file)
            #     pve_data = pve_img.get_data().astype(np.float32)
            #     pve_sum = pve_sum + pve_data
            #
            # background[pve_sum>0] = 0
            #
            # include_map = np.zeros(imref.shape)
            # exclude_map = np.zeros(imref.shape)
            # for pve_file in self.inputs.in_partial_volume_files:
            #     pve_img = nib.load(pve_file)
            #     pve_data = pve_img.get_data().astype(np.float32)
            #     if "pve_0" in pve_file:# CSF
            #         exclude_map = pve_data
            #     elif "pve_1" in pve_file:# GM
            #         include_map = pve_data
            #
            # include_map[background>0] = 1
            # IFLOGGER.info('Building ACT Tissue Classifier')
            # classifier = ActStoppingCriterion(include_map,exclude_map)
        else:
            if isdefined(self.inputs.tracking_mask):
                IFLOGGER.info('Loading Tracking Mask')
                tmsk = clipMask(nib.load(self.inputs.tracking_mask).get_data())
                tmsk[tmsk > 0] = 1
                tmsk[tmsk < 0] = 0
            else:
                tmsk = np.ones(imref.shape)

            IFLOGGER.info('Loading and masking FA')
            img_fa = nib.load(self.inputs.in_fa)
            fa = img_fa.get_data().astype(np.float32)
            fa = fa * tmsk

            IFLOGGER.info('Saving masked FA')
            hdr.set_data_shape(fa.shape)
            nib.Nifti1Image(fa.astype(np.float32), affine, hdr).to_filename(
                self._gen_filename('fa_masked'))

            IFLOGGER.info('Building Binary Tissue Classifier')
            # classifier = ThresholdStoppingCriterion(fa,self.inputs.fa_thresh)
            classifier = BinaryStoppingCriterion(tmsk)

        seeds = self.inputs.num_seeds

        if isdefined(self.inputs.seed_mask[0]) or (self.inputs.seed_from_gmwmi and isdefined(self.inputs.gmwmi_file)):

            # Handle GMWM interface or seed mask
            if self.inputs.seed_from_gmwmi and isdefined(self.inputs.gmwmi_file):
                IFLOGGER.info(f'Loading Seed Mask from {self.inputs.gmwmi_file}')
                seedmsk = nib.load(self.inputs.gmwmi_file).get_data()
                seedmsk = np.squeeze(seedmsk)
            else:
                IFLOGGER.info(f'Loading Seed Mask from {self.inputs.seed_mask[0]}')
                seedmsk = nib.load(self.inputs.seed_mask[0]).get_data()

            # assert (seedmsk.shape == data.shape[:3])
            # seedmsk = clipMask(seedmsk)

            print(f'seedmsk min: {seedmsk.min()}')
            print(f'seedmsk max: {seedmsk.max()}')

            seedmsk[seedmsk > 0] = 1
            seedmsk[seedmsk < 1] = 0

            IFLOGGER.info(f'Saving seed mask (shape: {seedmsk.shape})')
            hdr.set_data_shape(seedmsk.shape)
            nib.Nifti1Image(seedmsk.astype(np.float32),
                            affine,
                            hdr).to_filename(self._gen_filename('desc-seed_mask'))

            seedps = np.array(np.where(seedmsk == 1), dtype=np.float32).T
            vseeds = seedps.shape[0]
            nsperv = (seeds // vseeds) + 1
            IFLOGGER.info(f'Seed mask is provided ({vseeds} voxels inside '
                          f'mask), computing seeds ({nsperv} seeds/voxel).')
            if nsperv > 1:
                IFLOGGER.info(f'Needed {nsperv} seeds per selected voxel '
                              f'(total {vseeds}).')
                seedps = np.vstack(np.array([seedps] * nsperv))
                voxcoord = seedps + np.random.uniform(-1, 1, size=seedps.shape)
                nseeds = voxcoord.shape[0]
                seeds = affine.dot(np.vstack((voxcoord.T, np.ones((1, nseeds)))))[:3, :].T

                if self.inputs.save_seeds:
                    np.savetxt(self._gen_filename('seeds', ext='.txt'), seeds)

            IFLOGGER.info(f'Create seeds for fiber tracking from the binary seed mask (density: {self.inputs.seed_density})')
            tseeds = utils.seeds_from_mask(seedmsk,
                                           affine=affine,
                                           density=[self.inputs.seed_density,
                                                    self.inputs.seed_density,
                                                    self.inputs.seed_density]  # FIXME: density should be customizable
                                           )

        if self.inputs.recon_model == 'CSD':
            IFLOGGER.info('Loading CSD model')
            f = gzip.open(self.inputs.in_model, 'rb')
            csd_model = pickle.load(f)
            f.close()

            IFLOGGER.info('Generating peaks from CSD model')
            pfm = peaks_from_model(model=csd_model,
                                   data=data,
                                   sphere=sphere,
                                   relative_peak_threshold=.2,
                                   min_separation_angle=self.inputs.max_angle,
                                   mask=tmsk,
                                   return_sh=True,
                                   # sh_basis_type=args.basis,
                                   sh_order=self.inputs.recon_order,
                                   normalize_peaks=False,  # changed
                                   parallel=True)

            if self.inputs.algo == 'deterministic':
                dg = DeterministicMaximumDirectionGetter.from_shcoeff(pfm.shm_coeff,
                                                                      max_angle=self.inputs.max_angle,
                                                                      sphere=sphere)
            else:
                dg = ProbabilisticDirectionGetter.from_shcoeff(pfm.shm_coeff,
                                                               max_angle=self.inputs.max_angle,
                                                               sphere=sphere)
        else:
            IFLOGGER.info('Loading SHORE FOD')
            sh = nib.load(self.inputs.fod_file).get_data()
            sh = np.nan_to_num(sh)
            IFLOGGER.info('Generating peaks from SHORE model')
            if self.inputs.algo == 'deterministic':
                dg = DeterministicMaximumDirectionGetter.from_shcoeff(sh,
                                                                      max_angle=self.inputs.max_angle,
                                                                      sphere=sphere)
            else:
                dg = ProbabilisticDirectionGetter.from_shcoeff(sh,
                                                               max_angle=self.inputs.max_angle,
                                                               sphere=sphere)

        if not self.inputs.use_act:
            IFLOGGER.info('Performing %s tractography' % self.inputs.algo)

            streamlines = LocalTracking(dg,
                                        classifier,
                                        tseeds,
                                        affine,
                                        step_size=self.inputs.step_size,
                                        max_cross=1)

            IFLOGGER.info('Saving tracks')
            sft = StatefulTractogram(streamlines, imref, Space.RASMM)
            save_trk(sft, self._gen_filename('tracked', ext='.trk'))
        else:
            IFLOGGER.info('Performing PFT tractography')
            # Particle Filtering Tractography
            pft_streamline_generator = ParticleFilteringTracking(dg,
                                                                 cmc_classifier,
                                                                 tseeds,
                                                                 affine,
                                                                 max_cross=1,
                                                                 step_size=step_size,
                                                                 maxlen=200,
                                                                 pft_back_tracking_dist=2,
                                                                 pft_front_tracking_dist=1,
                                                                 particle_count=15,
                                                                 return_all=False)
            IFLOGGER.info('Saving tracks')
            # streamlines = list(pft_streamline_generator)
            streamlines = Streamlines(pft_streamline_generator)
            sft = StatefulTractogram(streamlines, imref, Space.RASMM)
            save_trk(sft, self._gen_filename('tracked', ext='.trk'))

            # from nibabel.streamlines import Field, Tractogram
            # from nibabel.orientations import aff2axcodes

            # print('-> Load nifti and copy header 1')

            # trkhdr = nib.trackvis.empty_header()
            # trkhdr['dim'] = imref.shape[:3]
            # trkhdr['voxel_size'] = imref.header.get_zooms()[:3]
            # trkhdr['voxel_order'] = "".join(aff2axcodes(imref.affine))
            # # utils.affine_for_trackvis(trkhdr['voxel_size'])
            # trkhdr['vox_to_ras'] = imref.affine.copy()

            # np.save(self._gen_filename('streamlines', ext='.npy'), streamlines)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['streamlines'] = self._gen_filename('streamlines', ext='.npy')
        outputs['tracks'] = self._gen_filename('tracked', ext='.trk')
        outputs['tracks2'] = self._gen_filename('tracked_old', ext='.trk')
        outputs['tracks3'] = self._gen_filename('tracked_nib2', ext='.trk')
        if self.inputs.save_seeds:
            outputs['out_seeds'] = self._gen_filename('seeds', ext='.txt')

        return outputs

    def _gen_filename(self, name, ext=None):
        fname, fext = op.splitext(op.basename(self.inputs.in_file))
        if fext == '.gz':
            fname, fext2 = op.splitext(fname)
            fext = fext2 + fext

        if not isdefined(self.inputs.out_prefix):
            out_prefix = op.abspath(fname)
        else:
            out_prefix = self.inputs.out_prefix

        if ext is None:
            ext = fext

        return out_prefix + '_' + name + ext


class MAPMRIInputSpec(DipyBaseInterfaceInputSpec):
    laplacian_regularization = traits.Bool(
        True, usedefault=True, desc='Apply laplacian regularization')

    laplacian_weighting = traits.Float(
        0.05, usedefault=True, desc='Regularization weight')

    positivity_constraint = traits.Bool(
        True, usedefault=True, desc='Apply positivity constraint')

    radial_order = traits.Int(8, usedefault=True,
                              desc='maximal shperical harmonics order')

    small_delta = traits.Float(0.02, mandatory=True,
                               desc='Small data for gradient table')

    big_delta = traits.Float(0.5, mandatory=True,
                             desc='Small data for gradient table')


class MAPMRIOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the MAP-MRI model fitted.')
    rtop_file = File(desc='rtop output file name')
    rtap_file = File(desc='rtap output file name')
    rtpp_file = File(desc='rtpp output file name')
    msd_file = File(desc='msd output file name')
    qiv_file = File(desc='qiv output file name')
    ng_file = File(desc='ng output file name')
    ng_perp_file = File(desc='ng perpendicular output file name')
    ng_para_file = File(desc='ng parallel output file name')


class MAPMRI(DipyDiffusionInterface):
    """Computes the MAP MRI model.

    .. check http://nipy.org/dipy/examples_built/reconst_mapmri.html#example-reconst-mapmri for reference on the settings

    Example
    -------
    >>> from cmtklib.interfaces.dipy import MAPMRI
    >>> mapmri = MAPMRI()
    >>> mapmri.inputs.in_file = '4d_dwi.nii'
    >>> mapmri.inputs.in_bval = 'bvals'
    >>> mapmri.inputs.in_bvec = 'bvecs'
    >>> res = mapmri.run()  # doctest: +SKIP

    """

    input_spec = MAPMRIInputSpec
    output_spec = MAPMRIOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst import mapmri
        # from dipy.data import fetch_cenir_multib, read_cenir_multib
        from dipy.core.gradients import gradient_table
        # import marshal as pickle
        import pickle as pickle
        import gzip

        img = nib.load(self.inputs.in_file)
        imref = nib.four_to_three(img)[0]
        affine = img.affine

        data = img.get_data().astype(np.float32)

        hdr = imref.header.copy()

        gtab = self._get_gradient_table()
        gtab = gradient_table(bvals=gtab.bvals, bvecs=gtab.bvecs,
                              small_delta=self.inputs.small_delta,
                              big_delta=self.inputs.big_delta)

        map_model_both_aniso = mapmri.MapmriModel(gtab,
                                                  radial_order=self.inputs.radial_order,
                                                  anisotropic_scaling=True,
                                                  laplacian_regularization=self.inputs.laplacian_regularization,
                                                  laplacian_weighting=self.inputs.laplacian_weighting,
                                                  positivity_constraint=self.inputs.positivity_constraint
                                                  )

        IFLOGGER.info('Fitting MAP-MRI model')
        mapfit_both_aniso = map_model_both_aniso.fit(data)

        '''maps'''
        maps = {}
        maps["rtop"] = mapfit_both_aniso.rtop()  # '''1/Volume of pore'''
        maps["rtap"] = mapfit_both_aniso.rtap()  # '''1/AREA ...'''
        maps["rtpp"] = mapfit_both_aniso.rtpp()  # '''1/length ...'''
        maps["msd"] = mapfit_both_aniso.msd(
        )  # '''similar to mean diffusivity'''
        maps["qiv"] = mapfit_both_aniso.qiv(
        )  # '''almost reciprocal of rtop'''
        maps["ng"] = mapfit_both_aniso.ng()  # '''general non Gaussianity'''
        maps[
            "ng_perp"] = mapfit_both_aniso.ng_perpendicular()  # '''perpendicular to main direction (likely to be non gaussian in white matter)'''
        maps["ng_para"] = mapfit_both_aniso.ng_parallel(
        )  # '''along main direction (likely to be gaussian)'''

        ''' The most related to white matter anisotropy are:
            rtpp, for anisotropy
            rtap, for axonal diameter
            MIGHT BE WORTH DIVINDING RTPP BY (1/RTOP): THAT IS:
            length/VOLUME = RTOP/RTPP
        '''

        f = gzip.open(self._gen_filename('mapmri', ext='.pklz'), 'wb')
        pickle.dump(map_model_both_aniso, f, -1)
        f.close()

        # "rtop", "rtap", "rtpp", "msd", "qiv", "ng", "ng_perp", "ng_para"
        for metric, data in list(maps.items()):
            out_name = self._gen_filename(metric)
            nib.Nifti1Image(data, affine).to_filename(out_name)
            IFLOGGER.info(
                'MAP-MRI {metric} image saved as {i}'.format(i=out_name, metric=metric))
            IFLOGGER.info('Shape :')
            IFLOGGER.info(data.shape)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['model'] = self._gen_filename('mapmri', ext='.pklz')

        for metric in ["rtop", "rtap", "rtpp", "msd", "qiv", "ng", "ng_perp", "ng_para"]:
            outputs["{}_file".format(metric)] = self._gen_filename(metric)
        return outputs
