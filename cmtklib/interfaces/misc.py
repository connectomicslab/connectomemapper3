# Copyright (C) 2017-2019, Brain Communication Pathways Sinergia Consortium, Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

import os
import glob
import numpy as np
from traits.api import *

from nipype.utils.filemanip import split_filename
from nipype.interfaces.mrtrix.convert  import get_vox_dims, get_data_dims
from nipype.interfaces.base import traits, isdefined, CommandLine, CommandLineInputSpec, \
    TraitedSpec, File, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec
import nipype.pipeline.engine as pe

import nibabel as nib


class match_orientationInputSpec(BaseInterfaceInputSpec):
    trackvis_file = File(exists=True, mandatory=True,
                         desc="Trackvis file outputed by gibbs miniapp, with the LPS orientation set as default")
    ref_image_file = File(exists=True, mandatory=True,
                          desc="File used as input for the gibbs tracking (wm mask)")


class match_orientationOutputSpec(TraitedSpec):
    out_file = File(
        exists=True, desc='Trackvis file with orientation matching gibbs input')


class match_orientations(BaseInterface):
    input_spec = match_orientationInputSpec
    output_spec = match_orientationOutputSpec

    def _run_interface(self, runtime):
        # filename = os.path.basename(self.inputs.trackvis_file)

        _, name, _ = split_filename(self.inputs.trackvis_file)
        filename = name + '_orcor.trk'

        dx, dy, dz = get_data_dims(self.inputs.ref_image_file)
        vx, vy, vz = get_vox_dims(self.inputs.ref_image_file)
        image_file = nib.load(self.inputs.ref_image_file)
        affine = image_file.get_affine()
        import numpy as np
        # Reads MITK tracks
        fib, hdr = nib.trackvis.read(self.inputs.trackvis_file)
        trk_header = nib.trackvis.empty_header()
        trk_header['dim'] = [dx, dy, dz]
        trk_header['voxel_size'] = [vx, vy, vz]
        trk_header['origin'] = [0, 0, 0]
        axcode = nib.orientations.aff2axcodes(affine)
        if axcode[0] != str(hdr['voxel_order'])[0]:
            flip_x = -1
        else:
            flip_x = 1
        if axcode[1] != str(hdr['voxel_order'])[1]:
            flip_y = -1
        else:
            flip_y = 1
        if axcode[2] != str(hdr['voxel_order'])[2]:
            flip_z = -1
        else:
            flip_z = 1
        trk_header['voxel_order'] = axcode[0] + axcode[1] + axcode[2]
        new_fib = []
        for i in range(len(fib)):
            temp_fib = fib[i][0].copy()
            for j in range(len(fib[i][0])):
                temp_fib[j] = [flip_x * (fib[i][0][j][0] - hdr['origin'][0]) + vx / 2,
                               flip_y * (fib[i][0][j][1] -
                                         hdr['origin'][1]) + vy / 2,
                               flip_z * (fib[i][0][j][2] - hdr['origin'][2]) + vz / 2]
            new_fib.append((temp_fib, None, None))
        nib.trackvis.write(os.path.abspath(filename), new_fib,
                           trk_header, points_space='voxmm')
        print('file written to %s' % os.path.abspath(filename))
        return runtime

    def _list_outputs(self):
        # filename = os.path.basename(self.inputs.trackvis_file)
        _, name, _ = split_filename(self.inputs.trackvis_file)
        filename = name + '_orcor.trk'

        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(filename)
        return outputs


class extractHeaderVoxel2WorldMatrixInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc='Input image file')


class extractHeaderVoxel2WorldMatrixOutputSpec(TraitedSpec):
    out_matrix = File(
        exists=true, desc='Output voxel to world affine transform file')


class extractHeaderVoxel2WorldMatrix(BaseInterface):
    input_spec = extractHeaderVoxel2WorldMatrixInputSpec
    output_spec = extractHeaderVoxel2WorldMatrixOutputSpec

    def _run_interface(self, runtime):
        im = nib.load(self.inputs.in_file)
        transform = np.array(im.get_affine())

        out_f = file(os.path.abspath('voxel2world.txt'), 'a')
        np.savetxt(out_f, transform, delimiter=' ', fmt="%6.6g")
        out_f.close()

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_matrix"] = os.path.abspath('voxel2world.txt')
        return outputs


class flipTableInputSpec(BaseInterfaceInputSpec):
    table = File(exists=True)
    flipping_axis = List()
    delimiter = Str()
    header_lines = Int(0)
    orientation = Enum(['v', 'h'])


class flipTableOutputSpec(TraitedSpec):
    table = File(exists=True)


class flipTable(BaseInterface):
    input_spec = flipTableInputSpec
    output_spec = flipTableOutputSpec

    def _run_interface(self, runtime):
        axis_dict = {'x': 0, 'y': 1, 'z': 2}
        import numpy as np
        f = open(self.inputs.table, 'r')
        header = ''
        for h in range(self.inputs.header_lines):
            header += f.readline()
        if self.inputs.delimiter == ' ':
            table = np.loadtxt(f)
        else:
            table = np.loadtxt(f, delimiter=self.inputs.delimiter)
        f.close()
        if self.inputs.orientation == 'v':
            for i in self.inputs.flipping_axis:
                table[:, axis_dict[i]] = -table[:, axis_dict[i]]
        elif self.inputs.orientation == 'h':
            for i in self.inputs.flipping_axis:
                table[axis_dict[i], :] = -table[axis_dict[i], :]
        out_f = file(os.path.abspath('flipped_table.txt'), 'a')
        if self.inputs.header_lines > 0:
            out_f.write(header)
        np.savetxt(out_f, table, delimiter=self.inputs.delimiter)
        out_f.close()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["table"] = os.path.abspath('flipped_table.txt')
        return outputs


class ExtractPVEsFrom5TTInputSpec(BaseInterfaceInputSpec):
    in_5tt = File(desc="Input 5TT (4D) image", exists=True, mandatory=True)
    ref_image = File(
        desc="Reference 3D image to be used to save 3D PVE volumes", exists=True, mandatory=True)
    pve_csf_file = File(
        desc="CSF Partial Volume Estimation volume estimated from", mandatory=True)
    pve_gm_file = File(
        desc="GM Partial Volume Estimation volume estimated from", mandatory=True)
    pve_wm_file = File(
        desc="WM Partial Volume Estimation volume estimated from", mandatory=True)


class ExtractPVEsFrom5TTOutputSpec(TraitedSpec):
    partial_volume_files = OutputMultiPath(File, desc="CSF/GM/WM Partial Volume Estimation images estimated from",
                                           exists=True)


class ExtractPVEsFrom5TT(BaseInterface):
    input_spec = ExtractPVEsFrom5TTInputSpec
    output_spec = ExtractPVEsFrom5TTOutputSpec

    def _run_interface(self, runtime):
        import subprocess

        img_5tt = nib.load(self.inputs.in_5tt)
        data_5tt = img_5tt.get_data()

        ref_img = nib.load(self.inputs.ref_image)
        hdr = ref_img.get_header()
        affine = ref_img.get_affine()

        print('Shape : {}'.format(data_5tt.shape))

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
        pve_gm = data_5tt[:, :, :, 0].squeeze() + data_5tt[:,
                                                           :, :, 1].squeeze()
        pve_gm_img = nib.Nifti1Image(pve_gm.astype(np.float), affine)
        nib.save(pve_gm_img, os.path.abspath(self.inputs.pve_gm_file))

        # Dilate PVEs and normalize to 1
        fwhm = 2.0
        radius = np.float(0.5 * fwhm)
        sigma = np.float(fwhm / 2.3548)

        print("sigma : %s" % sigma)

        fslmaths_cmd = 'fslmaths %s -kernel sphere %s -dilD %s' % (
            os.path.abspath(self.inputs.pve_csf_file), radius, os.path.abspath(self.inputs.pve_csf_file))
        print("Dilate CSF PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel sphere %s -dilD %s' % (
            os.path.abspath(self.inputs.pve_wm_file), radius, os.path.abspath(self.inputs.pve_wm_file))
        print("Dilate WM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel sphere %s -dilD %s' % (
            os.path.abspath(self.inputs.pve_gm_file), radius, os.path.abspath(self.inputs.pve_gm_file))
        print("Dilate GM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel gauss %s -fmean %s' % (
            os.path.abspath(self.inputs.pve_csf_file), sigma, os.path.abspath(self.inputs.pve_csf_file))
        print("Gaussian smoothing : CSF PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel gauss %s -fmean %s' % (
            os.path.abspath(self.inputs.pve_wm_file), sigma, os.path.abspath(self.inputs.pve_wm_file))
        print("Gaussian smoothing : WM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel gauss %s -fmean %s' % (
            os.path.abspath(self.inputs.pve_gm_file), sigma, os.path.abspath(self.inputs.pve_gm_file))
        print("Gaussian smoothing : GM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(
            fslmaths_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        pve_csf = nib.load(os.path.abspath(
            self.inputs.pve_csf_file)).get_data()
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

        outputs['partial_volume_files'] = pve_files

        return outputs


class ComputeSphereRadiusInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)
    dilation_radius = traits.Float(mandatory=True)


class ComputeSphereRadiusOutputSpec(TraitedSpec):
    sphere_radius = traits.Float


class ComputeSphereRadius(BaseInterface):
    input_spec = ComputeSphereRadiusInputSpec
    output_spec = ComputeSphereRadiusOutputSpec

    def _run_interface(self, runtime):
        img = nib.load(self.inputs.in_file)
        voxel_sizes = img.get_header().get_zooms()[:3]
        min_size = 100
        for voxel_size in voxel_sizes:
            if voxel_size < min_size:
                min_size = voxel_size
        self.sphere_radius = 0.5 * min_size + self.inputs.dilation_radius * min_size
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['sphere_radius'] = self.sphere_radius
        return outputs


class ExtractImageVoxelSizesInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)


class ExtractImageVoxelSizesOutputSpec(TraitedSpec):
    voxel_sizes = traits.List((traits.Int(), traits.Int(), traits.Int()))


class ExtractImageVoxelSizes(BaseInterface):
    input_spec = ExtractImageVoxelSizesInputSpec
    output_spec = ExtractImageVoxelSizesOutputSpec

    def _run_interface(self, runtime):
        img = nib.load(self.inputs.in_file)
        self.voxel_sizes = img.get_header().get_zooms()[:3]
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['voxel_sizes'] = self.voxel_sizes
        return outputs


class Tck2TrkInputSpec(BaseInterfaceInputSpec):
    in_tracks = File(exists=True, mandatory=True,
                     desc='Input track file in MRtrix .tck format')
    in_image = File(exists=True, mandatory=True,
                    desc='Input image used to extract the header')
    out_tracks = File(
        mandatory=True, desc='Output track file in Trackvis .trk format')


class Tck2TrkOutputSpec(TraitedSpec):
    out_tracks = File(
        exists=True, desc='Output track file in Trackvis .trk format')


class Tck2Trk(BaseInterface):
    input_spec = Tck2TrkInputSpec
    output_spec = Tck2TrkOutputSpec

    def _run_interface(self, runtime):

        from nibabel.streamlines import Field
        from nibabel.orientations import aff2axcodes
        print('-> Load nifti and copy header')
        nii = nib.load(self.inputs.in_image)

        header = {}
        header[Field.VOXEL_TO_RASMM] = nii.affine.copy()
        header[Field.VOXEL_SIZES] = nii.header.get_zooms()[:3]
        header[Field.DIMENSIONS] = nii.shape[:3]
        header[Field.VOXEL_ORDER] = "".join(aff2axcodes(nii.affine))

        if nib.streamlines.detect_format(self.inputs.in_tracks) is not nib.streamlines.TckFile:
            print("Skipping non TCK file: '{}'".format(self.inputs.in_tracks))
        else:
            tck = nib.streamlines.load(self.inputs.in_tracks)
            self.out_tracks = self.inputs.out_tracks
            nib.streamlines.save(
                tck.tractogram, self.out_tracks, header=header)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_tracks'] = os.path.abspath(self.out_tracks)
        return outputs


class flipBvecInputSpec(BaseInterfaceInputSpec):
    bvecs = File(exists=True)
    flipping_axis = traits.List()
    delimiter = traits.Str()
    header_lines = traits.Int(0)
    orientation = traits.Enum(['v', 'h'])


class flipBvecOutputSpec(TraitedSpec):
    bvecs_flipped = File(exists=True)


class flipBvec(BaseInterface):
    input_spec = flipBvecInputSpec
    output_spec = flipBvecOutputSpec

    def _run_interface(self, runtime):
        axis_dict = {'x': 0, 'y': 1, 'z': 2}
        import numpy as np
        f = open(self.inputs.bvecs, 'r')
        header = ''
        for h in range(self.inputs.header_lines):
            header += f.readline()
        if self.inputs.delimiter == ' ':
            table = np.loadtxt(f)
        else:
            table = np.loadtxt(f, delimiter=self.inputs.delimiter)
        f.close()
        
        if self.inputs.orientation == 'v':
            for i in self.inputs.flipping_axis:
                table[:, axis_dict[i]] = -table[:, axis_dict[i]]
        elif self.inputs.orientation == 'h':
            for i in self.inputs.flipping_axis:
                table[axis_dict[i], :] = -table[axis_dict[i], :]

        out_f = os.path.abspath('flipped_bvecs.bvec')
        np.savetxt(out_f, table, header=header, delimiter=self.inputs.delimiter)
        
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
        outputs["bvecs_flipped"] = os.path.abspath('flipped_bvecs.bvec')
        return outputs


class UpdateGMWMInterfaceSeedingInputSpec(BaseInterfaceInputSpec):
    in_gmwmi_file = File(exists=True, mandatory=True,
                         desc='Input GMWM interface image used for streamline seeding')
    out_gmwmi_file = File(
        mandatory=True, desc='Output GM WM interface used for streamline seeding')
    in_roi_volumes = InputMultiPath(
        File(exists=True), mandatory=True, desc='Input parcellation images')


class UpdateGMWMInterfaceSeedingOutputSpec(TraitedSpec):
    out_gmwmi_file = File(
        exists=True, desc='Output GM WM interface used for streamline seeding')


class UpdateGMWMInterfaceSeeding(BaseInterface):
    input_spec = UpdateGMWMInterfaceSeedingInputSpec
    output_spec = UpdateGMWMInterfaceSeedingOutputSpec

    def _run_interface(self, runtime):

        gmwmi_img = nib.load(self.inputs.in_gmwmi_file)
        gmwmi_data = gmwmi_img.get_data()
        maxv = gmwmi_data.max()

        for fname in self.inputs.in_roi_volumes:
            if ("scale1" in fname) or (len(self.inputs.in_roi_volumes) == 1):
                roi_fname = fname
                print('roi_fname: %s' % roi_fname)

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

        outputs['out_gmwmi_file'] = os.path.abspath(self.inputs.out_gmwmi_file)

        return outputs


class getCRS2XYZtkRegTransformInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, argstr='%s', mandatory=True, position=1,
                   desc="File used as input for getting CRS to XYZtkReg transform (DWI data)")
    crs2ras_tkr = traits.Bool(argstr='--crs2ras-tk', mandatory=True, position=2,
                              desc='return the crs2ras-tkr transform to output console')


class getCRS2XYZtkRegTransformOutputSpec(TraitedSpec):
    pass


class getCRS2XYZtkRegTransform(CommandLine):
    _cmd = 'mri_info'
    input_spec = getCRS2XYZtkRegTransformInputSpec
    output_spec = getCRS2XYZtkRegTransformOutputSpec

    def _run_interface(self, runtime):
        runtime = super(getCRS2XYZtkRegTransform, self)._run_interface(runtime)
        print('CMD: ', runtime.cmdline)
        print(runtime.stdout)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_transform'] = os.path.abspath(self._gen_outfilename())

    def _gen_outfilename(self):
        _, name, _ = split_filename(self.inputs.in_file)
        return name + '_crs2ras_tk_transform.txt'


class transform_trk_CRS2XYZtkRegInputSpec(CommandLineInputSpec):
    trackvis_file = File(exists=True, mandatory=True,
                         desc="Trackvis file output from MRtricToTrackvis converter, with the LAS orientation set as default")
    ref_image_file = File(exists=True, mandatory=True,
                          desc="File used as input for getting CRS to XYZtkReg transform (DWI data)")


class transform_trk_CRS2XYZtkRegOutputSpec(TraitedSpec):
    out_file = File(
        exists=True, desc='Trackvis file in the same space than Freesurfer data')
    out_transform = File(exists=True, desc='CRS to XYZtkReg transform file')


class transform_trk_CRS2XYZtkReg(BaseInterface):
    input_spec = transform_trk_CRS2XYZtkRegInputSpec
    output_spec = transform_trk_CRS2XYZtkRegOutputSpec

    def _run_interface(self, runtime):
        _, name, _ = split_filename(self.inputs.trackvis_file)
        transform_filename = 'CRS2XYZtkReg.txt'
        out_trackvis_filename = name + '_tkreg.trk'

        # Load original Trackvis file
        fib, hdr = nib.trackvis.read(self.inputs.trackvis_file)

        # Load reference image file
        ref_image = nib.load(self.inputs.ref_image_file)

        CRS2XYZtkRegtransform = pe.Node(interface=getCRS2XYZtkRegTransform(crs2ras_tkr=True),
                                        name='CRS2XYZtkRegtransform')
        CRS2XYZtkRegtransform.inputs.in_file = self.inputs.ref_image_file

        CRS2XYZtkRegtransform.run()

        # print "STDOUT:",runtime.stdout
        # Run "mrinfo path-to-ref_image_file --crs2ras-tkr" command to get 'CRS' to 'XYZtkReg' transform
        # cmd = 'mrinfo  --crs2ras-tkr' + ' ' + self.inputs.ref_image_file
        # cmd = ['mrinfo',self.inputs.ref_image_file,'--crs2ras-tkr']

        # transform_file = open(transform_filename,'w')
        # mrinfo_process = subprocess.call(cmd,stdout=transform_file,shell=True)

        nib.trackvis.write(out_trackvis_filename, fib, hdr)

        return runtime

    def _list_outputs(self):
        # filename = os.path.basename(self.inputs.trackvis_file)
        _, name, _ = split_filename(self.inputs.trackvis_file)
        transform_filename = 'CRS2XYZtkReg.txt'
        out_trackvis_filename = name + '_tkreg.trk'

        outputs = self.output_spec().get()
        outputs['out_file'] = os.path.abspath(out_trackvis_filename)
        outputs['out_transform'] = os.path.abspath(transform_filename)
        return outputs


class make_seedsInputSpec(BaseInterfaceInputSpec):
    ROI_files = InputMultiPath(
        File(exists=True), desc='ROI files registered to diffusion space')
    WM_file = File(
        mandatory=True, desc='WM mask file registered to diffusion space')
    # DWI = File(mandatory=True,desc='Diffusion data file for probabilistic tractography')


class make_seedsOutputSpec(TraitedSpec):
    seed_files = OutputMultiPath(
        File(exists=True), desc='Seed files for probabilistic tractography')


class make_seeds(BaseInterface):
    """ - Creates seeding ROIs by intersecting dilated ROIs with WM mask
    """
    input_spec = make_seedsInputSpec
    output_spec = make_seedsOutputSpec
    ROI_idx = []
    base_name = ''

    def _run_interface(self, runtime):
        print(
            "Computing seed files for probabilistic tractography\n===================================================")
        # Load ROI file
        txt_file = open(self.base_name + '_seeds.txt', 'w')

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
                    self.base_name + '_seed_' + str(i) + '.nii.gz')
                txt_file.write(str(self.base_name + '_seed_' +
                                   str(i) + '.nii.gz' + '\n'))
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
            output_list.append(os.path.abspath(
                self.base_name + '_seed_' + str(i) + '.nii.gz'))
        return output_list


class make_mrtrix_seeds(BaseInterface):
    """ - Creates seeding ROIs by intersecting dilated ROIs with WM mask
    """
    input_spec = make_seedsInputSpec
    output_spec = make_seedsOutputSpec
    ROI_idx = []
    base_name = ''

    def _run_interface(self, runtime):
        print(
            "Computing seed files for probabilistic tractography\n===================================================")
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
            save_as = os.path.abspath(self.base_name + '_seeds.nii.gz')
            nib.save(new_image, save_as)
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["seed_files"] = os.path.abspath(
            self.base_name + '_seeds.nii.gz')
        return outputs
