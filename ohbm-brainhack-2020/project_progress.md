# Integrate EEG inside Connectome Mapper 3

**Team**

Joan Rué Queralt, Sébastien Tourbier


**Achievements for the OHBM Brainhack**

1. Creation of a sample BIDS dataset with EEG derivatives (computed inverse solutions):
  - [x] Decide a sample dataset (open-source) to use (ultimately with T1w, DWI, rfMRI, EEG modality)
     - Simple T1w/sEEG dataset: https://openneuro.org/datasets/ds002718/versions/1.0.2
     - Keep only one subject (sub-002)
  - [x] Organize the sample dataset according to BIDS MRI/EEG standard
     - Already BIDS :)
  - [x] EEG analysis (computes the inverse solution, single ROI source dipoles, dynamic functional connectivity) by an open-source EEG analysis software such as MNE, EGGLab,... depending of the expertise in the team. Dispatched tasks:
    - [x] Compute multi-scale brain parcellations using CMP3 (v3.0.0-RC2)
    - [x] Investigate how to compute inverse solutions using MNE on the sample dataset
      - Need MNE-BIDS (python3 package)
      - Not straight forward to load the sample dataset (generated with eeglab - coordinatesystem ARS - against MNE - coordinatesystem RAS )
      -> Refined tasks:
        - [x] Investigate how to load inverse solutions already computed with cartool using pycartool and MNE on a second sample (unpublished) dataset (one subject with T1w/DTI/HD-EEG already processed by CMP3 and Cartool)
          - Loaded inverse solutions reconstructed with cartool software using pycartool (https://github.com/Functional-Brain-Mapping-Laboratory/PyCartool)
          - Computed single source dipoles per ROI based on SVD decomposition [Rubega et al. 2018] 
          - Computed diverse common functional connectivity metrics (Imaginary coherence, ...) using MNE 

**Remaining tasks for the upcoming future**
1. Creation of a sample BIDS dataset with EEG derivatives (computed inverse solutions):
  - [ ] Review EEG analysis outputs into the derivatives of the dataset according to new derivatives specs introduced in BIDS 1.4.0 (https://bids-specification.readthedocs.io/en/stable/05-derivatives/01-introduction.html)

2. Implementation of Nipype interfaces that:
  - [ ] loads the inverse solutions and their respective x,y,z locations
  - [ ] computes single source dipoles per ROI based on SVD decomposition 
  - [ ] computes diverse common functional connectivity metrics (Imaginary coherence, ...) using MNE - See how it integrates #203 

3. Implementation of EEG pipeline in the Connectome Mapper 3
  - [ ] Implementation of the EEG processing pipeline (`cmp/pipelines/functional/eeg.py`)
  - [ ] Extension with graphical components (`cmp/bidsappmanager/pipelines/functional/eeg.py`)

## Project report

**How to get setup**

* Clone the repo and track this branch
    ```
    git clone https://github.com/connectomicslab/connectomemapper3.git connectomemapper3
    git fetch
    git checkout --track origin/ohbm-brainhack-2020
    ```

* Go to the ohbm-brainhack-2020 directory and create the conda environment for development::
    ```
    cd ohbm-brainhack-2020
    conda env create -f py3EEGenvironment.yml
    ```
    
* Activate the conda environment::
    ```
    conda activate py3cmp-eeg
    ```
    
* Install jupyter notebook and dependencies::
    ```
    conda install -y -q jupyter notebook 
    ```
* Install cmp3
    ```
    cd ..
    python setup.py install
    ```
    
* launch Jupyter notebook
    ```
    cd ohbm-brainhack-2020
    jupyter notebook
    ```
    
* You can check if cmp is well installed using the `test.ipynb` notebook.


**Creation of sample dataset**

Dataset: https://openneuro.org/datasets/ds002718/versions/1.0.2

1. Download using aws CLI (faster than downloading directly from openneuro)
  ```
  mkdir ~/Data
  cd ~/Data
  aws s3 sync --no-sign-request s3://openneuro.org/ds002718 ds002718-cmpeeg/
  ```
2. Keep only `sub-002`
  ```
  cd ds002718-cmpeeg/
  ## Remove all sub-0** except sub-002
  rm -R sub-0*[0-1][3-9]
  rm -R sub-0*[1][0-1]
  ## Keep only sub-002 in participants.tsv
  head -n 2 participants.tsv >> participants.tsv
  ## Rename T1w to be in valid BIDS format for input to CMP
  mv sub-002/anat/sub-002_mod-T1w_defacemask.nii.gz sub-002/anat/sub-002_T1w.nii.gz
  ```


**Computing multi-scale brain parcellations**

1. Install the Connectome Mapper 3 GUI inside the `py27cmp-gui` conda environment
  ```
  conda activate py27cmp-gui #If not already activated
  python setup_gui.py install
  ```

2. Launch the GUI
  ```
  cmpbidsappmanager
  ```
3. Go to File->Load BIDS dataset.. and Select your `ds002718-cmpeeg/` directory

4. Create the configuration file for the anatomical parcellation (Segmentation stage by default / Parcellation stage: Lausanne 2018 with all extra structures)

5. Run the BIDS App
  
6. Output overview

  |  | Lausanne2018 Scale 1 | Lausanne2018 Scale 3 | Lausanne2018 Scale 5 |
  |:-------------------------:|:-------------------------:|:-------------------------:|:-------------------------:|
  | Axial |<img width="1604" alt="Axial Lausanne 2018 scale 1" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale1_ax.png"> |  <img width="1604" alt="Axial Lausanne 2018 scale 3" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale3_ax.png">|<img width="1604" alt="Axial Lausanne 2018 scale 5" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale5_ax.png">|
  | Sagittal |<img width="1604" alt="Sagittal Lausanne 2018 scale 1" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale1_sag.png"> |  <img width="1604" alt="Sagittal Lausanne 2018 scale 3" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale3_sag.png">|<img width="1604" alt="Sagittal Lausanne 2018 scale 5" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale5_sag.png">|
  | Coronal |<img width="1604" alt="Coronal Lausanne 2018 scale 1" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale1_cor.png"> |  <img width="1604" alt="Coronal Lausanne 2018 scale 3" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale3_cor.png">|<img width="1604" alt="Coronal Lausanne 2018 scale 5" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale5_cor.png">|
  | 3D |<img width="1604" alt="3D Lausanne 2018 scale 1" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale1_3d.png"> |  <img width="1604" alt="3D Lausanne 2018 scale 3" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale3_3d.png">|<img width="1604" alt="3D Lausanne 2018 scale 5" src="https://raw.githubusercontent.com/connectomicslab/connectomemapper3/ohbm-brainhack-2020/ohbm-brainhack-2020/images/sub-002_scale5_3d.png">|
  
  
**New sample dataset with already computed EEG inverse solutions**

**Structure:**
```
+--- code
|   +--- ...
+--- derivatives
|   +--- cartool
|   |   +--- sub-01
|   |   |   +--- Cartool.ini
|   |   |   +--- More
|   |   |   |   +--- ...
|   |   |   +--- sub-01 -no_ref.xyz
|   |   |   +--- sub-01.Brain.hdr
|   |   |   +--- sub-01.Brain.img
|   |   |   +--- sub-01.For Display.xyz
|   |   |   +--- sub-01.Grey.hdr
|   |   |   +--- sub-01.Grey.img
|   |   |   +--- sub-01.Head.hdr
|   |   |   +--- sub-01.Head.img
|   |   |   +--- sub-01.IS + XYZ.lm
|   |   |   +--- sub-01.IS.lm
|   |   |   +--- sub-01.Laura.is
|   |   |   +--- sub-01.Lead Field.ris
|   |   |   +--- sub-01.Loreta.is
|   |   |   +--- sub-01.RIS.lm
|   |   |   +--- sub-01.spi
|   |   |   +--- sub-01.vrb
|   |   |   +--- sub-01.xyz
|   |   |   +--- sub-01.XYZ.lm
|   +--- cmp
|   |   +--- dataset_description.json
|   |   +--- sub-01
|   |   |   +--- anat
|   |   |   |   +--- sub-01_desc-aparcaseg_dseg.nii.gz
|   |   |   |   +--- sub-01_desc-aseg_dseg.nii.gz
|   |   |   |   +--- sub-01_desc-brain_mask.nii.gz
|   |   |   |   +--- sub-01_desc-brain_T1w.nii.gz
|   |   |   |   +--- sub-01_desc-cmp_T1w.nii.gz
|   |   |   |   +--- sub-01_desc-head_T1w.nii.gz
|   |   |   |   +--- sub-01_label-brain_desc-eroded_dseg.nii.gz
|   |   |   |   +--- sub-01_label-CSF_desc-eroded_dseg.nii.gz
|   |   |   |   +--- sub-01_label-CSF_dseg.nii.gz
|   |   |   |   +--- sub-01_label-GM_dseg.nii.gz
|   |   |   |   +--- sub-01_label-L2008_desc-scale1_atlas.nii.gz
|   |   |   |   +--- sub-01_label-L2008_desc-scale2_atlas.nii.gz
|   |   |   |   +--- sub-01_label-L2008_desc-scale3_atlas.nii.gz
|   |   |   |   +--- sub-01_label-L2008_desc-scale4_atlas.nii.gz
|   |   |   |   +--- sub-01_label-L2008_desc-scale5_atlas.nii.gz
|   |   |   |   +--- sub-01_label-WM_desc-eroded_dseg.nii.gz
|   |   |   |   +--- sub-01_label-WM_dseg.nii.gz
|   |   |   |   +--- sub-01_space-DWI_desc-brain_mask.nii.gz
|   |   |   |   +--- sub-01_space-DWI_desc-brain_T1w.nii.gz
|   |   |   |   +--- sub-01_space-DWI_desc-head_T1w.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-5TT_probseg.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-CSF_probseg.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-GMWMI_probseg.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-GM_probseg.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-L2008_desc-scale1_atlas.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-L2008_desc-scale2_atlas.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-L2008_desc-scale3_atlas.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-L2008_desc-scale4_atlas.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-L2008_desc-scale5_atlas.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-WM_dseg.nii.gz
|   |   |   |   +--- sub-01_space-DWI_label-WM_probseg.nii.gz
|   |   |   +--- connectivity
|   |   |   |   +--- sub-01_label-L2008_desc-scale1_conndata-snetwork_connectivity.gpickle
|   |   |   |   +--- sub-01_label-L2008_desc-scale1_conndata-snetwork_connectivity.mat
|   |   |   |   +--- sub-01_label-L2008_desc-scale2_conndata-snetwork_connectivity.gpickle
|   |   |   |   +--- sub-01_label-L2008_desc-scale2_conndata-snetwork_connectivity.mat
|   |   |   |   +--- sub-01_label-L2008_desc-scale3_conndata-snetwork_connectivity.gpickle
|   |   |   |   +--- sub-01_label-L2008_desc-scale3_conndata-snetwork_connectivity.mat
|   |   |   |   +--- sub-01_label-L2008_desc-scale4_conndata-snetwork_connectivity.gpickle
|   |   |   |   +--- sub-01_label-L2008_desc-scale4_conndata-snetwork_connectivity.mat
|   |   |   |   +--- sub-01_label-L2008_desc-scale5_conndata-snetwork_connectivity.gpickle
|   |   |   |   +--- sub-01_label-L2008_desc-scale5_conndata-snetwork_connectivity.mat
|   |   |   +--- dwi
|   |   |   |   +--- sub-01_desc-brain_mask.nii.gz
|   |   |   |   +--- sub-01_desc-cmp_dwi.bval
|   |   |   |   +--- sub-01_desc-cmp_dwi.bvec
|   |   |   |   +--- sub-01_desc-cmp_dwi.json
|   |   |   |   +--- sub-01_desc-cmp_dwi.nii.gz
|   |   |   |   +--- sub-01_desc-grad_dwi.txt
|   |   |   |   +--- sub-01_desc-preproc_dwi.nii.gz
|   |   |   |   +--- sub-01_dwi.bval
|   |   |   |   +--- sub-01_dwi.bvec
|   |   |   |   +--- sub-01_dwi.nii.gz
|   |   |   |   +--- sub-01_model-CSD_desc-DET_tractogram.trk
|   |   |   |   +--- sub-01_model-CSD_diffmodel.nii.gz
|   |   |   |   +--- sub-01_model-DTI_FA.nii.gz
|   |   |   |   +--- sub-01_model-DTI_MD.nii.gz
|   |   |   +--- sub-01_anatomical_config.ini
|   |   |   +--- sub-01_diffusion_config.ini
|   |   |   +--- sub-01_log.txt
|   |   |   +--- xfm
|   |   |   |   +--- ...
|   +--- eeglab
|   |   +--- sub-01
|   |   |   +--- eeg
|   |   |   |   +--- sub-01_task-Face_eeg.fdt
|   |   |   |   +--- sub-01_task-Face_eeg.set
|   |   |   |   +--- sub-01_task-Face_events.txt
|   +--- freesurfer
|   |   +--- dataset_description.json
|   |   +--- fsaverage
|   |   |   +--- label
|   |   |   +--- mri
|   |   |   +--- surf
|   |   |   +--- ...
|   +--- mne
|   |   +--- sub-01
|   |   |   +--- sub-01-montage.fif
|   |   |   +--- sub-01_montage.fif
+--- participants.tsv
+--- project_description.json
+--- README.txt
+--- sub-01
|   +--- anat
|   |   +--- sub-01_T1w.json
|   |   +--- sub-01_T1w.nii.gz
|   +--- dwi
|   |   +--- sub-01_dwi.bval
|   |   +--- sub-01_dwi.bvec
|   |   +--- sub-01_dwi.json
|   |   +--- sub-01_dwi.nii.gz
```
Feedback is welcome :)
