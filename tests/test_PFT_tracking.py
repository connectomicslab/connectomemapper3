import sys
import os
from os import path as op

import nibabel as nb
from nibabel.streamlines import Field, Tractogram
from nibabel.orientations import aff2axcodes

import numpy as np

streamlines = np.load(
    '/media/localadmin/HagmannHDD/Seb/testPFT/diffusion_preproc_resampled_streamlines.npy')

imref = nb.load('/media/localadmin/HagmannHDD/Seb/testPFT/shore_gfa.nii.gz')

affine = imref.affine.copy()

print(imref.affine.copy())
print(affine)

header = {}
header[Field.ORIGIN] = affine[:3, 3]
header[Field.VOXEL_TO_RASMM] = affine
header[Field.VOXEL_SIZES] = imref.header.get_zooms()[:3]
header[Field.DIMENSIONS] = imref.shape[:3]
header[Field.VOXEL_ORDER] = "".join(aff2axcodes(affine))

for i, streamline in enumerate(streamlines):
    for j, voxel in enumerate(streamline):
        streamlines[i][j] = streamlines[i][j] - imref.affine.copy()[:3, 3]

print(header[Field.VOXEL_ORDER])
tractogram = Tractogram(streamlines=streamlines, affine_to_rasmm=affine)
out_fname = '/media/localadmin/HagmannHDD/Seb/testPFT/track_nib1.trk'
nb.streamlines.save(tractogram, out_fname, header=header)
