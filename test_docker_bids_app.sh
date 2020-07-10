#!/bin/sh

# sudo docker run -it --rm \
#       -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2:/bids_dataset \
#       -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2/derivatives:/outputs \
#       -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2/code:/code \
#       -v /usr/local/freesurfer/subjects/fsaverage:/bids_dataset/derivatives/freesurfer/fsaverage \
#       -v /usr/local/freesurfer/license.txt:/opt/freesurfer/license.txt \
#       connectomemapper3 \
#       /bids_dataset /outputs participant --participant_label A007 \
#       --anat_pipeline_config /code/ref_anatomical_config.ini \
#       --dwi_pipeline_config /code/ref_diffusion_config.ini \
#       --func_pipeline_config /code/ref_fMRI_config.ini

sudo docker run -it --rm \
      -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2:/bids_dataset \
      -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2/derivatives:/outputs \
      -v /media/localadmin/17646e81-4a2d-474e-9af6-31b511af858e/DS-Schizo2/code:/code \
      -v /usr/local/freesurfer/subjects/fsaverage:/bids_dataset/derivatives/freesurfer/fsaverage \
      -v /usr/local/freesurfer/license.txt:/opt/freesurfer/license.txt \
      sebastientourbier/connectomemapper-bidsapp:latest \
      /bids_dataset /outputs participant --participant_label A006 \
      --anat_pipeline_config /code/ref_anatomical_config.ini \
      --dwi_pipeline_config /code/ref_diffusion_config.ini \
      --func_pipeline_config /code/ref_fMRI_config.ini



docker run -it --rm \
--entrypoint /app/run_coverage.sh \
-v /home/localadmin/Desktop/hcp-retest-d2:/bids_dir \
-v /home/localadmin/Desktop/hcp-retest-d2/derivatives:/output_dir \
-v /usr/local/freesurfer/license.txt:/bids_dir/code/license.txt \
-u 1000:1000 \
sebastientourbier/connectomemapper-bidsapp:v3.0.0-beta-RC2 \
/bids_dir /output_dir participant --participant_label 103818 \
--anat_pipeline_config /bids_dir/code/ref_anatomical_config.ini \
--dwi_pipeline_config /bids_dir/code/ref_diffusion_config.ini \
--func_pipeline_config /bids_dir/code/ref_fMRI_config.ini \
--fs_license /bids_dir/code/license.txt \
--number_of_participants_processed_in_parallel 1'