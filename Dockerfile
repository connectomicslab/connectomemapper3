# Use an official Python runtime as a parent image
FROM sebastientourbier/connectomemapper-ubuntu16.04:latest

#RUN apt-get install software-properties-common && add-apt-repository universe && apt-get update && apt-get -qq -y install exfat-fuse exfat-utils
##
# Install any needed packages specified in requirements.txt
# RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
# EXPOSE 80

# WORKDIR /bids_dataset
# WORKDIR /bids_dataset/derivatives
# WORKDIR /bids_dataset/derivatives/freesurfer
# WORKDIR /bids_dataset/derivatives/freesurfer/fsaverage
# WORKDIR /opt/freesurfer/subjects/fsaverage
# ADD . /bids_dataset/derivatives/freesurfer/fsaverage

# Set the working directory to /app and copy contents of this repository
WORKDIR /app/connectomemapper3
ADD . /app/connectomemapper3

ENV CONDA_ENV py27cmp

#RUN apt-get -qq -y install libtiff5-dev=4.0.6-1ubuntu0.4 libssl-dev=1.0.2g-1ubuntu4.13
RUN /bin/bash -c ". activate $CONDA_ENV && \
    python setup.py install"

# ENV ANTSPATH=/opt/conda/bin
# ENV PATH=$ANTSPATH:$PATH
ENV ANTSPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PATH $ANTSPATH:$PATH
RUN export

# Create entrypoint script that simulated a X server - required by traitsui?
# try to change freesurfer home permission to copy the license
#RUN echo '#! /bin/bash \n chown "$(id -u):$(id -g)" /opt/freesurfer \n . activate $CONDA_ENV \n xvfb-run -a python /app/connectomemapper3/run.py $@ \n rm -f -R /tmp/.X99-lock /tmp/.X11-unix /tmp/.xvfb-run.*' > /app/run_connectomemapper3.sh
RUN echo '#! /bin/bash \n . activate $CONDA_ENV \n xvfb-run -a python /app/connectomemapper3/run.py $@ \n rm -f -R /tmp/.X99-lock /tmp/.X11-unix /tmp/.xvfb-run.*' > /app/run_connectomemapper3.sh

# Set the working directory back to /app
# Acquire script to be executed
RUN chmod 775 /app/connectomemapper3/run.py
RUN chmod 775 /app/run_connectomemapper3.sh
RUN chmod 777 /opt/freesurfer

ENV FS_LICENSE /tmp/code/license.txt

#COPY version /version
WORKDIR /tmp
ENTRYPOINT ["/app/run_connectomemapper3.sh"]

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

#Metadata
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="Connectome Mapper BIDS App"
LABEL org.label-schema.description="Connectome Mapper BIDS App - the processing core of Connectome Mapper 3"
LABEL org.label-schema.url="https://connectome-mapper-3.readthedocs.io"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.vcs-url="https://bitbucket.org/sinergiaconsortium/connectomemapper-bidsapp"
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.maintainer="Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>"
LABEL org.label-schema.vendor="Connectomics Lab, Centre Hospitalier Universitaire Vaudois (CHUV), Lausanne, Switzerland"
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.docker.cmd="docker run -v ~/data/bids_dataset:/tmp"
