import sys
import os
from os import path as op

from traits.api import *
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, TraitedSpec, InputMultiPath, File
import nipype.pipeline.engine as pe

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

        import nibabel as nib

        gmwmi_img = nib.load(self.inputs.in_gmwmi_file)
        gmwmi_data = gmwmi_img.get_data()

        roi_img = nib.load(self.inputs.in_roi_volumes[0])
        roi_data = roi_img.get_data()

        new_gmwmi_data = gmwmi_data.copy()

        new_gmwmi_img = nib.Nifti1Pair(new_gmwmi_data, gmwmi_img.affine)
        nib.save(new_gmwmi_img, self.inputs.out_gmwmi_file)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        outputs['out_gmwmi_file'] = os.path.abspath(self.inputs.out_gmwmi_file)

        return outputs

def main(argv):

    bids_dir='/home/localadmin/Softwares/BitBucket/ds-test'
    subject = 'sub-A006'
    session = 'ses-20170523161523'
    subject_derivatives_dir = op.join(bids_dir,'derivatives/cmp',subject,session)

    gmwmi_fname = op.join(subject_derivatives_dir,'tmp/diffusion_pipeline/preprocessing_stage/gmwmi_resample','gmwmi_resampled.nii.gz')
    roi_fnames = [op.join(subject_derivatives_dir,'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample3','sub-A006_ses-20170523161523_T1w_parc_scale1_out.nii.gz'),
                   op.join(subject_derivatives_dir,'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample1','sub-A006_ses-20170523161523_T1w_parc_scale2_out.nii.gz'),
                   op.join(subject_derivatives_dir,'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample4','sub-A006_ses-20170523161523_T1w_parc_scale3_out.nii.gz'),
                   op.join(subject_derivatives_dir,'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample2','sub-A006_ses-20170523161523_T1w_parc_scale4_out.nii.gz'),
                   op.join(subject_derivatives_dir,'tmp/diffusion_pipeline/preprocessing_stage/ROIs_resample/mapflow/_ROIs_resample0','sub-A006_ses-20170523161523_T1w_parc_scale5_out.nii.gz')]

    updateGMWM = pe.Node(interface=UpdateGMWMInterfaceSeeding(),name='updateGMWM')
    updateGMWM.inputs.in_gmwmi_file = gmwmi_fname
    updateGMWM.inputs.in_roi_volumes = roi_fnames
    updateGMWM.inputs.out_gmwmi_file = op.join('/home/localadmin/Desktop','%s_%s_gmwmi_proc.nii.gz'%(subject,session))

    node = updateGMWM.run()

    return True

if __name__ == '__main__':
    main(sys.argv[1:])
