# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK utility functions and Nipype interfaces for anatomical parcellation."""

# Common libraries import
import os
from time import localtime, strftime
import os.path as op
from pathlib import Path
import pkg_resources
import subprocess
import shutil
import math

import nibabel as ni
import networkx as nx
import numpy as np

try:
    from scipy import ndimage
    import scipy.ndimage.morphology as nd
except ImportError:
    raise Exception(
        'Need scipy for binary erosion of white matter and CSF masks')

# Nipype imports
from nipype.interfaces.base import traits, BaseInterfaceInputSpec, TraitedSpec, BaseInterface, Directory, File, \
    InputMultiPath, OutputMultiPath
from nipype.utils.logger import logging

iflogger = logging.getLogger('nipype.interface')


class ComputeParcellationRoiVolumesInputSpec(BaseInterfaceInputSpec):
    """This is a class for the definition of inputs of the `ComputeParcellationRoiVolumes` Nipype interface.

    Attributes
    ----------
    roi_volumes (files): list
        ROI volumes registered to diffusion space

    parcellation_scheme (files): list
        Parcellation scheme being used (only Lausanne2018)

    roi_graphMLs (files): list
        GraphML description of ROI volumes (Lausanne2018)
    """
    roi_volumes = InputMultiPath(File(
        exists=True), desc='ROI volumes registered to diffusion space', mandatory=True)

    parcellation_scheme = traits.Enum(
            'Lausanne2018',
            ['NativeFreesurfer', 'Lausanne2018', 'Custom'],
            usedefault=True, mandatory=True,
            desc="Parcellation scheme")

    roi_graphMLs = InputMultiPath(File(exists=True),
                                  desc='GraphML description of ROI volumes (Lausanne2018)',
                                  mandatory=True)


class ComputeParcellationRoiVolumesOutputSpec(TraitedSpec):
    """This is a class for the definition of outputs of the `ComputeParcellationRoiVolumes` Nipype interface.

    Attributes
    ----------
    roi_volumes_stats (files): list
        TSV files with volumes of ROIs for each scale
    """
    roi_volumes_stats = OutputMultiPath(File(), desc="TSV files with computed parcellation ROI volumes")


class ComputeParcellationRoiVolumes(BaseInterface):
    """Computes the volumes of each ROI for each parcellation scale.

    Examples
    --------
    >>> compute_vol = ComputeParcellationRoiVolumes()
    >>> compute_vol.inputs.roi_volumes = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                   '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                   '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                   '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                   '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> compute_vol.inputs.roi_graphmls = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.graphml',
    >>>                             '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.graphml']
    >>> compute_vol.inputs.parcellation_scheme = ['Lausanne2018']
    >>> compute_vol.run()  # doctest: +SKIP

    """

    input_spec = ComputeParcellationRoiVolumesInputSpec
    output_spec = ComputeParcellationRoiVolumesOutputSpec

    def _run_interface(self, runtime):

        if "Custom" in self.inputs.parcellation_scheme:
            self._compute_and_save_volumetry(
                self.inputs.roi_volumes[0],
                self.inputs.roi_graphMLs[0],
                "custom"
            )
        else:
            resolutions = get_parcellation(self.inputs.parcellation_scheme)

            for parkey, _ in list(resolutions.items()):

                for roi in self.inputs.roi_volumes:
                    if parkey in roi:
                        roi_fname = roi
                        break

                for graphml in self.inputs.roi_graphMLs:
                    if parkey in graphml:
                        roi_info_graphml = graphml
                        break

                iflogger.info(
                    "-------------------------------------------------------")
                iflogger.info(
                    "Processing {} parcellation - {}".format(self.inputs.parcellation_scheme, parkey))
                iflogger.info(
                    "-------------------------------------------------------")
                self._compute_and_save_volumetry(roi_fname, roi_info_graphml, parkey)

        iflogger.info('  [Done]')

        return runtime

    def _compute_and_save_volumetry(self, roi_fname, roi_info_graphml, parkey):
        iflogger.info("  > Load {}...".format(roi_fname))
        roiImg = ni.load(roi_fname)
        roiData = roiImg.get_data()

        # Compute the volume of the voxel
        voxel_dimX, voxel_dimY, voxel_dimZ = roiImg.header.get_zooms()
        voxel_volume = voxel_dimX * voxel_dimY * voxel_dimZ
        iflogger.info("    ... Voxel volume = {} mm3".format(voxel_volume))

        # Initialize the TSV file used to store the parcellation volumetry resulty
        volumetry_file = op.abspath('{}_roi_stats.tsv'.format(parkey))
        f_volumetry = open(volumetry_file, 'w+')
        iflogger.info(
            "  > Create Volumetry TSV file as {}".format(volumetry_file)
        )

        # Format the TSV file according to BIDS Extension Proposal 11 (BEP011):
        # The structural preprocessing derivatives.
        hdr_lines = [
            '{:<4}, {:<55}, {:<10}, {:>10} \n'.format("index", "name", "type", "volume-mm3")
        ]

        f_volumetry.writelines(hdr_lines)
        del hdr_lines

        # add node information from parcellation
        iflogger.info("  > Load {}...".format(roi_info_graphml))
        gp = nx.read_graphml(roi_info_graphml)
        n_nodes = len(gp)

        iflogger.info("  > Processing parcels...")
        # variables used by the percent counter
        pc = -1
        cnt = -1
        # Loop over each parcel/ROI
        for _, d in gp.nodes(data=True):
            # Percent counter
            cnt += 1
            pcN = int(round(float(100 * cnt) / n_nodes))
            if pcN > pc and pcN % 10 == 0:
                pc = pcN
                iflogger.info('%4.0f%%' % pc)

            # Get the label number
            if self.inputs.parcellation_scheme in ["Custom", "Lausanne2018"]:
                parcel_label = d["dn_multiscaleID"]
            else:
                parcel_label = d["dn_correspondence_id"]

            # Get if the parcel is cortical or subcortical
            parcel_type = d["dn_region"]

            # Get the name of the parcel
            parcel_name = d["dn_name"]

            # Compute the parcel/ROI volume
            parcel_volumetry = np.sum(roiData == int(
                    parcel_label)) * voxel_volume

            f_volumetry.write(
                    '{:<4}, {:<55}, {:<10}, {:>10} \n'.format(parcel_label, parcel_name, parcel_type, parcel_volumetry))

        f_volumetry.close()

    def _list_outputs(self):
        outputs = self._outputs().get()
        if self.inputs.parcellation_scheme == "Custom":
            outputs['roi_volumes_stats'] = 'custom_roi_stats.tsv'
        else:
            outputs['roi_volumes_stats'] = self._gen_outfilenames('roi_stats', '.tsv')

        return outputs

    def _gen_outfilenames(self, basename, posfix):
        filepaths = []
        for scale in list(get_parcellation(self.inputs.parcellation_scheme).keys()):
            filepaths.append(op.abspath(f'{scale}_{basename}{posfix}'))
        return filepaths


def erode_mask(fsdir, mask_file):
    """Erodes the mask and saves it the Freesurfer subject directory.

    Parameters
    ----------
    fsdir : string
        Freesurfer subject directory

    mask_file : string
        Path to mask file
    """
    # Define erosion mask
    imerode = nd.binary_erosion
    se = np.zeros((3, 3, 3))
    se[1, :, 1] = 1
    se[:, 1, 1] = 1
    se[1, 1, :] = 1

    # Erode mask
    print('    > Load mask {}'.format(mask_file))
    img = ni.load(mask_file)
    mask = img.get_data()

    # Circumvent a casting issue for csf_mask which did not have element exactly equal to 1 (instead 0.999998....)
    mask[mask > 0] = 1
    mask = mask.astype(np.uint32)

    er_mask = np.zeros(mask.shape)
    idx = np.where((mask == 1))
    er_mask[idx] = 1
    print(er_mask.sum())
    er_mask = imerode(er_mask, se)
    print(er_mask.sum())
    er_mask = imerode(er_mask, se)
    print(er_mask.sum())
    img = ni.Nifti1Image(er_mask, img.get_affine(), img.get_header())
    out_fname = os.path.join(fsdir, 'mri',
                             '{}_eroded.nii.gz'.format(os.path.splitext(op.splitext(op.basename(mask_file))[0])[0]))
    print('    > Save eroded mask to: {}'.format(out_fname))
    ni.save(img, out_fname)
    del img


class ParcellateHippocampalSubfieldsInputSpec(BaseInterfaceInputSpec):
    subjects_dir = Directory(mandatory=True, desc='Freesurfer main directory')

    subject_id = traits.Str(mandatory=True, desc='Subject ID')


class ParcellateHippocampalSubfieldsOutputSpec(TraitedSpec):
    lh_hipposubfields = File(desc='Left hemisphere hippocampal subfields file')

    rh_hipposubfields = File(
        desc='Right hemisphere hippocampal subfields  file')


class ParcellateHippocampalSubfields(BaseInterface):
    """Parcellates the hippocampal subfields using Freesurfer [Iglesias2015Hippo]_.

    References
    ----------
    .. [Iglesias2015Hippo] Iglesias et al., Neuroimage, 115, July 2015, 117-137.
                           <http://www.nmr.mgh.harvard.edu/~iglesias/pdf/subfieldsNeuroimage2015preprint.pdf>

    Examples
    --------
    >>> parc_hippo = ParcellateHippocampalSubfields()
    >>> parc_hippo.inputs.subjects_dir = '/path/to/derivatives/freesurfer'
    >>> parc_hippo.inputs.subject_id = 'sub-01'
    >>> parc_hippo.run()  # doctest: +SKIP

    """

    input_spec = ParcellateHippocampalSubfieldsInputSpec
    output_spec = ParcellateHippocampalSubfieldsOutputSpec

    def _run_interface(self, runtime):
        iflogger.info("Parcellation of hippocampal subfields (FreeSurfer)")
        iflogger.info("=============================================")

        lh_hipposubfields_mgz = os.path.join(self.inputs.subjects_dir, self.inputs.subject_id, 'mri',
                                             'lh.hippoSfLabels-T1.v10.mgz')
        if os.access(lh_hipposubfields_mgz, os.F_OK):
            iflogger.info('Warning: file {} is existing and being removed'.format(
                lh_hipposubfields_mgz))
            os.remove(lh_hipposubfields_mgz)

        rh_hipposubfields_mgz = os.path.join(self.inputs.subjects_dir, self.inputs.subject_id, 'mri',
                                             'rh.hippoSfLabels-T1.v10.mgz')
        if os.access(rh_hipposubfields_mgz, os.F_OK):
            iflogger.info('Warning: file {} is existing and being removed'.format(
                rh_hipposubfields_mgz))
            os.remove(rh_hipposubfields_mgz)

        fs_string = 'export SUBJECTS_DIR=' + self.inputs.subjects_dir
        iflogger.info(
            '- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(self.inputs.subjects_dir))

        reconall_cmd = fs_string + '; recon-all -no-isrunning -s "%s" -hippocampal-subfields-T1 ' % (
            self.inputs.subject_id)
        # reconall_cmd = [fs_string , ";" , "recon-all" , "-no-isrunning" , "-s" , "%s"% (self.inputs.subject_id) , "-hippocampal-subfields-T1" ]

        iflogger.info('Processing cmd: %s' % reconall_cmd)

        process = subprocess.Popen(
            reconall_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        # subprocess.check_call(reconall_cmd)

        # cmd = ['recon-all', '-s', self.inputs.subject_id, '-hippocampal-subfields-T1']

        # subprocess.check_call(cmd)
        iflogger.info(proc_stdout)

        mov = op.join(self.inputs.subjects_dir, self.inputs.subject_id,
                      'mri', 'lh.hippoSfLabels-T1.v10.mgz')
        targ = op.join(self.inputs.subjects_dir,
                       self.inputs.subject_id, 'mri', 'orig/001.mgz')
        out = op.abspath('lh_subFields.nii.gz')
        cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (
            mov, targ, out)

        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        mov = op.join(self.inputs.subjects_dir, self.inputs.subject_id,
                      'mri', 'rh.hippoSfLabels-T1.v10.mgz')
        targ = op.join(self.inputs.subjects_dir,
                       self.inputs.subject_id, 'mri', 'orig/001.mgz')
        out = op.abspath('rh_subFields.nii.gz')
        cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (
            mov, targ, out)

        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        iflogger.info('Done')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['lh_hipposubfields'] = op.abspath('lh_subFields.nii.gz')
        outputs['rh_hipposubfields'] = op.abspath('rh_subFields.nii.gz')
        return outputs


class ParcellateBrainstemStructuresInputSpec(BaseInterfaceInputSpec):
    subjects_dir = Directory(mandatory=True, desc='Freesurfer main directory')

    subject_id = traits.String(mandatory=True, desc='Subject ID')


class ParcellateBrainstemStructuresOutputSpec(TraitedSpec):
    brainstem_structures = File(desc='Parcellated brainstem structures file')


class ParcellateBrainstemStructures(BaseInterface):
    """Parcellates the brainstem sub-structures using Freesurfer [Iglesias2015Brainstem]_.

    References
    ----------
    .. [Iglesias2015Brainstem] Iglesias et al., NeuroImage, 113, June 2015, 184-195.
                               <http://www.nmr.mgh.harvard.edu/~iglesias/pdf/Neuroimage_2015_brainstem.pdf>

    Examples
    --------
    >>> parc_bstem = ParcellateBrainstemStructures()
    >>> parc_bstem.inputs.subjects_dir = '/path/to/derivatives/freesurfer'
    >>> parc_bstem.inputs.subject_id = 'sub-01'
    >>> parc_bstem.run()  # doctest: +SKIP

    """

    input_spec = ParcellateBrainstemStructuresInputSpec
    output_spec = ParcellateBrainstemStructuresOutputSpec

    def _run_interface(self, runtime):
        iflogger.info("Parcellation of brainstem structures (FreeSurfer)")
        iflogger.info("=============================================")

        fs_string = 'export SUBJECTS_DIR=' + self.inputs.subjects_dir
        iflogger.info(
            '- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(self.inputs.subjects_dir))

        reconall_cmd = fs_string + \
            '; recon-all -no-isrunning -s "%s" -brainstem-structures ' % (
                self.inputs.subject_id)
        # reconall_cmd = [fs_string , ";" , "recon-all" , "-no-isrunning" , "-s" , "%s"% (self.inputs.subject_id) , "-hippocampal-subfields-T1" ]

        iflogger.info('Processing cmd: %s' % reconall_cmd)

        process = subprocess.Popen(
            reconall_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        mov = op.join(self.inputs.subjects_dir, self.inputs.subject_id,
                      'mri', 'brainstemSsLabels.v10.mgz')
        targ = op.join(self.inputs.subjects_dir,
                       self.inputs.subject_id, 'mri', 'orig/001.mgz')
        out = op.abspath('brainstem.nii.gz')
        cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (
            mov, targ, out)

        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        iflogger.info('Done')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['brainstem_structures'] = op.abspath('brainstem.nii.gz')
        return outputs


class CombineParcellationsInputSpec(BaseInterfaceInputSpec):
    input_rois = InputMultiPath(File(exists=True), desc="Input parcellation files")

    lh_hippocampal_subfields = File(' ', desc="Input hippocampal subfields file for left hemisphere")

    rh_hippocampal_subfields = File(' ', desc="Input hippocampal subfields file for right hemisphere")

    brainstem_structures = File(' ', desc="Brainstem segmentation file")

    thalamus_nuclei = File(' ', desc="Thalamic nuclei segmentation file")

    create_colorLUT = traits.Bool(True, desc="If `True`, create the color lookup table in Freesurfer format")

    create_graphml = traits.Bool(True, desc="If `True`, create the parcellation node description files in `graphml` format")

    subjects_dir = Directory(desc='Freesurfer subjects dir')

    subject_id = traits.Str(desc='Freesurfer subject id')

    verbose_level = traits.Enum(
        1, 2, desc='verbose level (1: partial (default) / 2: full)')


class CombineParcellationsOutputSpec(TraitedSpec):
    aparc_aseg = File(desc="Modified Freesurfer aparc+aseg file")

    output_rois = OutputMultiPath(File(exists=True), desc="Output parcellation with all structures combined")

    colorLUT_files = OutputMultiPath(File(exists=True), desc="Color lookup table files in Freesurfer format")

    graphML_files = OutputMultiPath(File(exists=True), desc="Parcellation node description files in `graphml` format")


class CombineParcellations(BaseInterface):
    """Creates the final parcellation.

    It combines the original cortico sub-cortical parcellation with
    the following extra segmented structures:
        * Segmentation of the 8 thalamic nuclei per hemisphere
        * Segmentation of 14 hippocampal subfields per hemisphere
        * Segmentation of 3 brainstem sub-structures

    It also generates by defaults the corresponding (1) description of the nodes in `graphml`
    format and (2) color lookup tables in FreeSurfer format that can be displayed in `freeview`.

    Examples
    --------
    >>> parc_combine = CombineParcellations()
    >>> parc_combine.inputs.input_rois = ['/path/to/sub-01_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                                  '/path/to/sub-01_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                                  '/path/to/sub-01_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                                  '/path/to/sub-01_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                                  '/path/to/sub-01_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> parc_combine.inputs.lh_hippocampal_subfields = '/path/to/lh_hippocampal_subfields.nii.gz'
    >>> parc_combine.inputs.rh_hippocampal_subfields = '/path/to/rh_hippocampal_subfields.nii.gz'
    >>> parc_combine.inputs.brainstem_structures = '/path/to/brainstem_structures.nii.gz'
    >>> parc_combine.inputs.thalamus_nuclei = '/path/to/thalamus_nuclei.nii.gz'
    >>> parc_combine.inputs.create_colorLUT = True
    >>> parc_combine.inputs.create_graphml = True
    >>> parc_combine.inputs.subjects_dir = '/path/to/output_dir/freesurfer')
    >>> parc_combine.inputs.subject_id = 'sub-01'
    >>> parc_combine.run()  # doctest: +SKIP

    """

    input_spec = CombineParcellationsInputSpec
    output_spec = CombineParcellationsOutputSpec

    def ismember(a, b):
        bind = {}
        for i, elt in enumerate(b):
            if elt not in bind:
                bind[elt] = i
        # None can be replaced by any other "not in b" value
        return [bind.get(itm, None) for itm in a]

    def _run_interface(self, runtime):

        iflogger.info("Start running CombineParcellations interface...")

        # Freesurfer subject dir
        fs_dir = op.join(self.inputs.subjects_dir, self.inputs.subject_id)
        print("Freesurfer subject directory: {}".format(fs_dir))

        # Freesurfer IDs for subcortical structures
        left_subc_ids = np.array([10, 11, 12, 13, 26, 18, 17])
        left_subc_ids_2018_colors_r = np.array([0, 122, 236, 12, 255, 103, 220])
        left_subc_ids_2018_colors_g = np.array([118, 186, 13, 48, 165, 255, 216])
        left_subc_ids_2018_colors_b = np.array([14, 220, 176, 255, 0, 255, 20])
        left_subcort_names = ["Left-Thalamus_Proper", "Left-Caudate", "Left-Putamen", "Left-Pallidum",
                              "Left-Accumbens_area", "Left-Amygdala", "Left-Hippocampus"]

        right_subc_ids = np.array([49, 50, 51, 52, 58, 54, 53])
        right_subc_ids_2018_colors_r = np.array([0, 122, 236, 12, 255, 103, 220])
        right_subc_ids_2018_colors_g = np.array([118, 186, 13, 48, 165, 255, 216])
        right_subc_ids_2018_colors_b = np.array([14, 220, 176, 255, 0, 255, 20])
        right_subcort_names = ["Right-Thalamus_Proper", "Right-Caudate", "Right-Putamen", "Right-Pallidum",
                               "Right-Accumbens_area", "Right-Amygdala", "Right-Hippocampus"]

        # Amygdala and hippocampus swapped between Lausanne2008 and Lausanne2018
        left_subc_ids_2008 = np.array([10, 11, 12, 13, 26, 17, 18])
        # left_subc_ids_2008_colors_r = np.array([0, 122, 236, 12, 255, 220, 103])
        # left_subc_ids_2008_colors_g = np.array([118, 186, 13, 48, 165, 216, 255])
        # left_subc_ids_2008_colors_b = np.array([14, 220, 176, 255, 0, 20, 255])
        left_subcort_2008_names = ["Left-Thalamus_Proper", "Left-Caudate", "Left-Putamen", "Left-Pallidum",
                                   "Left-Accumbens_area", "Left-Hippocampus", "Left-Amygdala"]

        right_subc_ids_2008 = np.array([49, 50, 51, 52, 58, 53, 54])
        # right_subc_ids_2008_colors_r = np.array([0, 122, 236, 12, 255, 220, 103])
        # right_subc_ids_2008_colors_g = np.array([118, 186, 13, 48, 165, 216, 255])
        # right_subc_ids_2008_colors_b = np.array([14, 220, 176, 255, 0, 20, 255])
        right_subcort_2008_names = ["Right-Thalamus_Proper", "Right-Caudate", "Right-Putamen", "Right-Pallidum",
                                    "Right-Accumbens_area", "Right-Hippocampus", "Right-Amygdala"]

        # Thalamic Nuclei
        left_thalNuclei = np.array([1, 2, 3, 4, 5, 6, 7])
        left_thalNuclei_colors_r = np.array([255, 0, 255, 255, 0, 255, 0])
        left_thalNuclei_colors_g = np.array([0, 255, 255, 123, 255, 0, 0])
        left_thalNuclei_colors_b = np.array([0, 0, 0, 0, 255, 255, 255])
        left_thalNuclei_names = ["Left-Pulvinar", "Left-Anterior", "Left-Medio_Dorsal", "Left-Ventral_Latero_Dorsal",
                                 "Left-Central_Lateral-Lateral_Posterior-Medial_Pulvinar",
                                 "Left-Ventral_Anterior", "Left-Ventral_Latero_Ventral"]

        right_thalNuclei = np.array([8, 9, 10, 11, 12, 13, 14])
        right_thalNuclei_colors_r = np.array([255, 0, 255, 255, 0, 255, 0])
        right_thalNuclei_colors_g = np.array([0, 255, 255, 123, 255, 0, 0])
        right_thalNuclei_colors_b = np.array([0, 0, 0, 0, 255, 255, 255])
        right_thalNuclei_names = ["Right-Pulvinar", "Right-Anterior", "Right-Medio_Dorsal",
                                  "Right-Ventral_Latero_Dorsal",
                                  "Right-Central_Lateral-Lateral_Posterior-Medial_Pulvinar",
                                  "Right-Ventral_Anterior", "Right-Ventral_Latero_Ventral"]

        # Hippocampus subfields
        hippo_subf = np.array([203, 204, 205, 206, 208, 209, 210, 211, 212, 214, 215, 226])
        hippo_subf_colors_r = np.array([255, 64, 0, 255, 0, 196, 32, 128, 204, 128, 128, 170])
        hippo_subf_colors_g = np.array([255, 0, 0, 0, 128, 160, 200, 255, 153, 0, 32, 170])
        hippo_subf_colors_b = np.array([0, 64, 255, 0, 0, 128, 255, 128, 204, 0, 255, 255])
        left_hippo_subf_names = ["Left-Hippocampus_Parasubiculum", "Left-Hippocampus_Presubiculum",
                                 "Left-Hippocampus_Subiculum", "Left-Hippocampus_CA1", "Left-Hippocampus_CA3",
                                 "Left-Hippocampus_CA4",
                                 "Left-Hippocampus_GCDG", "Left-Hippocampus_HATA", "Left-Hippocampus_Fimbria",
                                 "Left-Hippocampus_Molecular_layer_HP", "Left-Hippocampus_Hippocampal_fissure",
                                 "Left-Hippocampus_Tail"]
        right_hippo_subf_names = ["Right-Hippocampus_Parasubiculum", "Right-Hippocampus_Presubiculum",
                                  "Right-Hippocampus_Subiculum", "Right-Hippocampus_CA1", "Right-Hippocampus_CA3",
                                  "Right-Hippocampus_CA4",
                                  "Right-Hippocampus_GCDG", "Right-Hippocampus_HATA", "Right-Hippocampus_Fimbria",
                                  "Right-Hippocampus_Molecular_layer_HP", "Right-Hippocampus_Hippocampal_fissure",
                                  "Right-Hippocampus_Tail"]

        # Left Ventral Diencephalon
        left_ventral = 28
        left_ventral_colors_r = 165
        left_ventral_colors_g = 42
        left_ventral_colors_b = 42
        left_ventral_names = ["Left-VentralDC"]

        # Right Ventral Diencephalon
        right_ventral = 60
        right_ventral_colors_r = 165
        right_ventral_colors_g = 42
        right_ventral_colors_b = 42
        right_ventral_names = ["Right-VentralDC"]

        # Third Ventricle
        ventricle3 = 14

        # Hypothalamus
        hypothal_colors_r = 204
        hypothal_colors_g = 182
        hypothal_colors_b = 142
        left_hypothal_names = ["Left-Hypothalamus"]
        right_hypothal_names = ["Right-Hypothalamus"]

        # BrainStem Parcellation
        brainstem = np.array([173, 174, 175, 178])
        brainstem_colors_r = np.array([242, 206, 119, 142])
        brainstem_colors_g = np.array([104, 195, 159, 182])
        brainstem_colors_b = np.array([76, 58, 176, 0])
        brainstem_names = ["Brain_Stem-Midbrain",
                           "Brain_Stem-Pons", "Brain_Stem-Medulla", "Brain_Stem-SCP"]

        lh_subfield_defined = False
        # Reading Subfields Images
        try:
            img_sublh = ni.load(self.inputs.lh_hippocampal_subfields)
            img_data_sublh = img_sublh.get_data()
            lh_subfield_defined = True
        except TypeError:
            print('Subfields image (Left hemisphere) not provided')

        rh_subfield_defined = False
        try:
            img_subrh = ni.load(self.inputs.rh_hippocampal_subfields)
            img_data_subrh = img_subrh.get_data()
            rh_subfield_defined = True
        except TypeError:
            print('Subfields image (Right hemisphere) not provided')

        thalamus_nuclei_defined = False
        # Reading  Nuclei
        try:
            Vthal = ni.load(self.inputs.thalamus_nuclei)
            img_data_thal = Vthal.get_data()

            thalamus_nuclei_defined = True
        except TypeError:
            print('Thalamic nuclei image not provided')

        brainstem_defined = False
        # Reading Stem Image
        try:
            img_stem = ni.load(self.inputs.brainstem_structures)
            img_data_stem = img_stem.get_data()
            indstem = np.where(img_data_stem > 0)
            brainstem_defined = True
        except TypeError:
            print('Brain stem image not provided')

        if not (thalamus_nuclei_defined and brainstem_defined and (lh_subfield_defined and rh_subfield_defined)):
            left_subc_labels = left_subc_ids_2008
            left_subcort_names = left_subcort_2008_names
            right_subc_labels = right_subc_ids_2008
            right_subcort_names = right_subcort_2008_names

        elif thalamus_nuclei_defined:
            left_subc_labels = left_subc_ids[1:]
            left_subcort_names = left_subcort_names[1:]
            right_subc_labels = right_subc_ids[1:]
            right_subcort_names = right_subcort_names[1:]

        else:
            left_subc_labels = left_subc_ids
            right_subc_labels = right_subc_ids

        # Get the first parcellation scale for ventricule image
        roi1_fname = None
        for roi_fname in self.inputs.input_rois:
            if 'scale1' in roi_fname:
                roi1_fname = roi_fname
                break

        # Dilate third ventricle and intersect with right and left ventral DC
        # to get voxels of left and right hypothalamus
        iflogger.info("  > Create ventricule image")
        img_v = ni.load(roi1_fname)
        img_data = img_v.get_data()
        tmp = np.zeros(img_data.shape)
        ind_v = np.where(img_data == ventricle3)
        tmp[ind_v] = 1

        third_vent_fn = op.abspath('ventricle3.nii.gz')
        hdr = img_v.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.int16)
        iflogger.info("    ... Image saved to {}".format(third_vent_fn))
        img = ni.Nifti1Image(tmp, img_v.get_affine(), hdr2)
        ni.save(img, third_vent_fn)
        del img

        iflogger.info("  > Dilate (modal) the ventricule image")
        third_vent_dil = op.abspath('ventricle3_dil.nii.gz')
        cmd = f'fslmaths -dt char {third_vent_fn} -mas {third_vent_fn} -kernel sphere 5 -dilD {third_vent_dil}'
        iflogger.info("    ... Command: {}".format(cmd))
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()

        if self.inputs.verbose_level == 2:
            print(proc_stdout)

        tmp = ni.load(third_vent_dil)
        indrhypothal = np.where((tmp == 1) & (img_data == right_ventral))
        indlhypothal = np.where((tmp == 1) & (img_data == left_ventral))
        del tmp

        f_color_lut = None
        f_graphml = None

        print("create color look up table : ", self.inputs.create_colorLUT)

        for _, roi in enumerate(self.inputs.input_rois):
            # colorLUT creation if enabled
            if self.inputs.create_colorLUT:
                outprefix_name = Path(roi).name.split(".")[0]
                color_lut_file = op.abspath(
                    '{}_FreeSurferColorLUT.txt'.format(outprefix_name))
                print("Create colorLUT file as %s" % color_lut_file)
                f_color_lut = open(color_lut_file, 'w+')
                time_now = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                hdr_lines = ['#$Id: {}_FreeSurferColorLUT.txt {} \n \n'.format(outprefix_name, time_now),
                             '{:<4} {:<55} {:>3} {:>3} {:>3} {} \n \n'.format("#No.", "Label Name:", "R", "G", "B",
                                                                              "A")]
                f_color_lut.writelines(hdr_lines)
                del hdr_lines

            # Create GraphML if enabled
            if self.inputs.create_graphml:
                outprefix_name = Path(roi).name.split(".")[0]
                graphml_file = op.abspath('{}.graphml'.format(outprefix_name))
                print("Create graphml_file as %s" % graphml_file)
                f_graphml = open(graphml_file, 'w+')

                hdr_lines = ['{} \n'.format('<?xml version="1.0" encoding="utf-8"?>'),
                             '{} \n'.format(
                                 '<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                                 'xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_region" attr.type="string" for="node" id="d0" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_fsname" attr.type="string" for="node" id="d1" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_hemisphere" attr.type="string" for="node" id="d2" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_multiscaleID" attr.type="int" for="node" id="d3" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_name" attr.type="string" for="node" id="d4" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_fsID" attr.type="int" for="node" id="d5" />'),
                             '{} \n'.format('  <graph edgedefault="undirected" id="">'), ]
                f_graphml.writelines(hdr_lines)
                del hdr_lines

            # Reading Cortical Parcellation
            img_v = ni.load(roi)
            img_data = img_v.get_data()

            # Replacing the brain stem (Stem is replaced by its own parcellation.
            # Mismatch between both global volumes, mainly due to partial volume
            # effect in the global stem parcellation)
            indrep = np.where(img_data == 16)
            img_data[indrep] = 0

        for _, roi in sorted(enumerate(self.inputs.input_rois)):
            # colorLUT creation if enabled
            if self.inputs.create_colorLUT:
                outprefix_name = Path(roi).name.split(".")[0]
                color_lut_file = op.abspath(
                    '{}_FreeSurferColorLUT.txt'.format(outprefix_name))
                iflogger.info("  > Create colorLUT file as %s" % color_lut_file)
                f_color_lut = open(color_lut_file, 'w+')
                time_now = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                hdr_lines = ['#$Id: {}_FreeSurferColorLUT.txt {} \n \n'.format(outprefix_name, time_now),
                             '{:<4} {:<55} {:>3} {:>3} {:>3} {} \n \n'.format("#No.", "Label Name:", "R", "G", "B",
                                                                              "A")]
                f_color_lut.writelines(hdr_lines)
                del hdr_lines

            # Create GraphML if enabled
            if self.inputs.create_graphml:
                outprefix_name = Path(roi).name.split(".")[0]
                graphml_file = op.abspath('{}.graphml'.format(outprefix_name))
                iflogger.info(
                    "  > Create graphml_file as {}".format(graphml_file))
                f_graphml = open(graphml_file, 'w+')

                hdr_lines = ['{} \n'.format('<?xml version="1.0" encoding="utf-8"?>'),
                             '{} \n'.format(
                                 '<graphml xmlns="http://graphml.graphdrawing.org/xmlns" '
                                 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                                 'xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns '
                                 'http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_region" attr.type="string" for="node" id="d0" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_fsname" attr.type="string" for="node" id="d1" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_hemisphere" attr.type="string" for="node" id="d2" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_multiscaleID" attr.type="int" for="node" id="d3" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_name" attr.type="string" for="node" id="d4" />'),
                             '{} \n'.format(
                                 '  <key attr.name="dn_fsID" attr.type="int" for="node" id="d5" />'),
                             '{} \n'.format('  <graph edgedefault="undirected" id="">'), ]
                f_graphml.writelines(hdr_lines)
                del hdr_lines

            # Reading Cortical Parcellation
            img_v = ni.load(roi)
            img_data = img_v.get_data()

            # Replacing the brain stem (Stem is replaced by its own parcellation.
            # Mismatch between both global volumes, mainly due to partial volume
            # effect in the global stem parcellation)
            indrep = np.where(img_data == 16)
            img_data[indrep] = 0

            # Processing Right Hemisphere

            # Relabelling Right hemisphere
            img_data_out = np.zeros(img_data.shape, dtype=np.int16)
            ind = np.where((img_data >= 2000) & (img_data < 3000))
            img_data_out[ind] = (img_data[ind] - 2000)
            nlabel = img_data_out.max()

            # ColorLUT (cortical)
            if self.inputs.create_colorLUT or self.inputs.create_graphml:
                f_color_lut.write("# Right Hemisphere. Cortical Structures \n")
                outprefix_name = Path(roi).name.split(".")[0]
                for elem in outprefix_name.split("_"):
                    if "scale" in elem:
                        scale = elem
                rh_annot_file = 'rh.lausanne2008.%s.annot' % scale
                iflogger.info("  > Load {}".format(rh_annot_file))
                rh_annot = ni.freesurfer.io.read_annot(
                    op.join(self.inputs.subjects_dir, self.inputs.subject_id, 'label', rh_annot_file))
                rgb_table = rh_annot[1][1:, 0:3]
                roi_names = rh_annot[2][1:]
                # roi_labels = rh_annot[0][1:]

                for label, name in enumerate(roi_names):
                    name = 'ctx-rh-{}'.format(name.decode())
                    if self.inputs.create_colorLUT:
                        r = rgb_table[label, 0]
                        g = rgb_table[label, 1]
                        b = rgb_table[label, 2]

                        if label == 0:
                            r = 0
                            g = 0
                            b = 0

                        f_color_lut.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(
                            label + 1, name, r, g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (label + 1)),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "cortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % name),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "right"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (label + 1)),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % name),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(label + 2000 + 1))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            # Relabelling Thalamic Nuclei
            if thalamus_nuclei_defined:
                if self.inputs.create_colorLUT:
                    f_color_lut.write(
                        "# Right Hemisphere. Subcortical Structures (Thalamic Nuclei) \n")

                new_labels = np.arange(
                    nlabel + 1, nlabel + 1 + right_thalNuclei.shape[0])

                i = 0
                for lab in right_thalNuclei:
                    if self.inputs.verbose_level == 2:
                        iflogger.info(
                            "  > Update right thalamic nucleus label ({} -> {})".format(lab, new_labels[i]))

                    if self.inputs.create_colorLUT:
                        r = right_thalNuclei_colors_r[i]
                        g = right_thalNuclei_colors_g[i]
                        b = right_thalNuclei_colors_b[i]
                        f_color_lut.write(
                            '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), right_thalNuclei_names[i],
                                                                         r, g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "subcortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % "thalamus"),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "right"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % (right_thalNuclei_names[i])),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(49))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                    ind = np.where(img_data_thal == lab)
                    img_data_out[ind] = new_labels[i]
                    i += 1
                nlabel = img_data_out.max()

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            # Relabelling Subcortical Structures
            if self.inputs.create_colorLUT:
                f_color_lut.write(
                    "# Right Hemisphere. Subcortical Structures \n")

            new_labels = np.arange(nlabel + 1, nlabel + 1 + left_subc_labels.shape[0])

            i = 0
            for lab in right_subc_labels:
                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update right subcortical label ({} -> {})".format(lab, new_labels[i]))

                if self.inputs.create_colorLUT:
                    r = right_subc_ids_2018_colors_r[i]
                    g = right_subc_ids_2018_colors_g[i]
                    b = right_subc_ids_2018_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), right_subcort_names[i], r, g,
                                                                     b))

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                  '{} \n'.format(
                                      '      <data key="d0">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d1">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d2">%s</data>' % "right"),
                                  '{} \n'.format(
                                      '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                  '{} \n'.format(
                                      '      <data key="d4">%s</data>' % (right_subcort_names[i])),
                                  '{} \n'.format(
                                      '      <data key="d5">%i</data>' % (int(lab))),
                                  '{} \n'.format('    </node>')]
                    f_graphml.writelines(node_lines)

                ind = np.where(img_data == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
            nlabel = img_data_out.max()

            if self.inputs.create_colorLUT:
                f_color_lut.write("\n")

            # Relabelling Subfields
            if rh_subfield_defined:
                if self.inputs.create_colorLUT:
                    f_color_lut.write(
                        "# Right Hemisphere. Subcortical Structures (Hippocampal Subfields) \n")

                new_labels = np.arange(
                    nlabel + 1, nlabel + 1 + hippo_subf.shape[0])
                i = 0
                for lab in hippo_subf:
                    if self.inputs.verbose_level == 2:
                        iflogger.info(
                            "  > Update right hippo subfield label ({} -> {})".format(lab, new_labels[i]))

                    if self.inputs.create_colorLUT:
                        # if len(ind) > 0:
                        r = hippo_subf_colors_r[i]
                        g = hippo_subf_colors_g[i]
                        b = hippo_subf_colors_b[i]
                        f_color_lut.write(
                            '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), right_hippo_subf_names[i],
                                                                         r, g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "subcortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % "hippocampus"),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "right"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % (right_hippo_subf_names[i])),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(lab))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                    ind = np.where(img_data_subrh == lab)
                    img_data_out[ind] = new_labels[i]
                    i += 1
                nlabel = img_data_out.max()

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Right VentralDC
                new_labels = np.arange(nlabel + 1, nlabel + 2)
                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update right ventral DC label ({} -> {})".format(right_ventral, new_labels[0]))
                ind = np.where(img_data == right_ventral)
                img_data_out[ind] = new_labels[0]
                nlabel = img_data_out.max()

                # ColorLUT (right ventral DC)
                if self.inputs.create_colorLUT:
                    f_color_lut.write(
                        "# Right Hemisphere. Ventral Diencephalon \n")
                    r = right_ventral_colors_r
                    g = right_ventral_colors_g
                    b = right_ventral_colors_b
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), right_ventral_names[0], r, g,
                                                                     b))
                    f_color_lut.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d0">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d1">%s</data>' % "ventral-diencephalon"),
                                  '{} \n'.format(
                                      '      <data key="d2">%s</data>' % "right"),
                                  '{} \n'.format(
                                      '      <data key="d3">%i</data>' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d4">%s</data>' % (right_ventral_names[0])),
                                  '{} \n'.format(
                                      '      <data key="d5">%i</data>' % (int(right_ventral))),
                                  '{} \n'.format('    </node>')]
                    f_graphml.writelines(node_lines)

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Right Hypothalamus
                new_labels = np.arange(nlabel + 1, nlabel + 2)
                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update right hypothalamus label ({} -> {})".format(right_ventral, new_labels[0]))
                img_data_out[indrhypothal] = new_labels[0]
                nlabel = img_data_out.max()

                # ColorLUT (right hypothalamus)
                if self.inputs.create_colorLUT:
                    f_color_lut.write("# Right Hemisphere. Hypothalamus \n")
                    r = hypothal_colors_r
                    g = hypothal_colors_g
                    b = hypothal_colors_b
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), right_hypothal_names[0], r, g,
                                                                     b))
                    f_color_lut.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d0">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d1">%s</data>' % "hypothalamus"),
                                  '{} \n'.format(
                                      '      <data key="d2">%s</data>' % "right"),
                                  '{} \n'.format(
                                      '      <data key="d3">%i</data>' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d4">%s</data>' % (right_hypothal_names[0])),
                                  '{} \n'.format(
                                      '      <data key="d5">%i</data>' % (-1)),
                                  '{} \n'.format('    </node>')]
                    f_graphml.writelines(node_lines)

            # Processing Left Hemisphere
            # Relabelling Left hemisphere
            ind = np.where((img_data > 1000) & (img_data < 2000))
            img_data_out[ind] = (img_data[ind] - 1000 + nlabel)
            old_nlabel = nlabel
            nlabel = img_data_out.max()

            # ColorLUT (cortical)
            if self.inputs.create_colorLUT or self.inputs.create_graphml:
                f_color_lut.write("# Left Hemisphere. Cortical Structures \n")
                outprefix_name = Path(roi).name.split(".")[0]
                for elem in outprefix_name.split("_"):
                    if "scale" in elem:
                        scale = elem
                lh_annot_file = 'lh.lausanne2008.%s.annot' % scale
                iflogger.info("  > Load {}".format(lh_annot_file))
                lh_annot = ni.freesurfer.io.read_annot(
                    op.join(self.inputs.subjects_dir, self.inputs.subject_id, 'label', lh_annot_file))
                rgb_table = lh_annot[1][1:, 0:3]
                roi_names = lh_annot[2][1:]

                for label, name in enumerate(roi_names):
                    name = 'ctx-lh-{}'.format(name.decode())

                    if self.inputs.create_colorLUT:
                        r = rgb_table[label, 0]
                        g = rgb_table[label, 1]
                        b = rgb_table[label, 2]

                        if label == 0:
                            r = 0
                            g = 0
                            b = 0

                        f_color_lut.write(
                            '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(label + old_nlabel + 1), name, r, g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(label + old_nlabel + 1))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "cortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % name),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "left"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(label + old_nlabel + 1))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % name),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(label + 1000 - old_nlabel))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            # Relabelling Thalamic Nuclei
            if thalamus_nuclei_defined:
                if self.inputs.create_colorLUT:
                    f_color_lut.write(
                        "# Left Hemisphere. Subcortical Structures (Thalamic Nuclei) \n")

                new_labels = np.arange(
                    nlabel + 1, nlabel + 1 + left_thalNuclei.shape[0])
                i = 0
                for lab in left_thalNuclei:
                    if self.inputs.verbose_level == 2:
                        iflogger.info(
                            "  > Update left thalamic nucleus label ({} -> {})".format(lab, new_labels[i]))

                    if self.inputs.create_colorLUT:
                        r = left_thalNuclei_colors_r[i]
                        g = left_thalNuclei_colors_g[i]
                        b = left_thalNuclei_colors_b[i]
                        f_color_lut.write(
                            '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), left_thalNuclei_names[i], r,
                                                                         g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "subcortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % "thalamus"),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "left"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % (left_thalNuclei_names[i])),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(10))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                    ind = np.where(img_data_thal == lab)
                    img_data_out[ind] = new_labels[i]
                    i += 1
                nlabel = img_data_out.max()

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            # Relabelling Subcortical Structures
            if self.inputs.create_colorLUT:
                f_color_lut.write(
                    "# Left Hemisphere. Subcortical Structures \n")

            new_labels = np.arange(nlabel + 1, nlabel + 1 + left_subc_labels.shape[0])

            i = 0
            for lab in left_subc_labels:
                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update left subcortical label ({} -> {})".format(lab, new_labels[i]))

                if self.inputs.create_colorLUT:
                    r = left_subc_ids_2018_colors_r[i]
                    g = left_subc_ids_2018_colors_g[i]
                    b = left_subc_ids_2018_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), left_subcort_names[i], r, g, b))

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                  '{} \n'.format(
                                      '      <data key="d0">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d1">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d2">%s</data>' % "left"),
                                  '{} \n'.format(
                                      '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                  '{} \n'.format(
                                      '      <data key="d4">%s</data>' % (left_subcort_names[i])),
                                  '{} \n'.format(
                                      '      <data key="d5">%i</data>' % (int(lab))),
                                  '{} \n'.format('    </node>')]
                    f_graphml.writelines(node_lines)

                ind = np.where(img_data == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
            nlabel = img_data_out.max()

            if self.inputs.create_colorLUT:
                f_color_lut.write("\n")

            # Relabelling Subfields
            if lh_subfield_defined:
                if self.inputs.create_colorLUT:
                    f_color_lut.write(
                        "# Left Hemisphere. Subcortical Structures (Hippocampal Subfields) \n")

                new_labels = np.arange(
                    nlabel + 1, nlabel + 1 + hippo_subf.shape[0])
                i = 0
                for lab in hippo_subf:
                    if self.inputs.verbose_level == 2:
                        iflogger.info(
                            "  > Update left hippo subfield label ({} -> {})".format(lab, new_labels[i]))

                    if self.inputs.create_colorLUT:
                        r = hippo_subf_colors_r[i]
                        g = hippo_subf_colors_g[i]
                        b = hippo_subf_colors_b[i]
                        f_color_lut.write(
                            '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), left_hippo_subf_names[i], r,
                                                                         g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "subcortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % "hippocampus"),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "left"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % (left_hippo_subf_names[i])),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(lab))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                    ind = np.where(img_data_sublh == lab)
                    img_data_out[ind] = new_labels[i]
                    i += 1
                nlabel = img_data_out.max()
                # newIds_LH_subFields = new_labels

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Left VentralDC
                new_labels = np.arange(nlabel + 1, nlabel + 2)
                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update left ventral DC label ({} -> {})".format(left_ventral, new_labels[0]))
                ind = np.where(img_data == left_ventral)
                img_data_out[ind] = new_labels[0]
                nlabel = img_data_out.max()
                # newIds_LH_ventralDC = new_labels

                # ColorLUT (left ventral DC)
                if self.inputs.create_colorLUT:
                    f_color_lut.write(
                        "# Left Hemisphere. Ventral Diencephalon \n")
                    r = left_ventral_colors_r
                    g = left_ventral_colors_g
                    b = left_ventral_colors_b
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), left_ventral_names[0], r, g, b))
                    f_color_lut.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d0">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d1">%s</data>' % "ventral-diencephalon"),
                                  '{} \n'.format(
                                      '      <data key="d2">%s</data>' % "left"),
                                  '{} \n'.format(
                                      '      <data key="d3">%i</data>' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d4">%s</data>' % (left_ventral_names[0])),
                                  '{} \n'.format(
                                      '      <data key="d5">%i</data>' % (int(left_ventral))),
                                  '{} \n'.format('    </node>')]
                    f_graphml.writelines(node_lines)

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Left Hypothalamus
                new_labels = np.arange(nlabel + 1, nlabel + 2)
                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update left hypothalamus label ({} -> {})".format(-1, new_labels[0]))
                img_data_out[indlhypothal] = new_labels[0]
                nlabel = img_data_out.max()

                # ColorLUT (right hypothalamus)
                if self.inputs.create_colorLUT:
                    f_color_lut.write("# Left Hemisphere. Hypothalamus \n")
                    r = hypothal_colors_r
                    g = hypothal_colors_g
                    b = hypothal_colors_b
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), left_hypothal_names[0], r, g,
                                                                     b))
                    f_color_lut.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d0">%s</data>' % "subcortical"),
                                  '{} \n'.format(
                                      '      <data key="d1">%s</data>' % "hypothalamus"),
                                  '{} \n'.format(
                                      '      <data key="d2">%s</data>' % "left"),
                                  '{} \n'.format(
                                      '      <data key="d3">%i</data>' % (int(new_labels[0]))),
                                  '{} \n'.format(
                                      '      <data key="d4">%s</data>' % (left_hypothal_names[0])),
                                  '{} \n'.format(
                                      '      <data key="d5">%i</data>' % (-1)),
                                  '{} \n'.format('    </node>')]
                    f_graphml.writelines(node_lines)

            # Relabelling Brain Stem
            if brainstem_defined:
                if self.inputs.create_colorLUT:
                    f_color_lut.write("# Brain Stem Structures \n")

                new_labels = np.arange(
                    nlabel + 1, nlabel + 1 + brainstem.shape[0])
                i = 0
                for lab in brainstem:
                    if self.inputs.verbose_level == 2:
                        iflogger.info(
                            "  > Update brainstem parcellation label ({} -> {})".format(lab, new_labels[i]))

                    if self.inputs.create_colorLUT:
                        r = brainstem_colors_r[i]
                        g = brainstem_colors_g[i]
                        b = brainstem_colors_b[i]
                        f_color_lut.write(
                            '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), brainstem_names[i], r, g,
                                                                         b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "subcortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % "brainstem"),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "central"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(new_labels[i]))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % (brainstem_names[i])),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(lab))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                    ind = np.where(img_data_stem == lab)
                    img_data_out[ind] = new_labels[i]
                    i += 1
                # nlabel = img_data_out.max()

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")
            else:
                if self.inputs.create_colorLUT:
                    f_color_lut.write("# Brain Stem \n")

                new_labels = np.arange(nlabel + 1, nlabel + 2)
                img_data_out[indrep] = new_labels[0]

                if self.inputs.verbose_level == 2:
                    iflogger.info(
                        "  > Update brainstem parcellation label ({} -> {})".format(lab, new_labels[0]))

                if self.inputs.create_colorLUT:
                    r = 119
                    g = 159
                    b = 176
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), 'brainstem', r, g, b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">' % (int(new_labels[0]))),
                                      '{} \n'.format(
                                          '      <data key="d0">%s</data>' % "subcortical"),
                                      '{} \n'.format(
                                          '      <data key="d1">%s</data>' % "brainstem"),
                                      '{} \n'.format(
                                          '      <data key="d2">%s</data>' % "central"),
                                      '{} \n'.format(
                                          '      <data key="d3">%i</data>' % (int(new_labels[0]))),
                                      '{} \n'.format(
                                          '      <data key="d4">%s</data>' % "brainstem"),
                                      '{} \n'.format(
                                          '      <data key="d5">%i</data>' % (int(lab))),
                                      '{} \n'.format('    </node>')]
                        f_graphml.writelines(node_lines)

                # nlabel = img_data_out.max()

                if self.inputs.create_colorLUT:
                    f_color_lut.write("\n")

            # Fix negative values
            img_data_out[img_data_out < 0] = 0

            # Saving the new parcellation
            outprefix_name = Path(roi).name.split(".")[0]
            output_roi = op.abspath('{}_final.nii.gz'.format(outprefix_name))
            hdr = img_v.get_header()
            hdr2 = hdr.copy()
            hdr2.set_data_dtype(np.int16)
            iflogger.info("  > Save output image to {}".format(output_roi))
            img = ni.Nifti1Image(img_data_out, img_v.get_affine(), hdr2)
            ni.save(img, output_roi)
            del img

            if self.inputs.create_colorLUT:
                f_color_lut.close()

            if self.inputs.create_graphml:
                bottom_lines = ['{} \n'.format('  </graph>'),
                                '{} \n'.format('</graphml>'), ]
                f_graphml.writelines(bottom_lines)
                f_graphml.close()

        orig = op.join(fs_dir, 'mri', 'rawavg.mgz')
        aparcaseg_fs = op.join(fs_dir, 'mri', 'aparc+aseg.mgz')
        tmp_aparcaseg_fs = op.join(fs_dir, 'tmp', 'aparc+aseg.mgz')
        aparcaseg_native = op.join(fs_dir, 'tmp', 'aparc+aseg.native.nii.gz')

        iflogger.info("    ... Copy aparc+aseg to {}".format(tmp_aparcaseg_fs))
        shutil.copyfile(aparcaseg_fs, tmp_aparcaseg_fs)

        # Redirect ouput if low verbose
        fnull = open(os.devnull, 'w')

        iflogger.info("    ... Transform to native space")
        cmd = 'mri_vol2vol --mov "{}" --targ "{}" --regheader --o "{}" --no-save-reg --interp nearest'.format(
            aparcaseg_fs, orig, aparcaseg_native)
        iflogger.info("        Command: {}".format(cmd))
        if self.inputs.verbose_level == 2:
            status = subprocess.call(cmd, shell=True)
        else:
            status = subprocess.call(
                cmd, shell=True, stdout=fnull, stderr=subprocess.STDOUT)

        if self.inputs.verbose_level == 2:
            print(status)

        img_aparcaseg = ni.load(aparcaseg_native)
        img_data_aparcaseg = img_aparcaseg.get_data()

        # Refine aparc+aseg.mgz with new subcortical and/or structures (if any)
        if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
            iflogger.info(
                "  > Correct and save Freesurfer-generated aparc+aseg.mgz in native space...")

            img_data_aparcaseg_new = img_data_aparcaseg.astype(np.int32)

            # Thalamus (aparc+aseg labels: 10 and 49)
            if thalamus_nuclei_defined:

                ind = np.where(img_data_aparcaseg == 10)
                mask_aparc_lh = np.zeros(img_data_aparcaseg.shape)
                mask_aparc_lh[ind] = 1

                ind = np.where(img_data_aparcaseg == 49)
                mask_aparc_rh = np.zeros(img_data_aparcaseg.shape)
                mask_aparc_rh[ind] = 1

                mask_thal_lh = np.zeros(img_data_aparcaseg.shape)
                for lab in left_thalNuclei:
                    ind = np.where(img_data_thal == lab)
                    mask_thal_lh[ind] = 1

                # Identify voxels not included by thalamic Nuclei - should set to 2 (Gm) or 0
                tmp = mask_aparc_lh - mask_thal_lh
                ind = np.where(tmp > 0)
                img_data_aparcaseg_new[ind] = 2

                # Identify voxels not included by freesurfer thalamic mask
                tmp = mask_aparc_lh - mask_thal_lh
                ind = np.where(tmp < 0)
                img_data_aparcaseg_new[ind] = 10

                out_tmp = op.join(fs_dir, 'tmp', 'aparc-thal.lh.native.nii.gz')
                iflogger.info("    ... Save tmp image to {}".format(out_tmp))
                img_tmp = ni.Nifti1Image(
                    tmp, img_aparcaseg.get_affine(), img_aparcaseg.get_header())
                ni.save(img_tmp, out_tmp)

                mask_thal_rh = np.zeros(img_data_aparcaseg.shape)
                for lab in right_thalNuclei:
                    ind = np.where(img_data_thal == lab)
                    mask_thal_rh[ind] = 1

                # Identify voxels not included by thalamic Nuclei - should set to 41 (Gm) or 0
                tmp = mask_aparc_rh - mask_thal_rh
                ind = np.where(tmp > 0)
                img_data_aparcaseg_new[ind] = 41

                # Identify voxels not included by freesurfer thalamic mask
                tmp = mask_aparc_rh - mask_thal_rh
                ind = np.where(tmp < 0)
                img_data_aparcaseg_new[ind] = 49

                out_tmp = op.join(fs_dir, 'tmp', 'aparc-thal.rh.native.nii.gz')
                iflogger.info("    ... Save tmp image to {}".format(out_tmp))
                img_tmp = ni.Nifti1Image(
                    tmp, img_aparcaseg.get_affine(), img_aparcaseg.get_header())
                ni.save(img_tmp, out_tmp)

            # Brainstem (aparc+aseg labels: 16)
            if brainstem_defined:
                ind = np.where(img_data_aparcaseg == 16)
                img_data_aparcaseg_new[ind] = 0
                img_data_aparcaseg_new[indstem] = 16

            # new_aparcaseg_native = op.join(fs_dir, 'tmp', 'aparc+aseg.Lausanne2018.native.nii.gz')
            new_aparcaseg_native = op.join(
                fs_dir, 'tmp', 'aparc+aseg.Lausanne2018.native.nii.gz')
            iflogger.info("    ... Save relabeled image to {}".format(
                new_aparcaseg_native))
            img = ni.Nifti1Image(
                img_data_aparcaseg_new, img_aparcaseg.get_affine(), img_aparcaseg.get_header())
            ni.save(img, new_aparcaseg_native)
            del img

        else:
            iflogger.info(
                "  > Save Freesurfer-generated aparc+aseg.mgz in native space...")

            aparcaseg_native = op.join(
                fs_dir, 'tmp', 'aparc+aseg.Lausanne2018.native.nii.gz')
            iflogger.info(
                "    ... Save relabeled image to {}".format(aparcaseg_native))
            img = ni.Nifti1Image(
                img_data_aparcaseg, img_aparcaseg.get_affine(), img_aparcaseg.get_header())
            ni.save(img, aparcaseg_native)
            del img

        return runtime

    def _list_outputs(self):

        fs_dir = op.join(self.inputs.subjects_dir, self.inputs.subject_id)

        outputs = self._outputs().get()
        outputs['aparc_aseg'] = op.join(
            fs_dir, 'tmp', 'aparc+aseg.Lausanne2018.native.nii.gz')
        outputs['output_rois'] = self._gen_outfilenames(
            'ROIv_Lausanne2018', '_final.nii.gz')
        outputs['colorLUT_files'] = self._gen_outfilenames(
            'ROIv_Lausanne2018', '_FreeSurferColorLUT.txt')
        outputs['graphML_files'] = self._gen_outfilenames(
            'ROIv_Lausanne2018', '.graphml')
        return outputs

    def _gen_outfilenames(self, basename, posfix):
        filepaths = []
        for scale in list(get_parcellation('Lausanne2018').keys()):
            filepaths.append(op.abspath(basename + '_' + scale + posfix))
        return filepaths


class ParcellateThalamusInputSpec(BaseInterfaceInputSpec):
    T1w_image = File(mandatory=True, desc='T1w image to be parcellated')

    bids_dir = Directory(desc='BIDS root directory')

    subject = traits.Str(desc='Subject id')

    session = traits.Str('', desc='Session id')

    template_image = File(mandatory=True, desc='Template T1w')

    thalamic_nuclei_maps = File(
        mandatory=True, desc='Probability maps of thalamic nuclei (4D image) in template space')

    subjects_dir = Directory(mandatory=True, desc='Freesurfer main directory')

    subject_id = traits.String(mandatory=True, desc='Subject ID')

    ants_precision_type = traits.Enum(['double', 'float'], desc="Precision type used during computation")


class ParcellateThalamusOutputSpec(TraitedSpec):
    warped_image = File(desc='Template registered to T1w image (native)')

    inverse_warped_image = File(desc='Inverse warped template')

    max_prob_registered = File(desc='Max probability label image (native)')

    prob_maps_registered = File(
        desc='Probabilistic map of thalamus nuclei (native)')

    transform_file = File(desc='Transform file')

    warp_file = File(desc='Deformation file')

    thalamus_mask = File(desc='Thalamus mask')


class ParcellateThalamus(BaseInterface):
    """Parcellates the thalamus into 8 nuclei using an atlas-based method [Najdenovska18]_.

    References
    ----------
    .. [Najdenovska18] Najdenovska et al., Sci Data 5, 180270 (2018). <https://doi.org/10.1038/sdata.2018.270>

    Examples
    --------
    >>> parc_thal = ParcellateThalamus()
    >>> parc_thal.inputs.T1w_image = File(mandatory=True, desc='T1w image to be parcellated')
    >>> parc_thal.inputs.bids_dir = Directory(desc='BIDS root directory')
    >>> parc_thal.inputs.subject = '01'
    >>> parc_thal.inputs.template_image = '/path/to/atlas/T1w.nii.gz'
    >>> parc_thal.inputs.thalamic_nuclei_maps = '/path/to/atlas/nuclei/probability/map.nii.gz'
    >>> parc_thal.inputs.subjects_dir = '/path/to/output_dir/freesurfer'
    >>> parc_thal.inputs.subject_id = 'sub-01'
    >>> parc_thal.inputs.ants_precision_type = 'float'
    >>> parc_thal.run()  # doctest: +SKIP

    """

    input_spec = ParcellateThalamusInputSpec
    output_spec = ParcellateThalamusOutputSpec

    def _run_interface(self, runtime):
        iflogger.info("Parcellation of Thalamic Nuclei")
        iflogger.info("=============================================")

        # fs_string = 'export ANTSPATH=/usr/lib/ants/'
        # fs_string = ''
        iflogger.info(
            '- Input T1w image:\n  {}\n'.format(self.inputs.T1w_image))
        iflogger.info(
            '- Template image:\n  {}\n'.format(self.inputs.template_image))
        iflogger.info(
            '- Thalamic nuclei maps:\n  {}\n'.format(self.inputs.thalamic_nuclei_maps))

        # Moving aparc+aseg.mgz back to its original space for thalamic parcellation
        mov = op.join(self.inputs.subjects_dir, self.inputs.subject_id, 'mri', 'aparc+aseg.mgz')
        targ = op.join(self.inputs.subjects_dir, self.inputs.subject_id, 'mri', 'orig/001.mgz')
        out = op.join(self.inputs.subjects_dir, self.inputs.subject_id, 'tmp', 'aparc+aseg.nii.gz')
        # cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov,targ,out)
        cmd = 'mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov, targ, out)

        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        # Load aparc+aseg file in native space
        atlas_fn = out
        img_atlas = ni.load(atlas_fn)
        img_data_atlas = img_atlas.get_data()
        hdr = img_atlas.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)

        outprefix_name = Path(self.inputs.T1w_image).name.split(".")[0]
        outprefix_name = op.abspath('{}_Ind2temp'.format(outprefix_name))

        # Register the template image image to the subject T1w image
        # cmd = fs_string +
        #   '; antsRegistrationSyN.sh -d 3 -f "%s" -m "%s" -t s -n "%i" -o "%s"' % (self.inputs.T1w_image,self.inputs.template_image,12,outprefix_name)

        if self.inputs.ants_precision_type == 'float':
            precision_type = 'f'
        else:
            precision_type = 'd'

        cmd = 'antsRegistrationSyNQuick.sh -p {} -d 3 -f {} -m {} -t s -n {} -o {}'.format(precision_type,
                                                                                           self.inputs.T1w_image,
                                                                                           self.inputs.template_image,
                                                                                           12,
                                                                                           outprefix_name)

        iflogger.info('Processing cmd: %s' % cmd)

        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        outprefix_name = Path(self.inputs.T1w_image).name.split(".")[0]
        transform_file = op.abspath(
            '{}_Ind2temp0GenericAffine.mat'.format(outprefix_name))
        warp_file = op.abspath('{}_Ind2temp1Warp.nii.gz'.format(outprefix_name))
        # transform_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_Ind2temp0GenericAffine.mat'
        # warp_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_Ind2temp1Warp.nii.gz'
        output_maps = op.abspath('{}_class-thalamus_probtissue.nii.gz'.format(outprefix_name))
        jacobian_file = op.abspath('{}_class-thalamus_probtissue_jacobian.nii.gz'.format(outprefix_name))

        # Compute and save jacobian
        # cmd = fs_string + '; CreateJacobianDeterminantImage 3 "%s" "%s" ' % (warp_file,jacobian_file)
        cmd = 'CreateJacobianDeterminantImage 3 "%s" "%s" ' % (
            warp_file, jacobian_file)

        iflogger.info('Processing cmd: %s' % cmd)
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        # Propagate nuclei probability maps to subject T1w space using estimated transforms and deformation
        # cmd = fs_string +
        #   '; antsApplyTransforms --float -d 3 -e 3 -i "%s" -o "%s" -r "%s" -t "%s" -t "%s" -n BSpline[3]' %
        #   (self.inputs.thalamic_nuclei_maps,output_maps,self.inputs.T1w_image,warp_file,transform_file)
        cmd = 'antsApplyTransforms --float -d 3 -e 3 -i "%s" -o "%s" -r "%s" -t "%s" -t "%s" -n BSpline[3]' % (
            self.inputs.thalamic_nuclei_maps, output_maps, self.inputs.T1w_image, warp_file, transform_file)

        iflogger.info('Processing cmd: %s' % cmd)
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        iflogger.info('Correcting the volumes after the interpolation ')
        # Load jacobian file
        img_data_jacob = ni.load(jacobian_file).get_data()  # numpy.ndarray

        # Load probability maps in native space after applying estimated transform and deformation
        img_spams = ni.load(output_maps)
        img_data_vspams = img_spams.get_data()  # numpy.ndarray
        img_data_vspams[img_data_vspams < 0] = 0
        img_data_vspams[img_data_vspams > 1] = 1

        thresh = 0.05
        # Creating max_prob
        img_data_spams = img_data_vspams.copy()
        img_data_spams[img_data_spams < thresh] = 0
        ind = np.where(np.sum(img_data_spams, axis=3) == 0)
        max_prob = img_data_spams.argmax(axis=3) + 1
        max_prob[ind] = 0
        # ?max_prob = imfill(max_prob,'holes');

        del img_data_spams

        debug_file = op.abspath('{}_class-thalamus_dtissue_after_ants.nii.gz'.format(outprefix_name))
        print("Save output image to %s" % debug_file)
        img = ni.Nifti1Image(max_prob, img_atlas.get_affine(), hdr2)
        ni.save(img, debug_file)
        del img

        # Take into account jacobian to correct the probability maps after interpolation
        img_data_spams = np.zeros(img_data_vspams.shape)
        for nuc in np.arange(img_data_vspams.shape[3]):
            temp_image = img_data_vspams[:, :, :, nuc]
            t = np.multiply(temp_image, img_data_jacob)
            img_data_spams[:, :, :, nuc] = t / t.max()
        del temp_image, t, img_data_vspams, img_data_jacob

        # Creating max_prob
        img_data_spams[img_data_spams < thresh] = 0
        ind = np.where(np.sum(img_data_spams, axis=3) == 0)
        max_prob = img_data_spams.argmax(axis=3) + 1
        max_prob[ind] = 0
        # ?max_prob = imfill(max_prob,'holes');

        debug_file = op.abspath('{}_class-thalamus_dtissue_after_jacobiancorr.nii.gz'.format(outprefix_name))
        print("Save output image to %s" % debug_file)
        img = ni.Nifti1Image(max_prob, img_atlas.get_affine(), hdr2)
        ni.save(img, debug_file)
        del img

        iflogger.info('Creating Thalamus mask from FreeSurfer aparc+aseg ')

        # fs_string = 'export SUBJECTS_DIR=' + self.inputs.subjects_dir
        iflogger.info('- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(self.inputs.subjects_dir))

        # Extract indices of left/right thalamus mask from aparc+aseg volume
        indl = np.where(img_data_atlas == 10)
        indr = np.where(img_data_atlas == 49)

        def filter_isolated_cells(array, struct):
            """ Return array with completely isolated single cells removed
            :param array: Array with completely isolated single cells
            :param struct: Structure array for generating unique regions
            :return: Array with minimum region size > 1
            """
            filtered_array = np.copy(array)
            id_regions, num_ids = ndimage.label(
                filtered_array, structure=struct)
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
            temp_i = np.zeros(img_data_atlas.shape)
            temp_i[indl] = 1
            temp_i = filter_isolated_cells(temp_i, struct=struct)
            indl = np.where(temp_i == 1)

            # Right Hemisphere
            # Removing isolated points
            temp_i = np.zeros(img_data_atlas.shape)
            temp_i[indr] = 1
            temp_i = filter_isolated_cells(temp_i, struct=struct)
            indr = np.where(temp_i == 1)

            del struct, temp_i

        # Creating Thalamic Mask (1: Left, 2:Right)
        img_data_thal = np.zeros(img_data_atlas.shape)
        img_data_thal[indl] = 1
        img_data_thal[indr] = 2

        del indl, indr

        # TODO: Masking according to csf
        # unzip_nifti([freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii.gz']);
        # Outfiles = Extract_brain([freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii'],
        #                          [freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii']);
        #
        # csfFilename = deblank(Outfiles(4,:));
        # Vcsf = spm_vol_gzip(csfFilename);
        # Icsf = spm_read_vols_gzip(Vcsf);
        # ind = find(Icsf > csfThresh);
        # img_data_thal(ind) = 0;

        # update the header and save thalamus mask
        thalamus_mask = op.abspath('{}_class-thalamus_dtissue.nii.gz'.format(outprefix_name))
        hdr = img_atlas.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)
        print("Save output image to %s" % thalamus_mask)
        img_thal = ni.Nifti1Image(img_data_thal, img_atlas.get_affine(), hdr2)
        ni.save(img_thal, thalamus_mask)

        del hdr, hdr2, img_thal

        nb_spams = img_data_spams.shape[3]
        thresh = 0.05

        use_thalamus_mask = True
        if use_thalamus_mask:
            img_data_thal_lh = np.zeros(img_data_thal.shape)
            indl = np.where(img_data_thal == 1)
            img_data_thal_lh[indl] = 1
            del indl

            img_data_thal_rh = np.zeros(img_data_thal.shape)
            indr = np.where(img_data_thal == 2)
            img_data_thal_rh[indr] = 1

            del img_data_thal

            # Mask probability maps using the left-hemisphere thalamus mask
            tmp_thal_lh = np.zeros(
                (img_data_thal_lh.shape[0], img_data_thal_lh.shape[1], img_data_thal_lh.shape[2], 1))
            tmp_thal_lh[:, :, :, 0] = img_data_thal_lh
            temp_m = np.repeat(tmp_thal_lh, int(nb_spams / 2), axis=3)
            del tmp_thal_lh
            img_data_spam_lh = np.multiply(img_data_spams[:, :, :, 0:int(nb_spams / 2)], temp_m)
            # print('img_data_spam_lh shape:', img_data_spam_lh.shape)
            del temp_m

            # Creating max_prob
            img_data_spam_lh[img_data_spam_lh < thresh] = 0
            ind = np.where(np.sum(img_data_spam_lh, axis=3) == 0)
            # max_prob_l = img_data_spam_lh.max(axis=3)
            max_prob_l = np.argmax(img_data_spam_lh, axis=3) + 1
            max_prob_l[ind] = 0
            # max_prob_l[ind] = 0
            # ?max_prob_l = ndimage.binary_fill_holes(max_prob_l)
            # ?max_prob_l = Atlas_Corr(img_data_thal_lh,max_prob_l)

            # Mask probability maps using the right-hemisphere thalamus mask
            tmp_thal_rh = np.zeros(
                (img_data_thal_rh.shape[0], img_data_thal_rh.shape[1], img_data_thal_rh.shape[2], 1))
            tmp_thal_rh[:, :, :, 0] = img_data_thal_rh
            temp_m = np.repeat(tmp_thal_rh, int(nb_spams / 2), axis=3)
            del tmp_thal_rh
            img_data_spam_rh = np.multiply(img_data_spams[:, :, :, int(nb_spams / 2):int(nb_spams)], temp_m)
            # print('img_data_spam_rh shape:', img_data_spam_rh.shape)
            del temp_m

            # Creating max_prob
            img_data_spam_rh[img_data_spam_rh < thresh] = 0
            ind = np.where(np.sum(img_data_spam_rh, axis=3) == 0)
            # max_prob_r = img_data_spam_rh.max(axis=3)
            max_prob_r = np.argmax(img_data_spam_rh, axis=3) + 1
            # ?max_prob_r = imfill(max_prob_r,'holes');
            # ?max_prob_r = Atlas_Corr(img_data_thal_rh,max_prob_r);
            max_prob_r[indr] = max_prob_r[indr] + int(nb_spams / 2)
            max_prob_r[ind] = 0

            del indr

            img_data_spams[:, :, :, 0:int(nb_spams / 2)] = img_data_spam_lh
            img_data_spams[:, :, :, int(nb_spams / 2):nb_spams] = img_data_spam_rh

        # Save corrected probability maps of thalamic nuclei
        # update the header
        hdr = img_spams.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)
        print("Save output image to %s" % output_maps)
        img = ni.Nifti1Image(img_data_spams, img_spams.get_affine(), hdr2)
        ni.save(img, output_maps)

        del hdr, img, img_spams

        # Save Maxprob
        # update the header
        max_prob_fn = op.abspath('{}_class-thalamus_probtissue_maxprob.nii.gz'.format(outprefix_name))
        hdr = img_atlas.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)

        if use_thalamus_mask:
            max_prob = max_prob_l + max_prob_r
        else:
            # Creating max_prob
            img_data_spams[img_data_spams < thresh] = 0
            ind = np.where(np.sum(img_data_spams, axis=3) == 0)
            max_prob = img_data_spams.argmax(axis=3) + 1
            max_prob[ind] = 0
            # ?max_prob = imfill(max_prob,'holes');

        del img_data_spams

        # debug_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_maxprobL.nii.gz'
        # print("Save output image to %s" % debug_file)
        # img = ni.Nifti1Image(max_prob_l, img_atlas.get_affine(), hdr2)
        # ni.save(img, debug_file)
        #
        # debug_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_maxprobR.nii.gz'
        # print("Save output image to %s" % debug_file)
        # img = ni.Nifti1Image(max_prob_r, img_atlas.get_affine(), hdr2)
        # ni.save(img, debug_file)

        print("Save output image to %s" % max_prob)
        img = ni.Nifti1Image(max_prob, img_atlas.get_affine(), hdr2)
        ni.save(img, max_prob_fn)

        del hdr2, img, max_prob

        iflogger.info('Done')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outprefix_name = Path(self.inputs.T1w_image).name.split(".")[0]

        outputs['prob_maps_registered'] = op.abspath('{}_class-thalamus_probtissue.nii.gz'.format(outprefix_name))
        outputs['max_prob_registered'] = op.abspath('{}_class-thalamus_probtissue_maxprob.nii.gz'.format(outprefix_name))
        outputs['thalamus_mask'] = op.abspath('{}_class-thalamus_dtissue.nii.gz'.format(outprefix_name))

        outprefix_name = op.abspath('{}_Ind2temp'.format(outprefix_name))

        outputs['warped_image'] = op.abspath('{}Warped.nii.gz'.format(outprefix_name))
        outputs['inverse_warped_image'] = op.abspath('{}InverseWarped.nii.gz'.format(outprefix_name))
        outputs['transform_file'] = op.abspath('{}0GenericAffine.mat'.format(outprefix_name))
        outputs['warp_file'] = op.abspath('{}1Warp.nii.gz'.format(outprefix_name))

        # outputs['lh_hipposubfields'] = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'tmp','lh_subFields.nii.gz')
        # outputs['rh_hipposubfields'] = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'tmp','rh_subFields.nii.gz')
        return outputs


class ParcellateInputSpec(BaseInterfaceInputSpec):
    subjects_dir = Directory(desc='Freesurfer main directory')

    subject_id = traits.String(mandatory=True, desc='Subject ID')

    parcellation_scheme = traits.Enum('Lausanne2018', ['Lausanne2018', 'NativeFreesurfer'],
                                      desc="Parcellation scheme",
                                      usedefault=True)

    erode_masks = traits.Bool(False, desc="If `True` erode the masks")


class ParcellateOutputSpec(TraitedSpec):
    # roi_files = OutputMultiPath(File(exists=True),desc='Region of Interest files for connectivity mapping')
    white_matter_mask_file = File(desc='White matter (WM) mask file')

    gray_matter_mask_file = File(desc='Cortical gray matter (GM) mask file')

    csf_mask_file = File(desc='Cerebrospinal fluid (CSF) mask file')
    # cc_unknown_file = File(desc='Image file with regions labelled as unknown cortical structures',
    #                exists=True)

    ribbon_file = File(desc='Image file detailing the cortical ribbon',
                       exists=True)
    # aseg_file = File(desc='Automated segmentation file converted from Freesurfer "subjects" directory',
    #                exists=True)

    wm_eroded = File(desc="Eroded wm file in original space")

    csf_eroded = File(desc="Eroded csf file in original space")

    brain_eroded = File(desc="Eroded brain file in original space")

    roi_files_in_structural_space = OutputMultiPath(
        File(exists=True),
        desc='ROI image resliced to the dimensions of the original structural image'
    )

    T1 = File(desc="T1 image file")

    brain = File(desc="Brain-masked T1 image file")

    brain_mask = File(desc="Brain mask file")

    aseg = File(desc="ASeg image file (in native space)")

    aparc_aseg = File(desc="APArc+ASeg image file (in native space)")


class Parcellate(BaseInterface):
    """Subdivides segmented ROI file into smaller subregions.

    This interface interfaces with the CMTK parcellation functions
        available in `cmtklib.parcellation` module for all parcellation
        resolutions of a given scheme.

    Example
    -------
    >>> from cmtklib.parcellation import Parcellate
    >>> parcellate = Parcellate()
    >>> parcellate.inputs.subjects_dir = '/path/to/output_dir/freesurfer'
    >>> parcellate.inputs.subject_id = 'sub-01'
    >>> parcellate.inputs.parcellation_scheme = 'Lausanne2018'
    >>> parcellate.run()  # doctest: +SKIP
    """

    input_spec = ParcellateInputSpec
    output_spec = ParcellateOutputSpec

    def _run_interface(self, runtime):
        # if self.inputs.subjects_dir:
        #   os.environ.update({'SUBJECTS_DIR': self.inputs.subjects_dir})
        iflogger.info("ROI_HR_th.nii.gz / fsmask_1mm.nii.gz CREATION")
        iflogger.info("=============================================")

        fsdir = op.join(self.inputs.subjects_dir, self.inputs.subject_id)

        if self.inputs.parcellation_scheme == "Lausanne2018":
            print("Parcellation scheme : Lausanne2018")
            create_T1_and_Brain(self.inputs.subject_id, self.inputs.subjects_dir)
            # create_annot_label(self.inputs.subject_id, self.inputs.subjects_dir)
            create_roi(self.inputs.subject_id, self.inputs.subjects_dir)
            create_wm_mask(self.inputs.subject_id, self.inputs.subjects_dir)
            if self.inputs.erode_masks:
                erode_mask(fsdir, op.join(fsdir, 'mri', 'fsmask_1mm.nii.gz'))
                erode_mask(fsdir, op.join(fsdir, 'mri', 'csf_mask.nii.gz'))
                erode_mask(fsdir, op.join(fsdir, 'mri', 'brainmask.nii.gz'))
            crop_and_move_datasets(self.inputs.subject_id, self.inputs.subjects_dir)
        elif self.inputs.parcellation_scheme == "NativeFreesurfer":
            print("Parcellation scheme : NativeFreesurfer")
            create_T1_and_Brain(self.inputs.subject_id, self.inputs.subjects_dir)
            generate_WM_and_GM_mask(self.inputs.subject_id, self.inputs.subjects_dir)
            if self.inputs.erode_masks:
                erode_mask(fsdir, op.join(fsdir, 'mri', 'fsmask_1mm.nii.gz'))
                erode_mask(fsdir, op.join(fsdir, 'mri', 'csf_mask.nii.gz'))
                erode_mask(fsdir, op.join(fsdir, 'mri', 'brainmask.nii.gz'))
            crop_and_move_WM_and_GM(self.inputs.subject_id, self.inputs.subjects_dir)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        outputs['T1'] = op.abspath('T1.nii.gz')
        outputs['brain'] = op.abspath('brain.nii.gz')
        outputs['brain_mask'] = op.abspath('brain_mask.nii.gz')

        outputs['aseg'] = op.abspath('aseg.nii.gz')
        outputs['aparc_aseg'] = op.abspath('aparc+aseg.native.nii.gz')

        outputs['csf_mask_file'] = op.abspath('csf_mask.nii.gz')
        outputs['white_matter_mask_file'] = op.abspath('fsmask_1mm.nii.gz')

        # outputs['cc_unknown_file'] = op.abspath('cc_unknown.nii.gz')
        outputs['ribbon_file'] = op.abspath('ribbon.nii.gz')
        # outputs['aseg_file'] = op.abspath('aseg.nii.gz')

        # outputs['roi_files'] = self._gen_outfilenames('ROI_HR_th')
        if self.inputs.parcellation_scheme == "Lausanne2018":
            outputs['gray_matter_mask_file'] = op.abspath(
                'T1w_class-GM.nii.gz')
            outputs['roi_files_in_structural_space'] = self._gen_outfilenames(
                'ROIv_Lausanne2018')
        else:  # Native Freesurfer
            outputs['gray_matter_mask_file'] = op.abspath('gmmask.nii.gz')
            outputs['roi_files_in_structural_space'] = self._gen_outfilenames(
                'ROIv_HR_th')

        if self.inputs.erode_masks:
            outputs['wm_eroded'] = op.abspath('wm_eroded.nii.gz')
            outputs['csf_eroded'] = op.abspath('csf_eroded.nii.gz')
            outputs['brain_eroded'] = op.abspath('brain_eroded.nii.gz')

        return outputs

    def _gen_outfilenames(self, basename):
        filepaths = []
        for scale in list(get_parcellation(self.inputs.parcellation_scheme).keys()):
            filepaths.append(op.abspath(basename + '_' + scale + '.nii.gz'))
        return filepaths


def get_parcellation(parcel="NativeFreesurfer"):
    """Returns a dictionary containing atlas information.

    .. note::
        `atlas_info` often used in the code refers to such a dictionary.

    Parameters
    ----------
    parcel : parcellation scheme
        It can be: 'NativeFreesurfer' or 'Lausanne2018'
    """
    if parcel == "Lausanne2018":
        return {
            'scale1': {'number_of_regions': 95,  # 83,
                       'node_information_graphml': pkg_resources.resource_filename('cmtklib',
                                                                                   op.join('data', 'parcellation',
                                                                                           'lausanne2018',
                                                                                           'resolution1',
                                                                                           'resolution1.graphml')),
                       # NOTE that all the node-wise information is stored in a dedicated graphml file
                       'surface_parcellation': None,
                       'volume_parcellation': None,
                       'fs_label_subdir_name': 'regenerated_%s_1',
                       'subtract_from_wm_mask': 1,
                       'annotation': 'myaparc_1'},
            'scale2': {'number_of_regions': 141,  # 129,
                       'node_information_graphml': pkg_resources.resource_filename('cmtklib',
                                                                                   op.join('data', 'parcellation',
                                                                                           'lausanne2018',
                                                                                           'resolution2',
                                                                                           'resolution2.graphml')),
                       'surface_parcellation': None,
                       'volume_parcellation': None,
                       'fs_label_subdir_name': 'regenerated_%s_2',
                       'subtract_from_wm_mask': 1,
                       'annotation': 'myaparc_2'},
            'scale3': {'number_of_regions': 246,  # 234,
                       'node_information_graphml': pkg_resources.resource_filename('cmtklib',
                                                                                   op.join('data', 'parcellation',
                                                                                           'lausanne2018',
                                                                                           'resolution3',
                                                                                           'resolution3.graphml')),
                       'surface_parcellation': None,
                       'volume_parcellation': None,
                       'fs_label_subdir_name': 'regenerated_%s_3',
                       'subtract_from_wm_mask': 1,
                       'annotation': 'myaparc_3'},
            'scale4': {'number_of_regions': 475,  # 463,
                       'node_information_graphml': pkg_resources.resource_filename('cmtklib',
                                                                                   op.join('data', 'parcellation',
                                                                                           'lausanne2018',
                                                                                           'resolution4',
                                                                                           'resolution4.graphml')),
                       'surface_parcellation': None,
                       'volume_parcellation': None,
                       'fs_label_subdir_name': 'regenerated_%s_4',
                       'subtract_from_wm_mask': 1,
                       'annotation': 'myaparc_4'},
            'scale5': {'number_of_regions': 1027,  # 1015,
                       'node_information_graphml': pkg_resources.resource_filename('cmtklib',
                                                                                   op.join('data', 'parcellation',
                                                                                           'lausanne2018',
                                                                                           'resolution5',
                                                                                           'resolution5.graphml')),
                       'surface_parcellation': None,
                       'volume_parcellation': None,
                       'fs_label_subdir_name': 'regenerated_%s_5',
                       'subtract_from_wm_mask': 1,
                       'annotation': ['myaparc_5_P1_16', 'myaparc_5_P17_28', 'myaparc_5_P29_36']}
        }
    else:
        return {'freesurferaparc': {'number_of_regions': 83,
                                    # freesurferaparc; contains name, url, color, freesurfer_label, etc. used for connection matrix
                                    'node_information_graphml': pkg_resources.resource_filename('cmtklib',
                                                                                                op.join('data',
                                                                                                        'parcellation',
                                                                                                        'nativefreesurfer',
                                                                                                        'freesurferaparc',
                                                                                                        'freesurferaparc.graphml')),
                                    # scalar node values on fsaverage? or atlas?
                                    'surface_parcellation': None,
                                    # scalar node values in fsaverage volume?
                                    'volume_parcellation': None,
                                    }
                }


def extract(Z, shape, position, fill):
    """ Extract voxel neighbourhood.

    Parameters
    ----------
    Z: numpy.array
        The original data

    shape: tuple
        Tuple containing neighbourhood dimensions

    position: tuple
        Tuple containing central point indexes

    fill: value
        Value for the padding of Z

    Returns
    -------
    R: numpy.array
        The output neighbourhood of the specified point in Z
    """
    # initialize output block to the fill value
    R = np.ones(shape, dtype=Z.dtype) * fill
    # position coordinates(numpy array)
    P = np.array(list(position)).astype(int)
    # output block dimensions (numpy array)
    Rs = np.array(list(R.shape)).astype(int)
    # original volume dimensions (numpy array)
    Zs = np.array(list(Z.shape)).astype(int)

    R_start = np.zeros(len(shape)).astype(int)
    R_stop = np.array(list(shape)).astype(int)
    Z_start = (P - Rs // 2)
    Z_start_cor = (np.maximum(Z_start, 0)).tolist()  # handle borders
    R_start = R_start + (Z_start_cor - Z_start)
    Z_stop = (P + Rs // 2) + Rs % 2
    Z_stop_cor = (np.minimum(Z_stop, Zs)).tolist()  # handle borders
    R_stop = R_stop - (Z_stop - Z_stop_cor)

    R[R_start[0]:R_stop[0], R_start[1]:R_stop[1], R_start[2]:R_stop[2]] = Z[Z_start_cor[0]:Z_stop_cor[0],
                                                                            Z_start_cor[1]:Z_stop_cor[1],
                                                                            Z_start_cor[2]:Z_stop_cor[2]]
    return R


def create_T1_and_Brain(subject_id, subjects_dir):
    """Generates T1, T1 masked and aseg+aparc Freesurfer images in NIFTI format.

    Parameters
    ----------
    subject_id : string
        Freesurfer subject id

    subjects_dir : string
        Freesurfer subjects dir
        (Typically ``/path/to/output_dir/freesurfer``)
    """
    fs_dir = op.join(subjects_dir, subject_id)

    # Convert T1 image
    mri_cmd = ['mri_convert', '-i',
               op.join(fs_dir, 'mri', 'T1.mgz'), '-o', op.join(fs_dir, 'mri', 'T1.nii.gz')]
    subprocess.check_call(mri_cmd)

    # Convert Brain_masked T1 image
    mri_cmd = ['mri_convert', '-i',
               op.join(fs_dir, 'mri', 'brain.mgz'), '-o', op.join(fs_dir, 'mri', 'brain.nii.gz')]
    subprocess.check_call(mri_cmd)

    # Convert ASeg image
    mri_cmd = ['mri_convert', '-i',
               op.join(fs_dir, 'mri', 'aseg.mgz'), '-o', op.join(fs_dir, 'mri', 'aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    # Moving aparc+aseg.mgz back to its original space for ACT
    mov = op.join(fs_dir, 'mri', 'aparc+aseg.mgz')
    targ = op.join(fs_dir, 'mri', 'rawavg.mgz')
    out = op.join(fs_dir, 'tmp', 'aparc+aseg.native.nii.gz')

    print("Create aparc+aseg.nii.gz in native space as %s" % out)
    cmd = 'mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (
        mov, targ, out)
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    proc_stdout = process.communicate()[0].strip()
    iflogger.info(proc_stdout)

    print("[DONE]")


def create_roi(subject_id, subjects_dir, v=True):
    """Iteratively creates the ROI_%s.nii.gz files using the given Lausanne2018 parcellation information from networks.

    Parameters
    ----------
    subject_id : string
        Freesurfer subject id

    subjects_dir : string
        Freesurfer subjects dir
        (Typically ``/path/to/output_dir/freesurfer``)

    v : Boolean
        Verbose mode
    """

    freesurfer_subj = os.path.abspath(subjects_dir)
    subject_dir = os.path.join(freesurfer_subj, subject_id)

    if not (os.access(freesurfer_subj, os.F_OK)):
        print('ERROR: FreeSurfer subjects directory ($SUBJECTS_DIR) does not exist')
    else:
        if v:
            print(
                '- FreeSurfer subjects directory ($SUBJECTS_DIR):\n  {}\n'.format(freesurfer_subj))

    if not (os.access(os.path.join(freesurfer_subj, 'fsaverage'), os.F_OK)):
        print('-  FreeSurfer subjects directory ($SUBJECTS_DIR) DOES NOT contain \'fsaverage\'')

        src = os.path.join(
            os.environ['FREESURFER_HOME'], 'subjects', 'fsaverage')
        dst = os.path.join(freesurfer_subj, 'fsaverage')

        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)

        print('         -> Copy fsaverage')
        shutil.copytree(src, dst)
    else:
        if v:
            print(
                '-  FreeSurfer subjects directory ($SUBJECTS_DIR) DOES contain \'fsaverage\'\n')

    if not (os.access(subject_dir, os.F_OK)):
        print('ERROR: No input subject directory was found in FreeSurfer $SUBJECTS_DIR')
    else:
        if v:
            print('- Freesurfer subject id:\n  {}\n'.format(subject_id))
            print('- Freesurfer subject directory:\n  {}\n'.format(subject_dir))

    # Number of scales in multiscale parcellation
    nscales = 5

    # # load aseg volume
    aseg = ni.load(op.join(subject_dir, 'mri', 'aseg.nii.gz'))
    asegd = aseg.get_data()  # numpy.ndarray

    # identify cortical voxels, right (3) and left (42) hemispheres
    idxr = np.where(asegd == 3)
    idxl = np.where(asegd == 42)
    xx = np.concatenate((idxr[0], idxl[0]))
    yy = np.concatenate((idxr[1], idxl[1]))
    zz = np.concatenate((idxr[2], idxl[2]))

    # initialize variables necessary for cortical ROIs dilation
    # dimensions of the neighbourhood for rois labels assignment (choose odd dimensions!)
    shape = (25, 25, 25)
    center = np.array(shape) // 2
    # dist: distances from the center of the neighbourhood
    dist = np.zeros(shape, dtype='float32')
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(shape[2]):
                distxyz = center - [x, y, z]
                dist[x, y, z] = math.sqrt(
                    np.sum(np.multiply(distxyz, distxyz)))

        # Check existence of tmp folder in input subject folder
        this_dir = os.path.join(subject_dir, 'tmp')
        if not (os.path.isdir(this_dir)):
            os.makedirs(this_dir)

    # Loop over parcellation scales
    if v:
        print('Generate MULTISCALE PARCELLATION for input subject')

    fs_string = 'export SUBJECTS_DIR=' + freesurfer_subj

    # Multiscale parcellation - define annotation and segmentation variables
    rh_annot_files = ['rh.lausanne2008.scale1.annot', 'rh.lausanne2008.scale2.annot', 'rh.lausanne2008.scale3.annot',
                      'rh.lausanne2008.scale4.annot', 'rh.lausanne2008.scale5.annot']
    lh_annot_files = ['lh.lausanne2008.scale1.annot', 'lh.lausanne2008.scale2.annot', 'lh.lausanne2008.scale3.annot',
                      'lh.lausanne2008.scale4.annot', 'lh.lausanne2008.scale5.annot']
    annot = ['lausanne2008.scale1', 'lausanne2008.scale2', 'lausanne2008.scale3', 'lausanne2008.scale4',
             'lausanne2008.scale5']
    rois_output = ['ROI_scale1_Lausanne2018.nii.gz', 'ROI_scale2_Lausanne2018.nii.gz', 'ROI_scale3_Lausanne2018.nii.gz',
                   'ROI_scale4_Lausanne2018.nii.gz', 'ROI_scale5_Lausanne2018.nii.gz']
    roivs_output = ['ROIv_scale1_Lausanne2018.nii.gz', 'ROIv_scale2_Lausanne2018.nii.gz',
                    'ROIv_scale3_Lausanne2018.nii.gz', 'ROIv_scale4_Lausanne2018.nii.gz',
                    'ROIv_scale5_Lausanne2018.nii.gz']

    FNULL = open(os.devnull, 'w')

    for i in reversed(list(range(0, nscales))):

        if v:
            print(' ... working on multiscale parcellation, SCALE {}'.format(i + 1))

        # 1. Resample fsaverage CorticalSurface onto SUBJECT_ID CorticalSurface and map annotation for current scale
        # Left hemisphere
        if v:
            print(
                '     > resample fsaverage CorticalSurface to individual CorticalSurface')
        mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi lh --sval-annot %s --tval %s' % (
            subject_id,
            pkg_resources.resource_filename('cmtklib',
                                            op.join('data', 'parcellation', 'lausanne2018', lh_annot_files[i])),
            os.path.join(subject_dir, 'label', lh_annot_files[i]))
        if v == 2:
            _ = subprocess.call(mri_cmd, shell=True)
        else:
            _ = subprocess.call(
                mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
        # Right hemisphere
        mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi rh --sval-annot %s --tval %s' % (
            subject_id,
            pkg_resources.resource_filename('cmtklib',
                                            op.join('data', 'parcellation', 'lausanne2018', rh_annot_files[i])),
            os.path.join(subject_dir, 'label', rh_annot_files[i]))
        if v == 2:
            status = subprocess.call(mri_cmd, shell=True)
        else:
            status = subprocess.call(
                mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

        # 2. Generate Nifti volume from annotation
        #    Note: change here --wmparc-dmax (FS default 5mm) to dilate cortical regions toward the WM
        if v:
            print('     > generate Nifti volume from annotation')
        mri_cmd = fs_string + '; mri_aparc2aseg --s %s --annot %s --wmparc-dmax 0 --labelwm --hypo-as-wm --new-ribbon --o %s' % (
            subject_id,
            annot[i],
            os.path.join(subject_dir, 'tmp', rois_output[i]))
        if v == 2:
            subprocess.call(mri_cmd, shell=True)
        else:
            subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

        # 3. Update numerical IDs of cortical and subcortical regions
        # Load Nifti volume
        if v:
            print(
                '     > relabel cortical and subcortical regions for consistency between resolutions')
        this_nifti = ni.load(os.path.join(subject_dir, 'tmp', rois_output[i]))
        vol = this_nifti.get_data()  # numpy.ndarray
        hdr = this_nifti.header
        # Initialize output
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)

        newrois = vol.copy()
        # store scale5 volume for correction on multi-resolution consistency
        if i == (nscales - 1):
            print("     ... storing ROIs volume maximal resolution")
            roisMax = vol.copy()
            idxMax = np.where(roisMax > 0)
            xxMax = idxMax[0]
            yyMax = idxMax[1]
            zzMax = idxMax[2]
        # correct cortical surfaces using as reference the roisMax volume (for consistency between resolutions)
        else:
            print("     > adapt cortical surfaces")
            # adaptstart = time()
            idxRois = np.where(vol > 0)
            xxRois = idxRois[0]
            yyRois = idxRois[1]
            zzRois = idxRois[2]
            # correct voxels labeled in current resolution, but not labeled in highest resolution
            for j in range(xxRois.size):
                if roisMax[xxRois[j], yyRois[j], zzRois[j]] == 0:
                    newrois[xxRois[j], yyRois[j], zzRois[j]] = 0
            # correct voxels not labeled in current resolution, but labeled in highest resolution
            for j in range(xxMax.size):
                if newrois[xxMax[j], yyMax[j], zzMax[j]] == 0:
                    local = extract(vol, shape, position=(
                        xxMax[j], yyMax[j], zzMax[j]), fill=0)
                    mask = local.copy()
                    mask[np.nonzero(local > 0)] = 1
                    thisdist = np.multiply(dist, mask)
                    thisdist[np.nonzero(thisdist == 0)] = np.amax(thisdist)
                    value = np.int_(
                        local[np.nonzero(thisdist == np.amin(thisdist))])
                    if value.size > 1:
                        counts = np.bincount(value)
                        value = np.argmax(counts)
                    newrois[xxMax[j], yyMax[j], zzMax[j]] = value
            # print("Cortical ROIs adaptation took %s seconds to process." % (time()-adaptstart))
        if v:
            print('     ... save output volumes')
        this_out = os.path.join(subject_dir, 'mri', rois_output[i])
        img = ni.Nifti1Image(newrois, this_nifti.affine, hdr2)
        ni.save(img, this_out)
        del img

        # 4. Dilate cortical regions
        if v:
            print("     > dilating cortical regions")
        # dilatestart = time()
        # loop throughout all the voxels belonging to the aseg GM volume
        for j in range(xx.size):
            if newrois[xx[j], yy[j], zz[j]] == 0:
                local = extract(vol, shape, position=(
                    xx[j], yy[j], zz[j]), fill=0)
                mask = local.copy()
                mask[np.nonzero(local > 0)] = 1
                thisdist = np.multiply(dist, mask)
                thisdist[np.nonzero(thisdist == 0)] = np.amax(thisdist)
                value = np.int_(
                    local[np.nonzero(thisdist == np.amin(thisdist))])
                if value.size > 1:
                    counts = np.bincount(value)
                    value = np.argmax(counts)
                newrois[xx[j], yy[j], zz[j]] = value

        # 5. Save Nifti and mgz volumes
        if v:
            print('     ... save output volumes ')
        this_out = os.path.join(subject_dir, 'mri', roivs_output[i])
        img = ni.Nifti1Image(newrois, this_nifti.affine, hdr2)
        ni.save(img, this_out)
        del img

        mri_cmd = fs_string + '; mri_convert -i %s -o %s' % (
            this_out,
            os.path.join(subject_dir, 'mri', roivs_output[i][0:-4] + '.mgz'))
        if v == 2:
            status = subprocess.call(mri_cmd, shell=True)
        else:
            status = subprocess.call(
                mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
        # os.remove(os.path.join(subject_dir, 'tmp', rois_output[i]))

        # Create Gray Matter mask
        if i == 0:
            print("     ... Creating gray matter mask from SCALE {}...".format(i + 1))
            gmMask = newrois.copy()
            gmMask[newrois == newrois.max()] = 0
            gmMask[gmMask > 0] = 1
            out_mask = op.join(subject_dir, 'label', 'T1w_class-GM.nii.gz')
            print("         Save gray matter mask to %s" % out_mask)
            img = ni.Nifti1Image(gmMask, this_nifti.affine, hdr2)
            ni.save(img, out_mask)
            del img

    mri_cmd = ['mri_convert', '-i', op.join(subject_dir, 'mri', 'ribbon.mgz'), '-o',
               op.join(subject_dir, 'mri', 'ribbon.nii.gz')]
    subprocess.check_call(mri_cmd)

    print("[ DONE ]")


def create_wm_mask(subject_id, subjects_dir, v=True):
    """Creates the white-matter mask using the Freesurfer ribbon as basis in the Lausanne2018 framework.

    Parameters
    ----------
    subject_id : string
        Freesurfer subject id

    subjects_dir : string
        Freesurfer subjects dir
        (Typically ``/path/to/output_dir/freesurfer``)

    v : Boolean
        Verbose mode
    """
    if v:
        iflogger.info("  > Create white matter mask")

    fs_dir = op.join(subjects_dir, subject_id)

    if v:
        iflogger.info("    ... FreeSurfer dir: %s" % fs_dir)

    # load ribbon as basis for white matter mask
    if v:
        iflogger.info("    > load ribbon")
    fsmask = ni.load(op.join(fs_dir, 'mri', 'ribbon.nii.gz'))
    fsmaskd = fsmask.get_data()

    wmmask = np.zeros(fsmask.get_data().shape)

    # these data is stored and could be extracted from fs_dir/stats/aseg.txt

    # FIXME understand when ribbon file has default value or has "aseg" value
    # extract right and left white matter
    if v:
        iflogger.info("    > Extract right and left wm")
    # Ribbon labels by default
    if fsmaskd.max() == 120:
        idx_lh = np.where(fsmaskd == 120)
        idx_rh = np.where(fsmaskd == 20)
    # Ribbon label w.r.t aseg label
    else:
        idx_lh = np.where(fsmaskd == 41)
        idx_rh = np.where(fsmaskd == 2)

    # extract right and left
    wmmask[idx_lh] = 1
    wmmask[idx_rh] = 1

    # remove subcortical nuclei from white matter mask
    if v:
        iflogger.info("     > Load aseg")
    aseg = ni.load(op.join(fs_dir, 'mri', 'aseg.nii.gz'))
    asegd = aseg.get_data()

    try:
        import scipy.ndimage.morphology as nd
    except ImportError:
        raise Exception(
            '      ... ERROR: Need scipy for binary erosion of white matter mask')

    # need binary erosion function
    imerode = nd.binary_erosion

    # ventricle erosion
    iflogger.info("    > Ventricle erosion")
    csfA = np.zeros(asegd.shape)
    csfB = np.zeros(asegd.shape)

    # structuring elements for erosion
    se1 = np.zeros((3, 3, 5))
    se1[1, :, 2] = 1
    se1[:, 1, 2] = 1
    se1[1, 1, :] = 1
    se = np.zeros((3, 3, 3))
    se[1, :, 1] = 1
    se[:, 1, 1] = 1
    se[1, 1, :] = 1

    # lateral ventricles, thalamus proper and caudate
    # the latter two removed for better erosion, but put back afterwards
    idx = np.where((asegd == 4) |
                   (asegd == 43) |
                   (asegd == 11) |
                   (asegd == 50) |
                   (asegd == 31) |
                   (asegd == 63) |
                   (asegd == 10) |
                   (asegd == 49))
    csfA[idx] = 1

    if v:
        iflogger.info("    > Save CSF mask")
    img = ni.Nifti1Image(csfA, aseg.get_affine(), aseg.get_header())
    ni.save(img, op.join(fs_dir, 'mri', 'csf_mask.nii.gz'))
    del img

    csfA = imerode(imerode(csfA, se1), se)

    # thalmus proper and cuadate are put back because they are not lateral ventricles
    idx = np.where((asegd == 11) |
                   (asegd == 50) |
                   (asegd == 10) |
                   (asegd == 49))
    csfA[idx] = 0

    # REST CSF, IE 3RD AND 4TH VENTRICULE AND EXTRACEREBRAL CSF
    idx = np.where((asegd == 5) |
                   (asegd == 14) |
                   (asegd == 15) |
                   (asegd == 24) |
                   (asegd == 44) |
                   (asegd == 72) |
                   (asegd == 75) |
                   (asegd == 76) |
                   (asegd == 213) |
                   (asegd == 221))
    # 43 ??, 4??  213?, 221?
    # more to discuss.
    for i in [5, 14, 15, 24, 44, 72, 75, 76, 213, 221]:
        idx = np.where(asegd == i)
        csfB[idx] = 1

    # do not remove the subthalamic nucleus for now from the wm mask
    # 23, 60
    # would stop the fiber going to the segmented "brainstem"

    # grey nuclei, either with or without erosion
    if v:
        iflogger.info("    > Grey nuclei, either with or without erosion")
    gr_ncl = np.zeros(asegd.shape)

    # with erosion
    for i in [10, 11, 12, 49, 50, 51]:
        idx = np.where(asegd == i)
        # temporary volume
        tmp = np.zeros(asegd.shape)
        tmp[idx] = 1
        tmp = imerode(tmp, se)
        idx = np.where(tmp == 1)
        gr_ncl[idx] = 1

    # without erosion
    for i in [13, 17, 18, 26, 52, 53, 54, 58]:
        idx = np.where(asegd == i)
        gr_ncl[idx] = 1

    # remove remaining structure, e.g. brainstem
    if v:
        iflogger.info("    > Remove remaining structure, e.g. brainstem")
    remaining = np.zeros(asegd.shape)
    idx = np.where(asegd == 16)
    remaining[idx] = 1

    # now remove all the structures from the white matter
    idx = np.where((csfA != 0) | (csfB != 0) |
                   (gr_ncl != 0) | (remaining != 0))
    wmmask[idx] = 0
    if v:
        iflogger.info(
            "    > Removing lateral ventricles and eroded grey nuclei and brainstem from white matter mask")

    # ADD voxels from 'cc_unknown.nii.gz' dataset
    # ccun = ni.load(op.join(fs_dir, 'label', 'cc_unknown.nii.gz'))
    # ccund = ccun.get_data()
    # idx = np.where(ccund != 0)
    # iflogger.info("Add corpus callosum and unknown to wm mask")
    # wmmask[idx] = 1

    # XXX add unknown dilation for connecting corpus callosum?
    #    se2R = zeros(15,3,3); se2R(8:end,2,2)=1;
    #    se2L = zeros(15,3,3); se2L(1:8,2,2)=1;
    #    temp = (cc_unknown.img==1 | cc_unknown.img==2);
    #    fsmask.img(imdilate(temp,se2R))    =  1;
    #    fsmask.img(imdilate(temp,se2L))    =  1;
    #    fsmask.img(cc_unknown.img==3)    =  1;
    #    fsmask.img(cc_unknown.img==4)    =  1;

    # output white matter mask. crop and move it afterwards
    # wm_out = op.join(fs_dir, 'mri', 'fsmask_1mm_all.nii.gz')
    # img = ni.Nifti1Image(wmmask, fsmask.get_affine(), fsmask.get_header() )
    # iflogger.info("Save white matter mask: %s" % wm_out)
    # ni.save(img, wm_out)

    # Extract cortical gray matter mask
    # remove remaining structure, e.g. brainstem
    gmmask = np.zeros(asegd.shape)

    # XXX: subtracting wmmask from ROI. necessary?
    # for parkey, parval in get_parcellation('Lausanne2018').items():
    #
    #     print parkey
    #
    #     # check if we should subtract the cortical rois from this parcellation
    #     if parval.has_key('subtract_from_wm_mask'):
    #         if not bool(int(parval['subtract_from_wm_mask'])):
    #             continue
    #     else:
    #         continue
    #
    #     iflogger.info("Loading %s to subtract cortical ROIs from white matter mask" % ('ROI_%s.nii.gz' % parkey) )
    #     roi = ni.load(op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' % parkey))
    #     roid = roi.get_data()
    #
    #     assert roid.shape[0] == wmmask.shape[0]
    #
    #     pg = nx.read_graphml(parval['node_information_graphml'])
    #
    #     for brk, brv in pg.nodes(data=True):
    #
    #         if brv['dn_region'] == 'cortical':
    #
    #             iflogger.info("Subtracting region %s with intensity value %s" % (brv['dn_region'], brv['dn_multiscaleID']))
    #
    #             idx = np.where(roid == int(brv['dn_multiscaleID']))
    #             wmmask[idx] = 0
    #             gmmask[idx] = 1

    # output white matter mask. crop and move it afterwards
    wm_out = op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz')
    img = ni.Nifti1Image(wmmask, fsmask.get_affine(), fsmask.get_header())
    if v:
        iflogger.info("    > Save white matter mask: %s" % wm_out)
    ni.save(img, wm_out)
    del img

    gm_out = op.join(fs_dir, 'mri', 'gmmask.nii.gz')
    img = ni.Nifti1Image(gmmask, fsmask.get_affine(), fsmask.get_header())
    if v:
        iflogger.info("    > Save gray matter mask: %s" % gm_out)
    ni.save(img, gm_out)
    del img

    # Redirect ouput if low verbose
    FNULL = open(os.devnull, 'w')

    # Convert whole brain mask
    mri_cmd = ['mri_convert', '-i', op.join(fs_dir, 'mri', 'brainmask.mgz'), '-o',
               op.join(fs_dir, 'mri', 'brainmask.nii.gz')]
    if v == 2:
        status = subprocess.call(' '.join(mri_cmd), shell=True)
    else:
        status = subprocess.call(
            ' '.join(mri_cmd), shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    iflogger.info(status)

    mri_cmd = ['fslmaths', op.join(fs_dir, 'mri', 'brainmask.nii.gz'), '-bin',
               op.join(fs_dir, 'mri', 'brainmask.nii.gz')]
    if v == 2:
        status = subprocess.call(' '.join(mri_cmd), shell=True)
    else:
        status = subprocess.call(
            ' '.join(mri_cmd), shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    iflogger.info(status)


def crop_and_move_datasets(subject_id, subjects_dir):
    """Convert Freesurfer images back to original native space when Lausanne2018 parcellation schemes are used.

    Parameters
    ----------
    subject_id : string
        Freesurfer subject id

    subjects_dir : string
        Freesurfer subjects dir
        (Typically ``/path/to/output_dir/freesurfer``)
    """
    print("Cropping datasets")
    fs_dir = op.join(subjects_dir, subject_id)

    # datasets to crop and move: (from, to)
    ds = [
        (op.join(fs_dir, 'mri', 'aseg.nii.gz'), 'aseg.nii.gz'),
        (op.join(fs_dir, 'mri', 'ribbon.nii.gz'), 'ribbon.nii.gz'),
        (op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz'), 'fsmask_1mm.nii.gz'),
        (op.join(fs_dir, 'mri', 'csf_mask.nii.gz'), 'csf_mask.nii.gz'),
        # (op.join(fs_dir, 'mri', 'gmmask.nii.gz'), 'gmmask.nii.gz'),
    ]

    for p in list(get_parcellation('Lausanne2018').keys()):
        # ds.append( (op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % p), 'ROI_HR_th_%s.nii.gz' % p) )
        ds.append((op.join(fs_dir, 'mri', 'ROI_%s_Lausanne2018.nii.gz' %
                           p), 'ROI_Lausanne2018_%s.nii.gz' % p))
        ds.append((op.join(fs_dir, 'mri', 'ROIv_%s_Lausanne2018.nii.gz' %
                           p), 'ROIv_Lausanne2018_%s.nii.gz' % p))
    ds.append((op.join(fs_dir, 'mri', 'gmmask.nii.gz'), 'T1w_class-GM.nii.gz'))
    ds.append((op.join(fs_dir, 'mri', 'aparc+aseg.mgz'),
               'aparc+aseg.native.nii.gz'))

    orig = op.join(fs_dir, 'mri', 'rawavg.mgz')

    for d in ds:
        print("Processing %s:" % d[0])

        # does it exist at all?
        if not op.exists(d[0]):
            raise Exception('File %s does not exist.' % d[0])
        # reslice to original volume because the roi creation with freesurfer
        # changed to 256x256x256 resolution
        # mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, d[0], d[1])
        # runCmd( mri_cmd,log )
        mri_cmd = ['mri_convert', '-rl', orig,
                   '-rt', 'nearest', d[0], '-nc', d[1]]
        subprocess.check_call(mri_cmd)

    ds = [(op.join(fs_dir, 'mri', 'fsmask_1mm_eroded.nii.gz'), 'wm_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'csf_mask_eroded.nii.gz'), 'csf_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask_eroded.nii.gz'), 'brain_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask.nii.gz'), 'brain_mask.nii.gz')]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig,
                       '-rt', 'nearest', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)

    ds = [(op.join(fs_dir, 'mri', 'T1.nii.gz'), 'T1.nii.gz'),
          (op.join(fs_dir, 'mri', 'brain.nii.gz'), 'brain.nii.gz'),
          ]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig,
                       '-rt', 'cubic', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)


def generate_WM_and_GM_mask(subject_id, subjects_dir):
    """Generates the white-matter and gray-matter masks when NativeFreesurfer parcellation is used.

    Parameters
    ----------
    subject_id : string
        Freesurfer subject id

    subjects_dir : string
        Freesurfer subjects dir
        (Typically ``/path/to/output_dir/freesurfer``)
    """
    fs_dir = op.join(subjects_dir, subject_id)

    print("Create the wm_labels and GM mask")

    # need to convert
    mri_cmd = ['mri_convert', '-i', op.join(fs_dir, 'mri', 'aparc+aseg.mgz'), '-o',
               op.join(fs_dir, 'mri', 'aparc+aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    fout = op.join(fs_dir, 'mri', 'aparc+aseg.nii.gz')
    nii_apar_cimg = ni.load(fout)
    nii_apar_cdata = nii_apar_cimg.get_data()

    # mri_convert aparc+aseg.mgz aparc+aseg.nii.gz
    wm_out = op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz')

    # %% label mapping
    # Using FreesurferColorLUT.txt
    # mappings are stored in mappings.ods

    #    CORTICAL = {1 : [ 1, 2, 3, 5, 6, 7, 8, 9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34],
    #                2 : [31,13, 9,21,27,25,19,29,15,23, 1,24, 4,30,26,11, 6, 2, 5,22,16,14,10,20,12, 7, 8,18,30,17, 3,28,33]}
    #
    #
    #    SUBCORTICAL = {1:[48,49,50,51,52,53,54,58,59,60, 9,10,11,12,13,17,18,26,27,28],
    #                   2:[34,34,35,36,37,40,41,38,39,39,75,75,76,77,78,81,82,79,80,80]}
    #
    #    OTHER = {1:[16],
    #             2:[83]}

    mapping = [[1, 2012], [2, 2019], [3, 2032], [4, 2014], [5, 2020], [6, 2018], [7, 2027], [8, 2028], [9, 2003],
               [10, 2024], [11, 2017], [12, 2026],
               [13, 2002], [14, 2023], [15, 2010], [16, 2022], [
                   17, 2031], [18, 2029], [19, 2008], [20, 2025],
               [21, 2005], [22, 2021], [23, 2011],
               [24, 2013], [25, 2007], [26, 2016], [27, 2006], [
                   28, 2033], [29, 2009], [30, 2015], [31, 2001],
               [32, 2030], [33, 2034], [34, 2035],
               [35, 49], [36, 50], [37, 51], [38, 52], [39, 58], [
                   40, 53], [41, 54], [42, 1012], [43, 1019], [44, 1032],
               [45, 1014], [46, 1020], [47, 1018],
               [48, 1027], [49, 1028], [50, 1003], [51, 1024], [
                   52, 1017], [53, 1026], [54, 1002], [55, 1023],
               [56, 1010], [57, 1022], [58, 1031],
               [59, 1029], [60, 1008], [61, 1025], [62, 1005], [
                   63, 1021], [64, 1011], [65, 1013], [66, 1007],
               [67, 1016], [68, 1006], [69, 1033],
               [70, 1009], [71, 1015], [72, 1001], [73, 1030], [
                   74, 1034], [75, 1035], [76, 10], [77, 11], [78, 12],
               [79, 13], [80, 26], [81, 17],
               [82, 18], [83, 16]]

    wm_labels = [2, 29, 32, 41, 61, 64, 59, 60, 27, 28] + \
        list(range(77, 86 + 1)) + \
        list(range(100, 117 + 1)) + \
        list(range(155, 158 + 1)) + \
        list(range(195, 196 + 1)) + \
        list(range(199, 200 + 1)) + \
        list(range(203, 204 + 1)) + \
        [212, 219, 223] + \
        list(range(250, 255 + 1))
    # add
    # 59  Right-Substancia-Nigra
    # 60  Right-VentralDC
    # 27  Left-Substancia-Nigra
    # 28  Left-VentralDC

    print("wm_labels mask....")
    # %% create wm_labels mask
    nii_wm = np.zeros(nii_apar_cdata.shape, dtype=np.uint8)

    for i in wm_labels:
        nii_wm[nii_apar_cdata == i] = 1

    # we do not add subcortical regions
    #    for i in SUBCORTICAL[1]:
    #         nii_wm[nii_apar_cdata == i] = 1

    img = ni.Nifti1Image(nii_wm, nii_apar_cimg.get_affine(),
                         nii_apar_cimg.get_header())
    print("Save to: " + wm_out)
    ni.save(img, wm_out)
    del img

    print("GM mask....")
    # %% create GM parcellation (CORTICAL+SUBCORTICAL)
    # %  -------------------------------------
    for park in list(get_parcellation('NativeFreesurfer').keys()):
        print("Parcellation: " + park)
        gm_out = op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' % park)

        nii_gm = np.zeros(nii_apar_cdata.shape, dtype=np.uint8)

        for ma in mapping:
            nii_gm[nii_apar_cdata == ma[1]] = ma[0]

        #        # % 33 cortical regions (stored in the order of "parcel33")
        #        for idx,i in enumerate(CORTICAL[1]):
        #            nii_gm[ nii_apar_cdata == (2000+i)] = CORTICAL[2][idx] # RIGHT
        #            nii_gm[ nii_apar_cdata == (1000+i)] = CORTICAL[2][idx] + 41 # LEFT
        #
        #        #% subcortical nuclei
        #        for idx,i in enumerate(SUBCORTICAL[1]):
        #            nii_gm[ nii_apar_cdata == i ] = SUBCORTICAL[2][idx]
        #
        #        # % other region to account for in the GM
        #        for idx, i in enumerate(OTHER[1]):
        #            nii_gm[ nii_apar_cdata == i ] = OTHER[2][idx]

        print("Save to: " + gm_out)
        img = ni.Nifti1Image(nii_gm, nii_apar_cimg.get_affine(),
                             nii_apar_cimg.get_header())
        ni.save(img, gm_out)
        del img

        # Create GM mask
        gm_maskout = op.join(fs_dir, 'mri', 'gmmask.nii.gz')
        nii_gm_mask = nii_gm.copy()
        # Remove brainstem (supposed to be the last label 83)
        nii_gm_mask[nii_gm_mask == nii_gm_mask.max()] = 0
        nii_gm_mask[nii_gm_mask > 0] = 1

        print("GM mask saved to: " + gm_maskout)
        img = ni.Nifti1Image(
            nii_gm_mask, nii_apar_cimg.get_affine(), nii_apar_cimg.get_header())
        ni.save(img, gm_maskout)
        del img

    # Create CSF mask
    mri_cmd = ['mri_convert', '-i',
               op.join(fs_dir, 'mri', 'aseg.mgz'), '-o', op.join(fs_dir, 'mri', 'aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    asegfile = op.join(fs_dir, 'mri', 'aseg.nii.gz')
    aseg = ni.load(asegfile).get_data().astype(np.uint32)
    idx = np.where((aseg == 4) |
                   (aseg == 43) |
                   (aseg == 11) |
                   (aseg == 50) |
                   (aseg == 31) |
                   (aseg == 63) |
                   (aseg == 10) |
                   (aseg == 49))
    er_mask = np.zeros(aseg.shape)
    er_mask[idx] = 1
    img = ni.Nifti1Image(er_mask, ni.load(
        asegfile).get_affine(), ni.load(asegfile).get_header())
    ni.save(img, op.join(fs_dir, 'mri', 'csf_mask.nii.gz'))
    del img

    # Convert whole brain mask
    mri_cmd = ['mri_convert', '-i', op.join(fs_dir, 'mri', 'brainmask.mgz'), '-o',
               op.join(fs_dir, 'mri', 'brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)
    mri_cmd = ['fslmaths', op.join(fs_dir, 'mri', 'brainmask.nii.gz'), '-bin',
               op.join(fs_dir, 'mri', 'brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)

    mri_cmd = ['mri_convert', '-i',
               op.join(fs_dir, 'mri', 'ribbon.mgz'), '-o', op.join(fs_dir, 'mri', 'ribbon.nii.gz')]
    subprocess.check_call(mri_cmd)

    print("[DONE]")


def crop_and_move_WM_and_GM(subject_id, subjects_dir):
    """Convert Freesurfer images back to original native space when NativeFreesurfer parcellation scheme is used.

    Parameters
    ----------
    subject_id : string
        Freesurfer subject id

    subjects_dir : string
        Freesurfer subjects dir
        (Typically ``/path/to/output_dir/freesurfer``)
    """
    fs_dir = op.join(subjects_dir, subject_id)

    #    print("Cropping and moving datasets to %s" % reg_path)

    # datasets to crop and move: (from, to)
    ds = [
        (op.join(fs_dir, 'mri', 'ribbon.nii.gz'), 'ribbon.nii.gz'),
        (op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz'), 'fsmask_1mm.nii.gz'),
        (op.join(fs_dir, 'mri', 'gmmask.nii.gz'), 'gmmask.nii.gz'),
        (op.join(fs_dir, 'mri', 'csf_mask.nii.gz'), 'csf_mask.nii.gz'),
        (op.join(fs_dir, 'mri', 'aparc+aseg.mgz'), 'aparc+aseg.native.nii.gz')
    ]

    for p in list(get_parcellation('NativeFreesurfer').keys()):
        if not op.exists(op.join(fs_dir, 'mri', p)):
            os.makedirs(op.join(fs_dir, 'mri', p))
        ds.append((op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' % p),
                   op.join(fs_dir, 'mri', p, 'ROIv_HR_th.nii.gz')))
        ds.append((op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' %
                           p), 'ROIv_HR_th_%s.nii.gz' % p))

    orig = op.join(fs_dir, 'mri', 'rawavg.mgz')

    for d in ds:
        print("Processing %s:" % d[0])

        # does it exist at all?
        if not op.exists(d[0]):
            raise Exception('File %s does not exist.' % d[0])
        # reslice to original volume because the roi creation with freesurfer
        # changed to 256x256x256 resolution
        #        mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, d[0], d[1])
        #        runCmd( mri_cmd,log )
        mri_cmd = ['mri_convert', '-rl', orig,
                   '-rt', 'nearest', d[0], '-nc', d[1]]
        subprocess.check_call(mri_cmd)

    ds = [(op.join(fs_dir, 'mri', 'fsmask_1mm_eroded.nii.gz'), 'wm_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'csf_mask_eroded.nii.gz'), 'csf_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask_eroded.nii.gz'), 'brain_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask.nii.gz'), 'brain_mask.nii.gz')]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig,
                       '-rt', 'nearest', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)

    ds = [(op.join(fs_dir, 'mri', 'T1.nii.gz'), 'T1.nii.gz'),
          (op.join(fs_dir, 'mri', 'brain.nii.gz'), 'brain.nii.gz'),
          ]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig,
                       '-rt', 'cubic', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)
