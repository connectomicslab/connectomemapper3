##################################################################
# Use Ubuntu 16.04 LTS as base image
##################################################################
FROM ubuntu:xenial-20210114 as builder

##################################################################
# Docker build command arguments
##################################################################
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

##################################################################
# Install system library dependencies including
# exfat libraries for exfat-formatted hard-drives (only MAC?) :
# exfat-fuse exfat-utils Neurodebian
##################################################################

WORKDIR /opt

# Pre-cache neurodebian key
COPY docker/files/neurodebian.gpg /root/.neurodebian.gpg

# Install system library dependencies
RUN apt-get update && \
    apt-get install python2.7 python2.7-minimal software-properties-common -y && \
    apt-get install -qq -y --no-install-recommends bc \
    locales libstdc++6 npm curl perl gzip bzip2 xvfb liblzma-dev locate exfat-fuse exfat-utils default-jre && \
    curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /root/.neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true) && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    apt-get update && \
    apt-get clean && \
    apt-get remove -y curl && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set local enccoding
ENV LANG="en_US.UTF-8"

##################################################################
# Install Miniconda3
##################################################################
FROM builder as builder_conda

WORKDIR /opt

# Add conda to $PATH
ENV PATH="/opt/conda/bin:$PATH"

# Install
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -bfp /opt/conda && \
    rm -rf /tmp/miniconda.sh && \
    apt-get remove -y curl && \
    conda update conda && \
    conda clean --all --yes && \
    rm -rf ~/.conda ~/.cache/pip/* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

##################################################################
## Install freesurfer 6.0.1
##################################################################
FROM builder_conda as builder_fs

WORKDIR /opt/freesurfer

# Download and install
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/6.0.1/freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz | tar zxv --no-same-owner -C /opt \
    --exclude='freesurfer/diffusion' \
    --exclude='freesurfer/docs' \
    --exclude='freesurfer/fsfast' \
    --exclude='freesurfer/trctrain' \
    --exclude='freesurfer/subjects/fsaverage_sym' \
    --exclude='freesurfer/subjects/fsaverage3' \
    --exclude='freesurfer/subjects/fsaverage4' \
    --exclude='freesurfer/subjects/cvs_avg35' \
    --exclude='freesurfer/subjects/cvs_avg35_inMNI152' \
    --exclude='freesurfer/subjects/bert' \
    --exclude='freesurfer/subjects/V1_average' \
    --exclude='freesurfer/average/mult-comp-cor' \
    --exclude='freesurfer/subjects/lh.EC_average' \
    --exclude='freesurfer/subjects/rh.EC_average' \
    --exclude='freesurfer/subjects/sample-*.mgz' \
    --exclude='freesurfer/lib/cuda' \
    --exclude='freesurfer/lib/qt' && \
    apt-get remove -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Installing the Matlab R2012b (v8.0) runtime // http://ssd.mathworks.com/supportfiles/MCR_Runtime/R2012b/MCR_R2012b_glnxa64_installer.zip
# Required by the brainstem and hippocampal subfield modules in FreeSurfer 6.0.1
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl "http://surfer.nmr.mgh.harvard.edu/fswiki/MatlabRuntime?action=AttachFile&do=get&target=runtime2012bLinux.tar.gz" -o "runtime2012b.tar.gz" && \
    apt-get remove -y curl && \
    tar xvf runtime2012b.tar.gz && \
    apt-get clean && \
    rm runtime2012b.tar.gz && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Simulate SetUpFreeSurfer.sh
ENV OS="Linux" \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA="" \
    FSF_OUTPUT_FORMAT="nii.gz" \
    FREESURFER_HOME="/opt/freesurfer"
ENV SUBJECTS_DIR="$FREESURFER_HOME/subjects" \
    FUNCTIONALS_DIR="$FREESURFER_HOME/sessions" \
    MNI_DIR="$FREESURFER_HOME/mni" \
    LOCAL_DIR="$FREESURFER_HOME/local" \
    MINC_BIN_DIR="$FREESURFER_HOME/mni/bin" \
    MINC_LIB_DIR="$FREESURFER_HOME/mni/lib" \
    MNI_DATAPATH="$FREESURFER_HOME/mni/data"
ENV PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    MNI_PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    PATH="$FREESURFER_HOME/bin:$FREESURFER_HOME/tktools:$MINC_BIN_DIR:$PATH"

##################################################################
## Install FSL and AFNI
##################################################################
FROM builder_fs as builder_afni

WORKDIR /opt

# Installing Neurodebian packages (FSL, AFNI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    dc wget \
    fsl-core=5.0.9-5~nd16.04+1 \
    fsl-mni152-templates=5.0.7-2 \
    fsl-5.0-eddy-nonfree \
    afni=16.2.07~dfsg.1-5~nd16.04+1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Setting AFNI envvars
ENV PATH="/usr/lib/afni/bin:$PATH" \
    AFNI_MODELPATH="/usr/lib/afni/models" \
    AFNI_IMSAVE_WARNINGS="NO" \
    AFNI_TTATLAS_DATASET="/usr/share/afni/atlases" \
    AFNI_PLUGINPATH="/usr/lib/afni/plugins"

# Setting FSL envvars
ENV FSLDIR="/usr/share/fsl/5.0" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    POSSUMDIR="/usr/share/fsl/5.0" \
    FSLTCLSH="/usr/bin/tclsh" \
    FSLWISH="/usr/bin/wish" \
    PATH="/usr/lib/fsl/5.0:$PATH" \
    LD_LIBRARY_PATH="/usr/lib/fsl/5.0:$LD_LIBRARY_PATH"

# Patch that replaces replace aff2rigid fsl_abspath fsladd imglob
# for python3 compatibility
WORKDIR /tmp
RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/patches/fsl-5.0.10-python3.tar.gz \
    && tar -zxvf fsl-5.0.10-python3.tar.gz \
    && cp fsl/bin/* "$FSLDIR/bin/" \
    && rm -r fsl*

# Mark a package as being manually installed, which will
# prevent the package from being automatically removed if no other packages
# depend on it
#RUN apt-mark manual package_name

###################################################################
## Install conda environment, including ANTs 2.2.0 and MRtrix 3.0.2
###################################################################
FROM builder_afni as builder_conda_env

WORKDIR /opt

ENV CONDA_ENV py37cmp-core
# Pull the environment name out of the environment.yml
COPY docker/environment.yml /app/environment.yml
RUN /bin/bash -c "conda env create -f /app/environment.yml && . activate $CONDA_ENV &&\
     conda clean -v --all --yes && rm -rf ~/.conda ~/.cache/pip/*"

# Make ANTs happy
ENV ANTSPATH="/opt/conda/envs/$CONDA_ENV/bin" \
    PATH="$ANTSPATH:$PATH" \
    PYTHON_EGG_CACHE="/cache/python-eggs"

##################################################################
# Install BIDS validator
##################################################################
# RUN npm install -g bids-validator && \
#     rm -rf ~/.npm ~/.empty

##################################################################
# Last environmment setup
##################################################################
ENV LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH"

##################################################################
# Installation of Connectome Mapper 3 packages
##################################################################
FROM builder_conda_env as builder_cmp3

# Set the working directory to /app/connectomemapper3
WORKDIR /app/connectomemapper3

# Copy contents of this repository.
COPY . /app/connectomemapper3

# Create cache directory for python eggs
RUN mkdir -p /cache/python-eggs && \
    chmod -R 777 /cache/python-eggs

# Install cmp and cmtklib packages in the conda environment $CONDA_ENV
# ENV CONDA_ENV py37cmp-core
# RUN apt-get -qq -y install libtiff5-dev=4.0.6-1ubuntu0.4 libssl-dev=1.0.2g-1ubuntu4.13
RUN /bin/bash -c ". activate ${CONDA_ENV} &&\
    pip install ."

# Environmment setup
ENV ANTSPATH="/opt/conda/envs/${CONDA_ENV}/bin" \
    PYTHONPATH="/opt/conda/envs/${CONDA_ENV}/bin" \
    PATH="$ANTSPATH:$PATH" \
    LD_LIBRARY_PATH="/opt/conda/envs/${CONDA_ENV}/lib:${LD_LIBRARY_PATH}"

# Make dipy.viz (fury/vtk) happy
# RUN /bin/bash -c "ln -s /opt/conda/envs/$CONDA_ENV/lib/libnetcdf.so.15 /opt/conda/envs/$CONDA_ENV/lib/libnetcdf.so.13"

##################################################################
# Copy primary BIDSapp entrypoint script
##################################################################
COPY scripts/bidsapp/run_cmp3.sh /app/run_cmp3.sh
RUN cat /app/run_cmp3.sh

##################################################################
# Copy secondary BIDSapp entrypoint script with code coverage
##################################################################
COPY scripts/bidsapp/run_coverage_cmp3.sh /app/run_coverage_cmp3.sh
RUN cat /app/run_coverage_cmp3.sh

##################################################################
# Acquire script to be executed
##################################################################
RUN chmod 775 /app/connectomemapper3/run.py && \
    chmod 775 /app/run_cmp3.sh && \
    chmod 775 /app/run_coverage_cmp3.sh && \
    chmod 777 /opt/freesurfer

##################################################################
# Temporary tmp folder
##################################################################
RUN /bin/bash -c "mkdir -p /var/tmp"
ENV TMPDIR="/var/tmp" \
    TMP="/var/tmp" \
    TEMP="/var/tmp"

##################################################################
# Create input and output directories for BIDS App
##################################################################
RUN mkdir /bids_dir && \
    mkdir /output_dir && \
    chmod -R 777 /bids_dir && \
    chmod -R 777 /output_dir

##################################################################
# Define Freesurfer license
##################################################################
ENV FS_LICENSE="/bids_dir/code/license.txt"

##################################################################
# Set locale settings
##################################################################
ENV LANG="C.UTF-8" \
    LC_ALL="C.UTF-8"

##################################################################
# Unless otherwise specified each process should only use one
# thread - nipype will handle parallelization
##################################################################
ENV MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

##################################################################
# Control random number generation
##################################################################
# Control MRTrix random number generation (RDG) for replicatable probabilistic tractography
# See https://community.mrtrix.org/t/random-number-generator/2063 for more details
# ENV MRTRIX_RNG_SEED=1234

# Control ANTs random number generation (RDG) and multithreading
# See https://github.com/ANTsX/ANTs/wiki/antsRegistration-reproducibility-issues for more details
# ENV ANTS_RANDOM_SEED=1234
# ENV ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS

##################################################################
# Run ldconfig for compatibility with Singularity
##################################################################
RUN ldconfig

##################################################################
# Show all environment variables
##################################################################
RUN export

##################################################################
# Define primary entryppoint script
##################################################################
WORKDIR /tmp/

##################################################################
# Define primary entryppoint script
##################################################################
ENTRYPOINT ["/app/run_cmp3.sh"]

##################################################################
# Copy version information
##################################################################
# COPY version /version

##################################################################
# Metadata
##################################################################
LABEL org.label-schema.build-date=${BUILD_DATE} \
      org.label-schema.name="Connectome Mapper BIDS App" \
      org.label-schema.description="Connectome Mapper BIDS App - the processing core of Connectome Mapper 3" \
      org.label-schema.url="https://connectome-mapper-3.readthedocs.io" \
      org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.vcs-url="https://github.com/connectomicslab/connectomemapper3" \
      org.label-schema.version=$VERSION \
      org.label-schema.maintainer="Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>" \
      org.label-schema.vendor="Connectomics Lab, Centre Hospitalier Universitaire Vaudois (CHUV), Lausanne, Switzerland" \
      org.label-schema.schema-version="1.0" \
      org.label-schema.docker.cmd="docker run --rm -v ~/data/bids_dataset:/bids_dir -t sebastientourbier/connectomemapper-bidsapp:${VERSION} /bids_dir /bids_dir/derivatives participant [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]] [-session_label SESSION_LABEL [SESSION_LABEL ...]] [--anat_pipeline_config ANAT_PIPELINE_CONFIG] [--dwi_pipeline_config DWI_PIPELINE_CONFIG] [--func_pipeline_config FUNC_PIPELINE_CONFIG]  [--number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL] [--fs_license FS_LICENSE]" \
