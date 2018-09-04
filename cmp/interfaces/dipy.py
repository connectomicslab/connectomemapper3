# -*- coding: utf-8 -*-
"""
Interfaces to the algorithms in dipy

"""
from __future__ import print_function, division, unicode_literals, absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str, open

import os.path as op

import time
import numpy as np
import nibabel as nb
import gzip

# Nipype imports
import nipype.pipeline.engine as pe
from nipype import logging
from nipype.interfaces.base import TraitedSpec, File, traits, isdefined, BaseInterfaceInputSpec, InputMultiPath
from nipype.interfaces.dipy.base import DipyDiffusionInterface, DipyBaseInterface, DipyBaseInterfaceInputSpec


IFLOGGER = logging.getLogger('interface')

class DTIEstimateResponseSHInputSpec(DipyBaseInterfaceInputSpec):
    in_mask = File(
        exists=True, desc=('input mask in which we find single fibers'))
    fa_thresh = traits.Float(
        0.7, usedefault=True, desc=('FA threshold'))
    roi_radius = traits.Int(
        10, usedefault=True, desc=('ROI radius to be used in auto_response'))
    auto = traits.Bool(
        xor=['recursive'], desc='use the auto_response estimator from dipy')
    recursive = traits.Bool(
        xor=['auto'], desc='use the recursive response estimator from dipy')
    response = File(
        'response.txt', usedefault=True, desc=('the output response file'))
    out_mask = File('wm_mask.nii.gz', usedefault=True, desc='computed wm mask')


class DTIEstimateResponseSHOutputSpec(TraitedSpec):
    response = File(exists=True, desc=('the response file'))
    dti_model = File(exists=True, desc=('DTI model object'))
    out_mask = File(exists=True, desc=('output wm mask'))
    fa_file = File(exists=True)
    md_file = File(exists=True)
    rd_file = File(exists=True)
    ad_file = File(exists=True)


class DTIEstimateResponseSH(DipyDiffusionInterface):

    """
    Uses dipy to compute the single fiber response to be used in spherical
    deconvolution methods, in a similar way to MRTrix's command
    ``estimate_response``.


    Example
    -------

    >>> from cmp.interfaces import dipy as ndp
    >>> dti = ndp.EstimateResponseSH()
    >>> dti.inputs.in_file = '4d_dwi.nii'
    >>> dti.inputs.in_bval = 'bvals'
    >>> dti.inputs.in_bvec = 'bvecs'
    >>> res = dti.run() # doctest: +SKIP


    """
    input_spec = DTIEstimateResponseSHInputSpec
    output_spec = DTIEstimateResponseSHOutputSpec

    def _run_interface(self, runtime):
        from dipy.core.gradients import GradientTable
        from dipy.reconst.dti import fractional_anisotropy, mean_diffusivity, TensorModel
        from dipy.reconst.csdeconv import recursive_response, auto_response

        import pickle as pickle

        img = nb.load(self.inputs.in_file)
        imref = nb.four_to_three(img)[0]
        affine = img.affine

        if isdefined(self.inputs.in_mask):
            msk = nb.load(self.inputs.in_mask).get_data()
            msk[msk > 0] = 1
            msk[msk < 0] = 0
        else:
            msk = np.ones(imref.shape)

        data = img.get_data().astype(np.float32)
        gtab = self._get_gradient_table()

        # Fit it
        tenmodel = TensorModel(gtab)
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
            data = nb.load(self.inputs.in_file).get_data()
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
                ('Estimated response is not valid, using a default one'))
        else:
            IFLOGGER.info(('Estimated response: %s') % str(response[:3]))

        np.savetxt(op.abspath(self.inputs.response), response)

        wm_mask = np.zeros_like(FA)
        wm_mask[indices] = 1
        nb.Nifti1Image(
            wm_mask.astype(np.uint8), affine,
            None).to_filename(op.abspath(self.inputs.out_mask))

        IFLOGGER.info('Affine :')
        IFLOGGER.info(affine)


                #FA MD RD and AD
        for metric in ["fa", "md", "rd", "ad"]:

            if metric == "fa":
                data = FA.astype("float32")
            else:
                data = getattr(ten_fit,metric).astype("float32")

            out_name = self._gen_filename(metric)
            nb.Nifti1Image(data, affine).to_filename(out_name)
            IFLOGGER.info('DTI {metric} image saved as {i}'.format(i=out_name, metric=metric))
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
    in_mask = File(exists=True, desc=('input mask in which compute tensors'))
    response = File(exists=True, desc=('single fiber estimated response'))
    fa_thresh = traits.Float(0.7, usedefault=True,
                            desc=('FA threshold used for response estimation'))
    sh_order = traits.Int(8, usedefault=True,
                          desc=('maximal shperical harmonics order'))
    save_fods = traits.Bool(True, usedefault=True,
                            desc=('save fODFs in file'))
    save_shm_coeff= traits.Bool(True, usedefault=True,
                            desc=('save Spherical Harmonics Coefficients in file'))
    out_fods = File(desc=('fODFs output file name'))
    out_shm_coeff = File(desc=('Spherical Harmonics Coefficients output file name'))


class CSDOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the CSD model fitted.')
    out_fods = File(desc=('fODFs output file name'))
    out_shm_coeff = File(desc=('Spherical Harmonics Coefficients output file name'))


class CSD(DipyDiffusionInterface):

    """
    Uses CSD [Tournier2007]_ to generate the fODF of DWIs. The interface uses
    :py:mod:`dipy`, as explained in `dipy's CSD example
    <http://nipy.org/dipy/examples_built/reconst_csd.html>`_.

    .. [Tournier2007] Tournier, J.D., et al. NeuroImage 2007.
      Robust determination of the fibre orientation distribution in diffusion
      MRI: Non-negativity constrained super-resolved spherical deconvolution


    Example
    -------

    >>> from nipype.interfaces import dipy as ndp
    >>> csd = ndp.CSD()
    >>> csd.inputs.in_file = '4d_dwi.nii'
    >>> csd.inputs.in_bval = 'bvals'
    >>> csd.inputs.in_bvec = 'bvecs'
    >>> res = csd.run() # doctest: +SKIP
    """
    input_spec = CSDInputSpec
    output_spec = CSDOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst.csdeconv import ConstrainedSphericalDeconvModel, auto_response
        from dipy.data import get_sphere, default_sphere
        # import marshal as pickle
        import pickle as pickle
        import gzip

        img = nb.load(self.inputs.in_file)
        imref = nb.four_to_three(img)[0]
        affine = img.affine

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects
            around the edge of the image"""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.in_mask):
            msk = clipMask(nb.load(self.inputs.in_mask).get_data().astype('float32'))
        else:
            msk = clipMask(np.ones(imref.shape).astype('float32'))

        data = img.get_data().astype(np.float32)
        data[msk==0] *=0

        hdr = imref.header.copy()

        gtab = self._get_gradient_table()

        if isdefined(self.inputs.response):
            resp_file = np.loadtxt(self.inputs.response)

            response = (np.array(resp_file[0:3]), resp_file[-1])
            ratio = response[0][1] / response[0][0]

            if abs(ratio - 0.2) > 0.1:
                IFLOGGER.warn(('Estimated response is not prolate enough. '
                               'Ratio=%0.3f.') % ratio)
        else:
            response, ratio, counts = auto_response(gtab, data, fa_thr=0.5, return_number_of_voxels=True)
            IFLOGGER.info("response: ")
            IFLOGGER.info(response)
            IFLOGGER.info("ratio: %g"%ratio)
            IFLOGGER.info("nbr_voxel_used: %g"%counts)

            if abs(ratio - 0.2) > 0.1:
                IFLOGGER.warn(('Estimated response is not prolate enough. '
                               'Ratio=%0.3f.') % ratio)

        sphere = get_sphere('symmetric724')
        csd_model = ConstrainedSphericalDeconvModel(gtab, response, sh_order=self.inputs.sh_order, reg_sphere=sphere, lambda_=np.sqrt(1. / 2))

        # IFLOGGER.info('Fitting CSD model')
        # csd_fit = csd_model.fit(data, msk)

        f = gzip.open(self._gen_filename('csdmodel', ext='.pklz'), 'wb')
        pickle.dump(csd_model, f, -1)
        f.close()

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
                             return_sh=True,
                             return_odf=False,
                             normalize_peaks=True,
                             npeaks=3,
                             parallel=False,
                             nbr_processes=None)
            # fods = csd_fit.odf(sphere)
            # IFLOGGER.info(fods)
            # IFLOGGER.info(fods.shape)
            IFLOGGER.info('Save Spherical Harmonics image')
            nb.Nifti1Image( csd_peaks.shm_coeff, img.affine,None).to_filename(self._gen_filename('shm_coeff'))

            from dipy.viz import actor, window
            ren = window.Renderer()
            ren.add(actor.peak_slicer(csd_peaks.peak_dirs,
                                      csd_peaks.peak_values,
                                      colors=None))

            window.record(ren, out_path=self._gen_filename('csd_direction_field', ext='.png'), size=(900, 900))

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
    in_mask = File(exists=True, desc=('input mask in which compute SHORE solution'))
    response = File(exists=True, desc=('single fiber estimated response'))
    radial_order = traits.Int(6, usedefault=True, desc=('Even number that represents the order of the basis'))
    zeta = traits.Int(700, usedefault=True, desc=('Scale factor'))
    lambdaN = traits.Float(1e-8, usedefault=True,desc=('radial regularisation constant'))
    lambdaL = traits.Float(1e-8, usedefault=True,desc=('angular regularisation constant'))
    tau = traits.Float(0.025330295910584444,desc=('Diffusion time. By default the value that makes q equal to the square root of the b-value.'))
    tracking_processing_tool = traits.Enum("mrtrix","dipy")

    constrain_e0 = traits.Bool(False, usedefault=True,desc=('Constrain the optimization such that E(0) = 1.'))
    positive_constraint = traits.Bool(False, usedefault=True,desc=('Constrain the optimization such that E(0) = 1.'))


class SHOREOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the CSD model fitted.')
    fod = File(desc=('Spherical Harmonics Coefficients output file name'))
    GFA = File(desc=('Generalized Fractional Anisotropy output file name'))


class SHORE(DipyDiffusionInterface):

    """
    Uses SHORE [Merlet13]_ to generate the fODF of DWIs. The interface uses
    :py:mod:`dipy`, as explained in `dipy's SHORE example
    <http://nipy.org/dipy/examples_built/reconst_shore.html#merlet2013>`_.

    .. [Merlet2013]	Merlet S. et. al, Medical Image Analysis, 2013.
    “Continuous diffusion signal, EAP and ODF estimation via Compressive Sensing in diffusion MRI”


    Example
    -------

    >>> from cmp.interfaces.dipy import SHORE
    >>> asm = SHORE(radial_order=radial_order,zeta=zeta, lambdaN=lambdaN, lambdaL=lambdaL)
    >>> asm.inputs.in_file = '4d_dwi.nii'
    >>> asm.inputs.in_bval = 'bvals'
    >>> asm.inputs.in_bvec = 'bvecs'
    >>> res = asm.run() # doctest: +SKIP
    """
    input_spec = SHOREInputSpec
    output_spec = SHOREOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst.shore import ShoreModel
        from dipy.data import get_sphere, default_sphere
        from dipy.reconst.odf import gfa
        from dipy.reconst.csdeconv import odf_sh_to_sharp
        from dipy.reconst.shm import sh_to_sf, sf_to_sh
        from dipy.core.ndindex import ndindex
        import nibabel as nib

        # import marshal as pickle
        import pickle as pickle
        import gzip

        import multiprocessing as mp

        img = nb.load(self.inputs.in_file)
        imref = nb.four_to_three(img)[0]
        affine = img.affine

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects
            around the edge of the image"""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.in_mask):
            msk = clipMask(nb.load(self.inputs.in_mask).get_data().astype('float32'))
        else:
            msk = clipMask(np.ones(imref.shape).astype('float32'))

        data = img.get_data().astype(np.float32)
        data[msk==0] *=0

        hdr = imref.header.copy()

        gtab = self._get_gradient_table()

        # if isdefined(self.inputs.response):
        #     resp_file = np.loadtxt(self.inputs.response)
        #
        #     response = (np.array(resp_file[0:3]), resp_file[-1])
        #     ratio = response[0][1] / response[0][0]
        #
        #     if abs(ratio - 0.2) > 0.1:
        #         IFLOGGER.warn(('Estimated response is not prolate enough. '
        #                        'Ratio=%0.3f.') % ratio)
        # else:
        #     response, ratio, counts = auto_response(gtab, data, fa_thr=0.5, return_number_of_voxels=True)
        #     IFLOGGER.info("response: ")
        #     IFLOGGER.info(response)
        #     IFLOGGER.info("ratio: %g"%ratio)
        #     IFLOGGER.info("nbr_voxel_used: %g"%counts)
        #
        #     if abs(ratio - 0.2) > 0.1:
        #         IFLOGGER.warn(('Estimated response is not prolate enough. '
        #                        'Ratio=%0.3f.') % ratio)

        sphere = get_sphere('symmetric724')
        shore_model = ShoreModel(gtab, radial_order=self.inputs.radial_order, zeta=self.inputs.zeta, lambdaN=self.inputs.lambdaN, lambdaL=self.inputs.lambdaL)

        # IFLOGGER.info('Fitting CSD model')
        # csd_fit = csd_model.fit(data, msk)

        f = gzip.open(op.abspath('shoremodel.pklz'), 'wb')
        pickle.dump(shore_model, f, -1)
        f.close()

        lmax = self.inputs.radial_order
        datashape=data.shape
        dimsODF=list(datashape)
        dimsODF[3]=int((lmax+1)*(lmax+2)/2)
        shODF=np.zeros(dimsODF)
        GFA=np.zeros(dimsODF[:3])
        MSD=np.zeros(dimsODF[:3])

        if self.inputs.tracking_processing_tool == "mrtrix":
            basis = 'mrtrix'
        else:
            basis = None

        # calculate odf per slice
        IFLOGGER.info('Fitting SHORE model')
        for i in ndindex(data.shape[:1]):
            IFLOGGER.info("Processing slice #%i " % i)
            start_time = time.time()
            shorefit   = shore_model.fit(data[i])
            sliceODF   = shorefit.odf(sphere)
            sliceGMSD  = shorefit.msd()
            sliceGFA   = gfa(sliceODF)
            shODF[i]   = sf_to_sh(sliceODF,sphere,sh_order=lmax,basis_type=basis)
            GFA[i]     = np.nan_to_num(sliceGFA)
            MSD[i]     = np.nan_to_num(sliceGMSD)
            IFLOGGER.info("Computation Time (slice %s): "%str(i) + str(time.time() - start_time) + " seconds")

        shFODF = odf_sh_to_sharp(shODF,sphere,basis='mrtrix',ratio=0.2, sh_order=lmax, lambda_=1.0, tau=0.1, r2_term=True)

        IFLOGGER.info('Save Spherical Harmonics / MSD / GFA images')

        nib.Nifti1Image(GFA,affine).to_filename(op.abspath('shore_gfa.nii.gz'))
        nib.Nifti1Image(MSD,affine).to_filename(op.abspath('shore_msd.nii.gz'))
        nib.Nifti1Image(shODF,affine).to_filename(op.abspath('shore_dodf.nii.gz'))
        nib.Nifti1Image(shFODF,affine).to_filename(op.abspath('shore_fodf.nii.gz'))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['model'] = op.abspath('shoremodel.pklz')
        outputs['fod'] = op.abspath('shore_fodf.nii.gz')
        outputs['GFA'] = op.abspath('shore_gfa.nii.gz')
        return outputs

class TensorInformedEudXTractographyInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc=('input diffusion data'))
    in_fa = File(exists=True, mandatory=True, desc=('input FA'))
    in_model = File(exists=True, mandatory=True, desc=('input Tensor model extracted from.'))
    tracking_mask = File(exists=True, mandatory=True,
                         desc=('input mask within which perform tracking'))
    seed_mask = InputMultiPath(File(exists=True), mandatory=True, desc='ROI files registered to diffusion space')
    fa_thresh = traits.Float(0.2, mandatory=True, usedefault=True,
                              desc=('FA threshold to build the tissue classifier'))
    max_angle = traits.Float(25.0, mandatory=True, usedefault=True,
                             desc=('Maximum angle'))
    step_size = traits.Float(0.5, mandatory=True, usedefault=True,
                             desc=('Step size'))
    multiprocess = traits.Bool(True, mandatory=True, usedefault=True,
                               desc=('use multiprocessing'))
    save_seeds = traits.Bool(False, mandatory=True, usedefault=True,
                             desc=('save seeding voxels coordinates'))
    num_seeds = traits.Int(10000, mandatory=True, usedefault=True,
                           desc=('desired number of tracks in tractography'))
    out_prefix = traits.Str(desc=('output prefix for file names'))


class TensorInformedEudXTractographyOutputSpec(TraitedSpec):
    tracks = File(desc='TrackVis file containing extracted streamlines')
    out_seeds = File(desc=('file containing the (N,3) *voxel* coordinates used'
                           ' in seeding.'))


class TensorInformedEudXTractography(DipyBaseInterface):

    """
    Streamline tractography using Deterrministic Maximum Direction Getter

    Example
    -------

    >>> from cmp3.interfaces import dipy as ndp
    >>> track = ndp.DeterministicMaximumDirectionGetterTractography()
    >>> track.inputs.in_file = '4d_dwi.nii'
    >>> track.inputs.in_model = 'model.pklz'
    >>> track.inputs.tracking_mask = 'dilated_wm_mask.nii'
    >>> res = track.run() # doctest: +SKIP
    """
    input_spec = TensorInformedEudXTractographyInputSpec
    output_spec = TensorInformedEudXTractographyOutputSpec

    def _run_interface(self, runtime):
        from dipy.tracking import utils
        from dipy.direction import peaks_from_model
        from dipy.tracking.local import ThresholdTissueClassifier, BinaryTissueClassifier
        from dipy.tracking.eudx import EuDX
        from dipy.data import get_sphere, default_sphere
        from dipy.io.trackvis import save_trk
        # import marshal as pickle
        import pickle as pickle
        import gzip

        if (not (isdefined(self.inputs.in_model)) ):
            raise RuntimeError(('in_model should be supplied'))


        img = nb.load(self.inputs.in_file)
        imref = nb.four_to_three(img)[0]
        affine = img.affine

        data = img.get_data().astype(np.float32)
        hdr = imref.header.copy()
        hdr.set_data_dtype(np.float32)
        hdr['data_type'] = 16

        trkhdr = nb.trackvis.empty_header()
        trkhdr['dim'] = imref.get_data().shape
        trkhdr['voxel_size'] = imref.get_header().get_zooms()[:3]
        trkhdr['voxel_order'] = 'ras'
        trackvis_affine = utils.affine_for_trackvis(trkhdr['voxel_size'])

        sphere = get_sphere('repulsion724')

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects
            around the edge of the image"""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.tracking_mask):
            IFLOGGER.info('Loading Tracking Mask')
            tmsk = clipMask(nb.load(self.inputs.tracking_mask).get_data())
            tmsk[tmsk > 0] = 1
            tmsk[tmsk < 0] = 0
        else:
            tmsk = np.ones(imref.shape)

        seeds = self.inputs.num_seeds

        if isdefined(self.inputs.seed_mask[0]):
            IFLOGGER.info('Loading Seed Mask')
            seedmsk = clipMask(nb.load(self.inputs.seed_mask[0]).get_data())
            assert(seedmsk.shape == data.shape[:3])
            seedmsk[seedmsk > 0] = 1
            seedmsk[seedmsk < 1] = 0
            seedps = np.array(np.where(seedmsk == 1), dtype=np.float32).T
            vseeds = seedps.shape[0]
            nsperv = (seeds // vseeds) + 1
            IFLOGGER.info(('Seed mask is provided (%d voxels inside '
                           'mask), computing seeds (%d seeds/voxel).') %
                          (vseeds, nsperv))
            if nsperv > 1:
                IFLOGGER.info(('Needed %d seeds per selected voxel '
                               '(total %d).') % (nsperv, vseeds))
                seedps = np.vstack(np.array([seedps] * nsperv))
                voxcoord = seedps + np.random.uniform(-1, 1, size=seedps.shape)
                nseeds = voxcoord.shape[0]
                seeds = affine.dot(np.vstack((voxcoord.T,
                                              np.ones((1, nseeds)))))[:3, :].T

                if self.inputs.save_seeds:
                    np.savetxt(self._gen_filename('seeds', ext='.txt'), seeds)

            tseeds = utils.seeds_from_mask(seedmsk, density=2, affine=affine)

        IFLOGGER.info('Loading and masking FA')
        img_fa = nb.load(self.inputs.in_fa)
        fa = img_fa.get_data().astype(np.float32)
        fa = fa * tmsk

        IFLOGGER.info('Saving masked FA')
        hdr.set_data_shape(fa.shape)
        nb.Nifti1Image(fa.astype(np.float32), affine, hdr).to_filename(self._gen_filename('fa_masked'))

        IFLOGGER.info('Building Tissue Classifier')
        # classifier = ThresholdTissueClassifier(fa,self.inputs.fa_thresh)
        classifier = BinaryTissueClassifier(tmsk)

        IFLOGGER.info('Loading tensor model')
        f = gzip.open(self.inputs.in_model, 'rb')
        tensor_model = pickle.load(f)
        f.close()

        IFLOGGER.info('Generating peaks from tensor model')
        pfm = peaks_from_model(model=tensor_model,
                       data=data,
                       sphere=sphere,
                       relative_peak_threshold=.2,
                       min_separation_angle=25,
                       mask=tmsk,
                       return_sh=True,
                       #sh_basis_type=args.basis,
                       sh_order=8,
                       normalize_peaks=False, ##changed
                       parallel=True)

        IFLOGGER.info('Performing tensor-informed EuDX tractography')

        streamlines = EuDX( pfm.peak_values,
                            pfm.peak_indices,
                            seeds=seeds,
                            affine=affine,
                            odf_vertices=sphere.vertices,
                            step_sz=self.inputs.step_size,
                            a_low=self.inputs.fa_thresh)

        IFLOGGER.info('Saving tracks')
        save_trk(self._gen_filename('tracked', ext='.trk'), streamlines, affine, fa.shape)

        # IFLOGGER.info('Loading CSD model and fitting')
        # f = gzip.open(self.inputs.in_model, 'rb')
        # csd_model = pickle.load(f)
        # f.close()

        # csd_fit = csd_model.fit(data, mask=tmsk)

        # if self.inputs.algo == 'deterministic':
        #     dg = DeterministicMaximumDirectionGetter.from_shcoeff(csd_fit.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)
        # else:
        #     dg = ProbabilisticDirectionGetter.from_shcoeff(csd_fit.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)

        # IFLOGGER.info(('Performing %s tractography') % (self.inputs.algo))

        # streamlines = LocalTracking(dg, classifier, tseeds, affine, step_size=self.inputs.step_size)

        # IFLOGGER.info('Saving tracks')
        # save_trk(self._gen_filename('tracked', ext='.trk'), streamlines, affine, fa.shape)

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
    algo = traits.Enum(["deterministic","probabilistic"], usedefault=True,
                              desc=('Use either deterministic maximum (default) or probabilistic direction getter tractography'))
    recon_model = traits.Enum(["CSD","SHORE"], usedefault=True, desc=('Use either fODFs from CSD (default) or SHORE models'))
    recon_order = traits.Int(8)
    use_act = traits.Bool(False, desc=('Use FAST for partial volume estimation and Anatomically-Constrained Tractography (ACT) tissue classifier'))
    fast_number_of_classes = traits.Int(3, desc=('Number of tissue classes used by FAST for Anatomically-Constrained Tractography (ACT)'))
    in_file = File(exists=True, mandatory=True, desc=('input diffusion data'))
    fod_file = File(exists=True, desc=('input fod file (if SHORE)'))
    in_fa = File(exists=True, mandatory=True, desc=('input FA'))
    in_partial_volume_files = InputMultiPath(File(exists=True), desc='Partial volume estimation result files (required if performing ACT)')
    # in_t1 = File(exists=True, desc=('input T1w (required if performing ACT)'))
    in_model = File(exists=True, mandatory=True, desc=('input f/d-ODF model extracted from.'))
    tracking_mask = File(exists=True, mandatory=True,
                         desc=('input mask within which perform tracking'))
    seed_mask = InputMultiPath(File(exists=True), mandatory=True, desc='ROI files registered to diffusion space')
    fa_thresh = traits.Float(0.2, mandatory=True, usedefault=True,
                              desc=('FA threshold to build the tissue classifier'))
    max_angle = traits.Float(25.0, mandatory=True, usedefault=True,
                             desc=('Maximum angle'))
    step_size = traits.Float(0.5, mandatory=True, usedefault=True,
                             desc=('Step size'))
    multiprocess = traits.Bool(True, mandatory=True, usedefault=True,
                               desc=('use multiprocessing'))
    save_seeds = traits.Bool(False, mandatory=True, usedefault=True,
                             desc=('save seeding voxels coordinates'))
    num_seeds = traits.Int(10000, mandatory=True, usedefault=True,
                           desc=('desired number of tracks in tractography'))
    out_prefix = traits.Str(desc=('output prefix for file names'))


class DirectionGetterTractographyOutputSpec(TraitedSpec):
    tracks = File(desc='TrackVis file containing extracted streamlines')
    out_seeds = File(desc=('file containing the (N,3) *voxel* coordinates used'
                           ' in seeding.'))


class DirectionGetterTractography(DipyBaseInterface):

    """
    Streamline tractography using Deterrministic Maximum Direction Getter

    Example
    -------

    >>> from cmp3.interfaces import dipy as ndp
    >>> track = ndp.DeterministicMaximumDirectionGetterTractography()
    >>> track.inputs.in_file = '4d_dwi.nii'
    >>> track.inputs.in_model = 'model.pklz'
    >>> track.inputs.tracking_mask = 'dilated_wm_mask.nii'
    >>> res = track.run() # doctest: +SKIP
    """
    input_spec = DirectionGetterTractographyInputSpec
    output_spec = DirectionGetterTractographyOutputSpec

    def _run_interface(self, runtime):
        from dipy.tracking import utils
        from dipy.direction import DeterministicMaximumDirectionGetter, ProbabilisticDirectionGetter
        from dipy.tracking.local import ThresholdTissueClassifier, BinaryTissueClassifier, ActTissueClassifier, LocalTracking, CmcTissueClassifier, ParticleFilteringTracking
        from dipy.reconst.peaks import peaks_from_model
        from dipy.data import get_sphere, default_sphere
        from dipy.io.trackvis import save_trk
        # import marshal as pickle
        import pickle as pickle
        import gzip

        if (not (isdefined(self.inputs.in_model)) ):
            raise RuntimeError(('in_model should be supplied'))


        img = nb.load(self.inputs.in_file)
        imref = nb.four_to_three(img)[0]
        affine = img.affine

        data = img.get_data().astype(np.float32)
        hdr = imref.header.copy()
        hdr.set_data_dtype(np.float32)
        hdr['data_type'] = 16

        trkhdr = nb.trackvis.empty_header()
        trkhdr['dim'] = imref.get_data().shape
        trkhdr['voxel_size'] = imref.get_header().get_zooms()[:3]
        trkhdr['voxel_order'] = 'ras'
        trackvis_affine = utils.affine_for_trackvis(trkhdr['voxel_size'])

        sphere = get_sphere('repulsion724')

        def clipMask(mask):
            """This is a hack until we fix the behaviour of the tracking objects
            around the edge of the image"""
            out = mask.copy()
            index = [slice(None)] * out.ndim
            for i in range(len(index)):
                idx = index[:]
                idx[i] = [0, -1]
                out[idx] = 0.
            return out

        if isdefined(self.inputs.tracking_mask):
            IFLOGGER.info('Loading Tracking Mask')
            tmsk = clipMask(nb.load(self.inputs.tracking_mask).get_data())
            tmsk[tmsk > 0] = 1
            tmsk[tmsk < 0] = 0
        else:
            tmsk = np.ones(imref.shape)

        seeds = self.inputs.num_seeds

        if isdefined(self.inputs.seed_mask[0]):
            IFLOGGER.info('Loading Seed Mask')
            seedmsk = clipMask(nb.load(self.inputs.seed_mask[0]).get_data())
            assert(seedmsk.shape == data.shape[:3])
            seedmsk[seedmsk > 0] = 1
            seedmsk[seedmsk < 1] = 0
            seedps = np.array(np.where(seedmsk == 1), dtype=np.float32).T
            vseeds = seedps.shape[0]
            nsperv = (seeds // vseeds) + 1
            IFLOGGER.info(('Seed mask is provided (%d voxels inside '
                           'mask), computing seeds (%d seeds/voxel).') %
                          (vseeds, nsperv))
            if nsperv > 1:
                IFLOGGER.info(('Needed %d seeds per selected voxel '
                               '(total %d).') % (nsperv, vseeds))
                seedps = np.vstack(np.array([seedps] * nsperv))
                voxcoord = seedps + np.random.uniform(-1, 1, size=seedps.shape)
                nseeds = voxcoord.shape[0]
                seeds = affine.dot(np.vstack((voxcoord.T,
                                              np.ones((1, nseeds)))))[:3, :].T

                if self.inputs.save_seeds:
                    np.savetxt(self._gen_filename('seeds', ext='.txt'), seeds)

            tseeds = utils.seeds_from_mask(seedmsk, density=2, affine=affine)

        IFLOGGER.info('Loading and masking FA')
        img_fa = nb.load(self.inputs.in_fa)
        fa = img_fa.get_data().astype(np.float32)
        fa = fa * tmsk

        IFLOGGER.info('Saving masked FA')
        hdr.set_data_shape(fa.shape)
        nb.Nifti1Image(fa.astype(np.float32), affine, hdr).to_filename(self._gen_filename('fa_masked'))

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

            img_pve_csf = nb.load(self.inputs.in_partial_volume_files[0])
            img_pve_gm = nb.load(self.inputs.in_partial_volume_files[1])
            img_pve_wm = nb.load(self.inputs.in_partial_volume_files[2])

            voxel_size = np.average(img_pve_wm.get_header()['pixdim'][1:4])
            step_size = self.inputs.step_size

            cmc_classifier = CmcTissueClassifier.from_pve(img_pve_wm.get_data(),
                                                          img_pve_gm.get_data(),
                                                          img_pve_csf.get_data(),
                                                          step_size=step_size,
                                                          average_voxel_size=voxel_size)

            # background = np.ones(imref.shape)
            # pve_sum = np.zeros(imref.shape)
            # for pve_file in self.inputs.in_partial_volume_files:
            #     pve_img = nb.load(pve_file)
            #     pve_data = pve_img.get_data().astype(np.float32)
            #     pve_sum = pve_sum + pve_data
            #
            # background[pve_sum>0] = 0
            #
            # include_map = np.zeros(imref.shape)
            # exclude_map = np.zeros(imref.shape)
            # for pve_file in self.inputs.in_partial_volume_files:
            #     pve_img = nb.load(pve_file)
            #     pve_data = pve_img.get_data().astype(np.float32)
            #     if "pve_0" in pve_file:# CSF
            #         exclude_map = pve_data
            #     elif "pve_1" in pve_file:# GM
            #         include_map = pve_data
            #
            # include_map[background>0] = 1
            # IFLOGGER.info('Building ACT Tissue Classifier')
            # classifier = ActTissueClassifier(include_map,exclude_map)
        else:
            IFLOGGER.info('Building Binary Tissue Classifier')
            # classifier = ThresholdTissueClassifier(fa,self.inputs.fa_thresh)
            classifier = BinaryTissueClassifier(tmsk)

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
                           min_separation_angle=25,
                           mask=tmsk,
                           return_sh=True,
                           #sh_basis_type=args.basis,
                           sh_order=self.inputs.recon_order,
                           normalize_peaks=False, ##changed
                           parallel=True)

            if self.inputs.algo == 'deterministic':
                dg = DeterministicMaximumDirectionGetter.from_shcoeff(pfm.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)
            else:
                dg = ProbabilisticDirectionGetter.from_shcoeff(pfm.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)

        else:
            from dipy.io.image import load_nifti

            IFLOGGER.info('Loading SHORE FOD')
            sh = nb.load(self.inputs.fod_file).get_data()
            sh = np.nan_to_num(sh)
            IFLOGGER.info('Generating peaks from SHORE model')
            if self.inputs.algo == 'deterministic':
                dg = DeterministicMaximumDirectionGetter.from_shcoeff(sh, max_angle=self.inputs.max_angle, sphere=sphere)
            else:
                dg = ProbabilisticDirectionGetter.from_shcoeff(sh, max_angle=self.inputs.max_angle, sphere=sphere)

        if not self.inputs.use_act:

            IFLOGGER.info(('Performing %s tractography') % (self.inputs.algo))

            streamlines = LocalTracking(dg, classifier, tseeds, affine, step_size=self.inputs.step_size, max_cross=1)

            IFLOGGER.info('Saving tracks')
            save_trk(self._gen_filename('tracked', ext='.trk'), streamlines, affine, fa.shape)

        else:
            # Particle Filtering Tractography
            pft_streamline_generator = ParticleFilteringTracking(dg,
                                                                 cmc_classifier,
                                                                 tseeds,
                                                                 affine,
                                                                 max_cross=1,
                                                                 step_size=step_size,
                                                                 maxlen=1000,
                                                                 pft_back_tracking_dist=2,
                                                                 pft_front_tracking_dist=1,
                                                                 particle_count=15,
                                                                 return_all=False)

            #streamlines = list(pft_streamline_generator)
            from dipy.tracking.streamline import Streamlines
            streamlines = Streamlines(pft_streamline_generator)

            save_trk(self._gen_filename('tracked', ext='.trk'), streamlines, affine, fa.shape)

        # IFLOGGER.info('Loading CSD model and fitting')
        # f = gzip.open(self.inputs.in_model, 'rb')
        # csd_model = pickle.load(f)
        # f.close()

        # csd_fit = csd_model.fit(data, mask=tmsk)

        # if self.inputs.algo == 'deterministic':
        #     dg = DeterministicMaximumDirectionGetter.from_shcoeff(csd_fit.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)
        # else:
        #     dg = ProbabilisticDirectionGetter.from_shcoeff(csd_fit.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)

        # IFLOGGER.info(('Performing %s tractography') % (self.inputs.algo))

        # streamlines = LocalTracking(dg, classifier, tseeds, affine, step_size=self.inputs.step_size)

        # IFLOGGER.info('Saving tracks')
        # save_trk(self._gen_filename('tracked', ext='.trk'), streamlines, affine, fa.shape)

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

class MAPMRIInputSpec(DipyBaseInterfaceInputSpec):

    laplacian_regularization = traits.Bool(True, usedefault=True, desc = ('Apply laplacian regularization'))

    laplacian_weighting= traits.Float(0.05, usedefault=True, desc = ('Regularization weight'))

    positivity_constraint = traits.Bool(True, usedefault=True, desc = ('Apply positivity constraint'))

    radial_order = traits.Int(8, usedefault=True,
                          desc=('maximal shperical harmonics order'))

    small_delta = traits.Float(0.02, mandatory=True,
                          desc=('Small data for gradient table'))

    big_delta = traits.Float(0.5, mandatory=True,
                          desc=('Small data for gradient table'))

class MAPMRIOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the MAP-MRI model fitted.')
    rtop_file = File(desc=('rtop output file name'))
    rtap_file = File(desc=('rtap output file name'))
    rtpp_file = File(desc=('rtpp output file name'))
    msd_file = File(desc=('msd output file name'))
    qiv_file = File(desc=('qiv output file name'))
    ng_file = File(desc=('ng output file name'))
    ng_perp_file = File(desc=('ng perpendicular output file name'))
    ng_para_file = File(desc=('ng parallel output file name'))


class MAPMRI(DipyDiffusionInterface):
    '''MAP MRI settings'''
    '''

    .. check http://nipy.org/dipy/examples_built/reconst_mapmri.html#example-reconst-mapmri
    for reference on the settings


    Example
    -------

    >>> from cmp.interfaces.dipy import MAPMRI
    >>> mapmri = MAPMRI()
    >>> mapmri.inputs.in_file = '4d_dwi.nii'
    >>> mapmri.inputs.in_bval = 'bvals'
    >>> mapmri.inputs.in_bvec = 'bvecs'
    >>> res = mapmri.run() # doctest: +SKIP
    """
    '''
    input_spec = MAPMRIInputSpec
    output_spec = MAPMRIOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst import mapmri
        from dipy.data import fetch_cenir_multib, read_cenir_multib, get_sphere,  default_sphere
        from dipy.core.gradients import gradient_table
        # import marshal as pickle
        import pickle as pickle
        import gzip

        img = nb.load(self.inputs.in_file)
        imref = nb.four_to_three(img)[0]
        affine = img.affine

        data = img.get_data().astype(np.float32)

        hdr = imref.header.copy()

        gtab = self._get_gradient_table()
        gtab = gradient_table(bvals=gtab.bvals, bvecs=gtab.bvecs,
                              small_delta=self.inputs.small_delta,
                              big_delta=self.inputs.big_delta)

        map_model_both_aniso = mapmri.MapmriModel(gtab,
                                                  radial_order = self.inputs.radial_order,
                                                  anisotropic_scaling = True,
                                                  laplacian_regularization = self.inputs.laplacian_regularization,
                                                  laplacian_weighting = self.inputs.laplacian_weighting,
                                                  positivity_constraint = self.inputs.positivity_constraint
                                                  )

        IFLOGGER.info('Fitting MAP-MRI model')
        mapfit_both_aniso = map_model_both_aniso.fit(data)

        '''maps'''
        maps = {}
        maps["rtop"] = mapfit_both_aniso.rtop() #'''1/Volume of pore'''
        maps["rtap"] = mapfit_both_aniso.rtap()  #'''1/AREA ...'''
        maps["rtpp"] = mapfit_both_aniso.rtpp()  #'''1/length ...'''
        maps["msd"] = mapfit_both_aniso.msd()  #'''similar to mean diffusivity'''
        maps["qiv"] = mapfit_both_aniso.qiv() #'''almost reciprocal of rtop'''
        maps["ng"] = mapfit_both_aniso.ng()  #'''general non Gaussianity'''
        maps["ng_perp"] = mapfit_both_aniso.ng_perpendicular()  #'''perpendicular to main direction (likely to be non gaussian in white matter)'''
        maps["ng_para"] = mapfit_both_aniso.ng_parallel()  #'''along main direction (likely to be gaussian)'''

        ''' The most related to white matter anisotropy are:
            rtpp, for anisotropy
            rtap, for axonal diameter
            MIGHT BE WORTH DIVINDING RTPP BY (1/RTOP): THAT IS:
            length/VOLUME = RTOP/RTPP
        '''

        f = gzip.open(self._gen_filename('mapmri', ext='.pklz'), 'wb')
        pickle.dump(csd_model, f, -1)
        f.close()

        #"rtop", "rtap", "rtpp", "msd", "qiv", "ng", "ng_perp", "ng_para"
        for metric, data in sampleDict.items():
            out_name = self._gen_filename(metric)
            nb.Nifti1Image(data, affine).to_filename(out_name)
            IFLOGGER.info('MAP-MRI {metric} image saved as {i}'.format(i=out_name, metric=metric))
            IFLOGGER.info('Shape :')
            IFLOGGER.info(data.shape)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['model'] = self._gen_filename('mapmri', ext='.pklz')

        for metric in ["rtop", "rtap", "rtpp", "msd", "qiv", "ng", "ng_perp", "ng_para"]:
            outputs["{}_file".format(metric)] = self._gen_filename(metric)
        return outputs
