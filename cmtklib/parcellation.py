# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMTK Parcellation functions
"""

import os
import re
import os.path as op
import pkg_resources
import subprocess
import shutil
import nibabel as ni
import networkx as nx
import numpy as np
import math

from scipy import ndimage

import scipy.ndimage.morphology as nd
import sys
from time import time, localtime, strftime
from nipype.interfaces.base import traits, BaseInterfaceInputSpec, TraitedSpec, BaseInterface, Directory, File, InputMultiPath, OutputMultiPath


from nipype.utils.logger import logging
iflogger = logging.getLogger('nipype.interface')

try:
    import scipy.ndimage.morphology as nd
except ImportError:
    raise Exception('Need scipy for binary erosion of white matter and CSF masks')

def erode_mask(maskFile):
    """ Erodes the mask """
    # Define erosion mask
    imerode = nd.binary_erosion
    se = np.zeros( (3,3,3) )
    se[1,:,1] = 1; se[:,1,1] = 1; se[1,1,:] = 1

    # Erode mask
    mask = ni.load( maskFile ).get_data().astype( np.uint32 )
    er_mask = np.zeros( mask.shape )
    idx = np.where( (mask == 1) )
    er_mask[idx] = 1
    er_mask = imerode(er_mask,se)
    er_mask = imerode(er_mask,se)
    img = ni.Nifti1Image(er_mask, ni.load( maskFile ).get_affine(), ni.load( maskFile ).get_header())
    ni.save(img, op.abspath('%s_eroded.nii.gz' % os.path.splitext(op.splitext(op.basename(maskFile))[0])[0]))

class Erode_inputspec(BaseInterfaceInputSpec):
    in_file = File(exists=True)

class Erode_outputspec(TraitedSpec):
    out_file = File(exists=True)

class Erode(BaseInterface):
    input_spec = Erode_inputspec
    output_spec = Erode_outputspec

    def _run_interface(self, runtime):
        erode_mask(self.inputs.in_file)
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = op.abspath('%s_eroded.nii.gz' % os.path.splitext(op.splitext(op.basename(self.inputs.in_file))[0])[0])
        return outputs

class ParcellateHippocampalSubfieldsInputSpec(BaseInterfaceInputSpec):
    subjects_dir = Directory(mandatory=True, desc='Freesurfer main directory')
    subject_id = traits.String(mandatory=True, desc='Subject ID')

class ParcellateHippocampalSubfieldsOutputSpec(TraitedSpec):
    lh_hipposubfields = File(desc='Left hemisphere hippocampal subfields file')
    rh_hipposubfields = File(desc='Right hemisphere hippocampal subfields  file')

class ParcellateHippocampalSubfields(BaseInterface):
    input_spec = ParcellateHippocampalSubfieldsInputSpec
    output_spec = ParcellateHippocampalSubfieldsOutputSpec

    def _run_interface(self,runtime):
        iflogger.info("Parcellation of hippocampal subfields (FreeSurfer)")
        iflogger.info("=============================================")

        fs_string = 'export SUBJECTS_DIR=' + self.inputs.subjects_dir
        iflogger.info('- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(self.inputs.subjects_dir))

        reconall_cmd = fs_string + '; recon-all -no-isrunning -s "%s" -hippocampal-subfields-T1 ' % (self.inputs.subject_id)
        #reconall_cmd = [fs_string , ";" , "recon-all" , "-no-isrunning" , "-s" , "%s"% (self.inputs.subject_id) , "-hippocampal-subfields-T1" ]

        iflogger.info('Processing cmd: %s' % reconall_cmd)

        process = subprocess.Popen(reconall_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        #subprocess.check_call(reconall_cmd)

        #cmd = ['recon-all', '-s', self.inputs.subject_id, '-hippocampal-subfields-T1']

        #subprocess.check_call(cmd)
        iflogger.info(proc_stdout)

        mov = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','lh.hippoSfLabels-T1.v10.mgz')
        targ = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','orig/001.mgz')
        out = op.abspath('lh_subFields.nii.gz')
        cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov,targ,out)

        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        mov = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','rh.hippoSfLabels-T1.v10.mgz')
        targ = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','orig/001.mgz')
        out = op.abspath('rh_subFields.nii.gz')
        cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov,targ,out)

        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
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
    input_spec = ParcellateBrainstemStructuresInputSpec
    output_spec = ParcellateBrainstemStructuresOutputSpec

    def _run_interface(self,runtime):
        iflogger.info("Parcellation of brainstem structures (FreeSurfer)")
        iflogger.info("=============================================")

        fs_string = 'export SUBJECTS_DIR=' + self.inputs.subjects_dir
        iflogger.info('- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(self.inputs.subjects_dir))

        reconall_cmd = fs_string + '; recon-all -no-isrunning -s "%s" -brainstem-structures ' % (self.inputs.subject_id)
        #reconall_cmd = [fs_string , ";" , "recon-all" , "-no-isrunning" , "-s" , "%s"% (self.inputs.subject_id) , "-hippocampal-subfields-T1" ]

        iflogger.info('Processing cmd: %s' % reconall_cmd)

        process = subprocess.Popen(reconall_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        mov = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','brainstemSsLabels.v10.mgz')
        targ = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','orig/001.mgz')
        out = op.abspath('brainstem.nii.gz')
        cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov,targ,out)

        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        iflogger.info('Done')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['brainstem_structures'] = op.abspath('brainstem.nii.gz')
        return outputs

class CombineParcellationsInputSpec(BaseInterfaceInputSpec):
    input_rois = InputMultiPath(File(exists=True))
    lh_hippocampal_subfields = File(' ')
    rh_hippocampal_subfields = File(' ')
    brainstem_structures = File(' ')
    thalamus_nuclei = File(' ')
    create_colorLUT = traits.Bool(True)
    create_graphml = traits.Bool(True)
    subjects_dir = Directory(desc='Freesurfer subjects dir')
    subject_id = traits.Str(desc='Freesurfer subject id')

class CombineParcellationsOutputSpec(TraitedSpec):
    output_rois = OutputMultiPath(File(exists=True))
    colorLUT_files = OutputMultiPath(File(exists=True))
    graphML_files = OutputMultiPath(File(exists=True))

class CombineParcellations(BaseInterface):
    input_spec = CombineParcellationsInputSpec
    output_spec = CombineParcellationsOutputSpec

    def ismember(a, b):
        bind = {}
        for i, elt in enumerate(b):
            if elt not in bind:
                bind[elt] = i
        return [bind.get(itm, None) for itm in a]  # None can be replaced by any other "not in b" value

    def _run_interface(self,runtime):

        # Freesurfer IDs for subcortical structures
        left_subcIds = np.array([10, 11, 12, 13, 26, 18, 17])
        left_subcIds_colors_r = np.array([0, 122, 236, 12, 255, 103, 220])
        left_subcIds_colors_g = np.array([118, 186, 13, 48, 165, 255, 216])
        left_subcIds_colors_b = np.array([14, 220, 176, 255, 0, 255, 20])
        left_subcort_names = ["Left-Thalamus_Proper","Left-Caudate","Left-Putamen","Left-Pallidum","Left-Accumbens_area","Left-Amygdala","Left-Hippocampus"]

        right_subcIds = np.array([49, 50, 51, 52, 58, 54, 53])
        right_subcIds_colors_r = np.array([0, 122, 236, 12, 255, 103, 220])
        right_subcIds_colors_g = np.array([118, 186, 13, 48, 165, 255, 216])
        right_subcIds_colors_b = np.array([14, 220, 176, 255, 0, 255, 20])
        right_subcort_names = ["Right-Thalamus_Proper","Right-Caudate","Right-Putamen","Right-Pallidum","Right-Accumbens_area","Right-Amygdala","Right-Hippocampus"]

        #Amygdala and hippocampus swapped between Lausanne2008 and Lausanne2018
        left_subcIds_2008 = np.array([10, 11, 12, 13, 26, 17, 18])
        left_subcIds_2008_colors_r = np.array([0, 122, 236, 12, 255, 220, 103])
        left_subcIds_2008_colors_g = np.array([118, 186, 13, 48, 165, 216, 255])
        left_subcIds_2008_colors_b = np.array([14, 220, 176, 255, 0, 20, 255])
        left_subcort_2008_names = ["Left-Thalamus_Proper","Left-Caudate","Left-Putamen","Left-Pallidum","Left-Accumbens_area","Left-Hippocampus","Left-Amygdala"]

        right_subcIds_2008 = np.array([49, 50, 51, 52, 58, 53, 54])
        right_subcIds_2008_colors_r = np.array([0, 122, 236, 12, 255, 220, 103])
        right_subcIds_2008_colors_g = np.array([118, 186, 13, 48, 165, 216, 255])
        right_subcIds_2008_colors_b = np.array([14, 220, 176, 255, 0, 20, 255])
        right_subcort_2008_names = ["Right-Thalamus_Proper","Right-Caudate","Right-Putamen","Right-Pallidum","Right-Accumbens_area","Right-Hippocampus","Right-Amygdala"]

        # Thalamic Nuclei
        left_thalNuclei  = np.array([1, 2, 3, 4, 5, 6, 7])
        left_thalNuclei_colors_r = np.array([255, 0, 255, 255, 0, 255, 0])
        left_thalNuclei_colors_g = np.array([0, 255, 255, 123, 255, 0, 0])
        left_thalNuclei_colors_b = np.array([0, 0, 0, 0, 255, 255, 255])
        left_thalNuclei_names = ["Left-Pulvinar","Left-Anterior","Left-Medio_Dorsal","Left-Ventral_Latero_Dorsal","Left-Central_Lateral-Lateral_Posterior-Medial_Pulvinar",
                                 "Left-Ventral_Anterior","Left-Ventral_Latero_Ventral"]

        right_thalNuclei = np.array([8, 9, 10, 11, 12, 13, 14])
        right_thalNuclei_colors_r = np.array([255, 0, 255, 255, 0, 255, 0])
        right_thalNuclei_colors_g = np.array([0, 255, 255, 123, 255, 0, 0])
        right_thalNuclei_colors_b = np.array([0, 0, 0, 0, 255, 255, 255])
        right_thalNuclei_names = ["Right-Pulvinar","Right-Anterior","Right-Medio_Dorsal","Right-Ventral_Latero_Dorsal","Right-Central_Lateral-Lateral_Posterior-Medial_Pulvinar",
                                  "Right-Ventral_Anterior","Right-Ventral_Latero_Ventral"]


        # Hippocampus subfields
        hippo_subf = np.array([203, 204, 205, 206, 208, 209, 210, 211, 212, 214, 215, 226])
        hippo_subf_colors_r = np.array([255, 64, 0, 255, 0, 196, 32, 128, 204, 128, 128, 170])
        hippo_subf_colors_g = np.array([255, 0, 0, 0, 128, 160, 200, 255, 153, 0, 32, 170 ])
        hippo_subf_colors_b = np.array([0, 64, 255, 0, 0, 128, 255, 128, 204, 0, 255, 255 ])
        left_hippo_subf_names  = ["Left-Hippocampus_Parasubiculum","Left-Hippocampus_Presubiculum","Left-Hippocampus_Subiculum","Left-Hippocampus_CA1","Left-Hippocampus_CA3","Left-Hippocampus_CA4",
                                  "Left-Hippocampus_GCDG","Left-Hippocampus_HATA","Left-Hippocampus_Fimbria","Left-Hippocampus_Molecular_layer_HP","Left-Hippocampus_Hippocampal_fissure",
                                  "Left-Hippocampus_Tail"]
        right_hippo_subf_names = ["Right-Hippocampus_Parasubiculum","Right-Hippocampus_Presubiculum","Right-Hippocampus_Subiculum","Right-Hippocampus_CA1","Right-Hippocampus_CA3","Right-Hippocampus_CA4",
                                  "Right-Hippocampus_GCDG","Right-Hippocampus_HATA","Right-Hippocampus_Fimbria","Right-Hippocampus_Molecular_layer_HP","Right-Hippocampus_Hippocampal_fissure",
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
        ventricle3 = 14;

        # Hypothalamus
        hypothal_colors_r = 204
        hypothal_colors_g = 182
        hypothal_colors_b = 142
        left_hypothal_names  = ["Left-Hypothalamus"]
        right_hypothal_names = ["Right-Hypothalamus"]

        # BrainStem Parcellation
        brainstem = np.array([173, 174, 175, 178 ])
        brainstem_colors_r = np.array([242, 206, 119, 142])
        brainstem_colors_g = np.array([104, 195, 159, 182])
        brainstem_colors_b = np.array([76, 58, 176, 0])
        brainstem_names = ["Brain_Stem-Midbrain","Brain_Stem-Pons","Brain_Stem-Medulla","Brain_Stem-SCP"]

        lh_subfield_defined = False
        # Reading Subfields Images
        try:
            Vsublh = ni.load(self.inputs.lh_hippocampal_subfields)
            Isublh = Vsublh.get_data()
            lh_subfield_defined = True
        except TypeError:
            print('Subfields image (Left hemisphere) not provided')

        rh_subfield_defined = False
        try:
            Vsubrh =  ni.load(self.inputs.rh_hippocampal_subfields)
            Isubrh = Vsubrh.get_data()
            rh_subfield_defined = True
        except TypeError:
            print('Subfields image (Right hemisphere) not provided')


        thalamus_nuclei_defined = False
        # Reading  Nuclei
        try:
            Vthal = ni.load(self.inputs.thalamus_nuclei)
            Ithal = Vthal.get_data()

            thalamus_nuclei_defined = True
        except TypeError:
            print('Thalamic nuclei image not provided')

        brainstem_defined = False
        # Reading Stem Image
        try:
            Vstem = ni.load(self.inputs.brainstem_structures)
            Istem = Vstem.get_data()
            indstem = np.where(Istem > 0)
            brainstem_defined = True
        except TypeError:
            print('Brain stem image not provided')

        #Annot files for creating colorLUT and graphml files
        rh_annot_files = ['rh.lausanne2008.scale1.annot', 'rh.lausanne2008.scale2.annot', 'rh.lausanne2008.scale3.annot', 'rh.lausanne2008.scale4.annot', 'rh.lausanne2008.scale5.annot']
    	lh_annot_files = ['lh.lausanne2008.scale1.annot', 'lh.lausanne2008.scale2.annot', 'lh.lausanne2008.scale3.annot', 'lh.lausanne2008.scale4.annot', 'lh.lausanne2008.scale5.annot']

        f_colorLUT = None

        print("create color look up table : ",self.inputs.create_colorLUT)

        for roi_index, roi in enumerate(self.inputs.input_rois):
            # colorLUT creation if enabled
            if self.inputs.create_colorLUT:
                outprefixName = roi.split(".")[0]
                outprefixName = outprefixName.split("/")[-1:][0]
                colorLUT_file = op.abspath('{}_FreeSurferColorLUT.txt'.format(outprefixName))
                print("Create colorLUT file as %s" % colorLUT_file)
                f_colorLUT = open(colorLUT_file,'w+')
                time_now = strftime("%a, %d %b %Y %H:%M:%S",localtime())
                hdr_lines = ['#$Id: {}_FreeSurferColorLUT.txt {} \n \n'.format(outprefixName,time_now),
                            '{:<4} {:<55} {:>3} {:>3} {:>3} {} \n \n'.format("#No.","Label Name:","R","G","B","A")]
                f_colorLUT.writelines (hdr_lines)
                del hdr_lines

            # Create GraphML if enabled
            if self.inputs.create_graphml:
                outprefixName = roi.split(".")[0]
                outprefixName = outprefixName.split("/")[-1:][0]
                graphML_file = op.abspath('{}.graphml'.format(outprefixName))
                print("Create graphML_file as %s" % graphML_file)
                f_graphML = open(graphML_file,'w+')

                hdr_lines = ['{} \n'.format('<?xml version="1.0" encoding="utf-8"?>'),
                             '{} \n'.format('<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">'),
                             '{} \n'.format('  <key attr.name="dn_region" attr.type="string" for="node" id="d0" />'),
                             '{} \n'.format('  <key attr.name="dn_fsname" attr.type="string" for="node" id="d1" />'),
                             '{} \n'.format('  <key attr.name="dn_hemisphere" attr.type="string" for="node" id="d2" />'),
                             '{} \n'.format('  <key attr.name="dn_multiscaleID" attr.type="int" for="node" id="d3" />'),
                             '{} \n'.format('  <key attr.name="dn_name" attr.type="string" for="node" id="d4" />'),
                             '{} \n'.format('  <key attr.name="dn_fsID" attr.type="int" for="node" id="d5" />'),
                             '{} \n'.format('  <graph edgedefault="undirected" id="">'),]
                f_graphML.writelines (hdr_lines)
                del hdr_lines

            # Reading Cortical Parcellation
            V = ni.load(roi)
            I = V.get_data()

            # Replacing the brain stem (Stem is replaced by its own parcellation. Mismatch between both global volumes, mainly due to partial volume effect in the global stem parcellation)
            indrep = np.where(I == 16)
            I[indrep] = 0

            #Dilate third ventricle and intersect with right and left ventral DC to get voxels of left and right hypothalamus
            tmp = np.zeros(I.shape)
            indV = np.where(I == ventricle3)
            tmp[indV] = 1

            thirdV = op.abspath('{}.nii.gz'.format("ventricle3"))
            hdr = V.get_header()
            hdr2 = hdr.copy()
            hdr2.set_data_dtype(np.int16)
            print("Save output image to %s" % thirdV)
            img = ni.Nifti1Image(tmp, V.get_affine(), hdr2)
            ni.save(img, thirdV)

            thirdV_dil = op.abspath('{}_dil.nii.gz'.format("ventricle3"))
            fslmaths_cmd = 'fslmaths %s -kernel sphere 5 -dilD %s' % (thirdV,thirdV_dil)
            print("RUN")
            print(fslmaths_cmd)
            process = subprocess.Popen(fslmaths_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            proc_stdout = process.communicate()[0].strip()

            tmp = ni.load(thirdV_dil).get_data()
            indrhypothal = np.where((tmp == 1) & (I == right_ventral))
            indlhypothal = np.where((tmp == 1) & (I == left_ventral))
            del(tmp)

            ## Processing Right Hemisphere
            # Relabelling Right hemisphere
            It = np.zeros(I.shape,dtype=np.int16)
            ind = np.where((I >= 2000) & (I < 3000))
            It[ind] = (I[ind] - 2000)
            nlabel = It.max()

            # nlabel = rh_annot[2].size()


            print("nlabel %i"%(int(nlabel)))

            #ColorLUT (cortical)
            if self.inputs.create_colorLUT or self.inputs.create_graphml:
                f_colorLUT.write("# Right Hemisphere. Cortical Structures \n")
                outprefixName = roi.split(".")[0]
                outprefixName = outprefixName.split("/")[-1:][0]
                for elem in outprefixName.split("_"):
                    if "scale" in elem:
                        scale = elem
                rh_annot_file = 'rh.lausanne2008.%s.annot'%scale
                print("Load %s"%rh_annot_file)
                rh_annot = ni.freesurfer.io.read_annot(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'label',rh_annot_file))
                rgb_table = rh_annot[1][1:,0:3]
                roi_names = rh_annot[2][1:]
                #roi_labels = rh_annot[0][1:]

                lines = []
                for label, name in enumerate(roi_names):
                    name = 'ctx-rh-{}'.format(name)
                    if self.inputs.create_colorLUT:
                        r = rgb_table[label,0]
                        g = rgb_table[label,1]
                        b = rgb_table[label,2]

                        if label == 0:
                            r = 0
                            g = 0
                            b = 0

                        f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(label+1,name,r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(label+1)),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("cortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%(name)),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("right")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(label+1)),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(name)),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(label+2000+1))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)


                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            # Relabelling Thalamic Nuclei
            if thalamus_nuclei_defined:
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Right Hemisphere. Subcortical Structures (Thalamic Nuclei) \n")

                newLabels = np.arange(nlabel+1,nlabel+1+right_thalNuclei.shape[0])
                print(newLabels)

                i=0
                for lab in right_thalNuclei:
                    print("update right thalamic nucleus label (%i -> %i)"%(lab,newLabels[i]))

                    if self.inputs.create_colorLUT:
                        r = right_thalNuclei_colors_r[i]
                        g = right_thalNuclei_colors_g[i]
                        b = right_thalNuclei_colors_b[i]
                        f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),right_thalNuclei_names[i],r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%("thalamus")),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("right")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(right_thalNuclei_names[i])),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(49))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                    ind = np.where(Ithal == lab)
                    It[ind] = newLabels[i]
                    i += 1
                nlabel = It.max()

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            # Relabelling Subcortical Structures
            if self.inputs.create_colorLUT:
                f_colorLUT.write("# Right Hemisphere. Subcortical Structures \n")


            if thalamus_nuclei_defined:
                right_subc_labels = right_subcIds[1:]
                right_subcort_names = right_subcort_names[1:]
                newLabels = np.arange(nlabel+1,nlabel+1+right_subcIds[1:].shape[0])
            elif not (thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined)):
                right_subc_labels = right_subcIds_2008
                right_subcort_names = right_subcort_2008_names
                newLabels = np.arange(nlabel+1,nlabel+1+right_subcIds_2008.shape[0])
            else:
                right_subc_labels = right_subcIds
                newLabels = np.arange(nlabel+1,nlabel+1+right_subcIds.shape[0])

            i=0
            for lab in right_subc_labels:
                print("update right subcortical label (%i -> %i)"%(lab,newLabels[i]))

                if self.inputs.create_colorLUT:
                    r = right_subcIds_colors_r[i]
                    g = right_subcIds_colors_g[i]
                    b = right_subcIds_colors_b[i]
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),right_subcort_names[i],r,g,b))

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                 '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d1">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d2">%s</data>'%("right")),
                                 '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                 '{} \n'.format('      <data key="d4">%s</data>'%(right_subcort_names[i])),
                                 '{} \n'.format('      <data key="d5">%i</data>'%(int(lab))),
                                 '{} \n'.format('    </node>')]
                    f_graphML.writelines(node_lines)

                ind = np.where(I == lab)
                It[ind] = newLabels[i]
                i += 1
            nlabel = It.max()

            if self.inputs.create_colorLUT:
                f_colorLUT.write("\n")

            # Relabelling Subfields
            if rh_subfield_defined:
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Right Hemisphere. Subcortical Structures (Hippocampal Subfields) \n")

                newLabels = np.arange(nlabel+1,nlabel+1+hippo_subf.shape[0])
                i=0
                for lab in hippo_subf:
                    print("update right hippo subfield label (%i -> %i)"%(lab,newLabels[i]))

                    if self.inputs.create_colorLUT:
                        # if len(ind) > 0:
                            r = hippo_subf_colors_r[i]
                            g = hippo_subf_colors_g[i]
                            b = hippo_subf_colors_b[i]
                            f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),right_hippo_subf_names[i],r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%("hippocampus")),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("right")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(right_hippo_subf_names[i])),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(lab))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                    ind = np.where(Isubrh == lab)
                    It[ind] = newLabels[i]
                    i += 1
                nlabel = It.max()

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Right VentralDC
                newLabels = np.arange(nlabel+1,nlabel+2)
                print("update right ventral DC label (%i -> %i)"%(right_ventral,newLabels[0]))
                ind = np.where(I == right_ventral)
                It[ind] = newLabels[0]
                nlabel = It.max()

                #ColorLUT (right ventral DC)
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Right Hemisphere. Ventral Diencephalon \n")
                    r = right_ventral_colors_r
                    g = right_ventral_colors_g
                    b = right_ventral_colors_b
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[0]),right_ventral_names[0],r,g,b))
                    f_colorLUT.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d1">%s</data>'%("ventral-diencephalon")),
                                 '{} \n'.format('      <data key="d2">%s</data>'%("right")),
                                 '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d4">%s</data>'%(right_ventral_names[0])),
                                 '{} \n'.format('      <data key="d5">%i</data>'%(int(right_ventral))),
                                 '{} \n'.format('    </node>')]
                    f_graphML.writelines(node_lines)

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Right Hypothalamus
                newLabels = np.arange(nlabel+1,nlabel+2)
                print("update right hypothalamus label (%i -> %i)"%(right_ventral,newLabels[0]))
                It[indrhypothal] = newLabels[0]
                nlabel = It.max()

                #ColorLUT (right hypothalamus)
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Right Hemisphere. Hypothalamus \n")
                    r = hypothal_colors_r
                    g = hypothal_colors_g
                    b = hypothal_colors_b
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[0]),right_hypothal_names[0],r,g,b))
                    f_colorLUT.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d1">%s</data>'%("hypothalamus")),
                                 '{} \n'.format('      <data key="d2">%s</data>'%("right")),
                                 '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d4">%s</data>'%(right_hypothal_names[0])),
                                 '{} \n'.format('      <data key="d5">%i</data>'%(-1)),
                                 '{} \n'.format('    </node>')]
                    f_graphML.writelines(node_lines)

            ## Processing Left Hemisphere
            # Relabelling Left hemisphere
            ind = np.where((I > 1000) & (I <2000))
            It[ind] = (I[ind] - 1000 + nlabel)
            old_nlabel = nlabel
            nlabel = It.max()

            #ColorLUT (cortical)
            if self.inputs.create_colorLUT or self.inputs.create_graphml:
                f_colorLUT.write("# Left Hemisphere. Cortical Structures \n")
                outprefixName = roi.split(".")[0]
                outprefixName = outprefixName.split("/")[-1:][0]
                for elem in outprefixName.split("_"):
                    if "scale" in elem:
                        scale = elem
                lh_annot_file = 'lh.lausanne2008.%s.annot'%scale
                print("Load %s"%lh_annot_file)
                lh_annot = ni.freesurfer.io.read_annot(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'label',lh_annot_file))
                rgb_table = lh_annot[1][1:,0:3]
                roi_names = lh_annot[2][1:]

                lines = []
                for label, name in enumerate(roi_names):
                    name = 'ctx-lh-{}'.format(name)

                    if self.inputs.create_colorLUT:
                        r = rgb_table[label,0]
                        g = rgb_table[label,1]
                        b = rgb_table[label,2]

                        if label == 0:
                            r = 0
                            g = 0
                            b = 0

                        f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(label+old_nlabel+1),name,r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(label+old_nlabel+1))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("cortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%(name)),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("left")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(label+old_nlabel+1))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(name)),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(label + 1000 - old_nlabel))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            # Relabelling Thalamic Nuclei
            if thalamus_nuclei_defined:
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Left Hemisphere. Subcortical Structures (Thalamic Nuclei) \n")

                newLabels = np.arange(nlabel+1,nlabel+1+left_thalNuclei.shape[0])
                i=0
                for lab in left_thalNuclei:
                    print("update left thalamic nucleus label (%i -> %i)"%(lab,newLabels[i]))

                    if self.inputs.create_colorLUT:
                        r = left_thalNuclei_colors_r[i]
                        g = left_thalNuclei_colors_g[i]
                        b = left_thalNuclei_colors_b[i]
                        f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),left_thalNuclei_names[i],r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%("thalamus")),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("left")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(left_thalNuclei_names[i])),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(10))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                    ind = np.where(Ithal == lab)
                    It[ind] = newLabels[i]
                    i += 1
                nlabel = It.max()

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            # Relabelling Subcortical Structures
            if self.inputs.create_colorLUT:
                f_colorLUT.write("# Left Hemisphere. Subcortical Structures \n")



            if thalamus_nuclei_defined:
                left_subc_labels = left_subcIds[1:]
                left_subcort_names = left_subcort_names[1:]
                newLabels = np.arange(nlabel+1,nlabel+1+left_subcIds[1:].shape[0])
            elif not (thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined)):
                left_subc_labels = left_subcIds_2008
                left_subcort_names = left_subcort_2008_names
                newLabels = np.arange(nlabel+1,nlabel+1+left_subcIds_2008.shape[0])
            else:
                left_subc_labels = left_subcIds
                newLabels = np.arange(nlabel+1,nlabel+1+left_subcIds.shape[0])

            i=0
            for lab in left_subc_labels:
                print("update left subcortical label (%i -> %i)"%(lab,newLabels[i]))

                if self.inputs.create_colorLUT:
                    r = left_subcIds_colors_r[i]
                    g = left_subcIds_colors_g[i]
                    b = left_subcIds_colors_b[i]
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),left_subcort_names[i],r,g,b))

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                 '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d1">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d2">%s</data>'%("left")),
                                 '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                 '{} \n'.format('      <data key="d4">%s</data>'%(left_subcort_names[i])),
                                 '{} \n'.format('      <data key="d5">%i</data>'%(int(lab))),
                                 '{} \n'.format('    </node>')]
                    f_graphML.writelines(node_lines)

                ind = np.where(I == lab)
                It[ind] = newLabels[i]
                i += 1
            nlabel = It.max()

            if self.inputs.create_colorLUT:
                f_colorLUT.write("\n")

            # Relabelling Subfields
            if lh_subfield_defined:
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Left Hemisphere. Subcortical Structures (Hippocampal Subfields) \n")

                newLabels = np.arange(nlabel+1,nlabel+1+hippo_subf.shape[0])
                i=0
                for lab in hippo_subf:
                    print("update left hippo subfield label (%i -> %i)"%(lab,newLabels[i]))

                    if self.inputs.create_colorLUT:
                        r = hippo_subf_colors_r[i]
                        g = hippo_subf_colors_g[i]
                        b = hippo_subf_colors_b[i]
                        f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),left_hippo_subf_names[i],r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%("hippocampus")),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("left")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(left_hippo_subf_names[i])),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(lab))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                    ind = np.where(Isublh == lab)
                    It[ind] = newLabels[i]
                    i += 1
                nlabel = It.max()
                newIds_LH_subFields = newLabels

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Left VentralDC
                newLabels = np.arange(nlabel+1,nlabel+2)
                print("update left ventral DC label (%i -> %i)"%(left_ventral,newLabels[0]))
                ind = np.where(I == left_ventral)
                It[ind] = newLabels[0]
                nlabel = It.max()
                newIds_LH_ventralDC = newLabels;

                #ColorLUT (left ventral DC)
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Left Hemisphere. Ventral Diencephalon \n")
                    r = left_ventral_colors_r
                    g = left_ventral_colors_g
                    b = left_ventral_colors_b
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[0]),left_ventral_names[0],r,g,b))
                    f_colorLUT.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d1">%s</data>'%("ventral-diencephalon")),
                                 '{} \n'.format('      <data key="d2">%s</data>'%("left")),
                                 '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d4">%s</data>'%(left_ventral_names[0])),
                                 '{} \n'.format('      <data key="d5">%i</data>'%(int(left_ventral))),
                                 '{} \n'.format('    </node>')]
                    f_graphML.writelines(node_lines)

            if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
                # Relabelling Left Hypothalamus
                newLabels = np.arange(nlabel+1,nlabel+2)
                print("update left hypothalamus label (%i -> %i)"%(-1,newLabels[0]))
                It[indlhypothal] = newLabels[0]
                nlabel = It.max()

                #ColorLUT (right hypothalamus)
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Left Hemisphere. Hypothalamus \n")
                    r = hypothal_colors_r
                    g = hypothal_colors_g
                    b = hypothal_colors_b
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[0]),left_hypothal_names[0],r,g,b))
                    f_colorLUT.write("\n")

                if self.inputs.create_graphml:
                    node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                 '{} \n'.format('      <data key="d1">%s</data>'%("hypothalamus")),
                                 '{} \n'.format('      <data key="d2">%s</data>'%("left")),
                                 '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[0]))),
                                 '{} \n'.format('      <data key="d4">%s</data>'%(left_hypothal_names[0])),
                                 '{} \n'.format('      <data key="d5">%i</data>'%(-1)),
                                 '{} \n'.format('    </node>')]
                    f_graphML.writelines(node_lines)

            # Relabelling Brain Stem
            if brainstem_defined:
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Brain Stem Structures \n")

                newLabels = np.arange(nlabel+1,nlabel+1+brainstem.shape[0])
                i=0
                for lab in brainstem:
                    print("update brainstem parcellation label (%i -> %i)"%(lab,newLabels[i]))

                    if self.inputs.create_colorLUT:
                        r = brainstem_colors_r[i]
                        g = brainstem_colors_g[i]
                        b = brainstem_colors_b[i]
                        f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[i]),brainstem_names[i],r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%("brainstem")),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("central")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[i]))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%(brainstem_names[i])),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(lab))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                    ind = np.where(Istem == lab)
                    It[ind] = newLabels[i]
                    i += 1
                nlabel = It.max()

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")
            else:
                if self.inputs.create_colorLUT:
                    f_colorLUT.write("# Brain Stem \n")

                newLabels = np.arange(nlabel+1,nlabel+2)
                It[indrep] = newLabels[0]

                print("update brainstem parcellation label (%i -> %i)"%(lab,newLabels[0]))

                if self.inputs.create_colorLUT:
                    r = 119
                    g = 159
                    b = 176
                    f_colorLUT.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(newLabels[0]),'brainstem',r,g,b))

                    if self.inputs.create_graphml:
                        node_lines = ['{} \n'.format('    <node id="%i">'%(int(newLabels[0]))),
                                     '{} \n'.format('      <data key="d0">%s</data>'%("subcortical")),
                                     '{} \n'.format('      <data key="d1">%s</data>'%("brainstem")),
                                     '{} \n'.format('      <data key="d2">%s</data>'%("central")),
                                     '{} \n'.format('      <data key="d3">%i</data>'%(int(newLabels[0]))),
                                     '{} \n'.format('      <data key="d4">%s</data>'%("brainstem")),
                                     '{} \n'.format('      <data key="d5">%i</data>'%(int(lab))),
                                     '{} \n'.format('    </node>')]
                        f_graphML.writelines(node_lines)

                nlabel = It.max()

                if self.inputs.create_colorLUT:
                    f_colorLUT.write("\n")

            # Fix negative values
            It[It<0] = 0

            # Saving the new parcellation
            outprefixName = roi.split(".")[0]
            outprefixName = outprefixName.split("/")[-1:][0]
            output_roi = op.abspath('{}_final.nii.gz'.format(outprefixName))
            hdr = V.get_header()
            hdr2 = hdr.copy()
            hdr2.set_data_dtype(np.int16)
            print("Save output image to %s" % output_roi)
            img = ni.Nifti1Image(It, V.get_affine(), hdr2)
            ni.save(img, output_roi)

            if self.inputs.create_colorLUT:
                f_colorLUT.close()

            if self.inputs.create_graphml:
                bottom_lines = ['{} \n'.format('  </graph>'),
                             '{} \n'.format('</graphml>'),]
                f_graphML.writelines(bottom_lines)
                f_graphML.close()

        # Refine aparc+aseg.mgz with new subcortical and/or structures (if any)
        if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
            orig = op.join(fs_dir, 'mri', 'orig', '001.mgz')
            aparcaseg_fs = op.join(fs_dir, 'mri', 'aparc+aseg.mgz')
            tmp_aparcaseg_fs = op.join(fs_dir, 'tmp', 'aparc+aseg.mgz')
            aparcaseg_native = op.join(fs_dir, 'tmp', 'aparc+aseg.nii.gz')

            shutil.copyfile(aparcaseg_fs,tmp_aparcaseg_fs)

            mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'nearest', tmp_aparcaseg_fs, '-nc', aparcaseg_native]
            subprocess.check_call(mri_cmd)

            aparcaseg_data = ni.load(aparcaseg_native)

            # Thalamus
            if thalamus_nuclei_defined :

            # Hippocampal subfields
            if (lh_subfield_defined and rh_subfield_defined):

            # Brainstem
            if brainstem_defined:

        for d in ds:
            print("Processing %s:" % d[0])

            # does it exist at all?
            if not op.exists(d[0]):
                raise Exception('File %s does not exist.' % d[0])
            # reslice to original volume because the roi creation with freesurfer
            # changed to 256x256x256 resolution
            #mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, d[0], d[1])
            #runCmd( mri_cmd,log )


        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_rois'] = self._gen_outfilenames('ROIv_HR_th','_final.nii.gz')
        outputs['colorLUT_files'] = self._gen_outfilenames('ROIv_HR_th','_FreeSurferColorLUT.txt')
        outputs['graphML_files'] = self._gen_outfilenames('ROIv_HR_th','.graphml')
        return outputs

    def _gen_outfilenames(self, basename, posfix):
        filepaths = []
        for scale in get_parcellation('Lausanne2018').keys():
            filepaths.append(op.abspath(basename+'_'+scale+posfix))
        return filepaths

class ParcellateThalamusInputSpec(BaseInterfaceInputSpec):
    T1w_image = File(mandatory=True, desc='T1w image to be parcellated')
    bids_dir = Directory(desc='BIDS root directory')
    subject = traits.Str(desc='Subject id')
    session = traits.Str('',desc='Session id')
    template_image = File(mandatory=True, desc='Template T1w')
    thalamic_nuclei_maps = File(mandatory=True, desc='Probability maps of thalamic nuclei (4D image) in template space')
    subjects_dir = Directory(mandatory=True, desc='Freesurfer main directory')
    subject_id = traits.String(mandatory=True, desc='Subject ID')

class ParcellateThalamusOutputSpec(TraitedSpec):
    warped_image = File(desc='Template registered to T1w image (native)')
    inverse_warped_image = File(desc='Inverse warped template')
    max_prob_registered = File(desc='Max probability label image (native)')
    prob_maps_registered = File(desc='Probabilistic map of thalamus nuclei (native)')
    transform_file = File(desc='Transform file')
    warp_file = File(desc='Deformation file')
    thalamus_mask = File(desc='Thalamus mask')

class ParcellateThalamus(BaseInterface):
    input_spec = ParcellateThalamusInputSpec
    output_spec = ParcellateThalamusOutputSpec

    def _run_interface(self,runtime):
        iflogger.info("Parcellation of Thalamic Nuclei")
        iflogger.info("=============================================")

        # fs_string = 'export ANTSPATH=/usr/lib/ants/'
        fs_string = ''
        iflogger.info('- Input T1w image:\n  {}\n'.format(self.inputs.T1w_image))
        iflogger.info('- Template image:\n  {}\n'.format(self.inputs.template_image))
        iflogger.info('- Thalamic nuclei maps:\n  {}\n'.format(self.inputs.thalamic_nuclei_maps))

        # Moving aparc+aseg.mgz back to its original space for thalamic parcellation
        mov = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','aparc+aseg.mgz')
        targ = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','orig/001.mgz')
        out = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'tmp','aparc+aseg.nii.gz')
        # cmd = fs_string + '; mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov,targ,out)
        cmd = 'mri_vol2vol --mov "%s" --targ "%s" --regheader --o "%s" --no-save-reg --interp nearest' % (mov,targ,out)

        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        # Load aparc+aseg file in native space
        Vatlas_fn = out
        Vatlas = ni.load(Vatlas_fn)
        Ia = Vatlas.get_data()
        hdr = Vatlas.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)

        outprefixName = self.inputs.T1w_image.split(".")[0]
        outprefixName = outprefixName.split("/")[-1:][0]
        outprefixName = op.abspath('{}_Ind2temp'.format(outprefixName))

        # Register the template image image to the subject T1w image
        # cmd = fs_string + '; antsRegistrationSyN.sh -d 3 -f "%s" -m "%s" -t s -n "%i" -o "%s"' % (self.inputs.T1w_image,self.inputs.template_image,12,outprefixName)
        cmd = 'antsRegistrationSyN.sh -d 3 -f "%s" -m "%s" -t s -n "%i" -o "%s"' % (self.inputs.T1w_image,self.inputs.template_image,12,outprefixName)

        iflogger.info('Processing cmd: %s' % cmd)

        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        outprefixName = self.inputs.T1w_image.split(".")[0]
        outprefixName = outprefixName.split("/")[-1:][0]
        transform_file = op.abspath('{}_Ind2temp0GenericAffine.mat'.format(outprefixName))
        warp_file = op.abspath('{}_Ind2temp1Warp.nii.gz'.format(outprefixName))
        #transform_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_Ind2temp0GenericAffine.mat'
        #warp_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_Ind2temp1Warp.nii.gz'
        output_maps = op.abspath('{}_class-thalamus_probtissue.nii.gz'.format(outprefixName))
        jacobian_file = op.abspath('{}_class-thalamus_probtissue_jacobian.nii.gz'.format(outprefixName))

        # Compute and save jacobian
        # cmd = fs_string + '; CreateJacobianDeterminantImage 3 "%s" "%s" ' % (warp_file,jacobian_file)
        cmd = 'CreateJacobianDeterminantImage 3 "%s" "%s" ' % (warp_file,jacobian_file)

        iflogger.info('Processing cmd: %s' % cmd)
        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        # Propagate nuclei probability maps to subject T1w space using estimated transforms and deformation
        # cmd = fs_string + '; antsApplyTransforms --float -d 3 -e 3 -i "%s" -o "%s" -r "%s" -t "%s" -t "%s" -n BSpline[3]' % (self.inputs.thalamic_nuclei_maps,output_maps,self.inputs.T1w_image,warp_file,transform_file)
        cmd = 'antsApplyTransforms --float -d 3 -e 3 -i "%s" -o "%s" -r "%s" -t "%s" -t "%s" -n BSpline[3]' % (self.inputs.thalamic_nuclei_maps,output_maps,self.inputs.T1w_image,warp_file,transform_file)

        iflogger.info('Processing cmd: %s' % cmd)
        process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        iflogger.info(proc_stdout)

        iflogger.info('Correcting the volumes after the interpolation ')
        # Load jacobian file
        Ij = ni.load(jacobian_file).get_data()	# numpy.ndarray

        # Load probability maps in native space after applying estimated transform and deformation
        imgVspams = ni.load(output_maps)
        Vspams = imgVspams.get_data()	# numpy.ndarray
        Vspams[Vspams < 0] = 0
        Vspams[Vspams > 1] = 1

        Thresh = 0.05
        # Creating MaxProb
        Ispams = Vspams.copy()
        ind = np.where(Ispams < Thresh)
        Ispams[ind] = 0
        ind = np.where(np.sum(Ispams,axis=3) == 0)
        MaxProb = Ispams.argmax(axis=3) + 1
        MaxProb[ind] = 0;
        #?MaxProb = imfill(MaxProb,'holes');

        del Ispams

        debug_file = op.abspath('{}_class-thalamus_dtissue_after_ants.nii.gz'.format(outprefixName))
        print("Save output image to %s" % debug_file)
        img = ni.Nifti1Image(MaxProb, Vatlas.get_affine(), hdr2)
        ni.save(img, debug_file)

        # Take into account jacobian to correct the probability maps after interpolation
        Ispams = np.zeros(Vspams.shape)
        for nuc in np.arange(Vspams.shape[3]):
            tempImage = Vspams[:,:,:,nuc]
            T = np.multiply(tempImage,Ij)
            Ispams[:,:,:,nuc] = T / T.max()
        del tempImage, T, Vspams, Ij

        # Creating MaxProb
        ind = np.where(Ispams < Thresh)
        Ispams[ind] = 0
        ind = np.where(np.sum(Ispams,axis=3) == 0)
        MaxProb = Ispams.argmax(axis=3) + 1
        MaxProb[ind] = 0;
        #?MaxProb = imfill(MaxProb,'holes');

        debug_file = op.abspath('{}_class-thalamus_dtissue_after_jacobiancorr.nii.gz'.format(outprefixName))
        print("Save output image to %s" % debug_file)
        img = ni.Nifti1Image(MaxProb, Vatlas.get_affine(), hdr2)
        ni.save(img, debug_file)

        iflogger.info('Creating Thalamus mask from FreeSurfer aparc+aseg ')

        fs_string = 'export SUBJECTS_DIR=' + self.inputs.subjects_dir
        iflogger.info('- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(self.inputs.subjects_dir))

        #Extract indices of left/right thalamus mask from aparc+aseg volume
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
            id_sizes = np.array(ndimage.sum(array, id_regions, range(num_ids + 1)))
            area_mask = (id_sizes == 1)
            filtered_array[area_mask[id_regions]] = 0
            return filtered_array

        remove_isolated_points = True
        if remove_isolated_points:
            struct = np.ones((3,3,3))

            #struct = np.zeros((3,3,3))
            #struct[1,1,1] = 1

            # Left Hemisphere
            # Removing isolated points
            tempI = np.zeros(Ia.shape)
            tempI[indl] = 1;
            tempI = filter_isolated_cells(tempI,struct=struct)
            indl = np.where(tempI == 1);

            # Right Hemisphere
            # Removing isolated points
            tempI = np.zeros(Ia.shape)
            tempI[indr] = 1;
            tempI = filter_isolated_cells(tempI,struct=struct)
            indr = np.where(tempI == 1)

            del struct, tempI

        # Creating Thalamic Mask (1: Left, 2:Right)
        Ithal = np.zeros(Ia.shape)
        Ithal[indl]  = 1
        Ithal[indr] = 2

        del indl, indr

        #TODO: Masking according to csf
        # unzip_nifti([freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii.gz']);
        # Outfiles = Extract_brain([freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii'],[freesDir filesep subjId filesep 'tmp' filesep 'T1native.nii']);
        #
        # csfFilename = deblank(Outfiles(4,:));
        # Vcsf = spm_vol_gzip(csfFilename);
        # Icsf = spm_read_vols_gzip(Vcsf);
        # ind = find(Icsf > csfThresh);
        # Ithal(ind) = 0;

        # update the header and save thalamus mask
        thalamus_mask = op.abspath('{}_class-thalamus_dtissue.nii.gz'.format(outprefixName))
        hdr = Vatlas.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)
        print("Save output image to %s" % thalamus_mask)
        Vthal = ni.Nifti1Image(Ithal, Vatlas.get_affine(), hdr2)
        ni.save(Vthal, thalamus_mask)

        del hdr, hdr2, Vthal


        Nspams = Ispams.shape[3]
        Thresh = 0.05

        use_thalamus_mask = True
        if use_thalamus_mask:
            IthalL = np.zeros(Ithal.shape)
            indl = np.where(Ithal == 1)
            IthalL[indl] = 1
            del indl

            IthalR = np.zeros(Ithal.shape)
            indr = np.where(Ithal == 2)
            IthalR[indr] = 1

            del Ithal

            # Mask probability maps using the left-hemisphere thalamus mask
            tmpIthalL = np.zeros((IthalL.shape[0],IthalL.shape[1],IthalL.shape[2],1))
            tmpIthalL[:,:,:,0] = IthalL
            tempM = np.repeat(tmpIthalL,Nspams/2,axis=3)
            del tmpIthalL
            IspamL = np.multiply(Ispams[:,:,:,0:Nspams/2],tempM)
            print('IspamL shape:',IspamL.shape)
            del tempM

            # Creating MaxProb
            ind = np.where(IspamL < Thresh)
            IspamL[ind] = 0
            ind = np.where(np.sum(IspamL,axis=3) == 0)
            #MaxProbL = IspamL.max(axis=3)
            MaxProbL = np.argmax(IspamL,axis=3) + 1
            MaxProbL[ind] = 0
            #MaxProbL[ind] = 0
            #?MaxProbL = ndimage.binary_fill_holes(MaxProbL)
            #?MaxProbL = Atlas_Corr(IthalL,MaxProbL)

            # Mask probability maps using the right-hemisphere thalamus mask
            tmpIthalR = np.zeros((IthalR.shape[0],IthalR.shape[1],IthalR.shape[2],1))
            tmpIthalR[:,:,:,0] = IthalR
            tempM = np.repeat(tmpIthalR,Nspams/2,axis=3)
            del tmpIthalR
            IspamR = np.multiply(Ispams[:,:,:,Nspams/2:Nspams],tempM)
            print('IspamR shape:',IspamR.shape)
            del tempM

            # Creating MaxProb
            ind = np.where(IspamR < Thresh)
            IspamR[ind] = 0
            ind = np.where(np.sum(IspamR,axis=3) == 0)
            #MaxProbR = IspamR.max(axis=3)
            MaxProbR = np.argmax(IspamR,axis=3) + 1
            #?MaxProbR = imfill(MaxProbR,'holes');
            #?MaxProbR = Atlas_Corr(IthalR,MaxProbR);
            MaxProbR[indr] = MaxProbR[indr] + Nspams/2;
            MaxProbR[ind] = 0

            del indr

            Ispams[:,:,:,0:Nspams/2] = IspamL
            Ispams[:,:,:,Nspams/2:Nspams] = IspamR

        # Save corrected probability maps of thalamic nuclei
        # update the header
        hdr = imgVspams.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)
        print("Save output image to %s" % output_maps)
        img = ni.Nifti1Image(Ispams, imgVspams.get_affine(), hdr2)
        ni.save(img, output_maps)

        del hdr, img, imgVspams

        # Save Maxprob
        # update the header
        max_prob = op.abspath('{}_class-thalamus_probtissue_maxprob.nii.gz'.format(outprefixName))
        hdr = Vatlas.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)

        if use_thalamus_mask:
            MaxProb = MaxProbL + MaxProbR
        else:
            # Creating MaxProb
            ind = np.where(Ispams < Thresh)
            Ispams[ind] = 0
            ind = np.where(np.sum(Ispams,axis=3) == 0)
            MaxProb = Ispams.argmax(axis=3) + 1
            MaxProb[ind] = 0;
            #?MaxProb = imfill(MaxProb,'holes');

        del Ispams

        # debug_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_maxprobL.nii.gz'
        # print("Save output image to %s" % debug_file)
        # img = ni.Nifti1Image(MaxProbL, Vatlas.get_affine(), hdr2)
        # ni.save(img, debug_file)
        #
        # debug_file = '/home/localadmin/~/Desktop/parcellation_tests/sub-A006_ses-20160520161029_T1w_brain_class-thalamus_maxprobR.nii.gz'
        # print("Save output image to %s" % debug_file)
        # img = ni.Nifti1Image(MaxProbR, Vatlas.get_affine(), hdr2)
        # ni.save(img, debug_file)

        print("Save output image to %s" % max_prob)
        img = ni.Nifti1Image(MaxProb, Vatlas.get_affine(), hdr2)
        ni.save(img, max_prob)

        del hdr2, img, max_prob

        iflogger.info('Done')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outprefixName = self.inputs.T1w_image.split(".")[0]
        outprefixName = outprefixName.split("/")[-1:][0]

        outputs['prob_maps_registered'] =op.abspath('{}_class-thalamus_probtissue.nii.gz'.format(outprefixName))
        outputs['max_prob_registered'] = op.abspath('{}_class-thalamus_probtissue_maxprob.nii.gz'.format(outprefixName))
        outputs['thalamus_mask'] = op.abspath('{}_class-thalamus_dtissue.nii.gz'.format(outprefixName))

        outprefixName = op.abspath('{}_Ind2temp'.format(outprefixName))

        outputs['warped_image'] = op.abspath('{}Warped.nii.gz'.format(outprefixName))
        outputs['inverse_warped_image'] = op.abspath('{}InverseWarped.nii.gz'.format(outprefixName))
        outputs['transform_file'] = op.abspath('{}0GenericAffine.mat'.format(outprefixName))
        outputs['warp_file'] = op.abspath('{}1Warp.nii.gz'.format(outprefixName))

        #outputs['lh_hipposubfields'] = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'tmp','lh_subFields.nii.gz')
        #outputs['rh_hipposubfields'] = op.join(self.inputs.subjects_dir,self.inputs.subject_id,'tmp','rh_subFields.nii.gz')
        return outputs


class ParcellateInputSpec(BaseInterfaceInputSpec):
    subjects_dir = Directory(desc='Freesurfer main directory')
    subject_id = traits.String(mandatory=True, desc='Subject ID')
    parcellation_scheme = traits.Enum('Lausanne2008',['Lausanne2008','Lausanne2018','NativeFreesurfer'], usedefault = True)
    erode_masks = traits.Bool(False)


class ParcellateOutputSpec(TraitedSpec):
    #roi_files = OutputMultiPath(File(exists=True),desc='Region of Interest files for connectivity mapping')
    white_matter_mask_file = File(desc='White matter mask file')
    gray_matter_mask_file = File(desc='Cortical gray matter mask file')
    #cc_unknown_file = File(desc='Image file with regions labelled as unknown cortical structures',
    #                exists=True)
    ribbon_file = File(desc='Image file detailing the cortical ribbon',exists=True)
    #aseg_file = File(desc='Automated segmentation file converted from Freesurfer "subjects" directory',
    #                exists=True)
    wm_eroded = File(desc="Eroded wm file in original space")
    csf_eroded = File(desc="Eroded csf file in original space")
    brain_eroded = File(desc="Eroded brain file in original space")
    roi_files_in_structural_space = OutputMultiPath(File(exists=True),
                                desc='ROI image resliced to the dimensions of the original structural image')
    T1 = File(desc="T1 image file")
    brain = File(desc="Brain-masked T1 image file")
    brain_mask = File(desc="Brain mask file")
    aseg = File(desc="ASeg image file")


class Parcellate(BaseInterface):
    """Subdivides segmented ROI file into smaller subregions

    This interface interfaces with the ConnectomeMapper Toolkit library
    parcellation functions (cmtklib/parcellation.py) for all
    parcellation resolutions of a given scheme.

    Example
    -------

    >>> import nipype.interfaces.cmtk as cmtk
    >>> parcellate = cmtk.Parcellate()
    >>> parcellate.inputs.subjects_dir = '.'
    >>> parcellate.inputs.subject_id = 'subj1'
    >>> parcellate.run()                 # doctest: +SKIP
    """

    input_spec = ParcellateInputSpec
    output_spec = ParcellateOutputSpec

    def _run_interface(self, runtime):
        #if self.inputs.subjects_dir:
        #   os.environ.update({'SUBJECTS_DIR': self.inputs.subjects_dir})
        iflogger.info("ROI_HR_th.nii.gz / fsmask_1mm.nii.gz CREATION")
        iflogger.info("=============================================")

        if self.inputs.parcellation_scheme == "Lausanne2008":
            print "Parcellation scheme : Lausanne2008"
            create_T1_and_Brain(self.inputs.subject_id, self.inputs.subjects_dir)
            create_annot_label(self.inputs.subject_id, self.inputs.subjects_dir)
            create_roi(self.inputs.subject_id, self.inputs.subjects_dir)
            create_wm_mask(self.inputs.subject_id, self.inputs.subjects_dir)
            if self.inputs.erode_masks:
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','fsmask_1mm.nii.gz'))
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','csf_mask.nii.gz'))
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','brainmask.nii.gz'))
            crop_and_move_datasets(self.inputs.parcellation_scheme,self.inputs.subject_id, self.inputs.subjects_dir)
        if self.inputs.parcellation_scheme == "Lausanne2018":
            print "Parcellation scheme : Lausanne2018"
            create_T1_and_Brain(self.inputs.subject_id, self.inputs.subjects_dir)
            #create_annot_label(self.inputs.subject_id, self.inputs.subjects_dir)
            create_roi_v2(self.inputs.subject_id, self.inputs.subjects_dir)
            create_wm_mask_v2(self.inputs.subject_id, self.inputs.subjects_dir)
            if self.inputs.erode_masks:
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','fsmask_1mm.nii.gz'))
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','csf_mask.nii.gz'))
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','brainmask.nii.gz'))
            crop_and_move_datasets(self.inputs.parcellation_scheme,self.inputs.subject_id, self.inputs.subjects_dir)
        if self.inputs.parcellation_scheme == "NativeFreesurfer":
            print "Parcellation scheme : NativeFreesurfer"
            create_T1_and_Brain(self.inputs.subject_id, self.inputs.subjects_dir)
            generate_WM_and_GM_mask(self.inputs.subject_id, self.inputs.subjects_dir)
            if self.inputs.erode_masks:
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','fsmask_1mm.nii.gz'))
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','csf_mask.nii.gz'))
                erode_mask(op.join(self.inputs.subjects_dir,self.inputs.subject_id,'mri','brainmask.nii.gz'))
            crop_and_move_WM_and_GM(self.inputs.subject_id, self.inputs.subjects_dir)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        outputs['T1'] = op.abspath('T1.nii.gz')
        outputs['brain'] = op.abspath('brain.nii.gz')
        outputs['brain_mask'] = op.abspath('brain_mask.nii.gz')

        outputs['aseg'] = op.abspath('aseg.nii.gz')

        outputs['white_matter_mask_file'] = op.abspath('fsmask_1mm.nii.gz')
        outputs['gray_matter_mask_file'] = op.abspath('gmmask.nii.gz')
        #outputs['cc_unknown_file'] = op.abspath('cc_unknown.nii.gz')
        outputs['ribbon_file'] = op.abspath('ribbon.nii.gz')
        #outputs['aseg_file'] = op.abspath('aseg.nii.gz')

        #outputs['roi_files'] = self._gen_outfilenames('ROI_HR_th')
        outputs['roi_files_in_structural_space'] = self._gen_outfilenames('ROIv_HR_th')

        if self.inputs.erode_masks:
            outputs['wm_eroded'] = op.abspath('wm_eroded.nii.gz')
            outputs['csf_eroded'] = op.abspath('csf_eroded.nii.gz')
            outputs['brain_eroded'] = op.abspath('brainmask_eroded.nii.gz')

        return outputs

    def _gen_outfilenames(self, basename):
        filepaths = []
        for scale in get_parcellation(self.inputs.parcellation_scheme).keys():
            filepaths.append(op.abspath(basename+'_'+scale+'.nii.gz'))
        return filepaths



def get_parcellation(parcel = "NativeFreesurfer"):
    if parcel == "Lausanne2008":
        return {
            'scale1' : {'number_of_regions' : 83,
                                    # contains name, url, color, freesurfer_label, etc. used for connection matrix
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution83','resolution83.graphml')),
                                    # scalar node values on fsaverage? or atlas?
                                    'surface_parcellation' : None,
                                    # scalar node values in fsaverage volume?
                                    'volume_parcellation' : None,
                                    # the subdirectory name from where to copy parcellations, with hemispheric wildcard
                                    'fs_label_subdir_name' : 'regenerated_%s_36',
                                    # should we subtract the cortical rois for the white matter mask?
                                    'subtract_from_wm_mask' : 1,
                                    },
                        'scale2' : {'number_of_regions' : 129,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution150','resolution150.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_60',
                                    'subtract_from_wm_mask' : 1,
                                     },
                        'scale3' : {'number_of_regions' : 234,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution258','resolution258.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_125',
                                    'subtract_from_wm_mask' : 1,
                                    },
                        'scale4' : {'number_of_regions' : 463,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution500','resolution500.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_250',
                                    'subtract_from_wm_mask' : 1,
                                    },
                        'scale5' : {'number_of_regions' : 1015,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution1015','resolution1015.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_500',
                                    'subtract_from_wm_mask' : 1,
                                    },
                    }
    elif parcel == "Lausanne2018":
        return {
            'scale1' : {'number_of_regions' : 95,#83,
        			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution1','resolution1.graphml')), # NOTE that all the node-wise information is stored in a dedicated graphml file
        			      'surface_parcellation' : None,
        			      'volume_parcellation' : None,
        			      'fs_label_subdir_name' : 'regenerated_%s_1',
                          'subtract_from_wm_mask' : 1,
        			      'annotation' : 'myaparc_1'},
        		  'scale2' : {'number_of_regions' : 141,#129,
        			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution2','resolution2.graphml')),
        			      'surface_parcellation' : None,
        			      'volume_parcellation' : None,
        			      'fs_label_subdir_name' : 'regenerated_%s_2',
                          'subtract_from_wm_mask' : 1,
        			      'annotation' : 'myaparc_2'},
        		  'scale3' : {'number_of_regions' : 246,#234,
        			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution3','resolution3.graphml')),
        			      'surface_parcellation' : None,
        			      'volume_parcellation' : None,
        			      'fs_label_subdir_name' : 'regenerated_%s_3',
                          'subtract_from_wm_mask' : 1,
        			      'annotation' : 'myaparc_3'},
        		  'scale4' : {'number_of_regions' : 475,#463,
        			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution4','resolution4.graphml')),
        			      'surface_parcellation' : None,
        			      'volume_parcellation' : None,
        			      'fs_label_subdir_name' : 'regenerated_%s_4',
                          'subtract_from_wm_mask' : 1,
        			      'annotation' : 'myaparc_4'},
        		  'scale5' : {'number_of_regions' : 1027,#1015,
        			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution5','resolution5.graphml')),
        			      'surface_parcellation' : None,
        			      'volume_parcellation' : None,
        			      'fs_label_subdir_name' : 'regenerated_%s_5',
                          'subtract_from_wm_mask' : 1,
        			      'annotation' : ['myaparc_5_P1_16', 'myaparc_5_P17_28', 'myaparc_5_P29_36']}
                       }
    else:
        return {'roi_volumes_flirt_crop_out_dil' : {'number_of_regions' : 83,
                                    # freesurferaparc; contains name, url, color, freesurfer_label, etc. used for connection matrix
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','nativefreesurfer','freesurferaparc','resolution83.graphml')),
                                    # scalar node values on fsaverage? or atlas?
                                    'surface_parcellation' : None,
                                    # scalar node values in fsaverage volume?
                                    'volume_parcellation' : None,
                                    }
        }

def extract(Z, shape, position, fill):
    """ Extract voxel neighbourhood
    Parameters
    ----------
    Z: the original data
    shape: tuple containing neighbourhood dimensions
    position: tuple containing central point indexes
    fill: value for the padding of Z
    Returns
    -------
    R: the neighbourhood of the specified point in Z
    """
    R = np.ones(shape, dtype=Z.dtype) * fill # initialize output block to the fill value
    P = np.array(list(position)).astype(int) # position coordinates(numpy array)
    Rs = np.array(list(R.shape)).astype(int) # output block dimensions (numpy array)
    Zs = np.array(list(Z.shape)).astype(int) # original volume dimensions (numpy array)

    R_start = np.zeros(len(shape)).astype(int)
    R_stop = np.array(list(shape)).astype(int)
    Z_start = (P - Rs // 2)
    Z_start_cor = (np.maximum(Z_start,0)).tolist() # handle borders
    R_start = R_start + (Z_start_cor - Z_start)
    Z_stop = (P + Rs // 2) + Rs % 2
    Z_stop_cor = (np.minimum(Z_stop,Zs)).tolist() # handle borders
    R_stop = R_stop - (Z_stop - Z_stop_cor)

    R[R_start[0]:R_stop[0], R_start[1]:R_stop[1], R_start[2]:R_stop[2]] = Z[Z_start_cor[0]:Z_stop_cor[0], Z_start_cor[1]:Z_stop_cor[1], Z_start_cor[2]:Z_stop_cor[2]]

    return R

def create_T1_and_Brain(subject_id, subjects_dir):

    fs_dir = op.join(subjects_dir,subject_id)

    # Convert T1 image
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','T1.mgz'),'-o',op.join(fs_dir,'mri','T1.nii.gz')]
    subprocess.check_call(mri_cmd)

    # Convert Brain_masked T1 image
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','brain.mgz'),'-o',op.join(fs_dir,'mri','brain.nii.gz')]
    subprocess.check_call(mri_cmd)

    # Convert ASeg image
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','aseg.mgz'),'-o',op.join(fs_dir,'mri','aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    print("[DONE]")

def create_annot_label(subject_id, subjects_dir):
    print("Create the cortical labels necessary for our ROIs")
    print("=================================================")

    fs_dir = op.join(subjects_dir,subject_id)
    fs_label_dir = op.join(fs_dir, 'label')

    paths = []

    for scale, features in get_parcellation('Lausanne2008').items():
        for hemi in ['lh', 'rh']:
            spath = features['fs_label_subdir_name'] % hemi
            paths.append(spath)
    for p in paths:
        try:
            os.makedirs(op.join('.', p))
        except:
            pass

    comp = [
    ('rh', 'myatlas_36_rh.gcs', 'rh.myaparc_36.annot', 'regenerated_rh_36','myaparc_36'),
    ('rh', 'myatlasP1_16_rh.gcs','rh.myaparcP1_16.annot','regenerated_rh_500','myaparcP1_16'),
    ('rh', 'myatlasP17_28_rh.gcs','rh.myaparcP17_28.annot','regenerated_rh_500','myaparcP17_28'),
    ('rh', 'myatlasP29_36_rh.gcs','rh.myaparcP29_36.annot','regenerated_rh_500','myaparcP29_36'),
    ('rh','myatlas_60_rh.gcs','rh.myaparc_60.annot','regenerated_rh_60','myaparc_60'),
    ('rh','myatlas_125_rh.gcs','rh.myaparc_125.annot','regenerated_rh_125','myaparc_125'),
    ('rh','myatlas_250_rh.gcs','rh.myaparc_250.annot','regenerated_rh_250','myaparc_250'),
    ('lh', 'myatlas_36_lh.gcs', 'lh.myaparc_36.annot', 'regenerated_lh_36','myaparc_36'),
    ('lh', 'myatlasP1_16_lh.gcs','lh.myaparcP1_16.annot','regenerated_lh_500','myaparcP1_16'),
    ('lh', 'myatlasP17_28_lh.gcs','lh.myaparcP17_28.annot','regenerated_lh_500','myaparcP17_28'),
    ('lh', 'myatlasP29_36_lh.gcs','lh.myaparcP29_36.annot','regenerated_lh_500','myaparcP29_36'),
    ('lh','myatlas_60_lh.gcs','lh.myaparc_60.annot','regenerated_lh_60', 'myaparc_60'),
    ('lh','myatlas_125_lh.gcs','lh.myaparc_125.annot','regenerated_lh_125','myaparc_125'),
    ('lh','myatlas_250_lh.gcs','lh.myaparc_250.annot','regenerated_lh_250','myaparc_250'),
    ]

    for out in comp:
        gcsfile = pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', out[1]))

        mris_cmd = ['mris_ca_label', '-sdir', subjects_dir, subject_id, out[0],
                    fs_dir+'/surf/'+out[0]+'.sphere.reg', gcsfile,
                    op.join(fs_label_dir, out[2])]
        print '*********'
        print mris_cmd
        subprocess.check_call(mris_cmd)
        print('-----------')

        #annot = '--annotation "%s"' % out[4]

        mri_an_cmd = ['mri_annotation2label', '--sd', subjects_dir, '--subject',
                      subject_id, '--hemi', out[0], '--outdir',
                      op.join(fs_label_dir, out[3]), '--annotation', out[4]]
        subprocess.check_call(mri_an_cmd)
        print('-----------')

    # extract cc and unknown to add to tractography mask, we do not want this as a region of interest
    # in FS 5.0, unknown and corpuscallosum are not available for the 35 scale (why?),
    # but for the other scales only, take the ones from _60
    rhun = op.join(fs_label_dir, 'rh.unknown.label')
    lhun = op.join(fs_label_dir, 'lh.unknown.label')
    rhco = op.join(fs_label_dir, 'rh.corpuscallosum.label')
    lhco = op.join(fs_label_dir, 'lh.corpuscallosum.label')
    shutil.copy(op.join(fs_label_dir, 'regenerated_rh_60', 'rh.unknown.label'), rhun)
    shutil.copy(op.join(fs_label_dir, 'regenerated_lh_60', 'lh.unknown.label'), lhun)
    shutil.copy(op.join(fs_label_dir, 'regenerated_rh_60', 'rh.corpuscallosum.label'), rhco)
    shutil.copy(op.join(fs_label_dir, 'regenerated_lh_60', 'lh.corpuscallosum.label'), lhco)

    mri_cmd = ['mri_label2vol','--label',rhun,'--label',lhun,'--label',rhco,'--label',lhco,'--temp',op.join(fs_dir, 'mri', 'orig.mgz'),'--o',op.join(fs_dir, 'label', 'cc_unknown.nii.gz'),'--identity']
    subprocess.check_call(mri_cmd)

    subprocess.check_call(['mris_volmask','--sd',subjects_dir,subject_id])

    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','ribbon.mgz'),'-o',op.join(fs_dir,'mri','ribbon.nii.gz')]
    subprocess.check_call(mri_cmd)

    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','aseg.mgz'),'-o',op.join(fs_dir,'mri','aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    print("[ DONE ]")

def create_roi(subject_id, subjects_dir):
    """ Creates the ROI_%s.nii.gz files using the given parcellation information
    from networks. Iteratively create volume. """

    print("Create the ROIs:")
    fs_dir = op.join(subjects_dir,subject_id)

    # load aseg volume
    aseg = ni.load(op.join(fs_dir, 'mri', 'aseg.nii.gz'))
    asegd = aseg.get_data()	# numpy.ndarray

    # identify cortical voxels, right (3) and left (42) hemispheres
    idxr = np.where(asegd == 3)
    idxl = np.where(asegd == 42)
    xx = np.concatenate((idxr[0],idxl[0]))
    yy = np.concatenate((idxr[1],idxl[1]))
    zz = np.concatenate((idxr[2],idxl[2]))

    # initialize variables necessary for cortical ROIs dilation
    # dimensions of the neighbourhood for rois labels assignment (choose odd dimensions!)
    shape = (25,25,25)
    center = np.array(shape) // 2
    # dist: distances from the center of the neighbourhood
    dist = np.zeros(shape, dtype='float32')
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(shape[2]):
                distxyz = center - [x,y,z]
                dist[x,y,z] = math.sqrt(np.sum(np.multiply(distxyz,distxyz)))

    # LOOP throughout all the SCALES
    # (from the one with the highest number of region to the one with the lowest number of regions)
    #parkeys = gconf.parcellation.keys()
    scales = get_parcellation('Lausanne2008').keys()
    values = list()
    for i in range(len(scales)):
        values.append(get_parcellation('Lausanne2008')[scales[i]]['number_of_regions'])
    temp = zip(values, scales)
    temp.sort(reverse=True)
    values, scales = zip(*temp)
    roisMax = np.zeros( (256, 256, 256), dtype=np.int16 ) # numpy.ndarray
    for i,parkey in enumerate(get_parcellation('Lausanne2008').keys()):
        parval = get_parcellation('Lausanne2008')[parkey]

        print("Working on parcellation: " + parkey)
        print("========================")
        pg = nx.read_graphml(parval['node_information_graphml'])

        # each node represents a brain region
        # create a big 256^3 volume for storage of all ROIs
        rois = np.zeros( (256, 256, 256), dtype=np.int16 ) # numpy.ndarray

        for brk, brv in pg.nodes(data=True):   # slow loop

            if brv['dn_hemisphere'] == 'left':
                hemi = 'lh'
            elif brv['dn_hemisphere'] == 'right':
                hemi = 'rh'

            if brv['dn_region'] == 'subcortical':

                print("---------------------")
                print("Work on brain region: %s" % (brv['dn_region']) )
                print("Freesurfer Name: %s" %  brv['dn_fsname'] )
                print("---------------------")

                # if it is subcortical, retrieve roi from aseg
                idx = np.where(asegd == int(brv['dn_fs_aseg_val']))
                rois[idx] = int(brv['dn_correspondence_id'])

            elif brv['dn_region'] == 'cortical':
                print("---------------------")
                print("Work on brain region: %s" % (brv['dn_region']) )
                print("Freesurfer Name: %s" %  brv['dn_fsname'] )
                print("---------------------")

                labelpath = op.join(fs_dir, 'label', parval['fs_label_subdir_name'] % hemi)

                # construct .label file name
                fname = '%s.%s.label' % (hemi, brv['dn_fsname'])

                # execute fs mri_label2vol to generate volume roi from the label file
                # store it in temporary file to be overwritten for each region (slow!)
                #mri_cmd = 'mri_label2vol --label "%s" --temp "%s" --o "%s" --identity' % (op.join(labelpath, fname),
                #        op.join(fs_dir, 'mri', 'orig.mgz'), op.join(labelpath, 'tmp.nii.gz'))
                #runCmd( mri_cmd, log )
                mri_cmd = ['mri_label2vol','--label',op.join(labelpath, fname),'--temp',op.join(fs_dir, 'mri', 'orig.mgz'),'--o',op.join(labelpath, 'tmp.nii.gz'),'--identity']
                subprocess.check_call(mri_cmd)

                tmp = ni.load(op.join(labelpath, 'tmp.nii.gz'))
                tmpd = tmp.get_data()

                # find voxel and set them to intensity value in rois
                idx = np.where(tmpd == 1)
                rois[idx] = int(brv['dn_correspondence_id'])

        newrois = rois.copy()
        # store scale500 volume for correction on multi-resolution consistency
        if i == 0:
            print("Storing ROIs volume maximal resolution...")
            roisMax = rois.copy()
            idxMax = np.where(roisMax > 0)
            xxMax = idxMax[0]
            yyMax = idxMax[1]
            zzMax = idxMax[2]
        # correct cortical surfaces using as reference the roisMax volume (for consistency between resolutions)
        else:
            print("Adapt cortical surfaces...")
            #adaptstart = time()
            idxRois = np.where(rois > 0)
            xxRois = idxRois[0]
            yyRois = idxRois[1]
            zzRois = idxRois[2]
            # correct voxels labeled in current resolution, but not labeled in highest resolution
            for j in range(xxRois.size):
                if ( roisMax[xxRois[j],yyRois[j],zzRois[j]]==0 ):
                    newrois[xxRois[j],yyRois[j],zzRois[j]] = 0;
            # correct voxels not labeled in current resolution, but labeled in highest resolution
            for j in range(xxMax.size):
                if ( newrois[xxMax[j],yyMax[j],zzMax[j]]==0 ):
                    local = extract(rois, shape, position=(xxMax[j],yyMax[j],zzMax[j]), fill=0)
                    mask = local.copy()
                    mask[np.nonzero(local>0)] = 1
                    thisdist = np.multiply(dist,mask)
                    thisdist[np.nonzero(thisdist==0)] = np.amax(thisdist)
                    value = np.int_(local[np.nonzero(thisdist==np.amin(thisdist))])
                    if value.size > 1:
                        counts = np.bincount(value)
                        value = np.argmax(counts)
                    newrois[xxMax[j],yyMax[j],zzMax[j]] = value
            #print("Cortical ROIs adaptation took %s seconds to process." % (time()-adaptstart))

        # store volume eg in ROI_scale33.nii.gz
        out_roi = op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % parkey)
        # update the header
        hdr = aseg.get_header()
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)
        print("Save output image to %s" % out_roi)
        img = ni.Nifti1Image(newrois, aseg.get_affine(), hdr2)
        ni.save(img, out_roi)

        # dilate cortical regions
        print("Dilating cortical regions...")
        #dilatestart = time()
        # loop throughout all the voxels belonging to the aseg GM volume
        for j in range(xx.size):
            if newrois[xx[j],yy[j],zz[j]] == 0:
                local = extract(rois, shape, position=(xx[j],yy[j],zz[j]), fill=0)
                mask = local.copy()
                mask[np.nonzero(local>0)] = 1
                thisdist = np.multiply(dist,mask)
                thisdist[np.nonzero(thisdist==0)] = np.amax(thisdist)
                value = np.int_(local[np.nonzero(thisdist==np.amin(thisdist))])
                if value.size > 1:
                    counts = np.bincount(value)
                    value = np.argmax(counts)
                newrois[xx[j],yy[j],zz[j]] = value
        #print("Cortical ROIs dilation took %s seconds to process." % (time()-dilatestart))

        # store volume eg in ROIv_scale33.nii.gz
        out_roi = op.join(fs_dir, 'label', 'ROIv_%s.nii.gz' % parkey)
        print("Save output image to %s" % out_roi)
        img = ni.Nifti1Image(newrois, aseg.get_affine(), hdr2)
        ni.save(img, out_roi)

    print("[ DONE ]")

def define_atlas_variables():
    print("Define atlas variables")
    print("=================================================")

    paths = ['regenerated_lh_1','regenerated_rh_1','regenerated_lh_2','regenerated_rh_2','regenerated_lh_3','regenerated_rh_3','regenerated_lh_4','regenerated_rh_4','regenerated_lh_5','regenerated_rh_5']
    # hemisphere - gcs file (cortical atlas) - annot file - label directory - path to gcs file
    comp=[('rh', 'myatlas_ 1_rh.gcs', 'rh.myaparc_1.annot', 'regenerated_rh_1', 'myaparc_1', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_1_rh.gcs'))),
       ('rh', 'myatlas_5_P1_16_rh.gcs', 'rh.myaparc_5_P1_16.annot', 'regenerated_rh_5', 'myaparc_5_P1_16', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_5_P1_16_rh.gcs'))),
       ('rh', 'myatlas_5_P17_28_rh.gcs', 'rh.myaparc_5_P17_28.annot', 'regenerated_rh_5', 'myaparc_5_P17_28', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_5_P17_28_rh.gcs'))),
       ('rh', 'myatlas_5_P29_36_rh.gcs', 'rh.myaparc_5_P29_36.annot', 'regenerated_rh_5', 'myaparc_5_P29_36', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_5_P29_36_rh.gcs'))),
       ('rh', 'myatlas_2_rh.gcs', 'rh.myaparc_2.annot', 'regenerated_rh_2', 'myaparc_2', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_2_rh.gcs'))),
       ('rh', 'myatlas_3_rh.gcs', 'rh.myaparc_3.annot', 'regenerated_rh_3', 'myaparc_3', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_3_rh.gcs'))),
       ('rh', 'myatlas_4_rh.gcs', 'rh.myaparc_4.annot', 'regenerated_rh_4', 'myaparc_4', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_4_rh.gcs'))),
       ('lh', 'myatlas_1_lh.gcs', 'lh.myaparc_1.annot', 'regenerated_lh_1', 'myaparc_1', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_1_lh.gcs'))),
       ('lh', 'myatlas_5_P1_16_lh.gcs', 'lh.myaparc_5_P1_16.annot', 'regenerated_lh_5', 'myaparc_5_P1_16', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_5_P1_16_lh.gcs'))),
       ('lh', 'myatlas_5_P17_28_lh.gcs', 'lh.myaparc_5_P17_28.annot', 'regenerated_lh_5', 'myaparc_5_P17_28', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_5_P17_28_lh.gcs'))),
       ('lh', 'myatlas_5_P29_36_lh.gcs', 'lh.myaparc_5_P29_36.annot', 'regenerated_lh_5', 'myaparc_5_P29_36', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_5_P29_36_lh.gcs'))),
       ('lh','myatlas_2_lh.gcs', 'lh.myaparc_2.annot', 'regenerated_lh_2', 'myaparc_2', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_2_lh.gcs'))),
       ('lh', 'myatlas_3_lh.gcs', 'lh.myaparc_3.annot', 'regenerated_lh_3', 'myaparc_3', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_3_lh.gcs'))),
       ('lh', 'myatlas_4_lh.gcs', 'lh.myaparc_4.annot', 'regenerated_lh_4', 'myaparc_4', pkg_resources.resource_filename('cmtklib', op.join('data', 'colortable_and_gcs', 'my_atlas_gcs', 'myatlas_4_lh.gcs')))]

    pardic = {'scale1' : {'number_of_regions' : 95,#83,
			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution1','resolution1.graphml')), # NOTE that all the node-wise information is stored in a dedicated graphml file
			      'surface_parcellation' : None,
			      'volume_parcellation' : None,
			      'fs_label_subdir_name' : 'regenerated_%s_1',
                  'subtract_from_wm_mask' : 1,
			      'annotation' : 'myaparc_1'},
		  'scale2' : {'number_of_regions' : 141,#129,141
			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution2','resolution2.graphml')),
			      'surface_parcellation' : None,
			      'volume_parcellation' : None,
			      'fs_label_subdir_name' : 'regenerated_%s_2',
                  'subtract_from_wm_mask' : 1,
			      'annotation' : 'myaparc_2'},
		  'scale3' : {'number_of_regions' : 246,#234,246
			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution3','resolution3.graphml')),
			      'surface_parcellation' : None,
			      'volume_parcellation' : None,
			      'fs_label_subdir_name' : 'regenerated_%s_3',
                  'subtract_from_wm_mask' : 1,
			      'annotation' : 'myaparc_3'},
		  'scale4' : {'number_of_regions' : 475,#463,475
			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution4','resolution4.graphml')),
			      'surface_parcellation' : None,
			      'volume_parcellation' : None,
			      'fs_label_subdir_name' : 'regenerated_%s_4',
                  'subtract_from_wm_mask' : 1,
			      'annotation' : 'myaparc_4'},
		  'scale5' : {'number_of_regions' : 1027,#1015,1027
			      'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018','resolution5','resolution5.graphml')),
			      'surface_parcellation' : None,
			      'volume_parcellation' : None,
			      'fs_label_subdir_name' : 'regenerated_%s_5',
                  'subtract_from_wm_mask' : 1,
			      'annotation' : ['myaparc_5_P1_16', 'myaparc_5_P17_28', 'myaparc_5_P29_36']}}

    parkeys = [ k for k in pardic ]

    return paths, comp, pardic, parkeys

def generate_single_parcellation(v,i,fs_string,subject_dir,subject_id):
    # Multiscale parcellation - define annotation and segmentation variables
    rh_annot_files = ['rh.lausanne2008.scale1.annot', 'rh.lausanne2008.scale2.annot', 'rh.lausanne2008.scale3.annot', 'rh.lausanne2008.scale4.annot', 'rh.lausanne2008.scale5.annot']
    lh_annot_files = ['lh.lausanne2008.scale1.annot', 'lh.lausanne2008.scale2.annot', 'lh.lausanne2008.scale3.annot', 'lh.lausanne2008.scale4.annot', 'lh.lausanne2008.scale5.annot']
    annot = ['lausanne2008.scale1', 'lausanne2008.scale2', 'lausanne2008.scale3', 'lausanne2008.scale4', 'lausanne2008.scale5']
    aseg_output = ['ROIv_scale1.nii.gz', 'ROIv_scale2.nii.gz', 'ROIv_scale3.nii.gz', 'ROIv_scale4.nii.gz', 'ROIv_scale5.nii.gz']

    if v:
        print(' ... working on multiscale parcellation, SCALE {}'.format(i+1))

    # 1. Resample fsaverage CorticalSurface onto SUBJECT_ID CorticalSurface and map annotation for current scale
    # Left hemisphere
    if v:
        print('     > resample fsaverage CorticalSurface to individual CorticalSurface')
    mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi lh --sval-annot %s --tval %s' % (
                subject_id,
                pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', lh_annot_files[i])),
                os.path.join(subject_dir, 'label', lh_annot_files[i]))
    if v == 2:
        status = subprocess.call(mri_cmd, shell=True)
    else:
        status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    # Right hemisphere
    mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi rh --sval-annot %s --tval %s' % (
                subject_id,
                pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', rh_annot_files[i])),
                os.path.join(subject_dir, 'label', rh_annot_files[i]))
    if v == 2:
        status = subprocess.call(mri_cmd, shell=True)
    else:
        status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

    # 2. Generate Nifti volume from annotation
    #    Note: change here --wmparc-dmax (FS default 5mm) to dilate cortical regions toward the WM
    if v:
        print('     > generate Nifti volume from annotation')
    mri_cmd = fs_string + '; mri_aparc2aseg --s %s --annot %s --wmparc-dmax 0 --labelwm --hypo-as-wm --new-ribbon --o %s' % (
                subject_id,
                annot[i],
                os.path.join(subject_dir, 'tmp', aseg_output[i]))
    if v == 2:
        status = subprocess.call(mri_cmd, shell=True)
    else:
        status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

    # 3. Update numerical IDs of cortical and subcortical regions
    # Load Nifti volume
    if v:
        print('     > relabel cortical and subcortical regions')
    this_nifti = ni.load(os.path.join(subject_dir, 'tmp', aseg_output[i]))
    vol = this_nifti.get_data()	# numpy.ndarray
    hdr = this_nifti.header
    # Initialize output
    hdr2 = hdr.copy()
    hdr2.set_data_dtype(np.uint16)
    # vol2 = np.zeros( this_nifti.shape, dtype=np.int16 )
    # # Relabelling Right hemisphere (2000+)
    # ii = np.where((vol > 2000) & (vol < 3000))
    # vol2[ii] = vol[ii] - 2000
    # nlabel = np.amax(vol2)	# keep track of the number of assigned labels
    # # Relabelling Subcortical Right hemisphere
    # # NOTE: skip numerical IDs which are used for the thalamic subcortical nuclei
    # newLabels = np.concatenate((np.array([nlabel+1]), np.arange(nlabel+8, nlabel+len(rh_sub)+7)), axis=0)
    # for j in range(0, len(rh_sub)):
    # 	ii = np.where(vol == rh_sub[j])
    # 	vol2[ii] = newLabels[j]
    # nlabel = np.amax(vol2)
    # # Relabelling Left hemisphere (1000+)
    # ii = np.where((vol > 1000) & (vol < 2000))
    # vol2[ii] = vol[ii] - 1000 + nlabel
    # nlabel = np.amax(vol2)	# n cortical label in right hemisphere
    # # Relabelling Subcortical Right hemisphere
    # # NOTE: skip numerical IDs which are used for the thalamic subcortical nuclei
    # newLabels = np.concatenate((np.array([nlabel+1]), np.arange(nlabel+8, nlabel+len(rh_sub)+7)), axis=0)
    # for j in range(0, len(lh_sub)):
    # 	ii = np.where(vol == lh_sub[j])
    # 	vol2[ii] = newLabels[j]
    # nlabel = np.amax(vol2)
    # # Relabelling Brain Stem
    # ii = np.where(vol == brain_stem)
    # vol2[ii] = nlabel + 1

    # 4. Save Nifti and mgz volumes
    if v:
        print('     > save output volumes')
    this_out = os.path.join(subject_dir, 'mri', aseg_output[i])
    img = ni.Nifti1Image(vol, this_nifti.affine, hdr2)
    ni.save(img, this_out)
    mri_cmd = fs_string + '; mri_convert -i %s -o %s' % (
                this_out,
                os.path.join(subject_dir, 'mri', aseg_output[i][0:-4]+'.mgz'))
    if v == 2:
        status = subprocess.call(mri_cmd, shell=True)
    else:
        status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    os.remove(os.path.join(subject_dir, 'tmp', aseg_output[i]))

    return 1

def create_roi_v2(subject_id, subjects_dir,v=True):
    """ Creates the ROI_%s.nii.gz files using the given parcellation information
    from networks. Iteratively create volume. """

    freesurfer_subj = os.path.abspath(subjects_dir)

    print("Freesurfer subjects dir : %s"%freesurfer_subj)
    print("Freesurfer subject id : %s"%subject_id)

    if not ( os.path.isdir(freesurfer_subj) and os.path.isdir(os.path.join(freesurfer_subj, 'fsaverage')) ):
        parser.error('FreeSurfer subject directory is invalid. The folder does not exist or does not contain \'fsaverage\'')
    else:
        if v:
            print('- FreeSurfer subject directory ($SUBJECTS_DIR):\n  {}\n'.format(freesurfer_subj))

    subject_dir = os.path.join(freesurfer_subj, subject_id)
    if not ( os.path.isdir(subject_dir) ):
        parser.error('No input subject directory was found in FreeSurfer $SUBJECTS_DIR')
    else:
        if v:
            print('- Input subject id:\n  {}\n'.format(subject_id))
            print('- Input subject directory:\n  {}\n'.format(subject_dir))


	# Number of scales in multiscale parcellation
	nscales = 5
	# Freesurfer IDs for subcortical structures and brain stem
	lh_sub = np.array([10,11,12,13,26,17,18])
	rh_sub = np.array([49,50,51,52,58,53,54])
	brain_stem = np.array([16])

	# Check existence of multiscale atlas fsaverage annot files
	# for i in range(0, nscales):
	# 	this_file = os.path.join(freesurfer_subj, 'fsaverage/label', rh_annot_files[i])
    #     this_file = pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', rh_annot_files[i]))
    #     # try:
    #     #     shutil.copy(pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', rh_annot_files[i])),this_file)
    #     # except PermissionError:
    #     shutil.os.system('sudo cp "{}" "{}"'.format(pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', rh_annot_files[i])),this_file))
    #
    #     if not os.path.isfile(this_file):
    #         parser.error('"{0}" is required! Please, copy the annot files FROM \'connectome_atlas/misc/multiscale_parcellation/fsaverage/label\' TO your FreeSurfer \'$SUBJECTS_DIR/fsaverage/label\' folder'.format(this_file))
    #         return
    #
    #     this_file = os.path.join(freesurfer_subj, 'fsaverage/label', lh_annot_files[i])
    #     this_file = pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', lh_annot_files[i]))
    #     # try:
    #     #     shutil.copy(pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', lh_annot_files[i])),this_file)
    #     # except PermissionError:
    #     shutil.os.system('sudo cp "{}" "{}"'.format(pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', lh_annot_files[i])),this_file))
    #
    #     if not os.path.isfile(this_file):
	# 		parser.error('"{0}" is required! Please, copy the annot files FROM \'connectome_atlas/misc/multiscale_parcellation/fsaverage/label\' TO your FreeSurfer \'$SUBJECTS_DIR/fsaverage/label\' folder'.format(this_file))
	# 		return


	# Check existence of tmp folder in input subject folder
	this_dir = os.path.join(subject_dir, 'tmp')
	if not ( os.path.isdir(this_dir) ):
		os.makedirs(this_dir)


	# We need to add these instructions when running FreeSurfer commands from Python
	# (if these instructions are not present, Python rises a 'Symbol not found: ___emutls_get_address' exception in macOS)
	fs_string = 'export SUBJECTS_DIR=' + freesurfer_subj


	# Redirect ouput if low verbose
	FNULL = open(os.devnull, 'w')


	# # Loop over parcellation scales
	# if v:
	# 	print('Generete MULTISCALE PARCELLATION for input subject')
	# for i in range(0, nscales):
	# 	if v:
	# 		print(' ... working on multiscale parcellation, SCALE {}'.format(i+1))
    #
	# 	# 1. Resample fsaverage CorticalSurface onto SUBJECT_ID CorticalSurface and map annotation for current scale
	# 	# Left hemisphere
	# 	if v:
	# 		print('     > resample fsaverage CorticalSurface to individual CorticalSurface')
	# 	mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi lh --sval-annot %s --tval %s' % (
	# 				subject_id,
	# 				pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', lh_annot_files[i])),
	# 				os.path.join(subject_dir, 'label', lh_annot_files[i]))
	# 	if v == 2:
	# 		status = subprocess.call(mri_cmd, shell=True)
	# 	else:
	# 		status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
	# 	# Right hemisphere
	# 	mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi rh --sval-annot %s --tval %s' % (
	# 				subject_id,
	# 				pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', rh_annot_files[i])),
	# 				os.path.join(subject_dir, 'label', rh_annot_files[i]))
	# 	if v == 2:
	# 		status = subprocess.call(mri_cmd, shell=True)
	# 	else:
	# 		status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    #
	# 	# 2. Generate Nifti volume from annotation
	# 	#    Note: change here --wmparc-dmax (FS default 5mm) to dilate cortical regions toward the WM
	# 	if v:
	# 		print('     > generate Nifti volume from annotation')
	# 	mri_cmd = fs_string + '; mri_aparc2aseg --s %s --annot %s --wmparc-dmax 0 --labelwm --hypo-as-wm --new-ribbon --o %s' % (
	# 				subject_id,
	# 				annot[i],
	# 				os.path.join(subject_dir, 'tmp', aseg_output[i]))
	# 	if v == 2:
	# 		status = subprocess.call(mri_cmd, shell=True)
	# 	else:
	# 		status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    #
	# 	# 3. Update numerical IDs of cortical and subcortical regions
	# 	# Load Nifti volume
	# 	if v:
	# 		print('     > relabel cortical and subcortical regions')
	# 	this_nifti = ni.load(os.path.join(subject_dir, 'tmp', aseg_output[i]))
	# 	vol = this_nifti.get_data()	# numpy.ndarray
	# 	hdr = this_nifti.header
	# 	# Initialize output
	# 	hdr2 = hdr.copy()
	# 	hdr2.set_data_dtype(np.uint16)
	# 	# vol2 = np.zeros( this_nifti.shape, dtype=np.int16 )
	# 	# # Relabelling Right hemisphere (2000+)
	# 	# ii = np.where((vol > 2000) & (vol < 3000))
	# 	# vol2[ii] = vol[ii] - 2000
	# 	# nlabel = np.amax(vol2)	# keep track of the number of assigned labels
	# 	# # Relabelling Subcortical Right hemisphere
	# 	# # NOTE: skip numerical IDs which are used for the thalamic subcortical nuclei
	# 	# newLabels = np.concatenate((np.array([nlabel+1]), np.arange(nlabel+8, nlabel+len(rh_sub)+7)), axis=0)
	# 	# for j in range(0, len(rh_sub)):
	# 	# 	ii = np.where(vol == rh_sub[j])
	# 	# 	vol2[ii] = newLabels[j]
	# 	# nlabel = np.amax(vol2)
	# 	# # Relabelling Left hemisphere (1000+)
	# 	# ii = np.where((vol > 1000) & (vol < 2000))
	# 	# vol2[ii] = vol[ii] - 1000 + nlabel
	# 	# nlabel = np.amax(vol2)	# n cortical label in right hemisphere
	# 	# # Relabelling Subcortical Right hemisphere
	# 	# # NOTE: skip numerical IDs which are used for the thalamic subcortical nuclei
	# 	# newLabels = np.concatenate((np.array([nlabel+1]), np.arange(nlabel+8, nlabel+len(rh_sub)+7)), axis=0)
	# 	# for j in range(0, len(lh_sub)):
	# 	# 	ii = np.where(vol == lh_sub[j])
	# 	# 	vol2[ii] = newLabels[j]
	# 	# nlabel = np.amax(vol2)
	# 	# # Relabelling Brain Stem
	# 	# ii = np.where(vol == brain_stem)
	# 	# vol2[ii] = nlabel + 1
    #
	# 	# 4. Save Nifti and mgz volumes
	# 	if v:
	# 		print('     > save output volumes')
	# 	this_out = os.path.join(subject_dir, 'mri', aseg_output[i])
	# 	img = ni.Nifti1Image(vol, this_nifti.affine, hdr2)
	# 	ni.save(img, this_out)
	# 	mri_cmd = fs_string + '; mri_convert -i %s -o %s' % (
	# 				this_out,
	# 				os.path.join(subject_dir, 'mri', aseg_output[i][0:-4]+'.mgz'))
	# 	if v == 2:
	# 		status = subprocess.call(mri_cmd, shell=True)
	# 	else:
	# 		status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
	# 	os.remove(os.path.join(subject_dir, 'tmp', aseg_output[i]))

    def generate_single_parcellation(v,i,fs_string,subject_dir,subject_id):
    	# Multiscale parcellation - define annotation and segmentation variables
    	rh_annot_files = ['rh.lausanne2008.scale1.annot', 'rh.lausanne2008.scale2.annot', 'rh.lausanne2008.scale3.annot', 'rh.lausanne2008.scale4.annot', 'rh.lausanne2008.scale5.annot']
    	lh_annot_files = ['lh.lausanne2008.scale1.annot', 'lh.lausanne2008.scale2.annot', 'lh.lausanne2008.scale3.annot', 'lh.lausanne2008.scale4.annot', 'lh.lausanne2008.scale5.annot']
    	annot = ['lausanne2008.scale1', 'lausanne2008.scale2', 'lausanne2008.scale3', 'lausanne2008.scale4', 'lausanne2008.scale5']
    	aseg_output = ['ROIv_scale1.nii.gz', 'ROIv_scale2.nii.gz', 'ROIv_scale3.nii.gz', 'ROIv_scale4.nii.gz', 'ROIv_scale5.nii.gz']

        if v:
            print(' ... working on multiscale parcellation, SCALE {}'.format(i+1))

        # 1. Resample fsaverage CorticalSurface onto SUBJECT_ID CorticalSurface and map annotation for current scale
        # Left hemisphere
        if v:
            print('     > resample fsaverage CorticalSurface to individual CorticalSurface')
        mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi lh --sval-annot %s --tval %s' % (
                    subject_id,
                    pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', lh_annot_files[i])),
                    os.path.join(subject_dir, 'label', lh_annot_files[i]))
        if v == 2:
            status = subprocess.call(mri_cmd, shell=True)
        else:
            status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
        # Right hemisphere
        mri_cmd = fs_string + '; mri_surf2surf --srcsubject fsaverage --trgsubject %s --hemi rh --sval-annot %s --tval %s' % (
                    subject_id,
                    pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2018', rh_annot_files[i])),
                    os.path.join(subject_dir, 'label', rh_annot_files[i]))
        if v == 2:
            status = subprocess.call(mri_cmd, shell=True)
        else:
            status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

        # 2. Generate Nifti volume from annotation
        #    Note: change here --wmparc-dmax (FS default 5mm) to dilate cortical regions toward the WM
        if v:
            print('     > generate Nifti volume from annotation')
        mri_cmd = fs_string + '; mri_aparc2aseg --s %s --annot %s --wmparc-dmax 0 --labelwm --hypo-as-wm --new-ribbon --o %s' % (
                    subject_id,
                    annot[i],
                    os.path.join(subject_dir, 'tmp', aseg_output[i]))
        if v == 2:
            status = subprocess.call(mri_cmd, shell=True)
        else:
            status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

        # 3. Update numerical IDs of cortical and subcortical regions
        # Load Nifti volume
        if v:
            print('     > relabel cortical and subcortical regions')
        this_nifti = ni.load(os.path.join(subject_dir, 'tmp', aseg_output[i]))
        vol = this_nifti.get_data()	# numpy.ndarray
        hdr = this_nifti.header
        # Initialize output
        hdr2 = hdr.copy()
        hdr2.set_data_dtype(np.uint16)
        # vol2 = np.zeros( this_nifti.shape, dtype=np.int16 )
        # # Relabelling Right hemisphere (2000+)
        # ii = np.where((vol > 2000) & (vol < 3000))
        # vol2[ii] = vol[ii] - 2000
        # nlabel = np.amax(vol2)	# keep track of the number of assigned labels
        # # Relabelling Subcortical Right hemisphere
        # # NOTE: skip numerical IDs which are used for the thalamic subcortical nuclei
        # newLabels = np.concatenate((np.array([nlabel+1]), np.arange(nlabel+8, nlabel+len(rh_sub)+7)), axis=0)
        # for j in range(0, len(rh_sub)):
        # 	ii = np.where(vol == rh_sub[j])
        # 	vol2[ii] = newLabels[j]
        # nlabel = np.amax(vol2)
        # # Relabelling Left hemisphere (1000+)
        # ii = np.where((vol > 1000) & (vol < 2000))
        # vol2[ii] = vol[ii] - 1000 + nlabel
        # nlabel = np.amax(vol2)	# n cortical label in right hemisphere
        # # Relabelling Subcortical Right hemisphere
        # # NOTE: skip numerical IDs which are used for the thalamic subcortical nuclei
        # newLabels = np.concatenate((np.array([nlabel+1]), np.arange(nlabel+8, nlabel+len(rh_sub)+7)), axis=0)
        # for j in range(0, len(lh_sub)):
        # 	ii = np.where(vol == lh_sub[j])
        # 	vol2[ii] = newLabels[j]
        # nlabel = np.amax(vol2)
        # # Relabelling Brain Stem
        # ii = np.where(vol == brain_stem)
        # vol2[ii] = nlabel + 1

        # 4. Save Nifti and mgz volumes
        if v:
            print('     > save output volumes')
        this_out = os.path.join(subject_dir, 'mri', aseg_output[i])
        img = ni.Nifti1Image(vol, this_nifti.affine, hdr2)
        ni.save(img, this_out)
        mri_cmd = fs_string + '; mri_convert -i %s -o %s' % (
                    this_out,
                    os.path.join(subject_dir, 'mri', aseg_output[i][0:-4]+'.mgz'))
        if v == 2:
            status = subprocess.call(mri_cmd, shell=True)
        else:
            status = subprocess.call(mri_cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
        os.remove(os.path.join(subject_dir, 'tmp', aseg_output[i]))

        return 1

    # Loop over parcellation scales
    if v:
        print('Generate MULTISCALE PARCELLATION for input subject')

    import multiprocessing as mp
    jobs = []
    for i in range(0, nscales):
        thread = mp.Process(
                            target=generate_single_parcellation,
                            args=(v,i,fs_string,subject_dir,subject_id,)
                            )
        jobs.append(thread)
        thread.start()
    #     #generate_single_parcellation(v,i,fs_string,subject_dir,subject_id,lh_annot_files,rh_annot_files,annot,aseg_output)
    # import multiprocessing as mp
    # pool = mp.Pool(processes=nscales)
    # # results = pool.apply(generate_single_parcellation, args=(v,i,fs_string,subject_dir,subject_id,)) for i in range(0,nscales)]
    #
    # job_args = [(v,i,fs_string,subject_dir,subject_id,) for i in range(0,nscales)]
    # pool.map(generate_single_parcellation,job_args)

    # # Start the processes (i.e. calculate the random number lists)
	# for j in jobs:
	# 	j.start()
    #
	# Ensure all of the processes have finished
	for j in jobs:
		j.join()

    mri_cmd = ['mri_convert','-i',op.join(subject_dir,'mri','ribbon.mgz'),'-o',op.join(subject_dir,'mri','ribbon.nii.gz')]
    subprocess.check_call(mri_cmd)

    print("[ DONE ]")



def create_wm_mask(subject_id, subjects_dir):
    print("Create white matter mask")

    fs_dir = op.join(subjects_dir,subject_id)

    # load ribbon as basis for white matter mask
    fsmask = ni.load(op.join(fs_dir, 'mri', 'ribbon.nii.gz'))
    fsmaskd = fsmask.get_data()

    wmmask = np.zeros( fsmask.get_data().shape )

    # these data is stored and could be extracted from fs_dir/stats/aseg.txt

    # extract right and left white matter
    idx_lh = np.where(fsmaskd == 120)
    idx_rh = np.where(fsmaskd == 20)

    wmmask[idx_lh] = 1
    wmmask[idx_rh] = 1

    # remove subcortical nuclei from white matter mask
    aseg = ni.load(op.join(fs_dir, 'mri', 'aseg.nii.gz'))
    asegd = aseg.get_data()

    try:
        import scipy.ndimage.morphology as nd
    except ImportError:
        raise Exception('Need scipy for binary erosion of white matter mask')

    # need binary erosion function
    imerode = nd.binary_erosion

    # ventricle erosion
    csfA = np.zeros( asegd.shape )
    csfB = np.zeros( asegd.shape )

    # structuring elements for erosion
    se1 = np.zeros( (3,3,5) )
    se1[1,:,2] = 1; se1[:,1,2] = 1; se1[1,1,:] = 1
    se = np.zeros( (3,3,3) )
    se[1,:,1] = 1; se[:,1,1] = 1; se[1,1,:] = 1

    # lateral ventricles, thalamus proper and caudate
    # the latter two removed for better erosion, but put back afterwards
    idx = np.where( (asegd == 4) |
                    (asegd == 43) |
                    (asegd == 11) |
                    (asegd == 50) |
                    (asegd == 31) |
                    (asegd == 63) |
                    (asegd == 10) |
                    (asegd == 49) )
    csfA[idx] = 1
    img = ni.Nifti1Image(csfA, aseg.get_affine(), aseg.get_header())
    ni.save(img, op.join(fs_dir, 'mri', 'csf_mask.nii.gz'))
    csfA = imerode(imerode(csfA, se1),se)

    # thalmus proper and cuadate are put back because they are not lateral ventricles
    idx = np.where( (asegd == 11) |
                    (asegd == 50) |
                    (asegd == 10) |
                    (asegd == 49) )
    csfA[idx] = 0

    # REST CSF, IE 3RD AND 4TH VENTRICULE AND EXTRACEREBRAL CSF
    idx = np.where( (asegd == 5) |
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
    for i in [5,14,15,24,44,72,75,76,213,221]:
        idx = np.where(asegd == i)
        csfB[idx] = 1

    # do not remove the subthalamic nucleus for now from the wm mask
    # 23, 60
    # would stop the fiber going to the segmented "brainstem"

    # grey nuclei, either with or without erosion
    gr_ncl = np.zeros( asegd.shape )

    # with erosion
    for i in [10,11,12,49,50,51]:
        idx = np.where(asegd == i)
        # temporary volume
        tmp = np.zeros( asegd.shape )
        tmp[idx] = 1
        tmp = imerode(tmp,se)
        idx = np.where(tmp == 1)
        gr_ncl[idx] = 1

    # without erosion
    for i in [13,17,18,26,52,53,54,58]:
        idx = np.where(asegd == i)
        gr_ncl[idx] = 1

    # remove remaining structure, e.g. brainstem
    remaining = np.zeros( asegd.shape )
    idx = np.where( asegd == 16 )
    remaining[idx] = 1

    # now remove all the structures from the white matter
    idx = np.where( (csfA != 0) | (csfB != 0) | (gr_ncl != 0) | (remaining != 0) )
    wmmask[idx] = 0
    print("Removing lateral ventricles and eroded grey nuclei and brainstem from white matter mask")

    # ADD voxels from 'cc_unknown.nii.gz' dataset
    ccun = ni.load(op.join(fs_dir, 'label', 'cc_unknown.nii.gz'))
    ccund = ccun.get_data()
    idx = np.where(ccund != 0)
    print("Add corpus callosum and unknown to wm mask")
    wmmask[idx] = 1
    # XXX add unknown dilation for connecting corpus callosum?
#    se2R = zeros(15,3,3); se2R(8:end,2,2)=1;
#    se2L = zeros(15,3,3); se2L(1:8,2,2)=1;
#    temp = (cc_unknown.img==1 | cc_unknown.img==2);
#    fsmask.img(imdilate(temp,se2R))    =  1;
#    fsmask.img(imdilate(temp,se2L))    =  1;
#    fsmask.img(cc_unknown.img==3)    =  1;
#    fsmask.img(cc_unknown.img==4)    =  1;

    # XXX: subtracting wmmask from ROI. necessary?
    for parkey, parval in get_parcellation('Lausanne2008').items():

        # check if we should subtract the cortical rois from this parcellation
        if parval.has_key('subtract_from_wm_mask'):
            if not bool(int(parval['subtract_from_wm_mask'])):
                continue
        else:
            continue

        print("Loading %s to subtract cortical ROIs from white matter mask" % ('ROI_%s.nii.gz' % parkey) )
        roi = ni.load(op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % parkey))
        roid = roi.get_data()

        assert roid.shape[0] == wmmask.shape[0]

        pg = nx.read_graphml(parval['node_information_graphml'])

        for brk, brv in pg.nodes(data=True):

            if brv['dn_region'] == 'cortical':

                print("Subtracting region %s with intensity value %s" % (brv['dn_region'], brv['dn_correspondence_id']))

                idx = np.where(roid == int(brv['dn_correspondence_id']))
                wmmask[idx] = 0

    # output white matter mask. crop and move it afterwards
    wm_out = op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz')
    img = ni.Nifti1Image(wmmask, fsmask.get_affine(), fsmask.get_header() )
    print("Save white matter mask: %s" % wm_out)
    ni.save(img, wm_out)

    # Convert whole brain mask
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','brainmask.mgz'),'-o',op.join(fs_dir,'mri','brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)
    mri_cmd = ['fslmaths',op.join(fs_dir,'mri','brainmask.nii.gz'),'-bin',op.join(fs_dir,'mri','brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)

def create_wm_mask_v2(subject_id, subjects_dir):
    print("Create white matter mask")

    fs_dir = op.join(subjects_dir,subject_id)

    print("FS dir: %s"%fs_dir)

    # load ribbon as basis for white matter mask
    print("load ribbon")
    fsmask = ni.load(op.join(fs_dir, 'mri', 'ribbon.nii.gz'))
    fsmaskd = fsmask.get_data()

    wmmask = np.zeros( fsmask.get_data().shape )

    # these data is stored and could be extracted from fs_dir/stats/aseg.txt

    #FIXME understand when ribbon file has default value or has "aseg" value
    # extract right and left white matter
    print("Extract right and left wm")
    #Ribbon labels by default
    if fsmaskd.max() == 120:
        idx_lh = np.where(fsmaskd == 120)
        idx_rh = np.where(fsmaskd == 20)
    #Ribbon label w.r.t aseg label
    else:
        idx_lh = np.where(fsmaskd == 41)
        idx_rh = np.where(fsmaskd == 2)

    # extract right and left
    wmmask[idx_lh] = 1
    wmmask[idx_rh] = 1

    # remove subcortical nuclei from white matter mask
    print("Load aseg")
    aseg = ni.load(op.join(fs_dir, 'mri', 'aseg.nii.gz'))
    asegd = aseg.get_data()

    try:
        import scipy.ndimage.morphology as nd
    except ImportError:
        raise Exception('Need scipy for binary erosion of white matter mask')

    # need binary erosion function
    imerode = nd.binary_erosion

    # ventricle erosion
    print("Ventricle erosion")
    csfA = np.zeros( asegd.shape )
    csfB = np.zeros( asegd.shape )

    # structuring elements for erosion
    se1 = np.zeros( (3,3,5) )
    se1[1,:,2] = 1; se1[:,1,2] = 1; se1[1,1,:] = 1
    se = np.zeros( (3,3,3) )
    se[1,:,1] = 1; se[:,1,1] = 1; se[1,1,:] = 1

    # lateral ventricles, thalamus proper and caudate
    # the latter two removed for better erosion, but put back afterwards
    idx = np.where( (asegd == 4) |
                    (asegd == 43) |
                    (asegd == 11) |
                    (asegd == 50) |
                    (asegd == 31) |
                    (asegd == 63) |
                    (asegd == 10) |
                    (asegd == 49) )
    csfA[idx] = 1

    print("Save CSF mask")
    img = ni.Nifti1Image(csfA, aseg.get_affine(), aseg.get_header())
    ni.save(img, op.join(fs_dir, 'mri', 'csf_mask.nii.gz'))
    csfA = imerode(imerode(csfA, se1),se)

    # thalmus proper and cuadate are put back because they are not lateral ventricles
    idx = np.where( (asegd == 11) |
                    (asegd == 50) |
                    (asegd == 10) |
                    (asegd == 49) )
    csfA[idx] = 0

    # REST CSF, IE 3RD AND 4TH VENTRICULE AND EXTRACEREBRAL CSF
    idx = np.where( (asegd == 5) |
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
    for i in [5,14,15,24,44,72,75,76,213,221]:
        idx = np.where(asegd == i)
        csfB[idx] = 1

    # do not remove the subthalamic nucleus for now from the wm mask
    # 23, 60
    # would stop the fiber going to the segmented "brainstem"

    # grey nuclei, either with or without erosion
    print("grey nuclei, either with or without erosion")
    gr_ncl = np.zeros( asegd.shape )

    # with erosion
    for i in [10,11,12,49,50,51]:
        idx = np.where(asegd == i)
        # temporary volume
        tmp = np.zeros( asegd.shape )
        tmp[idx] = 1
        tmp = imerode(tmp,se)
        idx = np.where(tmp == 1)
        gr_ncl[idx] = 1

    # without erosion
    for i in [13,17,18,26,52,53,54,58]:
        idx = np.where(asegd == i)
        gr_ncl[idx] = 1

    # remove remaining structure, e.g. brainstem
    print("remove remaining structure, e.g. brainstem")
    remaining = np.zeros( asegd.shape )
    idx = np.where( asegd == 16 )
    remaining[idx] = 1

    # now remove all the structures from the white matter
    idx = np.where( (csfA != 0) | (csfB != 0) | (gr_ncl != 0) | (remaining != 0) )
    wmmask[idx] = 0
    print("Removing lateral ventricles and eroded grey nuclei and brainstem from white matter mask")

    # ADD voxels from 'cc_unknown.nii.gz' dataset
    # ccun = ni.load(op.join(fs_dir, 'label', 'cc_unknown.nii.gz'))
    # ccund = ccun.get_data()
    # idx = np.where(ccund != 0)
    # print("Add corpus callosum and unknown to wm mask")
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
    # print("Save white matter mask: %s" % wm_out)
    # ni.save(img, wm_out)

    # Extract cortical gray matter mask
    # remove remaining structure, e.g. brainstem
    gmmask = np.zeros( asegd.shape )

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
    #     print("Loading %s to subtract cortical ROIs from white matter mask" % ('ROI_%s.nii.gz' % parkey) )
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
    #             print("Subtracting region %s with intensity value %s" % (brv['dn_region'], brv['dn_multiscaleID']))
    #
    #             idx = np.where(roid == int(brv['dn_multiscaleID']))
    #             wmmask[idx] = 0
    #             gmmask[idx] = 1

    # output white matter mask. crop and move it afterwards
    wm_out = op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz')
    img = ni.Nifti1Image(wmmask, fsmask.get_affine(), fsmask.get_header() )
    print("Save white matter mask: %s" % wm_out)
    ni.save(img, wm_out)

    gm_out = op.join(fs_dir, 'mri', 'gmmask.nii.gz')
    img = ni.Nifti1Image(gmmask, fsmask.get_affine(), fsmask.get_header() )
    print("Save gray matter mask: %s" % gm_out)
    ni.save(img, gm_out)

    # Convert whole brain mask
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','brainmask.mgz'),'-o',op.join(fs_dir,'mri','brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)
    mri_cmd = ['fslmaths',op.join(fs_dir,'mri','brainmask.nii.gz'),'-bin',op.join(fs_dir,'mri','brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)

def crop_and_move_datasets(parcellation_scheme,subject_id, subjects_dir):
    fs_dir = op.join(subjects_dir,subject_id)

    print("Cropping datasets")

    # datasets to crop and move: (from, to)
    ds = [
          (op.join(fs_dir, 'mri', 'aseg.nii.gz'), 'aseg.nii.gz'),
          (op.join(fs_dir, 'mri', 'ribbon.nii.gz'), 'ribbon.nii.gz'),
          (op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz'), 'fsmask_1mm.nii.gz'),
          (op.join(fs_dir, 'mri', 'gmmask.nii.gz'), 'gmmask.nii.gz'),
          ]
    if parcellation_scheme == 'Lausanne2008':
        ds.append( (op.join(fs_dir, 'label', 'cc_unknown.nii.gz'), 'cc_unknown.nii.gz') )
        for p in get_parcellation('Lausanne2008').keys():
            ds.append( (op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % p), 'ROI_HR_th_%s.nii.gz' % p) )
            ds.append( (op.join(fs_dir, 'label', 'ROIv_%s.nii.gz' % p), 'ROIv_HR_th_%s.nii.gz' % p) )
    elif parcellation_scheme == 'Lausanne2018':
        for p in get_parcellation('Lausanne2018').keys():
            #ds.append( (op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % p), 'ROI_HR_th_%s.nii.gz' % p) )
            ds.append( (op.join(fs_dir, 'mri','ROIv_%s.nii.gz' % p), 'ROIv_HR_th_%s.nii.gz' % p) )
#        try:
#            os.makedirs(op.join('.', p))
#        except:
#            pass

    orig = op.join(fs_dir, 'mri', 'orig', '001.mgz')

    for d in ds:
        print("Processing %s:" % d[0])

        # does it exist at all?
        if not op.exists(d[0]):
            raise Exception('File %s does not exist.' % d[0])
        # reslice to original volume because the roi creation with freesurfer
        # changed to 256x256x256 resolution
        #mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, d[0], d[1])
        #runCmd( mri_cmd,log )
        mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'nearest', d[0], '-nc', d[1]]
        subprocess.check_call(mri_cmd)

    ds =  [(op.join(fs_dir, 'mri', 'fsmask_1mm_eroded.nii.gz'), 'wm_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'csf_mask_eroded.nii.gz'), 'csf_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask_eroded.nii.gz'), 'brain_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask.nii.gz'), 'brain_mask.nii.gz')]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'nearest', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)

    ds =  [(op.join(fs_dir, 'mri', 'T1.nii.gz'), 'T1.nii.gz'),
          (op.join(fs_dir, 'mri', 'brain.nii.gz'), 'brain.nii.gz'),
          ]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'cubic', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)


def generate_WM_and_GM_mask(subject_id, subjects_dir):
    fs_dir = op.join(subjects_dir,subject_id)

    print("Create the WM and GM mask")

    # need to convert
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','aparc+aseg.mgz'),'-o',op.join(fs_dir,'mri','aparc+aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    fout = op.join(fs_dir, 'mri', 'aparc+aseg.nii.gz')
    niiAPARCimg = ni.load(fout)
    niiAPARCdata = niiAPARCimg.get_data()

    # mri_convert aparc+aseg.mgz aparc+aseg.nii.gz
    WMout = op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz')

    #%% label mapping
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

    MAPPING = [[1,2012],[2,2019],[3,2032],[4,2014],[5,2020],[6,2018],[7,2027],[8,2028],[9,2003],[10,2024],[11,2017],[12,2026],
               [13,2002],[14,2023],[15,2010],[16,2022],[17,2031],[18,2029],[19,2008],[20,2025],[21,2005],[22,2021],[23,2011],
               [24,2013],[25,2007],[26,2016],[27,2006],[28,2033],[29,2009],[30,2015],[31,2001],[32,2030],[33,2034],[34,2035],
               [35,49],[36,50],[37,51],[38,52],[39,58],[40,53],[41,54],[42,1012],[43,1019],[44,1032],[45,1014],[46,1020],[47,1018],
               [48,1027],[49,1028],[50,1003],[51,1024],[52,1017],[53,1026],[54,1002],[55,1023],[56,1010],[57,1022],[58,1031],
               [59,1029],[60,1008],[61,1025],[62,1005],[63,1021],[64,1011],[65,1013],[66,1007],[67,1016],[68,1006],[69,1033],
               [70,1009],[71,1015],[72,1001],[73,1030],[74,1034],[75,1035],[76,10],[77,11],[78,12],[79,13],[80,26],[81,17],
               [82,18],[83,16]]

    WM = [2, 29, 32, 41, 61, 64, 59, 60, 27, 28] +  range(77,86+1) + range(100, 117+1) + range(155,158+1) + range(195,196+1) + range(199,200+1) + range(203,204+1) + [212, 219, 223] + range(250,255+1)
    # add
    # 59  Right-Substancia-Nigra
    # 60  Right-VentralDC
    # 27  Left-Substancia-Nigra
    # 28  Left-VentralDC

    print("WM mask....")
    #%% create WM mask
    niiWM = np.zeros( niiAPARCdata.shape, dtype = np.uint8 )

    for i in WM:
        niiWM[niiAPARCdata == i] = 1

    # we do not add subcortical regions
#    for i in SUBCORTICAL[1]:
#         niiWM[niiAPARCdata == i] = 1

    img = ni.Nifti1Image(niiWM, niiAPARCimg.get_affine(), niiAPARCimg.get_header())
    print("Save to: " + WMout)
    ni.save(img, WMout)

    print("GM mask....")
    #%% create GM mask (CORTICAL+SUBCORTICAL)
    #%  -------------------------------------
    for park in get_parcellation('NativeFreesurfer').keys():
        print("Parcellation: " + park)
        GMout = op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' % park)

        niiGM = np.zeros( niiAPARCdata.shape, dtype = np.uint8 )

        for ma in MAPPING:
            niiGM[ niiAPARCdata == ma[1]] = ma[0]

#        # % 33 cortical regions (stored in the order of "parcel33")
#        for idx,i in enumerate(CORTICAL[1]):
#            niiGM[ niiAPARCdata == (2000+i)] = CORTICAL[2][idx] # RIGHT
#            niiGM[ niiAPARCdata == (1000+i)] = CORTICAL[2][idx] + 41 # LEFT
#
#        #% subcortical nuclei
#        for idx,i in enumerate(SUBCORTICAL[1]):
#            niiGM[ niiAPARCdata == i ] = SUBCORTICAL[2][idx]
#
#        # % other region to account for in the GM
#        for idx, i in enumerate(OTHER[1]):
#            niiGM[ niiAPARCdata == i ] = OTHER[2][idx]

        print("Save to: " + GMout)
        img = ni.Nifti1Image(niiGM, niiAPARCimg.get_affine(), niiAPARCimg.get_header())
        ni.save(img, GMout)

    # Create CSF mask
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','aseg.mgz'),'-o',op.join(fs_dir,'mri','aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    asegfile = op.join(fs_dir,'mri','aseg.nii.gz')
    aseg = ni.load( asegfile ).get_data().astype( np.uint32 )
    idx = np.where( (aseg == 4) |
                    (aseg == 43) |
                    (aseg == 11) |
                    (aseg == 50) |
                    (aseg == 31) |
                    (aseg == 63) |
                    (aseg == 10) |
                    (aseg == 49) )
    er_mask = np.zeros( aseg.shape )
    er_mask[idx] = 1
    img = ni.Nifti1Image(er_mask, ni.load( asegfile ).get_affine(), ni.load( asegfile ).get_header())
    ni.save(img, op.join(fs_dir, 'mri', 'csf_mask.nii.gz'))

    # Convert whole brain mask
    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','brainmask.mgz'),'-o',op.join(fs_dir,'mri','brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)
    mri_cmd = ['fslmaths',op.join(fs_dir,'mri','brainmask.nii.gz'),'-bin',op.join(fs_dir,'mri','brainmask.nii.gz')]
    subprocess.check_call(mri_cmd)

    print("[DONE]")

def crop_and_move_WM_and_GM(subject_id, subjects_dir):
    fs_dir = op.join(subjects_dir,subject_id)


#    print("Cropping and moving datasets to %s" % reg_path)

    # datasets to crop and move: (from, to)
    ds = [
          (op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz'), 'fsmask_1mm.nii.gz')
          ]

    for p in get_parcellation('NativeFreesurfer').keys():
        if not op.exists(op.join(fs_dir, 'mri',p)):
            os.makedirs(op.join(fs_dir, 'mri',p))
        ds.append( (op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' % p), op.join(fs_dir, 'mri',p, 'ROIv_HR_th.nii.gz')))
        ds.append( (op.join(fs_dir, 'mri', 'ROIv_%s.nii.gz' % p), 'ROIv_HR_th_%s.nii.gz' % p))

    orig = op.join(fs_dir, 'mri', 'orig', '001.mgz')

    for d in ds:
        print("Processing %s:" % d[0])

        # does it exist at all?
        if not op.exists(d[0]):
            raise Exception('File %s does not exist.' % d[0])
        # reslice to original volume because the roi creation with freesurfer
        # changed to 256x256x256 resolution
#        mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, d[0], d[1])
#        runCmd( mri_cmd,log )
        mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'nearest', d[0], '-nc', d[1]]
        subprocess.check_call(mri_cmd)

    ds =  [(op.join(fs_dir, 'mri', 'fsmask_1mm_eroded.nii.gz'), 'wm_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'csf_mask_eroded.nii.gz'), 'csf_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask_eroded.nii.gz'), 'brain_eroded.nii.gz'),
          (op.join(fs_dir, 'mri', 'brainmask.nii.gz'), 'brain_mask.nii.gz')]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'nearest', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)

    ds =  [(op.join(fs_dir, 'mri', 'T1.nii.gz'), 'T1.nii.gz'),
          (op.join(fs_dir, 'mri', 'brain.nii.gz'), 'brain.nii.gz'),
          ]

    for d in ds:
        if op.exists(d[0]):
            print("Processing %s:" % d[0])
            mri_cmd = ['mri_convert', '-rl', orig, '-rt', 'cubic', d[0], '-nc', d[1]]
            subprocess.check_call(mri_cmd)
