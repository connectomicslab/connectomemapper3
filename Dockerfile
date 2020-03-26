# Use an initial image, where all Connectome Mapper 3 dependencies are installed, as a parent image

ARG MAIN_DOCKER
FROM $MAIN_DOCKER

#RUN groupadd -r -g 1000 cmp && \
#    useradd -r -M -u 1000 -g cmp cmp

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

ENV CONDA_ENV py27cmp-core

#RUN apt-get -qq -y install libtiff5-dev=4.0.6-1ubuntu0.4 libssl-dev=1.0.2g-1ubuntu4.13
RUN /bin/bash -c ". activate $CONDA_ENV && \
    python setup.py install"

# ENV ANTSPATH=/opt/conda/bin
# ENV PATH=$ANTSPATH:$PATH
ENV ANTSPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PATH $ANTSPATH:$PATH

# Create entrypoint script that simulated a X server - required by traitsui?
# try to change freesurfer home permission to copy the license
#RUN echo '#! /bin/bash \n chown "$(id -u):$(id -g)" /opt/freesurfer \n . activate $CONDA_ENV \n xvfb-run -a python /app/connectomemapper3/run.py $@ \n rm -f -R /tmp/.X99-lock /tmp/.X11-unix /tmp/.xvfb-run.*' > /app/run_connectomemapper3.sh

#Previous for Docker
#RUN echo '#! /bin/bash \n . activate $CONDA_ENV \n xvfb-run -a python /app/connectomemapper3/run.py $@ \n rm -f -R /tmp/.X99-lock /tmp/.X11-unix /tmp/.xvfb-run.*' > /app/run_connectomemapper3.sh

#Current for singularity
RUN echo '#! /bin/bash \n echo "User: $USER" && echo "Group:"$(id -g -n $USER) && export && . activate $CONDA_ENV && xvfb-run -a python /app/connectomemapper3/run.py $@' > /app/run_connectomemapper3.sh

# Set the working directory back to /app
# Acquire script to be executed
RUN chmod 775 /app/connectomemapper3/run.py
RUN chmod 775 /app/run_connectomemapper3.sh
RUN chmod 777 /opt/freesurfer

#ENV LC_ALL="en_US.UTF-8"
#ENV LANG="en_US.UTF-8"

#Temporary tmp folder
RUN /bin/bash -c "mkdir -p /var/tmp"
ENV TMPDIR /var/tmp
ENV TMP /var/tmp
ENV TEMP /var/tmp

RUN export

#COPY version /version
RUN mkdir /bids_dir && \
    chmod -R 777 /bids_dir

RUN mkdir /output_dir && \
    chmod -R 777 /output_dir

ENV FS_LICENSE /bids_dir/code/license.txt

ENV LANG C.UTF-8 
ENV LC_ALL C.UTF-8 

RUN ldconfig
WORKDIR /tmp/
ENTRYPOINT ["/app/run_connectomemapper3.sh"]

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF

#Metadata
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="Connectome Mapper BIDS App"
LABEL org.label-schema.description="Connectome Mapper BIDS App - the processing core of Connectome Mapper 3"
LABEL org.label-schema.url="https://connectome-mapper-3.readthedocs.io"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.vcs-url="https://github.com/connectomicslab/connectomemapper3"
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.maintainer="Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>"
LABEL org.label-schema.vendor="Connectomics Lab, Centre Hospitalier Universitaire Vaudois (CHUV), Lausanne, Switzerland"
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.docker.cmd="docker run --rm -v ~/data/bids_dataset:/bids_dir -t sebastientourbier/connectomemapper-bidsapp:${VERSION} /bids_dir /bids_dir/derivatives participant [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]] [-session_label SESSION_LABEL [SESSION_LABEL ...]] [--anat_pipeline_config ANAT_PIPELINE_CONFIG] [--dwi_pipeline_config DWI_PIPELINE_CONFIG] [--func_pipeline_config FUNC_PIPELINE_CONFIG]  [--number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL] [--fs_license FS_LICENSE]"
