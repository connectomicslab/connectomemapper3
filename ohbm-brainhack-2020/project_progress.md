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
  - EEG analysis (computes the inverse solution) by an open-source EEG analysis software such as MNE, EGGLab,... depending of the expertise in the team. Dispatched tasks:
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
