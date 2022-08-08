from os import path as op
import nipype.pipeline.engine as pe
from cmp.stages.connectome.connectome import CMTK_cmat

cmtk_cmat = pe.Node(interface=CMTK_cmat(), name="compute_matrice",
                    base_dir='/home/localadmin/Desktop')

dir = '/media/localadmin/HagmannHDD/Seb/ds-newtest5'

cmtk_cmat.inputs.compute_curvature = False
cmtk_cmat.inputs.output_types = ["gpickle"]
cmtk_cmat.inputs.track_file = op.join(dir,
                                      "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/tracking/trackvis/converted.trk")
cmtk_cmat.inputs.roi_volumes = [op.join(dir,
                                        "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/dilate_rois/mapflow/_dilate_rois0/sub-A001_ses-20160707161422_label-L2018_desc-scale1_atlas_out_warped_dil.nii.gz"),
                                op.join(dir,
                                        "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/dilate_rois/mapflow/_dilate_rois1/sub-A001_ses-20160707161422_label-L2018_desc-scale2_atlas_out_warped_dil.nii.gz"),
                                op.join(dir,
                                        "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/dilate_rois/mapflow/_dilate_rois2/sub-A001_ses-20160707161422_label-L2018_desc-scale3_atlas_out_warped_dil.nii.gz"),
                                op.join(dir,
                                        "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/dilate_rois/mapflow/_dilate_rois3/sub-A001_ses-20160707161422_label-L2018_desc-scale4_atlas_out_warped_dil.nii.gz"),
                                op.join(dir,
                                        "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/dilate_rois/mapflow/_dilate_rois4/sub-A001_ses-20160707161422_label-L2018_desc-scale5_atlas_out_warped_dil.nii.gz")
                                ]
cmtk_cmat.inputs.parcellation_scheme = 'Lausanne2018'
cmtk_cmat.inputs.roi_graphMLs = [op.join(dir,
                                         "derivatives/cmp/sub-A001/ses-20160707161422/anat/sub-A001_ses-20160707161422_label-L2018_desc-scale1_atlas.graphml"),
                                 op.join(dir,
                                         "derivatives/cmp/sub-A001/ses-20160707161422/anat/sub-A001_ses-20160707161422_label-L2018_desc-scale2_atlas.graphml"),
                                 op.join(dir,
                                         "derivatives/cmp/sub-A001/ses-20160707161422/anat/sub-A001_ses-20160707161422_label-L2018_desc-scale3_atlas.graphml"),
                                 op.join(dir,
                                         "derivatives/cmp/sub-A001/ses-20160707161422/anat/sub-A001_ses-20160707161422_label-L2018_desc-scale4_atlas.graphml"),
                                 op.join(dir,
                                         "derivatives/cmp/sub-A001/ses-20160707161422/anat/sub-A001_ses-20160707161422_label-L2018_desc-scale5_atlas.graphml")
                                 ]
cmtk_cmat.inputs.additional_maps = [op.join(dir,
                                            "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/reconstruction/dipy_SHORE/shore_gfa.nii.gz"),
                                    op.join(dir,
                                            "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/reconstruction/dipy_SHORE/shore_msd.nii.gz"),
                                    op.join(dir,
                                            "derivatives/nipype/sub-A001/ses-20160707161422/diffusion_pipeline/diffusion_stage/reconstruction/dipy_SHORE/shore_rtop_signal.nii.gz")
                                    ]

cmtk_cmat.run()
