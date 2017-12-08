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

import scipy.ndimage.morphology as nd
import sys
from time import time

from nipype.interfaces.base import traits, BaseInterfaceInputSpec, TraitedSpec, BaseInterface, Directory, File, OutputMultiPath

from nipype.utils.logger import logging
iflogger = logging.getLogger('interface')

try:
    import scipy.ndimage.morphology as nd
except ImportError:
    raise Exception('Need scipy for binary erosion of white matter and CSF masks')

def erode_mask(maskFile):
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

class ParcellateInputSpec(BaseInterfaceInputSpec):
    subjects_dir = Directory(desc='Freesurfer main directory')
    subject_id = traits.String(mandatory=True, desc='Subject ID')
    parcellation_scheme = traits.Enum('Lausanne2008',['Lausanne2008','Lausanne2018','NativeFreesurfer'], usedefault = True)
    erode_masks = traits.Bool(False)


class ParcellateOutputSpec(TraitedSpec):
    #roi_files = OutputMultiPath(File(exists=True),desc='Region of Interest files for connectivity mapping')
    white_matter_mask_file = File(desc='White matter mask file')
    #cc_unknown_file = File(desc='Image file with regions labelled as unknown cortical structures',
    #                exists=True)
    #ribbon_file = File(desc='Image file detailing the cortical ribbon',
    #                exists=True)
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

        outputs['white_matter_mask_file'] = op.abspath('fsmask_1mm.nii.gz')
        #outputs['cc_unknown_file'] = op.abspath('cc_unknown.nii.gz')
        #outputs['ribbon_file'] = op.abspath('ribbon.nii.gz')
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
            'scale33' : {'number_of_regions' : 83,
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
                        'scale60' : {'number_of_regions' : 129,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution150','resolution150.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_60',
                                    'subtract_from_wm_mask' : 1,
                                     },
                        'scale125' : {'number_of_regions' : 234,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution258','resolution258.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_125',
                                    'subtract_from_wm_mask' : 1,
                                    },
                        'scale250' : {'number_of_regions' : 463,
                                    'node_information_graphml' : pkg_resources.resource_filename('cmtklib',op.join('data','parcellation','lausanne2008','resolution500','resolution500.graphml')),
                                    'surface_parcellation' : None,
                                    'volume_parcellation' : None,
                                    'fs_label_subdir_name' : 'regenerated_%s_250',
                                    'subtract_from_wm_mask' : 1,
                                    },
                        'scale500' : {'number_of_regions' : 1015,
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

        for brk, brv in pg.nodes_iter(data=True):   # slow loop

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

def create_roi_v2(subject_id, subjects_dir):
    """ Creates the ROI_%s.nii.gz files using the given parcellation information
    from networks. Iteratively create volume. """

    print("Create the ROIs:")
    fs_dir = op.join(subjects_dir,subject_id)
    if not ( op.isdir(fs_dir) and op.isdir(os.path.join(fs_dir, 'mri')) and op.isdir(os.path.join(fs_dir, 'surf')) ):
		print('Requested subject directory is invalid.')
    else:
        print('- Input subject directory:\n  {}\n'.format(fs_dir))

	# Check existence of required FreeSurfer recon-all output files
	this_file = 'mri/orig/001.mgz'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'mri/aseg.mgz'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'mri/orig.mgz'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'mri/ribbon.mgz'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/lh.pial'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/rh.pial'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/lh.smoothwm'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/rh.smoothwm'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/lh.sphere.reg'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/rh.sphere.reg'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/lh.white'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))
	this_file = 'surf/rh.white'
	if not os.path.isfile(os.path.join(fs_dir, this_file)):
		parser.error('"{0}" is a required input file!'.format(this_file))

	temp = re.split('\/',fs_dir)
	subject = temp[-1]
	if not subject:
		subject = temp[-2]
		fs_subj_dir = fs_dir[0:-len(subject)-1]
	else:
		fs_subj_dir = fs_dir[0:-len(subject)-1]
	print('- Subject identifier:\n  {}\n'.format(subject))

	# Define atlas variables
	paths, comp, pardic, parkeys = define_atlas_variables()

    # FreeSurfer directories and $SUBJECTS_DIR
    subject_dir = fs_dir
    fs_label_dir = os.path.join(fs_dir, 'label')
    fs_string = 'export SUBJECTS_DIR=' + fs_subj_dir
    print('- New FreeSurfer SUBJECTS_DIR:\n  {}\n'.format(fs_subj_dir))
    print('\nPROCESSING\n')

    # load aseg volume
    #aseg = ni.load(op.join(fs_dir, 'mri', 'aseg.nii.gz'))
    #asegd = aseg.get_data()	# numpy.ndarray

    # 1. Generate new annot files from FreeSurfer recon-all output
    # Loop over parcellation scales
    for out in comp:
        # Build new annotation files combining the recon-all segmentation (cortical surface) and the multi-scale gcs atlases 'Lausanne 2008'
        # mris_ca_label: for a single subject, produces an annotation file, in which each cortical surface vertex is assigned a neuroanatomical label (according to a given gcs atlas)
        #                Requires surf/?h.smoothwm, surf/?h.sphere.reg
        print(' ... generate new annot file {}\n'.format(out[2]))
        mris_cmd = fs_string + '; mris_ca_label "%s" %s "%s/surf/%s.sphere.reg" "%s" "%s" ' % (subject, out[0], subject_dir, out[0], out[5], os.path.join(fs_label_dir, out[2]))
        print mris_cmd
        process = subprocess.Popen(mris_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        proc_stdout = process.communicate()[0].strip()
        # if v:
        #     print proc_stdout
        #     print ' '

    # Path orig volume
    orig = os.path.join(subject_dir, 'mri', 'orig', '001.mgz')

    # extract cc and unknown to add to tractography mask, we do not want this as a region of interest
    # in FS 5.0, unknown and corpuscallosum are not available for the 35 scale (why?),
    # but for the other scales only, take the ones from _60
    # rhun = op.join(fs_dir, 'label', 'rh.unknown.label')
    # lhun = op.join(fs_dir, 'label', 'lh.unknown.label')
    # rhco = op.join(fs_dir, 'label', 'rh.corpuscallosum.label')
    # lhco = op.join(fs_dir, 'label', 'lh.corpuscallosum.label')
    # shutil.copy(op.join(fs_dir, 'label', 'regenerated_rh_2', 'rh.unknown.label'), rhun)
    # shutil.copy(op.join(fs_dir, 'label', 'regenerated_lh_2', 'lh.unknown.label'), lhun)
    # shutil.copy(op.join(fs_dir, 'label', 'regenerated_rh_2', 'rh.corpuscallosum.label'), rhco)
    # shutil.copy(op.join(fs_dir, 'label', 'regenerated_lh_2', 'lh.corpuscallosum.label'), lhco)
    #
    # mri_cmd = ['mri_label2vol','--label',rhun,'--label',lhun,'--label',rhco,'--label',lhco,'--temp',op.join(fs_dir, 'mri', 'orig.mgz'),'--o',op.join(fs_dir, 'label', 'cc_unknown.nii.gz'),'--identity']
    # subprocess.check_call(mri_cmd)

    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','ribbon.mgz'),'-o',op.join(fs_dir,'mri','ribbon.nii.gz')]
    subprocess.check_call(mri_cmd)

    mri_cmd = ['mri_convert','-i',op.join(fs_dir,'mri','aseg.mgz'),'-o',op.join(fs_dir,'mri','aseg.nii.gz')]
    subprocess.check_call(mri_cmd)

    shape = (25,25,25)
    center = np.array(shape) // 2
    # dist: distances from the center of the neighbourhood
    dist = np.zeros(shape, dtype='float32')
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(shape[2]):
                distxyz = center - [x,y,z]
                dist[x,y,z] = math.sqrt(np.sum(np.multiply(distxyz,distxyz)))

    # LOOP over parcellation SCALES
    for i,parkey in enumerate(parkeys):
        # Dictionary entry for current key
        parval = pardic[parkey]

        print('\n\n SCALE: {}\n'.format(parkey))

        if parkey!='scale5':
            # 2. Generate parcellation volume for current scale using mri_aparc2aseg
            # mri_aparc2aseg: maps the cortical labels from a cortical parcellation (annot) to the automatic segmentation volume (aseg)
            #                 Requires mri/aseg.mgz, mri/ribbon.mgz, surf/?h.pial, surf/?h.white and annot files generated in previous step
            # Path temporary file
            temp = os.path.join(fs_subj_dir, subject, 'mri/tmp.nii.gz')
            print(' ... generate new Nifti volume for parcellation {}\n'.format(parval['annotation']))
            mri_cmd = fs_string + '; mri_aparc2aseg --s "%s" --o "%s" --new-ribbon --annot "%s"' % (subject, temp, parval['annotation'])
            process = subprocess.Popen(mri_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            proc_stdout = process.communicate()[0].strip()
            # if v:
            #     print proc_stdout
            #     print ' '

            # 3. Re-assign regions' numerical ID using the information contianed in the graphml files
            #    of the multi-scale parcellation atlas
            #
            # Load parcellation Nifti 3D volume with FreeSurfer numerical IDs
            fsid = ni.load(temp)
            fsidd = fsid.get_data()	# numpy.ndarray
            # Header information
            hdr = fsid.get_header()
            hdr2 = hdr.copy()
            hdr2.set_data_dtype(np.uint16)

            # Create output volume for current parcellation
            rois = np.zeros( fsid.shape, dtype=np.int16 )

            # Read graphml information
            # (pg is a NetworkX graph)
            pg = nx.read_graphml(parval['node_information_graphml'])

            # LOOP over NODES in current parcellation scale
            print(' ... relabel brain regions according to {}:\n'.format(parval['node_information_graphml']))
            count = 0

            for brk, brv in pg.nodes_iter(data=True):
                count = count + 1
                print('      {} of {}\n'.format(count,pg.number_of_nodes()))
                idx = np.where(fsidd == int(brv['dn_fsID']))
                rois[idx] = int(brv['dn_multiscaleID'])
                # idx = np.where(fsidd == int(brv['dn_correspondence_id']))
                # rois[idx] = int(brv['dn_correspondence_id'])

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
            print("Save output image to %s" % out_roi)
            img = ni.Nifti1Image(newrois, fsid.get_affine(), hdr2)
            ni.save(img, out_roi)

            # 4. Store output volume
            print('\n ... crop and save output volume\n')
            out_vol_temp = os.path.join(subject_dir, 'mri/ROIv_%s.nii.gz' % parkey)
            img = ni.Nifti1Image(rois, fsid.get_affine(), hdr2)
            ni.save(img, out_vol_temp)

            # Crop mask to match orig-mgz volume
            out_vol = os.path.join(subject_dir, 'label', 'ROIv_%s.nii.gz' % parkey)
            mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, out_vol_temp, out_vol)
            process = subprocess.Popen(mri_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            proc_stdout = process.communicate()[0].strip()
            # if v:
            #     print proc_stdout
            #     print ' '

            # Delete temporary file
            #os.remove(temp)

        # Scale 5 needs a different processing as parcellaiton informaiton is spread over three distinct annot files
        else:
            # 2. Generate parcellation volumes for scale 5 using mri_aparc2aseg
            # mri_aparc2aseg: maps the cortical labels from a cortical parcellation (annot) to the automatic segmentation volume (aseg)
            #                 Requires mri/aseg.mgz, mri/ribbon.mgz, surf/?h.pial, surf/?h.white and annot files generated in previous step
            # Path temporary file
            temp = [os.path.join(fs_subj_dir, subject, 'mri/tmp1.nii.gz'),
                    os.path.join(fs_subj_dir, subject, 'mri/tmp2.nii.gz'),
                    os.path.join(fs_subj_dir, subject, 'mri/tmp3.nii.gz')]

            for k in range(0,3):
                print(' ... generate new Nifti volume for parcellation {}\n'.format(parval['annotation'][k]))
                mri_cmd = fs_string + '; mri_aparc2aseg --s "%s" --o "%s" --new-ribbon --annot "%s"' % (subject, temp[k], parval['annotation'][k])
                process = subprocess.Popen(mri_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
                proc_stdout = process.communicate()[0].strip()
                # if v:
                #     print proc_stdout
                #     print ' '    print("[ DONE ]")

            # 3. Re-assign regions' numerical ID using the information contianed in the graphml files
            #    of the multi-scale parcellation atlas
            #
            # Load parcellation Nifti 3D volumes (3 volumes for scale 5) with FreeSurfer numerical IDs
            fsid = ni.load(temp[0])
            fsidd1 = fsid.get_data()	# numpy.ndarray
            fsid = ni.load(temp[1])
            fsidd2 = fsid.get_data()
            fsid = ni.load(temp[2])
            fsidd3 = fsid.get_data()
            # Header information
            hdr = fsid.get_header()
            hdr2 = hdr.copy()
            hdr2.set_data_dtype(np.uint16)

            # Creat output volume for current parcellation
            rois = np.zeros( fsid.shape, dtype=np.int16 )

            # Read graphml information
            # (pg is a NetworkX graph)
            pg = nx.read_graphml(parval['node_information_graphml'])

            # LOOP over NODES in current parcellation scale
            print(' ... relabel brain regions according to {}:\n'.format(parval['node_information_graphml']))
            count = 0
            for brk, brv in pg.nodes_iter(data=True):
                count = count + 1
                print('      {} of {}\n'.format(count,pg.number_of_nodes()))

                if int(brv['dn_annotfile']) == 0 or int(brv['dn_annotfile']) == 1:
                    idx = np.where(fsidd1 == int(brv['dn_fsID']))
                elif int(brv['dn_annotfile']) == 2:
                    idx = np.where(fsidd2 == int(brv['dn_fsID']))
                else:
                    idx = np.where(fsidd3 == int(brv['dn_fsID']))

                rois[idx] = int(brv['dn_multiscaleID'])

            newrois = rois.copy()
            # store scale500 volume for correction on multi-resolution consistency
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
            print("Save output image to %s" % out_roi)
            img = ni.Nifti1Image(newrois, fsid.get_affine(), hdr2)
            ni.save(img, out_roi)

            # 4. Store output volume
            print('\n ... crop and save output volume\n')
            out_vol_temp = os.path.join(subject_dir, 'mri/ROIv_%s.nii.gz' % parkey)
            img = ni.Nifti1Image(newrois, fsid.get_affine(), hdr2)
            ni.save(img, out_vol_temp)

            # Crop mask to match orig-mgz volume
            out_vol = os.path.join(subject_dir, 'label', 'ROIv_%s.nii.gz' % parkey)
            mri_cmd = 'mri_convert -rl "%s" -rt nearest "%s" -nc "%s"' % (orig, out_vol_temp, out_vol)
            process = subprocess.Popen(mri_cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            proc_stdout = process.communicate()[0].strip()
            # if v:
            #     print proc_stdout
            #     print ' '

            # Delete temporary file
            #os.remove(temp[0])
            #os.remove(temp[1])
            #os.remove(temp[2])

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

        for brk, brv in pg.nodes_iter(data=True):

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

    # XXX: subtracting wmmask from ROI. necessary?
    for parkey, parval in get_parcellation('Lausanne2018').items():

        print parkey

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

        for brk, brv in pg.nodes_iter(data=True):

            if brv['dn_region'] == 'cortical':

                print("Subtracting region %s with intensity value %s" % (brv['dn_region'], brv['dn_multiscaleID']))

                idx = np.where(roid == int(brv['dn_multiscaleID']))
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

def crop_and_move_datasets(parcellation_scheme,subject_id, subjects_dir):
    fs_dir = op.join(subjects_dir,subject_id)

    print("Cropping datasets")

    # datasets to crop and move: (from, to)
    ds = [
          (op.join(fs_dir, 'mri', 'aseg.nii.gz'), 'aseg.nii.gz'),
          (op.join(fs_dir, 'mri', 'ribbon.nii.gz'), 'ribbon.nii.gz'),
          (op.join(fs_dir, 'mri', 'fsmask_1mm.nii.gz'), 'fsmask_1mm.nii.gz'),
          ]
    if parcellation_scheme == 'Lausanne2008':
        ds.append( (op.join(fs_dir, 'label', 'cc_unknown.nii.gz'), 'cc_unknown.nii.gz') )
        for p in get_parcellation('Lausanne2008').keys():
            ds.append( (op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % p), 'ROI_HR_th_%s.nii.gz' % p) )
            ds.append( (op.join(fs_dir, 'label', 'ROIv_%s.nii.gz' % p), 'ROIv_HR_th_%s.nii.gz' % p) )
    elif parcellation_scheme == 'Lausanne2018':
        for p in get_parcellation('Lausanne2018').keys():
            ds.append( (op.join(fs_dir, 'label', 'ROI_%s.nii.gz' % p), 'ROI_HR_th_%s.nii.gz' % p) )
            ds.append( (op.join(fs_dir, 'label', 'ROIv_%s.nii.gz' % p), 'ROIv_HR_th_%s.nii.gz' % p) )
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
