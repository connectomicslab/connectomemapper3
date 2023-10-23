import sys
import os
from os import path as op

from traits.api import *
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, TraitedSpec, InputMultiPath, File
import nipype.pipeline.engine as pe


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

        import nibabel as nib

        gmwmi_img = nib.load(self.inputs.in_gmwmi_file)
        gmwmi_data = gmwmi_img.get_data()
        maxv = gmwmi_data.max()

        for fname in self.inputs.in_roi_volumes:
            if "scale1" in fname:
                roi_fname = fname
                print('roi_fname: %s' % roi_fname)

        roi_img = nib.load(roi_fname)
        roi_data = roi_img.get_data()

        new_gmwmi_data = gmwmi_data.copy()

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


def main(argv):
    bids_dir = '/home/localadmin/Softwares/BitBucket/ds-test-bidsapp'
    subject = 'sub-A006'
    session = 'ses-20170523161523'
    subject_derivatives_dir = op.join(
        bids_dir, 'derivatives/cmp', subject, session)

    gmwmi_fname = op.join(subject_derivatives_dir, 'tmp/diffusion_pipeline/preprocessing_stage/gmwmi_resample',
                          'gmwmi_resampled.nii.gz')
    roi_fnames = [op.join(subject_derivatives_dir,
                          'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample3',
                          'sub-A006_ses-20170523161523_T1w_parc_scale1_out.nii.gz'),
                  op.join(subject_derivatives_dir,
                          'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample1',
                          'sub-A006_ses-20170523161523_T1w_parc_scale2_out.nii.gz'),
                  op.join(subject_derivatives_dir,
                          'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample4',
                          'sub-A006_ses-20170523161523_T1w_parc_scale3_out.nii.gz'),
                  op.join(subject_derivatives_dir,
                          'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample2',
                          'sub-A006_ses-20170523161523_T1w_parc_scale4_out.nii.gz'),
                  op.join(subject_derivatives_dir,
                          'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample0',
                          'sub-A006_ses-20170523161523_T1w_parc_scale5_out.nii.gz')]

    updateGMWM = pe.Node(
        interface=UpdateGMWMInterfaceSeeding(), name='updateGMWM')
    updateGMWM.inputs.in_gmwmi_file = gmwmi_fname
    updateGMWM.inputs.in_roi_volumes = roi_fnames
    updateGMWM.inputs.out_gmwmi_file = op.join('/home/localadmin/Desktop',
                                               '%s_%s_gmwmi_proc.nii.gz' % (subject, session))

    node = updateGMWM.run()

    return True


if __name__ == '__main__':
    main(sys.argv[1:])
