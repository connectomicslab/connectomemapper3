# -*- coding: utf-8 -*-
"""
Interfaces to the algorithms in dipy

"""
from __future__ import print_function, division, unicode_literals, absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str, open

import os.path as op

import numpy as np
import nibabel as nb
import gzip

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
    sh_order = traits.Int(8, usedefault=True,
                          desc=('maximal shperical harmonics order'))
    save_fods = traits.Bool(True, usedefault=True,
                            desc=('save fODFs in file'))
    out_fods = File(desc=('fODFs output file name'))


class CSDOutputSpec(TraitedSpec):
    model = File(desc='Python pickled object of the CSD model fitted.')
    out_fods = File(desc=('fODFs output file name'))


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
            response, _, counts = auto_response(gtab, data, fa_thr=0.7, return_number_of_voxels=True)
            IFLOGGER.info("nbr_voxel_used: %g"%counts)

        sphere = get_sphere('repulsion724')
        csd_model = ConstrainedSphericalDeconvModel(gtab, response, sh_order=self.inputs.sh_order, reg_sphere=sphere, lambda_=np.sqrt(1. / 2))

        # IFLOGGER.info('Fitting CSD model')
        # csd_fit = csd_model.fit(data, msk)

        f = gzip.open(self._gen_filename('csdmodel', ext='.pklz'), 'wb')
        pickle.dump(csd_model, f, -1)
        f.close()

        # if self.inputs.save_fods:
        #     # isphere = get_sphere('symmetric724')
        #     fods = csd_fit.odf(default_sphere)
        #     IFLOGGER.info(fods)
        #     IFLOGGER.info(fods.shape)

        #     nb.Nifti1Image(fods, img.affine,None).to_filename(self._gen_filename('fods'))


        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['model'] = self._gen_filename('csdmodel', ext='.pklz')
        if self.inputs.save_fods:
            outputs['out_fods'] = self._gen_filename('fods')
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

    in_file = File(exists=True, mandatory=True, desc=('input diffusion data'))
    in_fa = File(exists=True, mandatory=True, desc=('input FA'))
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
        from dipy.tracking.local import ThresholdTissueClassifier, BinaryTissueClassifier, LocalTracking
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

        IFLOGGER.info('Building Tissue Classifier')
        # classifier = ThresholdTissueClassifier(fa,self.inputs.fa_thresh)
        classifier = BinaryTissueClassifier(tmsk)

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
                       sh_order=8,
                       normalize_peaks=False, ##changed
                       parallel=True)

        if self.inputs.algo == 'deterministic':
            dg = DeterministicMaximumDirectionGetter.from_shcoeff(pfm.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)
        else:
            dg = ProbabilisticDirectionGetter.from_shcoeff(pfm.shm_coeff, max_angle=self.inputs.max_angle, sphere=sphere)

        IFLOGGER.info(('Performing %s tractography') % (self.inputs.algo))

        streamlines = LocalTracking(dg, classifier, tseeds, affine, step_size=self.inputs.step_size, max_cross=1)

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

class MAPMRIInputSpec(DipyBaseInterfaceInputSpec):

    laplacian_regularization = traits.Bool(True, usedefault=True, desc = ('Apply laplacian regularization'))

    laplacian_weighting= traits.Float(0.05, usedefault=True, desc = ('Regularization weight'))

    positivity_constraint = traits.Bool(True, usedefault=True, desc = ('Apply positivity constraint'))

    radial_order = traits.Int(8, usedefault=True,
                          desc=('maximal shperical harmonics order'))

    small_delta = traits.Int(0.02, mandatory=True,
                          desc=('Small data for gradient table'))

    big_delta = traits.Int(0.5, mandatory=True,
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
