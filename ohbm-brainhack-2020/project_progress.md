# Integrate EEG inside Connectome Mapper 3

**Team**

Joan Rué Queralt, Sébastien Tourbier


**Goals for the OHBM Brainhack**

1. Creation of a sample BIDS dataset with EEG derivatives (computed inverse solutions):
  - [x] Decide a sample dataset (open-source) to use (ultimately with T1w, DWI, rfMRI, EEG modality)
     - Simple T1w/sEEG dataset: https://openneuro.org/datasets/ds002718/versions/1.0.2
     - Keep only one subject (sub-002)
  - [x] Organize the sample dataset according to BIDS MRI/EEG standard
     - Already BIDS :)
  - [ ] EEG analysis (computes the inverse solution) by an open-source EEG analysis software such as MNE, EGGLab,... depending of the expertise in the team. Dispatched tasks:
    - [ ] Joan investigates how to get inverse solutions using MNE
    - [ ] Seb computes multi-scale brain parcellations using CMP3 (v3.0.0-RC2)
  
  - [ ] Organization of EEG analysis outputs into the derivatives of the dataset according to new derivatives specs introduced in BIDS 1.4.0 (https://bids-specification.readthedocs.io/en/stable/05-derivatives/01-introduction.html)

2. Implementation of Nipype interfaces that:
  - [ ] loads the inverse solutions and their respective x,y,z locations
  - [ ] computes ROI source dipoles using the SVD technique
  - [ ] computes single source dipoles per ROI based on SVD decomposition [Rubega et al. 2018] using pycartool (https://github.com/Functional-Brain-Mapping-Laboratory/PyCartool)
  - [ ] computes diverse common functional connectivity metrics (Imaginary coherence, ...) using MNE - See how it integrates #203 

3. Implementation of EEG pipeline in the Connectome Mapper 3
  - [ ] Implementation of the EEG processing pipeline (`cmp/pipelines/functional/eeg.py`)
  - [ ] Extension with graphical components (`cmp/bidsappmanager/pipelines/functional/eeg.py`)


**How to get setup**

* Clone the repo and track this branch
    ```
    git clone https://github.com/connectomicslab/connectomemapper3.git connectomemapper3
    git fetch
    git checkout --track origin/ohbm-brainhack-2020
    ```

* Create the conda environment for development::
    ```
    conda env create -f environment.yml
    ```
    
* Activate the conda environment::
    ```
    conda activate py27cmp-gui
    ```
    
* Install jupyter notebook and dependencies::
    ```
    conda install -y -q jupyter notebook
    ```
* Install cmp3
    ```
    python setup.py install
    ```
    
* Go to the ohbm-brainhack-2020 directory and launch Jupyter notebook
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
  rm -R sub-0*[1][0-2]
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
  
