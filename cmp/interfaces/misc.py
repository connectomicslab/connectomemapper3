import os
import glob
import numpy as np

try:
    from traitsui.api import *
    from traits.api import *

except ImportError:
    from enthought.traits.api import *
    from enthought.traits.ui.api import *

from nipype.interfaces.base import traits, isdefined, CommandLine, CommandLineInputSpec,\
    TraitedSpec, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec

import nibabel as nib

class ExtractPVEsFrom5TTInputSpec(BaseInterfaceInputSpec):
    in_5tt = File(desc="Input 5TT (4D) image",exists=True,mandatory=True)
    ref_image = File(desc="Reference 3D image to be used to save 3D PVE volumes",exists=True,mandatory=True)
    pve_csf_file = File(desc="CSF Partial Volume Estimation volume estimated from",mandatory=True)
    pve_gm_file = File(desc="GM Partial Volume Estimation volume estimated from",mandatory=True)
    pve_wm_file = File(desc="WM Partial Volume Estimation volume estimated from",mandatory=True)

class ExtractPVEsFrom5TTOutputSpec(TraitedSpec):
    pve_csf_file = File(desc="CSF Partial Volume Estimation volume estimated from",exists=True,mandatory=True)
    pve_gm_file = File(desc="GM Partial Volume Estimation volume estimated from",exists=True,mandatory=True)
    pve_wm_file = File(desc="WM Partial Volume Estimation volume estimated from",exists=True,mandatory=True)

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
        pve_csf = data_5tt[:,:,:,3].squeeze()
        pve_csf_img = nib.Nifti1Image(pve_csf.astype(np.float), affine)
        nib.save(pve_csf_img,os.path.abspath(self.inputs.pve_csf_file))

        # Create and save PVE for WM
        pve_wm = data_5tt[:,:,:,2].squeeze()
        pve_wm_img = nib.Nifti1Image(pve_wm.astype(np.float), affine)
        nib.save(pve_wm_img,os.path.abspath(self.inputs.pve_wm_file))

        # Create and save PVE for GM
        pve_gm = data_5tt[:,:,:,0].squeeze() + data_5tt[:,:,:,1].squeeze()
        pve_gm_img = nib.Nifti1Image(pve_gm.astype(np.float), affine)
        nib.save(pve_gm_img,os.path.abspath(self.inputs.pve_gm_file))

        # Dilate PVEs and normalize to 1
        fwhm = 2.0
        radius = np.float(0.5 * fwhm)
        sigma = np.float(fwhm / 2.3548)

        print("sigma : %s"%sigma)

        fslmaths_cmd = 'fslmaths %s -kernel sphere %s -dilD %s' % (os.path.abspath(self.inputs.pve_csf_file),radius,os.path.abspath(self.inputs.pve_csf_file))
        print("Dilate CSF PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel sphere %s -dilD %s' % (os.path.abspath(self.inputs.pve_wm_file),radius,os.path.abspath(self.inputs.pve_wm_file))
        print("Dilate WM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel sphere %s -dilD %s' % (os.path.abspath(self.inputs.pve_gm_file),radius,os.path.abspath(self.inputs.pve_gm_file))
        print("Dilate GM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel gauss %s -fmean %s' % (os.path.abspath(self.inputs.pve_csf_file),sigma,os.path.abspath(self.inputs.pve_csf_file))
        print("Gaussian smoothing : CSF PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel gauss %s -fmean %s' % (os.path.abspath(self.inputs.pve_wm_file),sigma,os.path.abspath(self.inputs.pve_wm_file))
        print("Gaussian smoothing : WM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        fslmaths_cmd = 'fslmaths %s -kernel gauss %s -fmean %s' % (os.path.abspath(self.inputs.pve_gm_file),sigma,os.path.abspath(self.inputs.pve_gm_file))
        print("Gaussian smoothing : GM PVE")
        print(fslmaths_cmd)
        process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        pve_csf = nib.load(os.path.abspath(self.inputs.pve_csf_file)).get_data()
        pve_wm = nib.load(os.path.abspath(self.inputs.pve_wm_file)).get_data()
        pve_gm = nib.load(os.path.abspath(self.inputs.pve_gm_file)).get_data()

        pve_sum = pve_csf + pve_wm + pve_gm
        pve_csf = np.divide(pve_csf,pve_sum)
        pve_wm = np.divide(pve_wm,pve_sum)
        pve_gm = np.divide(pve_gm,pve_sum)

        pve_csf_img = nib.Nifti1Image(pve_csf.astype(np.float), affine)
        nib.save(pve_csf_img,os.path.abspath(self.inputs.pve_csf_file))

        pve_wm_img = nib.Nifti1Image(pve_wm.astype(np.float), affine)
        nib.save(pve_wm_img,os.path.abspath(self.inputs.pve_wm_file))

        pve_gm_img = nib.Nifti1Image(pve_gm.astype(np.float), affine)
        nib.save(pve_gm_img,os.path.abspath(self.inputs.pve_gm_file))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['pve_csf_file'] = os.path.abspath(self.inputs.pve_csf_file)
        outputs['pve_wm_file'] = os.path.abspath(self.inputs.pve_wm_file)
        outputs['pve_gm_file'] = os.path.abspath(self.inputs.pve_gm_file)
        return outputs


class ComputeSphereRadiusInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)
    dilation_radius = Float(mandatory=True)

class ComputeSphereRadiusOutputSpec(TraitedSpec):
    sphere_radius = Float

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
        self.sphere_radius =  0.5*min_size + self.inputs.dilation_radius * min_size
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['sphere_radius'] = self.sphere_radius
        return outputs

class ExtractImageVoxelSizesInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)


class ExtractImageVoxelSizesOutputSpec(TraitedSpec):
    voxel_sizes = List(Int(),Int(),Int())

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
    in_tracks = File(exists=True,mandatory=True,desc='Input track file in MRtrix .tck format')
    in_image = File(exists=True,mandatory=True,desc='Input image used to extract the header')
    out_tracks = File(mandatory=True,desc='Output track file in Trackvis .trk format')

class Tck2TrkOutputSpec(TraitedSpec):
    out_tracks = File(exists=True,desc='Output track file in Trackvis .trk format')

class Tck2Trk(BaseInterface):

    input_spec = Tck2TrkInputSpec
    output_spec = Tck2TrkOutputSpec

    def _run_interface(self, runtime):
        import nibabel
        from nibabel.streamlines import Field
        from nibabel.orientations import aff2axcodes
        print '-> Load nifti and copy header'
        nii = nibabel.load(self.inputs.in_image)

        header = {}
        header[Field.VOXEL_TO_RASMM] = nii.affine.copy()
        header[Field.VOXEL_SIZES] = nii.header.get_zooms()[:3]
        header[Field.DIMENSIONS] = nii.shape[:3]
        header[Field.VOXEL_ORDER] = "".join(aff2axcodes(nii.affine))

        if nibabel.streamlines.detect_format(self.inputs.in_tracks) is not nibabel.streamlines.TckFile:
            print("Skipping non TCK file: '{}'".format(tractogram))
        else:
            tck = nibabel.streamlines.load(self.inputs.in_tracks)
            self.out_tracks = self.inputs.out_tracks
            nibabel.streamlines.save(tck.tractogram, self.out_tracks, header=header)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_tracks'] = os.path.abspath(self.out_tracks)
        return outputs
