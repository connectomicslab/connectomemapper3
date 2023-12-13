import nibabel as nib

# csf
img_prior1 = nib.load(
    '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/Priors/priors1.nii.gz')
# cort-gm
img_prior2 = nib.load(
    '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/Priors/priors2.nii.gz')
# wm
img_prior3 = nib.load(
    '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/Priors/priors3.nii.gz')
# deep-gm
img_prior4 = nib.load(
    '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/Priors/priors4.nii.gz')
# brainstem
# img_prior5 = nib.load('/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/Priors/priors5.nii.gz')
# cerebellum
# img_prior6 = nib.load('/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/Priors/priors6.nii.gz')

affine = img_prior1.affine

csf = img_prior1.get_data()
cort_gm = img_prior2.get_data()
wm = img_prior3.get_data()
deep_gm = img_prior4.get_data()

img_csf = nib.Nifti1Image(csf, affine)
nib.save(img_csf,
         '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/3Class-Priors/priors1.nii.gz')

gm = deep_gm + cort_gm
gm[gm > 1.0] = 1.0
img_gm = nib.Nifti1Image(gm, affine)
nib.save(img_gm,
         '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/3Class-Priors/priors2.nii.gz')

img_wm = nib.Nifti1Image(wm, affine)
nib.save(img_wm,
         '/home/localadmin/Softwares/cmp3/cmtklib/data/segmentation/ants_template_IXI/3Class-Priors/priors3.nii.gz')
