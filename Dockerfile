# Use Ubuntu 16.04 LTS
FROM ubuntu:xenial

# Pre-cache neurodebian key
COPY docker/files/neurodebian.gpg /root/.neurodebian.gpg

MAINTAINER Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

## Install miniconda2 and CMP dependencies

RUN apt-get update && apt-get -qq -y install curl bzip2 && \
    curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /root/.neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true) && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -bfp /usr/local && \
    rm -rf /tmp/miniconda.sh && \
    conda install -y python=2.7.13 && \
    conda update conda && \
    apt-get -qq -y remove curl bzip2 && \
    apt-get -qq -y autoremove && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/* /var/log/dpkg.log && \
    conda clean --all --yes
ENV PATH /opt/conda/bin:$PATH
# Note: (fix nodes_iter() to nodes() for networkx2 support)

RUN conda config --add channels conda-forge
RUN conda config --add channels aramislab

RUN conda install -y ipython jupyter matplotlib 

RUN conda install -y networkx=1.11 
RUN conda install -y numpy=1.11.3 
RUN conda install -y scipy=1.1.0 
RUN conda install -y sphinx=1.5.1 
RUN conda install -y traits=4.6.0 
RUN conda install -y dateutil=2.4.1 
RUN conda install -y nose=1.3.7 
RUN conda install -y pydot=1.0.28 
RUN conda install -y traitsui=5.1.0 
RUN conda install -y dipy=0.13.0 
RUN conda install -y nibabel=2.2.1 
RUN conda install -y mne=0.15 
RUN conda install -y nipype=1.0 
RUN conda install -y obspy=1.1.0 
RUN conda install -y graphviz=2.38.0 
RUN conda install -y pyqt=4 
RUN conda install -c aramislab -y pybids=0.1
RUN conda clean --all --yes

## Install Neurodebian
#RUN apt-get install neurodebian && \
#    apt-get update

## Install FSL from Neurodebian

RUN apt-get install fsl-complete

## Install MRTRIX

# Dependencies
RUN apt-get install git g++ libeigen3-dev zlib1g-dev libqt4-opengl-dev \
    libgl1-mesa-dev libfftw3-dev libtiff5-dev
# Get the latest version of MRtrix3

## Install AFNI
RUN apt-get install afni

