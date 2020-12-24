import sys
import os
from os import path as op


def test_ExtractPVEsFrom5TT(subject, session, in_5tt_image, ref_image, base_dir):
    from cmtklib.diffusion import ExtractPVEsFrom5TT
    from nipype import Node

    pve_extracter = Node(interface=ExtractPVEsFrom5TT(),
                         name='pve_extracter', base_dir=base_dir)
    pve_extracter.inputs.in_5tt = in_5tt_image
    pve_extracter.inputs.ref_image = ref_image
    pve_extracter.inputs.pve_csf_file = '%s_%s_class-CSF_probtissue.nii.gz' % (
        subject, session)
    pve_extracter.inputs.pve_wm_file = '%s_%s_class-WM_probtissue.nii.gz' % (
        subject, session)
    pve_extracter.inputs.pve_gm_file = '%s_%s_class-GM_probtissue.nii.gz' % (
        subject, session)

    eg = pve_extracter.run()

    return eg


# def test_dipy_PFT_pipeline(diffusion_img, gtab, gmwmi, pve_results):
#     import numpy as np
#
#     from dipy.data import default_sphere
#     from dipy.direction import ProbabilisticDirectionGetter
#     from dipy.io.trackvis import save_trk
#     from dipy.reconst.csdeconv import (ConstrainedSphericalDeconvModel,
#                                        auto_response)
#     from dipy.tracking.local import LocalTracking, ParticleFilteringTracking
#     from dipy.tracking import utils
#     # from dipy.viz import window, actor
#     # from dipy.viz.colormap import line_colors
#
#     img_pve_csf = pve_results.outputs.pve_csf_file
#     img_pve_gm = pve_results.outputs.pve_gm_file
#     img_pve_wm = pve_results.outputs.pve_wm_file
#
#     data = diffusion_img.get_data()
#     affine = hardi_img.get_affine()
#     shape = labels.shape
#
#     response, ratio = auto_response(gtab, data, roi_radius=10, fa_thr=0.7)
#     csd_model = ConstrainedSphericalDeconvModel(gtab, response)
#     csd_fit = csd_model.fit(data, mask=img_pve_wm.get_data())
#
#     dg = ProbabilisticDirectionGetter.from_shcoeff(csd_fit.shm_coeff,
#                                                    max_angle=20.,
#                                                    sphere=default_sphere)
#
#     from dipy.tracking.local import CmcTissueClassifier
#     from dipy.tracking.streamline import Streamlines
#
#     voxel_size = np.average(img_pve_wm.get_header()['pixdim'][1:4])
#     step_size = 0.2
#
#     cmc_classifier = CmcTissueClassifier.from_pve(img_pve_wm.get_data(),
#                                                   img_pve_gm.get_data(),
#                                                   img_pve_csf.get_data(),
#                                                   step_size=step_size,
#                                                   average_voxel_size=voxel_size)
#
#     # seeds are place in voxel of the corpus callosum containing only white matter
#     seed_mask = labels == 2
#     seed_mask[img_pve_wm.get_data() < 0.5] = 0
#     seeds = utils.seeds_from_mask(seed_mask, density=2, affine=affine)
#
#     # Particle Filtering Tractography
#     pft_streamline_generator = ParticleFilteringTracking(dg,
#                                                          cmc_classifier,
#                                                          seeds,
#                                                          affine,
#                                                          max_cross=1,
#                                                          step_size=step_size,
#                                                          maxlen=1000,
#                                                          pft_back_tracking_dist=2,
#                                                          pft_front_tracking_dist=1,
#                                                          particle_count=15,
#                                                          return_all=False)
#
#     #streamlines = list(pft_streamline_generator)
#     streamlines = Streamlines(pft_streamline_generator)
#     save_trk("pft_streamline.trk", streamlines, affine, shape)

if __name__ == '__main__':
    subjects_dir = '/media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo/derivatives/freesurfer'
    subject_id = 'sub-A006_ses-20170523161523'
    base_dir = '~/Desktop/dipy_pft_tests'
    subject = 'sub-A006'
    session = 'ses-20170523161523'
    bids_dataset = '/media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo'

    in_5tt_image = op.join(bids_dataset, 'derivatives/cmp', subject, session,
                           'tmp/diffusion_pipeline/preprocessing_stage/mrtrix_5tt', 'mrtrix_5tt.nii.gz')
    ref_image = op.join(bids_dataset, 'derivatives/cmp', subject, session,
                        'tmp/diffusion_pipeline/preprocessing_stage/mr_convert_T1', 'anat.nii.gz')

    test_ExtractPVEsFrom5TT(subject, session, in_5tt_image,
                            ref_image, base_dir=base_dir)
