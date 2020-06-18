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
  
  
**Computing EEG inverse solutions**

TBC
