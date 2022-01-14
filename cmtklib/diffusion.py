# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions for the diffusion pipeline."""

import os
import subprocess

import nibabel as nib
import numpy as np
import nibabel.trackvis as tv

from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
    File,
    TraitedSpec,
    OutputMultiPath,
    InputMultiPath,
)
from nipype.utils.filemanip import split_filename

from traits.trait_types import List, Str, Int, Enum

from .util import length


def compute_length_array(trkfile=None, streams=None, savefname="lengths.npy"):
    """Computes the length of the fibers in a tractogram and returns an array of length.

    Parameters
    ----------
    trkfile : TRK file
        Path to the tractogram in TRK format

    streams : the fibers data
        The fibers from which we want to compute the length

    savefname : string
        Output filename to write the length array

    Returns
    -------
    leng : numpy.array
        Array of fiber lengths
    """
    if streams is None and trkfile is not None:
        print("Compute length array for fibers in %s" % trkfile)
        streams, hdr = tv.read(trkfile, as_generator=True)
        n_fibers = hdr["n_count"]
        if n_fibers == 0:
            msg = (
                "Header field n_count of trackfile %s is set to 0. No track seem to exist in this file."
                % trkfile
            )
            print(msg)
            raise Exception(msg)
    else:
        n_fibers = len(streams)

    leng = np.zeros(n_fibers, dtype=np.float)
    for i, fib in enumerate(streams):
        leng[i] = length(fib[0])

    # store length array
    np.save(savefname, leng)
    print("Store lengths array to: %s" % savefname)

    return leng


def filter_fibers(intrk, outtrk="", fiber_cutoff_lower=20, fiber_cutoff_upper=500):
    """Filters a tractogram based on lower / upper cutoffs.

    Parameters
    ----------
    intrk : TRK file
        Path to a tractogram file in TRK format

    outtrk : TRK file
        Output path for the filtered tractogram

    fiber_cutoff_lower : int
        Lower number of fibers cutoff (Default: 20)

    fiber_cutoff_upper : int
        Upper number of fibers cutoff (Default: 500)
    """
    print("Cut Fiber Filtering")
    print("===================")

    print("Input file for fiber cutting is: %s" % intrk)

    if outtrk == "":
        _, filename = os.path.split(intrk)
        base, ext = os.path.splitext(filename)
        outtrk = os.path.abspath(base + "_cutfiltered" + ext)

    # compute length array
    le = compute_length_array(intrk)

    # cut the fibers smaller than value
    reducedidx = np.where((le > fiber_cutoff_lower) & (le < fiber_cutoff_upper))[0]

    # load trackfile (downside, needs everything in memory)
    fibold, hdrold = tv.read(intrk)

    # rewrite the track vis file with the reduced number of fibers
    outstreams = []
    for i in reducedidx:
        outstreams.append(fibold[i])

    n_fib_out = len(outstreams)
    hdrnew = hdrold.copy()
    hdrnew["n_count"] = n_fib_out

    # print("Compute length array for cutted fibers")
    # le = compute_length_array(streams=outstreams)
    print("Write out file: %s" % outtrk)
    print("Number of fibers out : %d" % hdrnew["n_count"])
    tv.write(outtrk, outstreams, hdrnew)
    print("File wrote : %d" % os.path.exists(outtrk))

    # ----
    # extension idea

    # find a balance between discarding spurious fibers and still
    # keep cortico-cortico ones, amidst of not having ground-truth

    # compute a downsampled version of the fibers using 4 points

    # discard smaller than x mm fibers
    # and which have a minimum angle smaller than y degrees


class FlipTableInputSpec(BaseInterfaceInputSpec):
    table = File(exists=True, desc="Input diffusion gradient table")

    flipping_axis = List(desc="List of axis to be flipped")

    delimiter = Str(desc="Delimiter used in the table")

    header_lines = Int(0, desc="Line number of table header")

    orientation = Enum(["v", "h"], desc="Orientation of the table")


class FlipTableOutputSpec(TraitedSpec):
    table = File(exists=True, desc="Output table with flipped axis")


class FlipTable(BaseInterface):
    """Flip axis and rewrite a gradient table.

    Examples
    --------
    >>> from cmtklib.diffusion import FlipTable
    >>> flip_table = FlipTable()
    >>> flip_table.inputs.table = 'sub-01_mod-dwi_gradient.txt'
    >>> flip_table.inputs.flipping_axis = ['x']
    >>> flip_table.inputs.orientation = 'v'
    >>> flip_table.inputs.delimiter = ','
    >>> flip_table.run()  # doctest: +SKIP

    """

    input_spec = FlipTableInputSpec
    output_spec = FlipTableOutputSpec

    def _run_interface(self, runtime):
        axis_dict = {"x": 0, "y": 1, "z": 2}
        f = open(self.inputs.table, "r")
        header = ""
        for h in range(self.inputs.header_lines):
            header += f.readline()
        if self.inputs.delimiter == " ":
            table = np.loadtxt(f)
        else:
            table = np.loadtxt(f, delimiter=self.inputs.delimiter)
        f.close()
        if self.inputs.orientation == "v":
            for i in self.inputs.flipping_axis:
                table[:, axis_dict[i]] = -table[:, axis_dict[i]]
        elif self.inputs.orientation == "h":
            for i in self.inputs.flipping_axis:
                table[axis_dict[i], :] = -table[axis_dict[i], :]

        with open(os.path.abspath("flipped_table.txt"), "a") as out_f:
            if self.inputs.header_lines > 0:
                np.savetxt(out_f, table, header=header, delimiter=self.inputs.delimiter)
            else:
                np.savetxt(out_f, table, delimiter=self.inputs.delimiter)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["table"] = os.path.abspath("flipped_table.txt")
        return outputs


class ExtractPVEsFrom5TTInputSpec(BaseInterfaceInputSpec):
    in_5tt = File(desc="Input 5TT (4D) image", exists=True, mandatory=True)

    ref_image = File(
        desc="Reference 3D image to be used to save 3D PVE volumes",
        exists=True,
        mandatory=True,
    )

    pve_csf_file = File(
        desc="CSF Partial Volume Estimation volume estimated from", mandatory=True
    )

    pve_gm_file = File(
        desc="GM Partial Volume Estimation volume estimated from", mandatory=True
    )

    pve_wm_file = File(
        desc="WM Partial Volume Estimation volume estimated from", mandatory=True
    )


class ExtractPVEsFrom5TTOutputSpec(TraitedSpec):
    partial_volume_files = OutputMultiPath(
        File,
        desc="CSF/GM/WM Partial Volume Estimation images estimated from",
        exists=True,
    )


class ExtractPVEsFrom5TT(BaseInterface):
    """Create Partial Volume Estimation maps for CSF, GM, WM tissues from `mrtrix3` 5TT image.

    Examples
    --------
    >>> from cmtklib.diffusion import ExtractPVEsFrom5TT
    >>> pves = ExtractPVEsFrom5TT()
    >>> pves.inputs.in_5tt = 'sub-01_desc-5tt_dseg.nii.gz'
    >>> pves.inputs.ref_image = 'sub-01_T1w.nii.gz'
    >>> pves.inputs.pve_csf_file = '/path/to/output_csf_pve.nii.gz'
    >>> pves.inputs.pve_gm_file = '/path/to/output_gm_pve.nii.gz'
    >>> pves.inputs.pve_wm_file = '/path/to/output_wm_pve.nii.gz'
    >>> pves.run()  # doctest: +SKIP

    """

    input_spec = ExtractPVEsFrom5TTInputSpec
    output_spec = ExtractPVEsFrom5TTOutputSpec

    def _run_interface(self, runtime):
        img_5tt = nib.load(self.inputs.in_5tt)
        data_5tt = img_5tt.get_data()

        ref_img = nib.load(self.inputs.ref_image)
        # hdr = ref_img.get_header()
        affine = ref_img.get_affine()

        print("Shape : {}".format(data_5tt.shape))

        # The tissue type volumes must appear in the following order for the anatomical priors to be applied correctly during tractography:
        #
        # 0: Cortical grey matter
        # 1: Sub-cortical grey matter
        # 2: White matter
        # 3: CSF
        # 4: Pathological tissue
        #
        # Extract from https://mrtrix.readthedocs.io/en/latest/quantitative_structural_connectivity/act.html

        # Create and save PVE for CSF
        pve_csf = data_5tt[:, :, :, 3].squeeze()
        pve_csf_img = nib.Nifti1Image(pve_csf.astype(np.float), affine)
        nib.save(pve_csf_img, os.path.abspath(self.inputs.pve_csf_file))

        # Create and save PVE for WM
        pve_wm = data_5tt[:, :, :, 2].squeeze()
        pve_wm_img = nib.Nifti1Image(pve_wm.astype(np.float), affine)
        nib.save(pve_wm_img, os.path.abspath(self.inputs.pve_wm_file))

        # Create and save PVE for GM
        pve_gm = data_5tt[:, :, :, 0].squeeze() + data_5tt[:, :, :, 1].squeeze()
        pve_gm_img = nib.Nifti1Image(pve_gm.astype(np.float), affine)
        nib.save(pve_gm_img, os.path.abspath(self.inputs.pve_gm_file))

        # Dilate PVEs and normalize to 1
        fwhm = 2.0
        radius = np.float(0.5 * fwhm)
        sigma = np.float(fwhm / 2.3548)

        print("sigma : %s" % sigma)

        fslmaths_cmd = "fslmaths %s -kernel sphere %s -dilD %s" % (
            os.path.abspath(self.inputs.pve_csf_file),
            radius,
            os.path.abspath(self.inputs.pve_csf_file),
        )
        print("Dilate CSF PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = "fslmaths %s -kernel sphere %s -dilD %s" % (
            os.path.abspath(self.inputs.pve_wm_file),
            radius,
            os.path.abspath(self.inputs.pve_wm_file),
        )
        print("Dilate WM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = "fslmaths %s -kernel sphere %s -dilD %s" % (
            os.path.abspath(self.inputs.pve_gm_file),
            radius,
            os.path.abspath(self.inputs.pve_gm_file),
        )
        print("Dilate GM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = "fslmaths %s -kernel gauss %s -fmean %s" % (
            os.path.abspath(self.inputs.pve_csf_file),
            sigma,
            os.path.abspath(self.inputs.pve_csf_file),
        )
        print("Gaussian smoothing : CSF PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = "fslmaths %s -kernel gauss %s -fmean %s" % (
            os.path.abspath(self.inputs.pve_wm_file),
            sigma,
            os.path.abspath(self.inputs.pve_wm_file),
        )
        print("Gaussian smoothing : WM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = "fslmaths %s -kernel gauss %s -fmean %s" % (
            os.path.abspath(self.inputs.pve_gm_file),
            sigma,
            os.path.abspath(self.inputs.pve_gm_file),
        )
        print("Gaussian smoothing : GM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        proc_stdout = process.communicate()[0].strip()

        pve_csf = nib.load(os.path.abspath(self.inputs.pve_csf_file)).get_data()
        pve_wm = nib.load(os.path.abspath(self.inputs.pve_wm_file)).get_data()
        pve_gm = nib.load(os.path.abspath(self.inputs.pve_gm_file)).get_data()

        pve_sum = pve_csf + pve_wm + pve_gm
        pve_csf = np.divide(pve_csf, pve_sum)
        pve_wm = np.divide(pve_wm, pve_sum)
        pve_gm = np.divide(pve_gm, pve_sum)

        pve_csf_img = nib.Nifti1Image(pve_csf.astype(np.float), affine)
        nib.save(pve_csf_img, os.path.abspath(self.inputs.pve_csf_file))

        pve_wm_img = nib.Nifti1Image(pve_wm.astype(np.float), affine)
        nib.save(pve_wm_img, os.path.abspath(self.inputs.pve_wm_file))

        pve_gm_img = nib.Nifti1Image(pve_gm.astype(np.float), affine)
        nib.save(pve_gm_img, os.path.abspath(self.inputs.pve_gm_file))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        pve_files = []
        pve_files.append(os.path.abspath(self.inputs.pve_csf_file))
        pve_files.append(os.path.abspath(self.inputs.pve_gm_file))
        pve_files.append(os.path.abspath(self.inputs.pve_wm_file))

        outputs["partial_volume_files"] = pve_files

        return outputs


class Tck2TrkInputSpec(BaseInterfaceInputSpec):
    in_tracks = File(
        exists=True, mandatory=True, desc="Input track file in MRtrix .tck format"
    )

    in_image = File(
        exists=True, mandatory=True, desc="Input image used to extract the header"
    )

    out_tracks = File(mandatory=True, desc="Output track file in Trackvis .trk format")


class Tck2TrkOutputSpec(TraitedSpec):
    out_tracks = File(exists=True, desc="Output track file in Trackvis .trk format")


class Tck2Trk(BaseInterface):
    """Convert a tractogram in `mrtrix` TCK format to `trackvis` TRK format.

    Examples
    --------
    >>> from cmtklib.diffusion import Tck2Trk
    >>> tck_to_trk = Tck2Trk()
    >>> tck_to_trk.inputs.in_tracks = 'sub-01_tractogram.tck'
    >>> tck_to_trk.inputs.in_image = 'sub-01_desc-preproc_dwi.nii.gz'
    >>> tck_to_trk.inputs.out_tracks = 'sub-01_tractogram.trk'
    >>> tck_to_trk.run()  # doctest: +SKIP

    """

    input_spec = Tck2TrkInputSpec
    output_spec = Tck2TrkOutputSpec

    def _run_interface(self, runtime):

        from nibabel.streamlines import Field
        from nibabel.orientations import aff2axcodes

        print("-> Load nifti and copy header")
        nii = nib.load(self.inputs.in_image)

        header = {
            Field.VOXEL_TO_RASMM: nii.affine.copy(),
            Field.VOXEL_SIZES: nii.header.get_zooms()[:3],
            Field.DIMENSIONS: nii.shape[:3],
            Field.VOXEL_ORDER: "".join(aff2axcodes(nii.affine)),
        }

        if (
            nib.streamlines.detect_format(self.inputs.in_tracks)
            is not nib.streamlines.TckFile
        ):
            print("Skipping non TCK file: '{}'".format(self.inputs.in_tracks))
        else:
            tck = nib.streamlines.load(self.inputs.in_tracks)
            self.out_tracks = self.inputs.out_tracks
            nib.streamlines.save(tck.tractogram, self.out_tracks, header=header)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_tracks"] = os.path.abspath(self.out_tracks)
        return outputs


class FlipBvecInputSpec(BaseInterfaceInputSpec):
    bvecs = File(exists=True, desc="Input diffusion gradient bvec file")

    flipping_axis = List(desc="List of axis to be flipped")

    delimiter = Str(desc="Delimiter used in the table")

    header_lines = Int(0, desc="Line number of table header")

    orientation = Enum(["v", "h"], desc="Orientation of the table")


class FlipBvecOutputSpec(TraitedSpec):
    bvecs_flipped = File(exists=True, desc="Output bvec file with flipped axis")


class FlipBvec(BaseInterface):
    """Return a diffusion bvec file with flipped axis as specified by `flipping_axis` input.

    Examples
    --------
    >>> from cmtklib.diffusion import FlipBvec
    >>> flip_bvec = FlipBvec()
    >>> flip_bvec.inputs.bvecs = 'sub-01_dwi.bvecs'
    >>> flip_bvec.inputs.flipping_axis = ['x']
    >>> flip_bvec.inputs.delimiter = ' '
    >>> flip_bvec.inputs.header_lines = 0
    >>> flip_bvec.inputs.orientation = 'h'
    >>> flip_bvec.run()  # doctest: +SKIP

    """

    input_spec = FlipBvecInputSpec
    output_spec = FlipBvecOutputSpec

    def _run_interface(self, runtime):
        axis_dict = {"x": 0, "y": 1, "z": 2}
        import numpy as np

        f = open(self.inputs.bvecs, "r")
        header = ""
        for h in range(self.inputs.header_lines):
            header += f.readline()
        if self.inputs.delimiter == " ":
            table = np.loadtxt(f)
        else:
            table = np.loadtxt(f, delimiter=self.inputs.delimiter)
        f.close()

        if self.inputs.orientation == "v":
            for i in self.inputs.flipping_axis:
                table[:, axis_dict[i]] = -table[:, axis_dict[i]]
        elif self.inputs.orientation == "h":
            for i in self.inputs.flipping_axis:
                table[axis_dict[i], :] = -table[axis_dict[i], :]

        with open(os.path.abspath("flipped_bvecs.bvec"), "w") as out_f:
            if self.inputs.header_lines > 0:
                np.savetxt(out_f, table, header=header, delimiter=self.inputs.delimiter)
            else:
                np.savetxt(out_f, table, delimiter=self.inputs.delimiter)

        # with open(os.path.abspath('flipped_bvecs.bvec'), 'w') as out_f:
        #    np.savetxt(out_f, table, header=header, delimiter=self.inputs.delimiter)

        # out_f = file(os.path.abspath('flipped_bvecs.bvec'), 'w')
        # if self.inputs.header_lines > 0:
        #     out_f.write(header)
        # np.savetxt(out_f, table, header=header, delimiter=self.inputs.delimiter)
        # out_f.close()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["bvecs_flipped"] = os.path.abspath("flipped_bvecs.bvec")
        return outputs


class UpdateGMWMInterfaceSeedingInputSpec(BaseInterfaceInputSpec):
    in_gmwmi_file = File(
        exists=True,
        mandatory=True,
        desc="Input GMWM interface image used for streamline seeding",
    )

    out_gmwmi_file = File(
        mandatory=True, desc="Output GM WM interface used for streamline seeding"
    )

    in_roi_volumes = InputMultiPath(
        File(exists=True), mandatory=True, desc="Input parcellation images"
    )


class UpdateGMWMInterfaceSeedingOutputSpec(TraitedSpec):
    out_gmwmi_file = File(
        exists=True, desc="Output GM WM interface used for streamline seeding"
    )


class UpdateGMWMInterfaceSeeding(BaseInterface):
    """Add extra Lausanne2018 structures to the Gray-matter/White-matter interface for tractography seeding.

    Examples
    --------
    >>> from cmtklib.diffusion import UpdateGMWMInterfaceSeeding
    >>> update_gmwmi = UpdateGMWMInterfaceSeeding()
    >>> update_gmwmi.inputs.in_gmwmi_file = 'sub-01_label-gmwmi_desc-orig_dseg.nii.gz'
    >>> update_gmwmi.inputs.out_gmwmi_file = 'sub-01_label-gmwmi_desc-modif_dseg.nii.gz'
    >>> update_gmwmi.inputs.in_roi_volumes = ['sub-01_space-DWI_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                       'sub-01_space-DWI_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                       'sub-01_space-DWI_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                       'sub-01_space-DWI_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                       'sub-01_space-DWI_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> update_gmwmi.run()  # doctest: +SKIP

    """

    input_spec = UpdateGMWMInterfaceSeedingInputSpec
    output_spec = UpdateGMWMInterfaceSeedingOutputSpec

    def _run_interface(self, runtime):

        gmwmi_img = nib.load(self.inputs.in_gmwmi_file)
        gmwmi_data = gmwmi_img.get_data()
        maxv = gmwmi_data.max()

        for fname in self.inputs.in_roi_volumes:
            if ("scale1" in fname) or (len(self.inputs.in_roi_volumes) == 1):
                roi_fname = fname
                print("roi_fname: %s" % roi_fname)

        roi_img = nib.load(roi_fname)
        roi_data = roi_img.get_data()

        new_gmwmi_data = gmwmi_data.copy()

        if roi_data.max() > 83:
            # Thalamic nuclei
            new_gmwmi_data[roi_data == 35] = maxv
            new_gmwmi_data[roi_data == 36] = maxv
            new_gmwmi_data[roi_data == 37] = maxv
            new_gmwmi_data[roi_data == 38] = maxv
            new_gmwmi_data[roi_data == 39] = maxv
            new_gmwmi_data[roi_data == 40] = maxv
            new_gmwmi_data[roi_data == 41] = maxv
            new_gmwmi_data[roi_data == 96] = maxv
            new_gmwmi_data[roi_data == 97] = maxv
            new_gmwmi_data[roi_data == 98] = maxv
            new_gmwmi_data[roi_data == 99] = maxv
            new_gmwmi_data[roi_data == 100] = maxv
            new_gmwmi_data[roi_data == 101] = maxv
            new_gmwmi_data[roi_data == 102] = maxv

            # Hippocampal subfields
            new_gmwmi_data[roi_data == 48] = maxv
            new_gmwmi_data[roi_data == 49] = maxv
            new_gmwmi_data[roi_data == 50] = maxv
            new_gmwmi_data[roi_data == 51] = maxv
            new_gmwmi_data[roi_data == 52] = maxv
            new_gmwmi_data[roi_data == 53] = maxv
            new_gmwmi_data[roi_data == 54] = maxv
            new_gmwmi_data[roi_data == 55] = maxv
            new_gmwmi_data[roi_data == 56] = maxv
            new_gmwmi_data[roi_data == 57] = maxv
            new_gmwmi_data[roi_data == 58] = maxv
            new_gmwmi_data[roi_data == 59] = maxv
            new_gmwmi_data[roi_data == 109] = maxv
            new_gmwmi_data[roi_data == 110] = maxv
            new_gmwmi_data[roi_data == 111] = maxv
            new_gmwmi_data[roi_data == 112] = maxv
            new_gmwmi_data[roi_data == 113] = maxv
            new_gmwmi_data[roi_data == 114] = maxv
            new_gmwmi_data[roi_data == 115] = maxv
            new_gmwmi_data[roi_data == 116] = maxv
            new_gmwmi_data[roi_data == 117] = maxv
            new_gmwmi_data[roi_data == 118] = maxv
            new_gmwmi_data[roi_data == 119] = maxv
            new_gmwmi_data[roi_data == 120] = maxv

            # Brain stem
            new_gmwmi_data[roi_data == 123] = maxv
            new_gmwmi_data[roi_data == 124] = maxv
            new_gmwmi_data[roi_data == 125] = maxv
            new_gmwmi_data[roi_data == 126] = maxv

        new_gmwmi_img = nib.Nifti1Pair(new_gmwmi_data, gmwmi_img.affine)
        nib.save(new_gmwmi_img, self.inputs.out_gmwmi_file)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        outputs["out_gmwmi_file"] = os.path.abspath(self.inputs.out_gmwmi_file)

        return outputs


class MakeSeedsInputSpec(BaseInterfaceInputSpec):
    ROI_files = InputMultiPath(
        File(exists=True), desc="ROI files registered to diffusion space"
    )

    WM_file = File(mandatory=True, desc="WM mask file registered to diffusion space")
    # DWI = File(mandatory=True,desc='Diffusion data file for probabilistic tractography')


class MakeSeedsOutputSpec(TraitedSpec):
    seed_files = OutputMultiPath(
        File(exists=True), desc="Seed files for probabilistic tractography"
    )


class MakeSeeds(BaseInterface):
    """Creates seeding ROIs by intersecting dilated ROIs with WM mask for `Dipy`.

    Examples
    --------
    >>> from cmtklib.diffusion import MakeSeeds
    >>> make_dipy_seeds = MakeSeeds()
    >>> make_dipy_seeds.inputs.ROI_files  = ['sub-01_space-DWI_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> make_dipy_seeds.inputs.WM_file = 'sub-01_space-DWI_label-WM_dseg.nii.gz'
    >>> make_dipy_seeds.run()  # doctest: +SKIP

    """

    input_spec = MakeSeedsInputSpec
    output_spec = MakeSeedsOutputSpec
    ROI_idx = []
    base_name = ""

    def _run_interface(self, runtime):
        print(
            "Computing seed files for probabilistic tractography\n"
            "==================================================="
        )
        # Load ROI file
        txt_file = open(self.base_name + "_seeds.txt", "w")

        print(self.inputs.ROI_files)

        for ROI_file in self.inputs.ROI_files:
            ROI_vol = nib.load(ROI_file)
            ROI_data = ROI_vol.get_data()
            ROI_affine = ROI_vol.get_affine()
            # Load WM mask
            WM_vol = nib.load(self.inputs.WM_file)
            WM_data = WM_vol.get_data()
            # Extract ROI indexes, define number of ROIs, overlap code and start ROI dilation
            print("ROI dilation...")
            tmp_data = np.unique(ROI_data[ROI_data != 0]).astype(int)
            print(tmp_data.shape)
            self.ROI_idx = np.unique(tmp_data).astype(int)
            bins = np.arange(83)
            counts = np.histogram(self.ROI_idx, bins=bins)
            print(counts)
            print(self.ROI_idx.shape)
            print(self.ROI_idx)
            # Take overlap between dilated ROIs and WM to define seeding regions
            border = (np.multiply(ROI_data, WM_data)).astype(int)
            # Save one nifti file per seeding ROI
            temp = border.copy()
            # print border.max
            _, self.base_name, _ = split_filename(ROI_file)
            for i in self.ROI_idx:
                temp[border == i] = 1
                temp[border != i] = 0
                new_image = nib.Nifti1Image(temp, ROI_affine)
                save_as = os.path.abspath(
                    self.base_name + "_seed_" + str(i) + ".nii.gz"
                )
                txt_file.write(
                    str(self.base_name + "_seed_" + str(i) + ".nii.gz" + "\n")
                )
                nib.save(new_image, save_as)
        txt_file.close()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["seed_files"] = self.gen_outputfilelist()
        return outputs

    def gen_outputfilelist(self):
        output_list = []
        for i in self.ROI_idx:
            output_list.append(
                os.path.abspath(self.base_name + "_seed_" + str(i) + ".nii.gz")
            )
        return output_list


class Make_Mrtrix_Seeds(BaseInterface):
    """Creates seeding ROIs by intersecting dilated ROIs with WM mask for `mrtrix`.

    Examples
    --------
    >>> from cmtklib.diffusion import Make_Mrtrix_Seeds
    >>> make_mrtrix_seeds = Make_Mrtrix_Seeds()
    >>> make_mrtrix_seeds.inputs.ROI_files  = ['sub-01_space-DWI_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                 'sub-01_space-DWI_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> make_mrtrix_seeds.inputs.WM_file = 'sub-01_space-DWI_label-WM_dseg.nii.gz'
    >>> make_mrtrix_seeds.run()  # doctest: +SKIP

    """

    input_spec = MakeSeedsInputSpec
    output_spec = MakeSeedsOutputSpec
    ROI_idx = []
    base_name = ""

    def _run_interface(self, runtime):
        print(
            "Computing seed files for probabilistic tractography\n==================================================="
        )
        # Load ROI file
        print(self.inputs.ROI_files)

        for ROI_file in self.inputs.ROI_files:
            ROI_vol = nib.load(ROI_file)
            ROI_data = ROI_vol.get_data()
            ROI_affine = ROI_vol.get_affine()
            # Load WM mask
            WM_vol = nib.load(self.inputs.WM_file)
            WM_data = WM_vol.get_data()
            # Extract ROI indexes, define number of ROIs, overlap code and start ROI dilation
            print("ROI dilation...")
            tmp_data = np.unique(ROI_data[ROI_data != 0]).astype(int)
            print(tmp_data.shape)
            self.ROI_idx = np.unique(tmp_data).astype(int)
            bins = np.arange(83)
            counts = np.histogram(self.ROI_idx, bins=bins)
            print(counts)
            print(self.ROI_idx.shape)
            print(self.ROI_idx)
            # Take overlap between dilated ROIs and WM to define seeding regions
            border = (np.multiply(ROI_data, WM_data)).astype(int)
            # Save one nifti file per seeding ROI
            _, self.base_name, _ = split_filename(ROI_file)

            new_image = nib.Nifti1Image(border, ROI_affine)
            save_as = os.path.abspath(self.base_name + "_seeds.nii.gz")
            nib.save(new_image, save_as)
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["seed_files"] = os.path.abspath(self.base_name + "_seeds.nii.gz")
        return outputs


class SplitDiffusionInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, desc="Input diffusion MRI file")

    start = Int(0, desc="Volume index to start the split")

    end = Int(desc="Volume index to end the split")


class SplitDiffusionOutputSpec(TraitedSpec):
    data = File(exists=True, desc="Extracted volumes")

    padding1 = File(exists=False, desc="Extracted volumes with padding 1")

    padding2 = File(exists=False, desc="Extracted volumes with padding 2")


class SplitDiffusion(BaseInterface):
    """Extract volumes from diffusion MRI data given a start and end index.

    Examples
    --------
    >>> from cmtklib.diffusion import SplitDiffusion
    >>> split_dwi = SplitDiffusion()
    >>> split_dwi.inputs.in_file  = 'sub-01_dwi.nii.gz'
    >>> split_dwi.inputs.start  = 5
    >>> split_dwi.inputs.in_file  = 30
    >>> split_dwi.run()  # doctest: +SKIP

    """

    input_spec = SplitDiffusionInputSpec
    output_spec = SplitDiffusionOutputSpec

    def _run_interface(self, runtime):
        diffusion_file = nib.load(self.inputs.in_file)
        diffusion = diffusion_file.get_data()
        affine = diffusion_file.get_affine()
        dim = diffusion.shape
        if self.inputs.start > 0 and self.inputs.end > dim[3] - 1:
            print(
                "End volume is set to {} but it should be bellow {}".format(
                    self.inputs.end, dim[3] - 1
                )
            )
        padding_idx1 = list(range(0, self.inputs.start))
        if len(padding_idx1) > 0:
            temp = diffusion[:, :, :, 0 : self.inputs.start]
            nib.save(
                nib.nifti1.Nifti1Image(temp, affine), os.path.abspath("padding1.nii.gz")
            )
        temp = diffusion[:, :, :, self.inputs.start : self.inputs.end + 1]
        nib.save(nib.nifti1.Nifti1Image(temp, affine), os.path.abspath("data.nii.gz"))
        padding_idx2 = list(range(self.inputs.end, dim[3] - 1))
        if len(padding_idx2) > 0:
            temp = diffusion[:, :, :, self.inputs.end + 1 : dim[3]]
            nib.save(
                nib.nifti1.Nifti1Image(temp, affine), os.path.abspath("padding2.nii.gz")
            )

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["data"] = os.path.abspath("data.nii.gz")
        if os.path.exists(os.path.abspath("padding1.nii.gz")):
            outputs["padding1"] = os.path.abspath("padding1.nii.gz")
        if os.path.exists(os.path.abspath("padding2.nii.gz")):
            outputs["padding2"] = os.path.abspath("padding2.nii.gz")
        return outputs
