##################################################################
# Build environment variables arguments
##################################################################
ARG MAIN_DOCKER
ARG MAIN_VERSION
ARG VERSION
ARG BUILD_DATE
ARG VCS_REF

##################################################################
# Use an initial image, where all Connectome Mapper 3 dependencies
# are installed, as a parent image
##################################################################
FROM "${MAIN_DOCKER}":"${MAIN_VERSION}"

##################################################################
# Installation of Connectome Mapper 3 packages
##################################################################

# Set the working directory to /app/connectomemapper3
WORKDIR /app/connectomemapper3

# Copy contents of this repository.
COPY . /app/connectomemapper3

# Install cmp and cmtklib packages in the conda environment $CONDA_ENV
# ENV CONDA_ENV py37cmp-core
# RUN apt-get -qq -y install libtiff5-dev=4.0.6-1ubuntu0.4 libssl-dev=1.0.2g-1ubuntu4.13
RUN /bin/bash -c ". activate ${CONDA_ENV} && pip install networkx==2.4 &&\
    python setup.py install"

# Environmment setup
ENV ANTSPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PYTHONPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PATH $ANTSPATH:$PATH
ENV LD_LIBRARY_PATH /opt/conda/envs/$CONDA_ENV/lib:$LD_LIBRARY_PATH

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
# Set the working directory back to /app
# Acquire script to be executed
##################################################################
RUN chmod 775 /app/connectomemapper3/run.py
RUN chmod 775 /app/run_cmp3.sh
RUN chmod 775 /app/run_coverage_cmp3.sh
RUN chmod 777 /opt/freesurfer

##################################################################
# Temporary tmp folder
##################################################################
RUN /bin/bash -c "mkdir -p /var/tmp"
ENV TMPDIR /var/tmp
ENV TMP /var/tmp
ENV TEMP /var/tmp

##################################################################
# Create input and output directories for BIDS App
##################################################################
RUN mkdir /bids_dir && \
    chmod -R 777 /bids_dir

RUN mkdir /output_dir && \
    chmod -R 777 /output_dir

##################################################################
# Define Freesurfer license
##################################################################
ENV FS_LICENSE /bids_dir/code/license.txt

##################################################################
# Set locale settings
##################################################################
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

##################################################################
# Control random number generation
##################################################################
# Control MRTrix random number generation (RDG) for replicatable probabilistic tractography
# See https://community.mrtrix.org/t/random-number-generator/2063 for more details
ENV MRTRIX_RNG_SEED 1234

# Control ANTs random number generation (RDG) and multithreading
# See https://github.com/ANTsX/ANTs/wiki/antsRegistration-reproducibility-issues for more details
ENV ANTS_RANDOM_SEED 1234
# ENV ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS

##################################################################
# Run ldconfig for compatibility with Singularity
##################################################################
RUN ldconfig

##################################################################
# Show all environment variables
##################################################################
RUN export
RUN df -h
RUN du -xm ~/ | sort -rn

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
