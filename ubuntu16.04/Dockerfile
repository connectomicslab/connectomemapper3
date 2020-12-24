# Use Ubuntu 16.04 LTS
FROM ubuntu:xenial-20181218

##################################################################
## Install apt-fast, neurodebian, conda
##################################################################

# Pre-cache neurodebian key
COPY files/neurodebian.gpg /root/.neurodebian.gpg

# Install system library dependencies including
# exfat libraries for exfat-formatted hard-drives (only MAC?) : exfat-fuse exfat-utils
# Neurodebian
RUN apt-get update && \
    apt-get install software-properties-common -y && \
    # apt-add-repository ppa:saiarcot895/myppa -y && \
    # apt-get update && \
    # apt-get -y install apt-fast \
    apt-get install -qq -y --no-install-recommends bc \
    locales libstdc++6 npm curl bzip2 xvfb liblzma-dev locate exfat-fuse exfat-utils default-jre && \
    curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /root/.neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true) && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    apt-get update && \
    apt-get clean && \
    apt-get remove -y curl && \
    rm -rf /var/lib/apt/lists/*

# Set local enccoding
ENV LANG en_US.UTF-8

# Add conda to $PATH
ENV PATH /opt/conda/bin:$PATH

# Install Miniconda3
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -bfp /opt/conda && \
    rm -rf /tmp/miniconda.sh && \
    apt-get remove -y curl && \
    conda update conda && \
    conda clean --all --yes && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

##################################################################
## Install freesurfer 6.0.1
##################################################################

# Download
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/6.0.1/freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz | tar zxv --no-same-owner -C /opt \
    --exclude='freesurfer/trctrain' \
    --exclude='freesurfer/subjects/fsaverage_sym' \
    --exclude='freesurfer/subjects/fsaverage3' \
    --exclude='freesurfer/subjects/fsaverage4' \
    --exclude='freesurfer/subjects/cvs_avg35' \
    --exclude='freesurfer/subjects/cvs_avg35_inMNI152' \
    --exclude='freesurfer/subjects/bert' \
    --exclude='freesurfer/subjects/V1_average' \
    --exclude='freesurfer/average/mult-comp-cor' \
    --exclude='freesurfer/lib/cuda' \
    --exclude='freesurfer/lib/qt' && \
    apt-get remove -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/freesurfer

# Installing the Matlab R2012b (v8.0) runtime // http://ssd.mathworks.com/supportfiles/MCR_Runtime/R2012b/MCR_R2012b_glnxa64_installer.zip
# Required by the brainstem and hippocampal subfield modules in FreeSurfer 6.0.1
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    curl "http://surfer.nmr.mgh.harvard.edu/fswiki/MatlabRuntime?action=AttachFile&do=get&target=runtime2012bLinux.tar.gz" -o "runtime2012b.tar.gz" && \
    apt-get remove -y curl && \
    rm -rf /var/lib/apt/lists/* && \
    tar xvf runtime2012b.tar.gz && \
    apt-get clean && \
    rm runtime2012b.tar.gz && \
    rm -rf /var/lib/apt/lists/*

# Make FreeSurfer happy
ENV OS=Linux
ENV FS_OVERRIDE=0
ENV FIX_VERTEX_AREA=""
ENV FSF_OUTPUT_FORMAT=nii.gz
ENV FREESURFER_HOME=/opt/freesurfer

ENV SUBJECTS_DIR=$FREESURFER_HOME/subjects
ENV FUNCTIONALS_DIR=$FREESURFER_HOME/sessions
ENV MNI_DIR=$FREESURFER_HOME/mni
ENV LOCAL_DIR=$FREESURFER_HOME/local
ENV FSFAST_HOME=$FREESURFER_HOME/fsfast
ENV MINC_BIN_DIR=$FREESURFER_HOME/mni/bin
ENV MINC_LIB_DIR=$FREESURFER_HOME/mni/lib
ENV MNI_DATAPATH=$FREESURFER_HOME/mni/data
ENV FMRI_ANALYSIS_DIR=$FREESURFER_HOME/fsfast

ENV PERL5LIB=$MINC_LIB_DIR/perl5/5.8.5
ENV MNI_PERL5LIB=$MINC_LIB_DIR/perl5/5.8.5
ENV PATH=$FREESURFER_HOME/bin:$FSFAST_HOME/bin:$FREESURFER_HOME/tktools:$MINC_BIN_DIR:$PATH

##################################################################
## Install AFNI
##################################################################

# Installing Neurodebian packages (FSL, AFNI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    dc wget afni=16.2.07~dfsg.1-5~nd16.04+1 && \
    # rm -r /var/cache/apt/archives/apt-fast && \
    apt-get clean && \
    # apt-fast clean && \
    rm -rf /var/lib/apt/lists/*
                                               # fsl-core=5.0.9-5~nd16.04+1 \
                                               # fsl-mni152-templates=5.0.7-2 \
                                               # fsl-5.0-eddy-nonfree \
# Make AFNI happy
ENV PATH /usr/lib/afni/bin:$PATH
ENV AFNI_MODELPATH /usr/lib/afni/models
ENV AFNI_IMSAVE_WARNINGS NO
ENV AFNI_TTATLAS_DATASET /usr/share/afni/atlases
ENV AFNI_PLUGINPATH /usr/lib/afni/plugins

# Mark a package as being manually installed, which will
# prevent the package from being automatically removed if no other packages
# depend on it
#RUN apt-mark manual package_name

##################################################################
## Install conda environment, including ANTs 2.2.0
##################################################################
ENV CONDA_ENV py37cmp-core
# Pull the environment name out of the environment.yml
COPY environment.yml /app/environment.yml
RUN /bin/bash -c "conda env create -f /app/environment.yml && . activate $CONDA_ENV &&\
     conda clean -v --all --yes"

# Make ANTs happy
ENV ANTSPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PATH $ANTSPATH:$PATH

##################################################################
## Install MRTRIX
##################################################################

# Additional dependencies for MRtrix3 compilation
# Get the latest version of MRtrix3
# MRtrix3 setup
WORKDIR /opt
RUN apt-get update && \
    apt-get install -y git && \
    git clone https://github.com/MRtrix3/mrtrix3.git mrtrix3 && \
    apt-get -y remove git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/mrtrix3
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    build-essential git g++ \
    libeigen3-dev zlib1g-dev libqt4-opengl-dev \
    libgl1-mesa-dev libfftw3-dev libtiff5-dev libssl-dev && \
    git checkout -f 3.0_RC3_latest && \
    #git checkout 3.0_RC3 && \
    python configure -nogui && \
    python build -persistent -nopaginate && \
    git describe --tags > /mrtrix3_version && \
    apt-get -y remove git g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Setup environment variables for MRtrix3
ENV PATH=/opt/mrtrix3/bin:$PATH
ENV PYTHONPATH=/opt/mrtrix3/lib:$PYTHONPATH

##################################################################
## Install FSL 6.0.0
##################################################################
WORKDIR /opt
RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends curl && \
    echo "Downloading FSL ..." \
    && curl -sSL --retry 5 https://fsl.fmrib.ox.ac.uk/fsldownloads/fsl-6.0.3-centos6_64.tar.gz \
    | tar zx -C /opt \
    && /bin/bash /opt/fsl/etc/fslconf/fslpython_install.sh -q -f /opt/fsl \
    && rm -rf /opt/fsl/data/first \
    && rm -rf /opt/fsl/data/possum \
    && rm -rf /opt/fsl/data/atlases/HarvardOxford \
    && rm -rf /opt/fsl/data/atlases/JHU \
    && rm -rf /opt/fsl/data/atlases/Juelich \
    && rm -rf /opt/fsl/doc \
    && apt-get remove -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV FSLDIR=/opt/fsl \
    PATH=/opt/fsl/bin:$PATH

##################################################################
# Install BIDS validator
##################################################################
# RUN npm install -g bids-validator

##################################################################
# Last environmment setup
##################################################################
ENV LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH

##################################################################
# Docker build command arguments
##################################################################
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

##################################################################
# Metadata
##################################################################
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="Connectome Mapper Ubuntu 16.04"
LABEL org.label-schema.description="Computing environment of the Connectome Mapper BIDS App based on Ubuntu 16.04."
LABEL org.label-schema.url="https://connectome-mapper-3.readthedocs.io"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.vcs-url="https://github.com/connectomicslab/connectomemapper3"
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.maintainer="Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>"
LABEL org.label-schema.vendor="Connectomics Lab, Centre Hospitalier Universitaire Vaudois (CHUV), Lausanne, Switzerland"
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.docker.cmd="docker run --rm -v ~/data/bids_dataset:/tmp -t sebastientourbier/connectomemapper-ubuntu16.04:${VERSION}"
