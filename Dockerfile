# Use an official Python runtime as a parent image

FROM ubuntu:xenial
MAINTAINER Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

## Install miniconda2 and CMP dependencies

RUN apt-get update && apt-get -qq -y install curl bzip2 && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -bfp /usr/local && \
    rm -rf /tmp/miniconda.sh && \
    conda install -y python=2 && \
    conda update conda && \
    apt-get -qq -y remove curl bzip2 && \
    apt-get -qq -y autoremove && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/* /var/log/dpkg.log && \
    conda clean --all --yes
ENV PATH /opt/conda/bin:$PATH
# Note: (fix nodes_iter() to nodes() for networkx2 support)

RUN conda config --add channels conda-forge
RUN conda install -y python ipython jupyter matplotlib networkx numpy scipy sphinx traits dateutil nose pydot traitsui dipy nibabel mne nipype obspy graphviz
    
RUN conda install -c aramislab -y pybids
RUN conda install -y pyqt=4 
RUN conda install -y networkx=1  
RUN conda clean --all --yes

## Install Neurodebian

RUN apt-get install neurodebian && \
    apt-get update

## Install FSL from Neurodebian

RUN apt-get install fsl-complete

## Install MRTRIX

# Dependencies
RUN apt-get install git g++ libeigen3-dev zlib1g-dev libqt4-opengl-dev \
    libgl1-mesa-dev libfftw3-dev libtiff5-dev
# Get the latest version of MRtrix3

## Install AFNI
RUN apt-get install afni

