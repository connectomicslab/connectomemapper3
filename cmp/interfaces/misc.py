import os
import glob
import numpy as np

# try:
#     from traitsui.api import *
#     from traits.api import *
#
# except ImportError:
#     from enthought.traits.api import *
#     from enthought.traits.ui.api import *

from nipype.interfaces.base import traits, isdefined, CommandLine, CommandLineInputSpec,\
    TraitedSpec, File, InputMultiPath, OutputMultiPath, BaseInterface, BaseInterfaceInputSpec

import nibabel as nib

class ExtractPVEsFrom5TTInputSpec(BaseInterfaceInputSpec):
    in_5tt = File(desc="Input 5TT (4D) image",exists=True,mandatory=True)
    ref_image = File(desc="Reference 3D image to be used to save 3D PVE volumes",exists=True,mandatory=True)
    pve_csf_file = File(desc="CSF Partial Volume Estimation volume estimated from",mandatory=True)
    pve_gm_file = File(desc="GM Partial Volume Estimation volume estimated from",mandatory=True)
    pve_wm_file = File(desc="WM Partial Volume Estimation volume estimated from",mandatory=True)

class ExtractPVEsFrom5TTOutputSpec(TraitedSpec):
    partial_volume_files = OutputMultiPath(File,desc="CSF/GM/WM Partial Volume Estimation images estimated from",exists=True)

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
        self.sphere_radius =  0.5*min_size + self.inputs.dilation_radius * min_size
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['sphere_radius'] = self.sphere_radius
        return outputs

class ExtractImageVoxelSizesInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True)


class ExtractImageVoxelSizesOutputSpec(TraitedSpec):
    voxel_sizes = traits.List(traits.Int(),traits.Int(),traits.Int())

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


class flipBvecInputSpec(BaseInterfaceInputSpec):
    bvecs = File(exists=True)
    flipping_axis = traits.List()
    delimiter = traits.Str()
    header_lines = traits.Int(0)
    orientation = traits.Enum(['v','h'])

class flipBvecOutputSpec(TraitedSpec):
    bvecs_flipped = File(exists=True)

class flipBvec(BaseInterface):
    input_spec = flipBvecInputSpec
    output_spec = flipBvecOutputSpec

    def _run_interface(self,runtime):
        axis_dict = {'x':0, 'y':1, 'z':2}
        import numpy as np
        f = open(self.inputs.bvecs,'r')
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
                table[:,axis_dict[i]] = -table[:,axis_dict[i]]
        elif self.inputs.orientation == 'h':
            for i in self.inputs.flipping_axis:
                table[axis_dict[i],:] = -table[axis_dict[i],:]
        out_f = file(os.path.abspath('flipped_bvecs.bvec'),'a')
        if self.inputs.header_lines > 0:
            out_f.write(header)
        np.savetxt(out_f,table,delimiter=self.inputs.delimiter)
        out_f.close()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["bvecs_flipped"] = os.path.abspath('flipped_bvecs.bvec')
        return outputs


class UpdateGMWMInterfaceSeedingInputSpec(BaseInterfaceInputSpec):
    in_gmwmi_file = File(exists=True,mandatory=True,desc='Input GMWM interface image used for streamline seeding')
    out_gmwmi_file = File(mandatory=True, desc='Output GM WM interface used for streamline seeding')
    in_roi_volumes = InputMultiPath(File(exists=True),mandatory=True,desc='Input parcellation images')

class UpdateGMWMInterfaceSeedingOutputSpec(TraitedSpec):
    out_gmwmi_file = File(exists=True, desc='Output GM WM interface used for streamline seeding')

class UpdateGMWMInterfaceSeeding(BaseInterface):
    input_spec = UpdateGMWMInterfaceSeedingInputSpec
    output_spec = UpdateGMWMInterfaceSeedingOutputSpec

    def _run_interface(self, runtime):

        gmwmi_img = nib.load(self.inputs.in_gmwmi_file)
        gmwmi_data = gmwmi_img.get_data()
        maxv = gmwmi_data.max()

        for fname in self.inputs.in_roi_volumes:
            if "scale1" in fname:
                roi_fname = fname
                print('roi_fname: %s'%roi_fname)


        roi_img = nib.load(roi_fname)
        roi_data = roi_img.get_data()

        new_gmwmi_data = gmwmi_data.copy()

        if roi_data.max() > 83:

            # Thalamic nuclei
            new_gmwmi_data[roi_data==35] = maxv
            new_gmwmi_data[roi_data==36] = maxv
            new_gmwmi_data[roi_data==37] = maxv
            new_gmwmi_data[roi_data==38] = maxv
            new_gmwmi_data[roi_data==39] = maxv
            new_gmwmi_data[roi_data==40] = maxv
            new_gmwmi_data[roi_data==41] = maxv
            new_gmwmi_data[roi_data==96] = maxv
            new_gmwmi_data[roi_data==97] = maxv
            new_gmwmi_data[roi_data==98] = maxv
            new_gmwmi_data[roi_data==99] = maxv
            new_gmwmi_data[roi_data==100] = maxv
            new_gmwmi_data[roi_data==101] = maxv
            new_gmwmi_data[roi_data==102] = maxv

            # Hippocampal subfields
            new_gmwmi_data[roi_data==48] = maxv
            new_gmwmi_data[roi_data==49] = maxv
            new_gmwmi_data[roi_data==50] = maxv
            new_gmwmi_data[roi_data==51] = maxv
            new_gmwmi_data[roi_data==52] = maxv
            new_gmwmi_data[roi_data==53] = maxv
            new_gmwmi_data[roi_data==54] = maxv
            new_gmwmi_data[roi_data==55] = maxv
            new_gmwmi_data[roi_data==56] = maxv
            new_gmwmi_data[roi_data==57] = maxv
            new_gmwmi_data[roi_data==58] = maxv
            new_gmwmi_data[roi_data==59] = maxv
            new_gmwmi_data[roi_data==109] = maxv
            new_gmwmi_data[roi_data==110] = maxv
            new_gmwmi_data[roi_data==111] = maxv
            new_gmwmi_data[roi_data==112] = maxv
            new_gmwmi_data[roi_data==113] = maxv
            new_gmwmi_data[roi_data==114] = maxv
            new_gmwmi_data[roi_data==115] = maxv
            new_gmwmi_data[roi_data==116] = maxv
            new_gmwmi_data[roi_data==117] = maxv
            new_gmwmi_data[roi_data==118] = maxv
            new_gmwmi_data[roi_data==119] = maxv
            new_gmwmi_data[roi_data==120] = maxv

            # Brain stem
            new_gmwmi_data[roi_data==123] = maxv
            new_gmwmi_data[roi_data==124] = maxv
            new_gmwmi_data[roi_data==125] = maxv
            new_gmwmi_data[roi_data==126] = maxv

        new_gmwmi_img = nib.Nifti1Pair(new_gmwmi_data, gmwmi_img.affine)
        nib.save(new_gmwmi_img, self.inputs.out_gmwmi_file)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        outputs['out_gmwmi_file'] = os.path.abspath(self.inputs.out_gmwmi_file)

        return outputs
