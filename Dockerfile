# Use an official Python runtime as a parent image
FROM sebastientourbier/connectomemapper-ubuntu16.04:latest

MAINTAINER Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

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

WORKDIR /app

# Set the working directory to /app and copy contents of this repository
WORKDIR /app
ADD . /app

#RUN apt-get -qq -y install libtiff5-dev=4.0.6-1ubuntu0.4 libssl-dev=1.0.2g-1ubuntu4.13

#Clone the master branch of connectomemapper 3 from BitBucket
ARG password
RUN git clone --progress --verbose -b dev --single-branch https://sebastientourbier:$password@bitbucket.org/sinergiaconsortium/connectomemapper3.git connectomemapper3

# Set the working directory to /app/connectomemapper3 and install connectomemapper3
WORKDIR /app/connectomemapper3
RUN python setup.py install
ENV ANTSPATH=/opt/conda/bin
#ENV PATH=$ANTSPATH:$PATH

# Create entrypoint script that simulated a X server - required by traitsui
RUN echo '#! /bin/sh \n chown "$(id -u):$(id -g)" /opt/freesurfer \n xvfb-run -a python "/app/run_connectomemapper3.py" "$@" \n rm -R /tmp/.X99-lock /tmp/.X11-unix' > /app/run_connectomemapper3.sh

# Set the working directory back to /app
# Acquire script to be executed
RUN chmod 775 /app/run_connectomemapper3.py
RUN chmod 775 /app/run_connectomemapper3.sh
RUN chmod 777 /opt/freesurfer

WORKDIR /

#COPY version /version
ENTRYPOINT ["/app/run_connectomemapper3.sh"]
