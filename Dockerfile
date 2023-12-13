##################################################################
# Use Ubuntu 16.04 LTS as base image
##################################################################
FROM ubuntu:xenial-20210804 AS main

##################################################################
# Pre-cache neurodebian key
##################################################################
COPY docker/files/neurodebian.gpg /root/.neurodebian.gpg

##################################################################
# Install system library dependencies including
# exfat libraries for exfat-formatted hard-drives (only MAC?) :
# exfat-fuse exfat-utils Neurodebian
##################################################################
RUN apt-get update && \
    apt-get install software-properties-common -y && \
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

##################################################################
## Install freesurfer 7.1.1, FSL and AFNI
##################################################################
FROM main AS neurobuntu

# Installing Freesurfer
WORKDIR /opt/freesurfer

# Download and install
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.1.1/freesurfer-linux-centos6_x86_64-7.1.1.tar.gz | tar zxv --no-same-owner -C /opt \
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

# Installing the Matlab R2014b
# Required by the brainstem and hippocampal subfield modules in FreeSurfer 7.1.1
WORKDIR /opt/freesurfer/bin

ENV OS="Linux" FREESURFER_HOME="/opt/freesurfer"
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl libxt-dev libxext-dev libncurses5 unzip && \
    curl "https://raw.githubusercontent.com/freesurfer/freesurfer/dev/scripts/fs_install_mcr" -o fs_install_mcr && \
    ls -al . && \
    chmod +x ./fs_install_mcr && \
    ./fs_install_mcr R2014b && \
    rm -rf ./fs_install_mcr ./R2014b && \
    apt-get remove -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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

# Patch that replaces replace aff2rigid fsl_abspath fsladd imglob
# for python3 compatibility
WORKDIR /tmp
ENV FSLDIR="/usr/share/fsl/5.0"
RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/patches/fsl-5.0.10-python3.tar.gz \
    && tar -zxvf ./fsl-5.0.10-python3.tar.gz \
    && cp ./fsl/bin/* "$FSLDIR/bin/" \
    && rm -r ./fsl*

# Mark a package as being manually installed, which will
# prevent the package from being automatically removed if no other packages
# depend on it
#RUN apt-mark manual package_name

##################################################################
## Install Miniconda3 and the environment incl. ANTs and MRtrix
##################################################################
FROM main AS neurocondabuntu

# Add conda to $PATH
ENV PATH="/opt/conda/bin:$PATH"

# Install Miniconda3
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

## Create conda environment, including ANTs 2.2.0 and MRtrix 3.0.2
ENV CONDA_ENV="py37cmp-core"
COPY docker/spec-file.txt /app/spec-file.txt
COPY docker/requirements.txt /app/requirements.txt
RUN /bin/bash -c "conda config --set default_threads 4 &&\
    conda create --name ${CONDA_ENV} --file /app/spec-file.txt &&\
    . activate ${CONDA_ENV} &&\
    pip install -r /app/requirements.txt &&\
    conda clean -v --all --yes &&\
    rm -rf ~/.conda ~/.cache/pip/*"

##################################################################
# Install BIDS validator
##################################################################
# RUN npm install -g bids-validator && \
#     rm -rf ~/.npm ~/.empty

##################################################################
# Installation of Connectome Mapper 3 packages
##################################################################
FROM neurocondabuntu AS cmpbuntu

# Docker build command arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Copy content of neurobuntu intermediate stage build
COPY --from=neurobuntu /opt/freesurfer /opt/freesurfer
COPY --from=neurobuntu /etc /etc
COPY --from=neurobuntu /usr/lib /usr/lib
COPY --from=neurobuntu /usr/bin /usr/bin
COPY --from=neurobuntu /usr/sbin /usr/sbin
COPY --from=neurobuntu /usr/local/bin /usr/local/bin
COPY --from=neurobuntu /usr/local/sbin /usr/local/sbin
COPY --from=neurobuntu /bin /bin
COPY --from=neurobuntu /sbin /sbin

COPY --from=neurobuntu /usr/share/fsl /usr/share/fsl
COPY --from=neurobuntu /usr/share/afni /usr/share/afni
COPY --from=neurobuntu /usr/share/man /usr/share/man
COPY --from=neurobuntu /usr/share/matlab /usr/share/matlab
COPY --from=neurobuntu /usr/share/octave /usr/share/octave

# Set the working directory to /app/connectomemapper3
WORKDIR /app/connectomemapper3

# Copy Python contents of this repository.
COPY LICENSE ./LICENSE
COPY setup.py ./setup.py
COPY README.md ./README.md
COPY cmp ./cmp
COPY cmtklib ./cmtklib
COPY resources ./resources
COPY run.py ../run.py
COPY .coveragerc ../.coveragerc

# Create cache directory for python eggs
RUN mkdir -p /cache/python-eggs && \
    chmod -R 777 /cache/python-eggs

# Install cmp and cmtklib packages in the conda environment $CONDA_ENV
ENV CONDA_ENV="py37cmp-core"
RUN /bin/bash -c ". activate ${CONDA_ENV} &&\
    pip install ."

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
RUN chmod 775 /app/.coveragerc && \
    chmod 775 /app/run.py && \
    chmod 775 /app/run_cmp3.sh && \
    chmod 775 /app/run_coverage_cmp3.sh && \
    chmod 777 /opt/freesurfer

##################################################################
# Add conda to $PATH
##################################################################
ENV PATH="/opt/conda/bin:$PATH"

##################################################################
# Simulate SetUpFreeSurfer.sh
##################################################################
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
# Setting AFNI envvars
##################################################################
ENV PATH="/usr/lib/afni/bin:$PATH" \
    AFNI_MODELPATH="/usr/lib/afni/models" \
    AFNI_IMSAVE_WARNINGS="NO" \
    AFNI_TTATLAS_DATASET="/usr/share/afni/atlases" \
    AFNI_PLUGINPATH="/usr/lib/afni/plugins"

##################################################################
# Setting FSL envvars
##################################################################
ENV FSLDIR="/usr/share/fsl/5.0" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    POSSUMDIR="/usr/share/fsl/5.0" \
    FSLTCLSH="/usr/bin/tclsh" \
    FSLWISH="/usr/bin/wish" \
    PATH="/usr/lib/fsl/5.0:$PATH" \
    LD_LIBRARY_PATH="/usr/lib/fsl/5.0:$LD_LIBRARY_PATH"

##################################################################
# Make ANTs happy
##################################################################
ENV ANTSPATH="/opt/conda/envs/${CONDA_ENV}/bin" \
    PYTHONPATH="/opt/conda/envs/${CONDA_ENV}/bin" \
    PYTHON_EGG_CACHE="/cache/python-eggs" \
    PATH="$ANTSPATH:$PATH" \
    LD_LIBRARY_PATH="/opt/conda/envs/${CONDA_ENV}/lib:${LD_LIBRARY_PATH}" \
    LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH"

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
