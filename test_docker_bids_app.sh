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

