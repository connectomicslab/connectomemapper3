# Use Ubuntu 16.04 LTS
FROM ubuntu:xenial-20181218

# Pre-cache neurodebian key
COPY files/neurodebian.gpg /root/.neurodebian.gpg

## Install miniconda2 and CMP dependencies including exfat libraries for exfat-formatted hard-drives (only MAC?) : exfat-fuse exfat-utils
RUN apt-get update && apt-get -qq -y install locales libstdc++6 npm curl bzip2 xvfb liblzma-dev locate exfat-fuse exfat-utils default-jre && \
    curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /root/.neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true) && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -bfp /opt/conda && \
    rm -rf /tmp/miniconda.sh

ENV LANG en_US.UTF-8

ENV PATH /opt/conda/bin:$PATH

RUN conda update conda && \
    conda clean --all --yes

# RUN conda install -y python=2.7.15 && \
#     conda update conda && \
#     conda clean --all --yes
#
# ## FIXME: (fix nodes_iter() to nodes() for networkx2 support)
#
# RUN conda config --add channels conda-forge
# RUN conda config --add channels aramislab
#
# RUN conda install -y ipython jupyter matplotlib
#
# RUN conda install -c aramislab -y ants=2.2.0
# RUN conda install -y networkx=2.2
#
# # RUN conda install -y pyqt=5.6.0
# RUN conda install -y pyqt=4
#
# RUN conda install -y scipy=1.1.0
# RUN conda install -y sphinx=1.5.1
# RUN conda install -y traits=4.6.0
# RUN conda install -y dateutil=2.4.1
# RUN conda install -y certifi=2018.4.16
# RUN conda install -y pandas=0.23.4
# RUN conda install -y patsy=0.4.1
# RUN conda install -y statsmodels=0.8.0
# RUN conda install -y nose=1.3.7
# RUN conda install -y pydot=1.2.3
# RUN conda install -y traitsui=5.1.0
# RUN conda install -y numpy=1.14
# RUN conda install -y nipype=1.1.3
# RUN conda install -c anaconda -y configparser=3.5.0
# RUN conda install -y dipy=0.14.0
# RUN conda install -y nibabel=2.3.0
# RUN conda install -y mne=0.15
# RUN conda install -y obspy=1.1.0
# RUN conda install -y graphviz=2.38.0
# RUN conda install -c aramislab -y pybids
# RUN conda install -c anaconda -y configparser=3.5.0
#RUN conda install -c conda-forge python-dateutil=2.5.3

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

WORKDIR /opt/freesurfer

# Installing the Matlab R2012b (v8.0) runtime // http://ssd.mathworks.com/supportfiles/MCR_Runtime/R2012b/MCR_R2012b_glnxa64_installer.zip
# Required by the brainstem and hippocampal subfield modules in FreeSurfer 6.0.1
RUN curl "http://surfer.nmr.mgh.harvard.edu/fswiki/MatlabRuntime?action=AttachFile&do=get&target=runtime2012bLinux.tar.gz" -o "runtime2012b.tar.gz"
RUN tar xvf runtime2012b.tar.gz
RUN rm runtime2012b.tar.gz
#RUN mv /opt/freesurfer/MCRv80/sys/os/glnxa64/libstdc++.so.6 /opt/freesurfer/MCRv80/sys/os/glnxa64/libstdc++.so.6.old
#RUN mv /opt/freesurfer/MCRv80/sys/os/glnxa64/libstdc++.so.6.0.13 /opt/freesurfer/MCRv80/sys/os/glnxa64/libstdc++.so.6.0.13.old

# RUN curl "http://ssd.mathworks.com/supportfiles/MCR_Runtime/R2012b/MCR_R2012b_glnxa64_installer.zip" -o "MCR_R2012b_glnxa64_installer.zip"
# RUN tar xvf MCR_R2012b_glnxa64_installer.zip
# RUN rm MCR_R2012b_glnxa64_installer.zip
# RUN cd MCR_R2012b_glnxa64_installer && ./install -mode silent -agreeToLicense yes -destinationFolder /opt/freesurfer/MCRv80 -outputFile /opt/freesurfer/mcrv80_installation.log
# RUN cd .. && rm -r MCR_R2012b_glnxa64_installer

# Installing the Matlab R2014b (v8.4) runtime
# Required by the brainstem and hippocampal subfield modules in FreeSurfer > 6.0.1
# RUN curl "https://surfer.nmr.mgh.harvard.edu/fswiki/MatlabRuntime?action=AttachFile&do=get&target=runtime2014bLinux.tar.gz" -o "runtime2014b.tar.gz"
# RUN tar xvf runtime2014b.tar.gz
# RUN rm runtime2014b.tar.gz

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

# Installing Neurodebian packages (FSL, AFNI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends fsl-core=5.0.9-5~nd16.04+1 \
                                               fsl-mni152-templates=5.0.7-2 \
                                               fsl-5.0-eddy-nonfree \
                                               afni=16.2.07~dfsg.1-5~nd16.04+1

# Mark a package as being manually installed, which will
# prevent the package from being automatically removed if no other packages
# depend on it
#RUN apt-mark manual fsl-core
#RUN apt-mark manual fsl-5.0-core
#RUN apt-mark manual fsl-mni152-templates
#RUN apt-mark manual afni
#RUN apt-mark manual ants

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

# Pull the environment name out of the environment.yml
ADD environment.yml /app/environment.yml
RUN conda env create -f /app/environment.yml

# ENV ANTSPATH=/opt/conda/bin
# ENV PATH=$ANTSPATH:$PATH
ENV ANTSPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PATH $ANTSPATH:$PATH

## Install MRTRIX

# Additional dependencies for MRtrix3 compilation
# Get the latest version of MRtrix3
# MRtrix3 setup
WORKDIR /opt
RUN apt-get update && \
    apt-get install -y build-essential git g++ libeigen3-dev zlib1g-dev libqt4-opengl-dev \
    libgl1-mesa-dev libfftw3-dev libtiff5-dev libssl-dev && \
    git clone https://github.com/MRtrix3/mrtrix3.git mrtrix3 && \
    cd mrtrix3 && \
    git checkout -f 3.0_RC3_latest && \
    #git checkout 3.0_RC3 && \
    python configure -nogui && \
    python build -persistent -nopaginate && \
    git describe --tags > /mrtrix3_version
    #&& \
    #apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Setup environment variables for MRtrix3
ENV PATH=/opt/mrtrix3/bin:$PATH
ENV PYTHONPATH=/opt/mrtrix3/lib:$PYTHONPATH

## Install Neurodebian
#RUN apt-get install neurodebian && \
#    apt-get update

#BIDS validator
#RUN npm install -g bids-validator

ENV LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH
# Cleanup
#RUN apt-get -y remove git g++ curl bzip2
    #apt-get -qq -y autoremove && \
    #apt-get autoclean && \
    #rm -rf /var/lib/apt/lists/* /var/log/dpkg.log
#

#ENV BIN_DIR "/usr/local/bin"
#ENV DISPLAY :0

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

#Metadata
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
