import numpy as np
import nibabel as ni

# Freesurfer subject dir
fs_dir =  '/home/localadmin/DATA/TestParc00008/derivatives/freesurfer-7.1.1/sub-TLE00008_ses-20101007/'
subjects_dir = '/home/localadmin/DATA/TestParc00008/derivatives/freesurfer-7.1.1/'
subject_id = 'sub-TLE00008_ses-20101007'
path_lh_hippocampal_subfields = '.'
path_rh_hippocampal_subfields = '.'
path_thalamus_nuclei = '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/parcThal/T1_class-thalamus_probtissue_maxprob.nii.gz'
path_brainstem_structures = '.'
path_input_rois =  ['/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/Lausanne2018_parcellation/ROIv_Lausanne2018_scale1.nii.gz', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/Lausanne2018_parcellation/ROIv_Lausanne2018_scale2.nii.gz', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/Lausanne2018_parcellation/ROIv_Lausanne2018_scale3.nii.gz', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/Lausanne2018_parcellation/ROIv_Lausanne2018_scale4.nii.gz', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/Lausanne2018_parcellation/ROIv_Lausanne2018_scale5.nii.gz']
path_create_colorLUT =  ['/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/parcCombiner/ROIv_Lausanne2018_scale1_FreeSurferColorLUT.txt', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/parcCombiner/ROIv_Lausanne2018_scale2_FreeSurferColorLUT.txt', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/parcCombiner/ROIv_Lausanne2018_scale3_FreeSurferColorLUT.txt', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/parcCombiner/ROIv_Lausanne2018_scale4_FreeSurferColorLUT.txt', '/home/localadmin/DATA/TestParc00008/derivatives/nipype-1.8.0/sub-TLE00008/ses-20101007/anatomical_pipeline/parcellation_stage/parcCombiner/ROIv_Lausanne2018_scale5_FreeSurferColorLUT.txt']
verbose_level = 2


print("Freesurfer subject directory: {}".format(fs_dir))

# Freesurfer IDs for subcortical structures
left_subc_ids = np.array([10, 11, 12, 13, 26, 18, 17])
left_subc_ids_2018_colors_r = np.array([0, 122, 236, 12, 255, 103, 220])
left_subc_ids_2018_colors_g = np.array([118, 186, 13, 48, 165, 255, 216])
left_subc_ids_2018_colors_b = np.array([14, 220, 176, 255, 0, 255, 20])
left_subcort_names = ["Left-Thalamus_Proper", "Left-Caudate", "Left-Putamen", "Left-Pallidum","Left-Accumbens_area", "Left-Amygdala", "Left-Hippocampus"]

right_subc_ids = np.array([49, 50, 51, 52, 58, 54, 53])
right_subc_ids_2018_colors_r = np.array([0, 122, 236, 12, 255, 103, 220])
right_subc_ids_2018_colors_g = np.array([118, 186, 13, 48, 165, 255, 216])
right_subc_ids_2018_colors_b = np.array([14, 220, 176, 255, 0, 255, 20])
right_subcort_names = ["Right-Thalamus_Proper", "Right-Caudate", "Right-Putamen", "Right-Pallidum", "Right-Accumbens_area", "Right-Amygdala", "Right-Hippocampus"]

# Amygdala and hippocampus swapped between Lausanne2008 and Lausanne2018
left_subc_ids_2008 = np.array([10, 11, 12, 13, 26, 17, 18])
left_subcort_2008_names = ["Left-Thalamus_Proper", "Left-Caudate", "Left-Putamen", "Left-Pallidum","Left-Accumbens_area", "Left-Hippocampus", "Left-Amygdala"]
right_subc_ids_2008 = np.array([49, 50, 51, 52, 58, 53, 54])
right_subcort_2008_names = ["Right-Thalamus_Proper", "Right-Caudate", "Right-Putamen", "Right-Pallidum","Right-Accumbens_area", "Right-Hippocampus", "Right-Amygdala"]

# Thalamic Nuclei
left_thalNuclei = np.array([1, 2, 3, 4, 5, 6, 7])
left_thalNuclei_colors_r = np.array([255, 0, 255, 255, 0, 255, 0])
left_thalNuclei_colors_g = np.array([0, 255, 255, 123, 255, 0, 0])
left_thalNuclei_colors_b = np.array([0, 0, 0, 0, 255, 255, 255])
left_thalNuclei_names = ["Left-Pulvinar", "Left-Anterior", "Left-Medio_Dorsal", "Left-Ventral_Latero_Dorsal","Left-Central_Lateral-Lateral_Posterior-Medial_Pulvinar","Left-Ventral_Anterior", "Left-Ventral_Latero_Ventral"]

right_thalNuclei = np.array([8, 9, 10, 11, 12, 13, 14])
right_thalNuclei_colors_r = np.array([255, 0, 255, 255, 0, 255, 0])
right_thalNuclei_colors_g = np.array([0, 255, 255, 123, 255, 0, 0])
right_thalNuclei_colors_b = np.array([0, 0, 0, 0, 255, 255, 255])
right_thalNuclei_names = ["Right-Pulvinar", "Right-Anterior", "Right-Medio_Dorsal","Right-Ventral_Latero_Dorsal","Right-Central_Lateral-Lateral_Posterior-Medial_Pulvinar","Right-Ventral_Anterior", "Right-Ventral_Latero_Ventral"]

# Hippocampus subfields
hippo_subf = np.array([203, 204, 205, 206, 208, 209, 210, 211, 212, 214, 215, 226])
hippo_subf_colors_r = np.array([255, 64, 0, 255, 0, 196, 32, 128, 204, 128, 128, 170])
hippo_subf_colors_g = np.array([255, 0, 0, 0, 128, 160, 200, 255, 153, 0, 32, 170])
hippo_subf_colors_b = np.array([0, 64, 255, 0, 0, 128, 255, 128, 204, 0, 255, 255])
left_hippo_subf_names = ["Left-Hippocampus_Parasubiculum", "Left-Hippocampus_Presubiculum","Left-Hippocampus_Subiculum", "Left-Hippocampus_CA1", "Left-Hippocampus_CA3","Left-Hippocampus_CA4","Left-Hippocampus_GCDG", "Left-Hippocampus_HATA", "Left-Hippocampus_Fimbria","Left-Hippocampus_Molecular_layer_HP", "Left-Hippocampus_Hippocampal_fissure","Left-Hippocampus_Tail"]
right_hippo_subf_names = ["Right-Hippocampus_Parasubiculum", "Right-Hippocampus_Presubiculum","Right-Hippocampus_Subiculum", "Right-Hippocampus_CA1", "Right-Hippocampus_CA3","Right-Hippocampus_CA4","Right-Hippocampus_GCDG", "Right-Hippocampus_HATA", "Right-Hippocampus_Fimbria","Right-Hippocampus_Molecular_layer_HP", "Right-Hippocampus_Hippocampal_fissure","Right-Hippocampus_Tail"]

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
brainstem_names = ["Brain_Stem-Midbrain","Brain_Stem-Pons", "Brain_Stem-Medulla", "Brain_Stem-SCP"]

lh_subfield_defined = False
# Reading Subfields Images
try:
    img_sublh = ni.load(path_lh_hippocampal_subfields)
    img_data_sublh = img_sublh.get_data()
    lh_subfield_defined = True
except TypeError:
    print('Subfields image (Left hemisphere) not provided')

    rh_subfield_defined = False
    try:
        img_subrh = ni.load(path_rh_hippocampal_subfields)
        img_data_subrh = img_subrh.get_data()
        rh_subfield_defined = True
    except TypeError:
        print('Subfields image (Right hemisphere) not provided')

    thalamus_nuclei_defined = False
    # Reading  Nuclei
    try:
        Vthal = ni.load(path_thalamus_nuclei)
        img_data_thal = Vthal.get_data()
        thalamus_nuclei_defined = True
    except TypeError:
        print('Thalamic nuclei image not provided')

    brainstem_defined = False
    # Reading Stem Image
    try:
        img_stem = ni.load(path_brainstem_structures)
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
    for roi_fname in path_input_rois:
        if 'scale1' in roi_fname:
            roi1_fname = roi_fname
            break

    # Dilate third ventricle and intersect with right and left ventral DC to get voxels of left and right hypothalamus
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


    tmp = ni.load(third_vent_dil)
    indrhypothal = np.where((tmp == 1) & (img_data == right_ventral))
    indlhypothal = np.where((tmp == 1) & (img_data == left_ventral))
    del tmp

    f_color_lut = None
    f_graphml = None

    print("create color look up table : ", path_create_colorLUT)

    for _, roi in enumerate(path_input_rois):
        # colorLUT creation if enabled
        if path_create_colorLUT:
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

           
        # Reading Cortical Parcellation
        img_v = ni.load(roi)
        img_data = img_v.get_data()

        # Replacing the brain stem (Stem is replaced by its own parcellation.
        # Mismatch between both global volumes, mainly due to partial volume
        # effect in the global stem parcellation)
        indrep = np.where(img_data == 16)
        img_data[indrep] = 0

    for _, roi in sorted(enumerate(path_input_rois)):
        # colorLUT creation if enabled
        if path_create_colorLUT:
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
        if path_create_colorLUT:
            f_color_lut.write("# Right Hemisphere. Cortical Structures \n")
            outprefix_name = Path(roi).name.split(".")[0]
            for elem in outprefix_name.split("_"):
                if "scale" in elem:
                    scale = elem
            rh_annot_file = 'rh.lausanne2018.%s.annot' % scale
            iflogger.info("  > Load {}".format(rh_annot_file))
            rh_annot = ni.freesurfer.io.read_annot(
                op.join(subjects_dir, subject_id, 'label', rh_annot_file))
            rgb_table = rh_annot[1][1:, 0:3] 
            roi_names = rh_annot[2][1:]
            # roi_labels = rh_annot[0][1:]

            for label, name in enumerate(roi_names):
                name = 'ctx-rh-{}'.format(name.decode())
                if path_create_colorLUT:
                    r = rgb_table[label, 0]
                    g = rgb_table[label, 1]
                    b = rgb_table[label, 2]

                    f_color_lut.write('{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(
                        label + 1, name, r, g, b))


            if path_create_colorLUT:
                f_color_lut.write("\n")

        # Relabelling Thalamic Nuclei
        if thalamus_nuclei_defined:
            if path_create_colorLUT:
                f_color_lut.write(
                    "# Right Hemisphere. Subcortical Structures (Thalamic Nuclei) \n")

            new_labels = np.arange(
                nlabel + 1, nlabel + 1 + right_thalNuclei.shape[0])

            i = 0
            for lab in right_thalNuclei:
                if verbose_level == 2:
                    iflogger.info(
                        "  > Update right thalamic nucleus label ({} -> {})".format(lab, new_labels[i]))

                if path_create_colorLUT:
                    r = right_thalNuclei_colors_r[i]
                    g = right_thalNuclei_colors_g[i]
                    b = right_thalNuclei_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), right_thalNuclei_names[i],
                                                                         r, g, b))


                ind = np.where(img_data_thal == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
            nlabel = img_data_out.max()

            if path_create_colorLUT:
                f_color_lut.write("\n")

        # Relabelling Subcortical Structures
        if path.create_colorLUT:
            f_color_lut.write(
                "# Right Hemisphere. Subcortical Structures \n")

        new_labels = np.arange(nlabel + 1, nlabel + 1 + left_subc_labels.shape[0])

        i = 0
        for lab in right_subc_labels:
            if verbose_level == 2:
                iflogger.info(
                    "  > Update right subcortical label ({} -> {})".format(lab, new_labels[i]))

            if path_create_colorLUT:
                r = right_subc_ids_2018_colors_r[i]
                g = right_subc_ids_2018_colors_g[i]
                b = right_subc_ids_2018_colors_b[i]
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), right_subcort_names[i], r, g,
                                                                     b))

            ind = np.where(img_data == lab)
            img_data_out[ind] = new_labels[i]
            i += 1
        nlabel = img_data_out.max()

        if path_create_colorLUT:
            f_color_lut.write("\n")

        # Relabelling Subfields
        if rh_subfield_defined:
            if path_create_colorLUT:
                f_color_lut.write(
                    "# Right Hemisphere. Subcortical Structures (Hippocampal Subfields) \n")

            new_labels = np.arange(
                nlabel + 1, nlabel + 1 + hippo_subf.shape[0])
            i = 0
            for lab in hippo_subf:
                if verbose_level == 2:
                    iflogger.info(
                        "  > Update right hippo subfield label ({} -> {})".format(lab, new_labels[i]))

                if path_create_colorLUT:
                    # if len(ind) > 0:
                    r = hippo_subf_colors_r[i]
                    g = hippo_subf_colors_g[i]
                    b = hippo_subf_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), right_hippo_subf_names[i],
                                                                         r, g, b))

                ind = np.where(img_data_subrh == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
            nlabel = img_data_out.max()

            if path_create_colorLUT:
                f_color_lut.write("\n")

        if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
            # Relabelling Right VentralDC
            new_labels = np.arange(nlabel + 1, nlabel + 2)
            if verbose_level == 2:
                iflogger.info(
                    "  > Update right ventral DC label ({} -> {})".format(right_ventral, new_labels[0]))
            ind = np.where(img_data == right_ventral)
            img_data_out[ind] = new_labels[0]
            nlabel = img_data_out.max()

            # ColorLUT (right ventral DC)
            if path_create_colorLUT:
                f_color_lut.write(
                    "# Right Hemisphere. Ventral Diencephalon \n")
                r = right_ventral_colors_r
                g = right_ventral_colors_g
                b = right_ventral_colors_b
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), right_ventral_names[0], r, g,
                                                                     b))
                f_color_lut.write("\n")



        if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
            # Relabelling Right Hypothalamus
            new_labels = np.arange(nlabel + 1, nlabel + 2)
            if verbose_level == 2:
                iflogger.info(
                    "  > Update right hypothalamus label ({} -> {})".format(right_ventral, new_labels[0]))
            img_data_out[indrhypothal] = new_labels[0]
            nlabel = img_data_out.max()

            # ColorLUT (right hypothalamus)
            if path_create_colorLUT:
                f_color_lut.write("# Right Hemisphere. Hypothalamus \n")
                r = hypothal_colors_r
                g = hypothal_colors_g
                b = hypothal_colors_b
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), right_hypothal_names[0], r, g,
                                                                     b))
                f_color_lut.write("\n")

        # Processing Left Hemisphere
        # Relabelling Left hemisphere
        ind = np.where((img_data > 1000) & (img_data < 2000))
        img_data_out[ind] = (img_data[ind] - 1000 + nlabel)
        old_nlabel = nlabel + 1 ### changed 18.02
        #old_nlabel = nlabel
        nlabel = img_data_out.max()

        # ColorLUT (cortical)
        if path_create_colorLUT:
            f_color_lut.write("# Left Hemisphere. Cortical Structures \n")
            outprefix_name = Path(roi).name.split(".")[0]
            for elem in outprefix_name.split("_"):
                if "scale" in elem:
                    scale = elem
            lh_annot_file = 'lh.lausanne2018.%s.annot' % scale
            iflogger.info("  > Load {}".format(lh_annot_file))
            lh_annot = ni.freesurfer.io.read_annot(
                op.join(subjects_dir, subject_id, 'label', lh_annot_file))
            rgb_table = lh_annot[1][1:, 0:3] ## 25.02
            roi_names = lh_annot[2][1:]

            for label, name in enumerate(roi_names):
                name = 'ctx-lh-{}'.format(name.decode())

                if path_create_colorLUT:
                    r = rgb_table[label, 0]
                    g = rgb_table[label, 1]
                    b = rgb_table[label, 2]

                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(label + old_nlabel + 1), name, r, g, b))

            if path_create_colorLUT:
                f_color_lut.write("\n")

        # Relabelling Thalamic Nuclei
        if thalamus_nuclei_defined:
            if path_create_colorLUT:
                f_color_lut.write(
                    "# Left Hemisphere. Subcortical Structures (Thalamic Nuclei) \n")

            nlabel = nlabel + 1 ## added 25.02
            new_labels = np.arange(
                nlabel + 1, nlabel + 1 + left_thalNuclei.shape[0])
            i = 0
            for lab in left_thalNuclei:
                if verbose_level == 2:
                    iflogger.info(
                        "  > Update left thalamic nucleus label ({} -> {})".format(lab, new_labels[i]))

                if path_create_colorLUT:
                    r = left_thalNuclei_colors_r[i]
                    g = left_thalNuclei_colors_g[i]
                    b = left_thalNuclei_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), left_thalNuclei_names[i], r,
                                                                         g, b))


                ind = np.where(img_data_thal == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
            nlabel = img_data_out.max()

            if path_create_colorLUT:
                f_color_lut.write("\n")

        # Relabelling Subcortical Structures
        if path_create_colorLUT:
            f_color_lut.write(
                "# Left Hemisphere. Subcortical Structures \n")

        new_labels = np.arange(nlabel + 1, nlabel + 1 + left_subc_labels.shape[0])

        i = 0
        for lab in left_subc_labels:
            if verbose_level == 2:
                iflogger.info(
                    "  > Update left subcortical label ({} -> {})".format(lab, new_labels[i]))

            if path_create_colorLUT:
                r = left_subc_ids_2018_colors_r[i]
                g = left_subc_ids_2018_colors_g[i]
                b = left_subc_ids_2018_colors_b[i]
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), left_subcort_names[i], r, g, b))


            ind = np.where(img_data == lab)
            img_data_out[ind] = new_labels[i]
            i += 1
        nlabel = img_data_out.max()

        if path_create_colorLUT:
            f_color_lut.write("\n")

        # Relabelling Subfields
        if lh_subfield_defined:
            if path_create_colorLUT:
                f_color_lut.write(
                    "# Left Hemisphere. Subcortical Structures (Hippocampal Subfields) \n")

            new_labels = np.arange(
                nlabel + 1, nlabel + 1 + hippo_subf.shape[0])
            i = 0
            for lab in hippo_subf:
                if verbose_level == 2:
                    iflogger.info(
                        "  > Update left hippo subfield label ({} -> {})".format(lab, new_labels[i]))

                if path_create_colorLUT:
                    r = hippo_subf_colors_r[i]
                    g = hippo_subf_colors_g[i]
                    b = hippo_subf_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), left_hippo_subf_names[i], r,
                                                                         g, b))

                ind = np.where(img_data_sublh == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
            nlabel = img_data_out.max()
            # newIds_LH_subFields = new_labels

            if path_create_colorLUT:
                f_color_lut.write("\n")

        if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
            # Relabelling Left VentralDC
            new_labels = np.arange(nlabel + 1, nlabel + 2)
            if verbose_level == 2:
                iflogger.info(
                    "  > Update left ventral DC label ({} -> {})".format(left_ventral, new_labels[0]))
            ind = np.where(img_data == left_ventral)
            img_data_out[ind] = new_labels[0]
            nlabel = img_data_out.max()
            # newIds_LH_ventralDC = new_labels

            # ColorLUT (left ventral DC)
            if path_create_colorLUT:
                f_color_lut.write(
                    "# Left Hemisphere. Ventral Diencephalon \n")
                r = left_ventral_colors_r
                g = left_ventral_colors_g
                b = left_ventral_colors_b
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), left_ventral_names[0], r, g, b))
                f_color_lut.write("\n")

        if thalamus_nuclei_defined or brainstem_defined or (lh_subfield_defined and rh_subfield_defined):
            # Relabelling Left Hypothalamus
            new_labels = np.arange(nlabel + 1, nlabel + 2)
            if verbose_level == 2:
                iflogger.info(
                    "  > Update left hypothalamus label ({} -> {})".format(-1, new_labels[0]))
            img_data_out[indlhypothal] = new_labels[0]
            nlabel = img_data_out.max()

            # ColorLUT (right hypothalamus)
            if path_create_colorLUT:
                f_color_lut.write("# Left Hemisphere. Hypothalamus \n")
                r = hypothal_colors_r
                g = hypothal_colors_g
                b = hypothal_colors_b
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), left_hypothal_names[0], r, g,
                                                                     b))
                f_color_lut.write("\n")


        # Relabelling Brain Stem
        if brainstem_defined:
            if path_create_colorLUT:
                f_color_lut.write("# Brain Stem Structures \n")

            nlabel = nlabel + 2
            new_labels = np.arange(
                nlabel + 1, nlabel + 1 + brainstem.shape[0])
            i = 0
            for lab in brainstem:
                if verbose_level == 2:
                    iflogger.info(
                        "  > Update brainstem parcellation label ({} -> {})".format(lab, new_labels[i]))

                if path_create_colorLUT:
                    r = brainstem_colors_r[i]
                    g = brainstem_colors_g[i]
                    b = brainstem_colors_b[i]
                    f_color_lut.write(
                        '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[i]), brainstem_names[i], r, g,
                                                                         b))

                ind = np.where(img_data_stem == lab)
                img_data_out[ind] = new_labels[i]
                i += 1
                # nlabel = img_data_out.max()

            if path_create_colorLUT:
                f_color_lut.write("\n")
        else:
            if path_create_colorLUT:
                f_color_lut.write("# Brain Stem \n")

            new_labels = np.arange(nlabel + 1, nlabel + 2)
            img_data_out[indrep] = new_labels[0]

            if verbose_level == 2:
                iflogger.info(
                    "  > Update brainstem parcellation label ({} -> {})".format(lab, new_labels[0]))

            if path_create_colorLUT:
                r = 119
                g = 159
                b = 176
                f_color_lut.write(
                    '{:<4} {:<55} {:>3} {:>3} {:>3} 0 \n'.format(int(new_labels[0]), 'brainstem', r, g, b))


            # nlabel = img_data_out.max()

            if path_create_colorLUT:
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

        if path_create_colorLUT:
            f_color_lut.close()



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
    if verbose_level == 2:
        status = subprocess.call(cmd, shell=True)
    else:
        status = subprocess.call(
            cmd, shell=True, stdout=fnull, stderr=subprocess.STDOUT)

    if verbose_level == 2:
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

