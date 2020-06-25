import sys
import os
from os import path as op


def test_combine_parcellation(subjects_dir, subject_id, input_rois, lh_subfields, rh_subfields, brainstem, thalamus,
                              base_dir):
    from cmtklib.parcellation import CombineParcellations
    from nipype import Node

    combiner = Node(interface=CombineParcellations(),
                    name='combine_parcellations', base_dir=base_dir)
    combiner.inputs.subjects_dir = subjects_dir
    combiner.inputs.subject_id = subject_id
    combiner.inputs.input_rois = input_rois
    combiner.inputs.lh_hippocampal_subfields = lh_subfields
    combiner.inputs.rh_hippocampal_subfields = rh_subfields
    combiner.inputs.brainstem_structures = brainstem
    combiner.inputs.thalamus_nuclei = thalamus
    combiner.inputs.create_colorLUT = True
    combiner.inputs.create_graphml = True

    # Execute the node
    combiner.run()


def test_parcellate_hippocampal_subfields(subjects_dir, subject_id, base_dir):
    from cmtklib.parcellation import ParcellateHippocampalSubfields
    from nipype import Node, Workflow

    parcellate_hipposubfields = Node(interface=ParcellateHippocampalSubfields(), name='parcellate_hipposubfield',
                                     base_dir=base_dir)
    parcellate_hipposubfields.inputs.subjects_dir = subjects_dir
    parcellate_hipposubfields.inputs.subject_id = subject_id

    # Execute the node
    parcellate_hipposubfields.run()

    print('Output 1: %s' % (parcellate_hipposubfields.outputs.lh_hipposubfields))
    print('Output 2: %s' % (parcellate_hipposubfields.outputs.rh_hipposubfields))


def test_parcellate_brainstem(subjects_dir, subject_id, base_dir):
    from cmtklib.parcellation import ParcellateBrainstemStructures
    from nipype import Node, Workflow

    parcellate_brainstem = Node(interface=ParcellateBrainstemStructures(), name='parcellate_brainstem',
                                base_dir=base_dir)
    parcellate_brainstem.inputs.subjects_dir = subjects_dir
    parcellate_brainstem.inputs.subject_id = subject_id

    # Execute the node
    parcellate_brainstem.run()

    print('Output : %s' % (parcellate_brainstem.outputs.brainstem_structures))


def test_parcellate(subjects_dir, subject_id, parcellation_scheme, base_dir):
    from cmtklib.parcellation import Parcellate
    from nipype import Node

    parcellate = Node(interface=Parcellate(),
                      name='parcellate', base_dir=base_dir)
    parcellate.inputs.subjects_dir = subjects_dir
    parcellate.inputs.subject_id = subject_id
    parcellate.inputs.parcellation_scheme = parcellation_scheme

    # Execute the node
    parcellate.run()

    print('Output : ', parcellate.outputs.roi_files_in_structural_space)


def test_parcellate_thalamus(subjects_dir, subject_id, subject_T1w, template, thalamic_maps, base_dir):
    from cmtklib.parcellation import ParcellateThalamus
    from nipype import Node

    parcellate_thalamus = Node(interface=ParcellateThalamus(
    ), name='parcellate_thalamus', base_dir=base_dir)
    parcellate_thalamus.inputs.T1w_image = subject_T1w
    parcellate_thalamus.inputs.template_image = template
    parcellate_thalamus.inputs.thalamic_nuclei_maps = thalamic_maps
    parcellate_thalamus.inputs.subjects_dir = subjects_dir
    parcellate_thalamus.inputs.subject_id = subject_id

    # Execute the node
    parcellate_thalamus.run()

    # print('Output : ', parcellate.roi_files_in_structural_space)


def test_correcting_interpolation(jacobian_file, input_maps, corrected_maps):
    import nibabel as ni
    import numpy as np

    Ij = ni.load(jacobian_file).get_data()  # numpy.ndarray
    imgVspams = ni.load(input_maps)
    Vspams = imgVspams.get_data()  # numpy.ndarray
    Ispams = np.zeros(Vspams.shape)

    for nuc in np.arange(Vspams.shape[3]):
        tempImage = Vspams[:, :, :, nuc]
        tempImage[tempImage < 0] = 0
        tempImage[tempImage > 1] = 1
        T = np.multiply(tempImage, Ij)
        Ispams[:, :, :, nuc] = T / T.max()

    # update the header
    hdr = imgVspams.get_header()
    hdr2 = hdr.copy()
    hdr2.set_data_dtype(np.uint16)
    print("Save output image to %s" % corrected_maps)
    img = ni.Nifti1Image(Ispams, imgVspams.get_affine(), hdr2)
    ni.save(img, corrected_maps)


def test_thalamus_masking(subjects_dir, subject_id, thalamus_mask, thalamus_maps, output_maps, max_prob, base_dir):
    import nibabel as ni
    import numpy as np
    from scipy import ndimage
    import os
    import sys
    import subprocess

    print('Creating Thalamus mask from FreeSurfer aparc+aseg ')

    fs_string = 'export SUBJECTS_DIR=' + subjects_dir
    print('- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(subjects_dir))

    # Moving aparc+aseg.mgz back to its original space for thalamic parcellation
    mov = op.join(subjects_dir, subject_id, 'mri', 'aparc+aseg.mgz')
    targ = op.join(subjects_dir, subject_id, 'mri', 'orig/001.mgz')
    out = op.join(subjects_dir, subject_id, 'tmp', 'aparc+aseg.nii.gz')
    cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (
        mov, targ, out)

    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    proc_stdout = process.communicate()[0].strip()

    imgVspams = ni.load(thalamus_maps)
    Ispams = imgVspams.get_data()  # numpy.ndarray

    Vatlas_fn = out
    Vatlas = ni.load(Vatlas_fn)
    Ia = Vatlas.get_data()
    indl = np.where(Ia == 10)
    indr = np.where(Ia == 49)

    def filter_isolated_cells(array, struct):
        """ Return array with completely isolated single cells removed
        :param array: Array with completely isolated single cells
        :param struct: Structure array for generating unique regions
        :return: Array with minimum region size > 1
        """
        filtered_array = np.copy(array)
        id_regions, num_ids = ndimage.label(filtered_array, structure=struct)
        id_sizes = np.array(ndimage.sum(
            array, id_regions, list(range(num_ids + 1))))
        area_mask = (id_sizes == 1)
        filtered_array[area_mask[id_regions]] = 0
        return filtered_array

    remove_isolated_points = True
    if remove_isolated_points:
        struct = np.ones((3, 3, 3))

        # struct = np.zeros((3,3,3))
        # struct[1,1,1] = 1

        # Left Hemisphere
        # Removing isolated points
        tempI = np.zeros(Ia.shape)
        tempI[indl] = 1
        tempI = filter_isolated_cells(tempI, struct=struct)
        indl = np.where(tempI == 1)

        # Right Hemisphere
        # Removing isolated points
        tempI = np.zeros(Ia.shape)
        tempI[indr] = 1
        tempI = filter_isolated_cells(tempI, struct=struct)
        indr = np.where(tempI == 1)

    # Creating Thalamic Mask (1: Left, 2:Right)
    Ithal = np.zeros(Ia.shape)
    Ithal[indl] = 1
    Ithal[indr] = 2

    # TODO: Masking according to csf
    # unzip_nifti([freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii.gz']);
    # Outfiles = Extract_brain([freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii'],[freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii']);
    #
    # csfFilename = deblank(Outfiles(4,:));
    # Vcsf = spm_vol_gzip(csfFilename);
    # Icsf = spm_read_vols_gzip(Vcsf);
    # ind = find(Icsf > csfThresh);
    # Ithal(ind) = 0;

    # update the header
    hdr = Vatlas.get_header()
    hdr2 = hdr.copy()
    hdr2.set_data_dtype(np.uint16)
    print("Save output image to %s" % thalamus_mask)
    Vthal = ni.Nifti1Image(Ithal, Vatlas.get_affine(), hdr2)
    ni.save(Vthal, thalamus_mask)

    Nspams = Ispams.shape[3]
    Thresh = 0.05

    use_thalamus_mask = True
    if use_thalamus_mask:
        IthalL = np.zeros(Ithal.shape)
        indl = np.where(Ithal == 1)
        IthalL[indl] = 1

        IthalR = np.zeros(Ithal.shape)
        indr = np.where(Ithal == 2)
        IthalR[indr] = 1

        tmpIthalL = np.zeros(
            (Ithal.shape[0], Ithal.shape[1], Ithal.shape[2], 1))
        tmpIthalL[:, :, :, 0] = IthalL
        tempM = np.repeat(tmpIthalL, Nspams / 2, axis=3)

        IspamL = np.multiply(Ispams[:, :, :, 0:Nspams / 2], tempM)
        # Creating MaxProb
        ind = np.where(IspamL < Thresh)
        IspamL[ind] = 0
        ind = np.where(np.sum(IspamL, axis=3) == 0)
        # MaxProbL = IspamL.max(axis=3)
        MaxProbL = np.argmax(IspamL, axis=3) + 1
        MaxProbL[ind] = 0
        # MaxProbL[ind] = 0
        # ?MaxProbL = ndimage.binary_fill_holes(MaxProbL)
        # ?MaxProbL = Atlas_Corr(IthalL,MaxProbL)

        tmpIthalR = np.zeros(
            (Ithal.shape[0], Ithal.shape[1], Ithal.shape[2], 1))
        tmpIthalR[:, :, :, 0] = IthalR
        tempM = np.repeat(tmpIthalR, Nspams / 2, axis=3)

        IspamR = np.multiply(Ispams[:, :, :, Nspams / 2:Nspams], tempM)
        # Creating MaxProb
        ind = np.where(IspamR < Thresh)
        IspamR[ind] = 0
        ind = np.where(np.sum(IspamR, axis=3) == 0)
        # MaxProbR = IspamR.max(axis=3)
        MaxProbR = np.argmax(IspamR, axis=3) + 1
        MaxProbR[ind] = 0
        # ?MaxProbR = imfill(MaxProbR,'holes');
        # ?MaxProbR = Atlas_Corr(IthalR,MaxProbR);
        MaxProbR[indr] = MaxProbR[indr] + Nspams / 2

        Ispams[:, :, :, 0:Nspams / 2] = IspamL
        Ispams[:, :, :, Nspams / 2:Nspams] = IspamR

    # Saving Volume
    # update the header
    hdr = imgVspams.get_header()
    hdr2 = hdr.copy()
    hdr2.set_data_dtype(np.uint16)
    print("Save output image to %s" % output_maps)
    img = ni.Nifti1Image(Ispams, imgVspams.get_affine(), hdr2)
    ni.save(img, output_maps)

    # Saving Maxprob
    # update the header
    hdr = Vatlas.get_header()
    hdr2 = hdr.copy()
    hdr2.set_data_dtype(np.uint16)

    if use_thalamus_mask:
        MaxProb = MaxProbL + MaxProbR
    else:
        # Creating MaxProb
        ind = np.where(Ispams < Thresh)
        Ispams[ind] = 0
        ind = np.where(np.sum(Ispams, axis=3) == 0)
        MaxProb = Ispams.argmax(axis=3) + 1
        MaxProb[ind] = 0
        # ?MaxProb = imfill(MaxProb,'holes');

    print("Save output image to %s" % max_prob)
    img = ni.Nifti1Image(MaxProb, Vatlas.get_affine(), hdr2)
    ni.save(img, max_prob)


if __name__ == '__main__':
    subjects_dir = '/media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo/derivatives/freesurfer'
    subject_id = 'sub-A006_ses-20160520161029'
    base_dir = '~/Desktop/parcellation_tests'

    subject_T1w = '/media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo/derivatives/cmp/sub-A006/ses-20160520161029/anat/sub-A006_ses-20160520161029_T1w_brain.nii.gz'
    template = '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/thalamus2018/mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz'
    thalamic_maps = '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/thalamus2018/Thalamus_Nuclei-HCP-4DSPAMs.nii.gz'

    thalamus_mask = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_dtissue.nii.gz'
    thalamus_maps = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissue.nii.gz'
    output_maps = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissue_masked.nii.gz'
    max_prob = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissue_maxprob.nii.gz'
    # from cmtklib.parcellation import create_roi_v2
    # create_roi_v2(subject_id,subjects_dir,2)

    # test_parcellate(subjects_dir,subject_id,'Lausanne2018',base_dir)

    # test_parcellate_thalamus(subjects_dir,subject_id,subject_T1w,template,thalamic_maps,base_dir)

    # test_parcellate_brainstem(subjects_dir,subject_id,base_dir)

    # test_parcellate_hippocampal_subfields(subjects_dir,subject_id,base_dir)
    input_rois = ['/home/localadmin/~/Desktop/parcellation_tests/parcellate/ROIv_HR_th_scale1.nii.gz',
                  '/home/localadmin/~/Desktop/parcellation_tests/parcellate/ROIv_HR_th_scale2.nii.gz',
                  '/home/localadmin/~/Desktop/parcellation_tests/parcellate/ROIv_HR_th_scale3.nii.gz',
                  '/home/localadmin/~/Desktop/parcellation_tests/parcellate/ROIv_HR_th_scale4.nii.gz',
                  '/home/localadmin/~/Desktop/parcellation_tests/parcellate/ROIv_HR_th_scale5.nii.gz']
    lh_subfields = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_hipposubfield/lh_subFields.nii.gz'
    rh_subfields = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_hipposubfield/rh_subFields.nii.gz'
    brainstem = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_brainstem/brainstem.nii.gz'
    thalamus = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissue_maxprob.nii.gz'
    test_combine_parcellation(subjects_dir, subject_id, input_rois, lh_subfields, rh_subfields, brainstem, thalamus,
                              base_dir)

    # test_thalamus_masking(subjects_dir,subject_id,thalamus_mask,thalamus_maps,output_maps,max_prob,base_dir)

    # jacobian_file = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissue_jacobian.nii.gz'
    # input_maps = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissue.nii.gz'
    # corrected_maps = '/home/localadmin/~/Desktop/parcellation_tests/parcellate_thalamus/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_probtissuefinal.nii.gz'
    # test_correcting_interpolation(jacobian_file,input_maps,corrected_maps)
