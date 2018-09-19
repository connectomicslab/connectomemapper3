# Use Ubuntu 16.04 LTS
FROM ubuntu:16.04

# Pre-cache neurodebian key
COPY docker/files/neurodebian.gpg /root/.neurodebian.gpg

MAINTAINER Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

## Install miniconda2 and CMP dependencies

RUN apt-get update && apt-get -qq -y install npm curl bzip2 xvfb && \
    curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /root/.neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true) && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -bfp /usr/local && \
    rm -rf /tmp/miniconda.sh && \
    conda install -y python=2.7.13 && \
    conda update conda && \
    conda clean --all --yes
ENV PATH /opt/conda/bin:$PATH
# Note: (fix nodes_iter() to nodes() for networkx2 support)

RUN conda config --add channels conda-forge
RUN conda config --add channels aramislab

RUN conda install -y ipython jupyter matplotlib

RUN conda install -c aramislab -y ants=2.2.0
RUN conda install -y networkx=1.11
RUN conda install -y numpy=1.11.3
RUN conda install -y scipy=1.1.0
RUN conda install -y sphinx=1.5.1
RUN conda install -y traits=4.6.0
RUN conda install -y dateutil=2.4.1
RUN conda install -y certifi=2018.4.16
RUN conda install -y pandas=0.19.2
RUN conda install -y patsy=0.4.1
RUN conda install -y statsmodels=0.8.0
RUN conda install -y nose=1.3.7
RUN conda install -y pydot=1.0.28
RUN conda install -y traitsui=5.1.0
RUN conda install -y dipy=0.14.0
RUN conda install -y nibabel=2.2.1
RUN conda install -y mne=0.15
RUN conda install -y nipype=1.0
RUN conda install -y obspy=1.1.0
RUN conda install -y graphviz=2.38.0
RUN conda install -y pyqt=4
RUN conda install -c aramislab -y pybids
RUN conda clean --all --yes

## Install Neurodebian
#RUN apt-get install neurodebian && \
#    apt-get update

# Installing freesurfer
RUN curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/6.0.1/freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz | tar zxv --no-same-owner -C /opt \
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
    --exclude='freesurfer/lib/qt'

# Installing the Matlab R2012b (v8.0) runtime
# Required by the brainstem and hippocampal subfield modules in FreeSurfer 6.0.1
#RUN curl "https://surfer.nmr.mgh.harvard.edu/fswiki/MatlabRuntime?action=AttachFile&do=get&target=runtime2012bLinux.tar.gz" -o "/opt/freesurfer/runtime.tar.gz"
#RUN tar xvf /opt/freesurfer/runtime.tar.gz
#RUN rm /opt/freesurfer/runtime.tar.gz
WORKDIR /opt/freesurfer
RUN curl "http://surfer.nmr.mgh.harvard.edu/fswiki/MatlabRuntime?action=AttachFile&do=get&target=runtime2012bLinux.tar.gz" -o "runtime2012b.tar.gz"
RUN tar xvf runtime2012b.tar.gz
RUN rm runtime2012b.tar.gz
# Make FreeSurfer happy
ENV FSL_DIR=/usr/share/fsl/5.0 \
    OS=Linux \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA= \
    FSF_OUTPUT_FORMAT=nii.gz \
    FREESURFER_HOME=/opt/freesurfer
ENV SUBJECTS_DIR=$FREESURFER_HOME/subjects \
    FUNCTIONALS_DIR=$FREESURFER_HOME/sessions \
    MNI_DIR=$FREESURFER_HOME/mni \
    LOCAL_DIR=$FREESURFER_HOME/local \
    FSFAST_HOME=$FREESURFER_HOME/fsfast \
    MINC_BIN_DIR=$FREESURFER_HOME/mni/bin \
    MINC_LIB_DIR=$FREESURFER_HOME/mni/lib \
    MNI_DATAPATH=$FREESURFER_HOME/mni/data \
    FMRI_ANALYSIS_DIR=$FREESURFER_HOME/fsfast
ENV PERL5LIB=$MINC_LIB_DIR/perl5/5.8.5 \
    MNI_PERL5LIB=$MINC_LIB_DIR/perl5/5.8.5 \
    PATH=$FREESURFER_HOME/bin:$FSFAST_HOME/bin:$FREESURFER_HOME/tktools:$MINC_BIN_DIR:$PATH


## Install FSL from Neurodebian
#RUN apt-get install fsl-complete

# Mark a package as being manually installed, which will
# prevent the package from being automatically removed if no other packages
# depend on it
RUN apt-mark manual fsl-core
RUN apt-mark manual fsl-5.0-core
#RUN apt-mark manual fsl-mni152-templates
RUN apt-mark manual afni
RUN apt-mark manual ants

# Installing Neurodebian packages (FSL, AFNI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends fsl-core=5.0.9-4~nd16.04+1 fsl-mni152-templates=5.0.7-2 fsl-5.0-eddy-nonfree

RUN apt-get install -y --no-install-recommends afni=16.2.07~dfsg.1-5~nd16.04+1

#Make FSL/AFNI happy
ENV FSLDIR=/usr/share/fsl/5.0 \
    FSLOUTPUTTYPE=NIFTI_GZ \
    FSLMULTIFILEQUIT=TRUE \
    POSSUMDIR=/usr/share/fsl/5.0 \
    LD_LIBRARY_PATH=/usr/lib/fsl/5.0:$LD_LIBRARY_PATH \
    FSLTCLSH=/usr/bin/tclsh \
    FSLWISH=/usr/bin/wish \
    AFNI_MODELPATH=/usr/lib/afni/models \
    AFNI_IMSAVE_WARNINGS=NO \
    AFNI_TTATLAS_DATASET=/usr/share/afni/atlases \
    AFNI_PLUGINPATH=/usr/lib/afni/plugins
ENV PATH=/usr/lib/fsl/5.0:/usr/lib/afni/bin:$PATH

## Install ANTs --no-install-suggests
#RUN apt-get install -y ants=2.2.0-1~nd16.04+1
#ENV ANTSPATH=/usr/lib/ants
#ENV PATH=$ANTSPATH:$PATH

## Install MRTRIX

# Additional dependencies for MRtrix3 compilation
RUN apt-get install -y build-essential git g++ libeigen3-dev zlib1g-dev libqt4-opengl-dev \
    libgl1-mesa-dev libfftw3-dev libtiff5-dev libssl-dev
# Get the latest version of MRtrix3
# MRtrix3 setup
RUN git clone https://github.com/MRtrix3/mrtrix3.git mrtrix3 && \
    cd mrtrix3 && \
    git checkout 3.0_RC3 && \
    python configure -nogui && \
    python build -persistent -nopaginate && \
    git describe --tags > /mrtrix3_version

# Setup environment variables for MRtrix3
ENV PATH=/mrtrix3/bin:$PATH
ENV PYTHONPATH=/mrtrix3/lib:$PYTHONPATH

#BIDS validator
RUN npm install -g bids-validator

ENV LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH
# Cleanup
#RUN apt-get -y remove git g++ curl bzip2
    #apt-get -qq -y autoremove && \
    #apt-get autoclean && \
    #rm -rf /var/lib/apt/lists/* /var/log/dpkg.log
#

#ENV BIN_DIR "/usr/local/bin"
#ENV DISPLAY :0
